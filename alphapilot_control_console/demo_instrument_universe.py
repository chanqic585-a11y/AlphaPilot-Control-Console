"""Authenticated/public OKX Demo USDT perpetual universe intersection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Literal

from .config import DATA_DIR
from .demo_instrument_identity import canonicalize_demo_instrument
from .demo_instrument_universe_store import DemoInstrumentUniverseStore
from .okx_market_universe import fetch_okx_usdt_swap_universe


DEMO_UNIVERSE_STORE_PATH = DATA_DIR / "demo_instrument_universe.sqlite"


def _hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DemoUniversePolicy:
    environment: Literal["demo"]
    cacheTtlSeconds: int = 300
    staleAfterSeconds: int = 900
    maximumIncludedSample: int = 10
    maximumExcludedSample: int = 10

    def __post_init__(self) -> None:
        if self.environment != "demo":
            raise ValueError("Demo universe policy must use environment='demo'")
        if self.cacheTtlSeconds <= 0 or self.staleAfterSeconds < self.cacheTtlSeconds:
            raise ValueError("Demo universe cache policy is invalid")
        if self.maximumIncludedSample < 0 or self.maximumExcludedSample < 0:
            raise ValueError("Demo universe samples must be bounded")


def _blocked(*, blocker: str, policy: DemoUniversePolicy, now: datetime, public_count: int = 0) -> dict[str, Any]:
    return {
        "status": "blocked",
        "environment": policy.environment,
        "publicUniverseCount": public_count,
        "demoAccountInstrumentCount": 0,
        "intersectionCount": 0,
        "liquidityEligibleCount": 0,
        "excludedNotInDemoAccount": 0,
        "excludedUnavailableState": 0,
        "excludedDataMissing": 0,
        "excludedLiquidity": 0,
        "generatedAt": now.isoformat(),
        "cacheAgeSeconds": 0.0,
        "cacheTtlSeconds": policy.cacheTtlSeconds,
        "stale": False,
        "cached": False,
        "includedSample": [],
        "excludedSample": [],
        "eligibleInstrumentIds": [],
        "publicManifestHash": _hash([]),
        "authenticatedInstrumentHash": _hash([]),
        "blockers": [blocker],
        "rawPrivatePayloadStored": False,
    }


def build_demo_instrument_universe(
    *,
    publicUniverse: dict[str, Any],
    accountInstrumentsResponse: dict[str, Any],
    policy: DemoUniversePolicy,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or datetime.now(UTC)
    public_rows = publicUniverse.get("screeningPool")
    public_rows = public_rows if isinstance(public_rows, list) else []
    public_ids: list[str] = []
    public_missing = 0
    for row in public_rows:
        try:
            public_value = row.get("instId") if isinstance(row, dict) else row
            identity = canonicalize_demo_instrument(str(public_value or ""))
        except (TypeError, ValueError):
            public_missing += 1
            continue
        if identity.instId not in public_ids:
            public_ids.append(identity.instId)
    public_hash = str(publicUniverse.get("manifestHash") or _hash(public_ids))
    if str(accountInstrumentsResponse.get("code")) != "0":
        result = _blocked(
            blocker="demo_account_instruments_read_failed",
            policy=policy,
            now=current,
            public_count=len(public_ids),
        )
        result["publicManifestHash"] = public_hash
        return result
    raw_private_rows = accountInstrumentsResponse.get("data")
    if not isinstance(raw_private_rows, list) or not raw_private_rows:
        result = _blocked(
            blocker="demo_account_instruments_empty",
            policy=policy,
            now=current,
            public_count=len(public_ids),
        )
        result["publicManifestHash"] = public_hash
        return result

    private_states: dict[str, str] = {}
    private_missing = 0
    for row in raw_private_rows:
        if not isinstance(row, dict):
            private_missing += 1
            continue
        try:
            identity = canonicalize_demo_instrument(row)
        except (TypeError, ValueError):
            private_missing += 1
            continue
        state = str(row.get("state") or "").strip().lower()
        if not state:
            private_missing += 1
            continue
        previous = private_states.get(identity.instId)
        if previous != "live":
            private_states[identity.instId] = state

    authenticated_hash = _hash(sorted(private_states.items()))
    if not private_states:
        result = _blocked(
            blocker="demo_account_instruments_malformed",
            policy=policy,
            now=current,
            public_count=len(public_ids),
        )
        result["publicManifestHash"] = public_hash
        result["authenticatedInstrumentHash"] = authenticated_hash
        result["excludedDataMissing"] = private_missing
        return result

    eligible: list[str] = []
    excluded: list[dict[str, str]] = []
    excluded_not_demo = 0
    excluded_unavailable = 0
    for inst_id in public_ids:
        state = private_states.get(inst_id)
        if state is None:
            excluded_not_demo += 1
            excluded.append({"instId": inst_id, "reason": "not_in_demo_account"})
        elif state != "live":
            excluded_unavailable += 1
            excluded.append({"instId": inst_id, "reason": "demo_instrument_unavailable"})
        else:
            eligible.append(inst_id)

    liquidity_rejections = [
        row
        for row in (publicUniverse.get("rejections") or [])
        if isinstance(row, dict)
        and str(row.get("reason") or "") in {
            "ticker_missing",
            "price_invalid",
            "volume_invalid",
            "spread_invalid",
            "spread_too_wide",
        }
    ]
    excluded.extend(
        {
            "instId": str(row.get("instId") or "--"),
            "reason": str(row.get("reason") or "liquidity_rejected"),
        }
        for row in liquidity_rejections
    )
    stale = False
    generated_at = current.isoformat()
    status = "usable" if eligible else "blocked"
    blockers = [] if eligible else ["demo_public_intersection_empty"]
    return {
        "status": status,
        "environment": policy.environment,
        "publicUniverseCount": len(public_ids),
        "demoAccountInstrumentCount": len(private_states),
        "intersectionCount": len(eligible),
        "liquidityEligibleCount": len(eligible),
        "excludedNotInDemoAccount": excluded_not_demo,
        "excludedUnavailableState": excluded_unavailable,
        "excludedDataMissing": private_missing + public_missing,
        "excludedLiquidity": len(liquidity_rejections),
        "generatedAt": generated_at,
        "cacheAgeSeconds": 0.0,
        "cacheTtlSeconds": policy.cacheTtlSeconds,
        "stale": stale,
        "cached": False,
        "includedSample": eligible[: policy.maximumIncludedSample],
        "excludedSample": excluded[: policy.maximumExcludedSample],
        "eligibleInstrumentIds": eligible,
        "publicManifestHash": public_hash,
        "authenticatedInstrumentHash": authenticated_hash,
        "blockers": blockers,
        "rawPrivatePayloadStored": False,
    }


def load_or_refresh_demo_instrument_universe(
    client: Any,
    *,
    fresh: bool = False,
    policy: DemoUniversePolicy | None = None,
    publicUniverseLoader: Callable[[], dict[str, Any]] = fetch_okx_usdt_swap_universe,
    storePath: Path | str = DEMO_UNIVERSE_STORE_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    active_policy = policy or DemoUniversePolicy(environment="demo")
    current = now or datetime.now(UTC)
    store = DemoInstrumentUniverseStore(storePath)
    try:
        if not fresh:
            cached = store.load_latest(environment="demo", now=current)
            if cached is not None:
                return cached
        try:
            public_universe = publicUniverseLoader()
            private_response = client.get_account_instruments("SWAP")
        except Exception:
            return _blocked(
                blocker="demo_account_instruments_unavailable",
                policy=active_policy,
                now=current,
            )
        result = build_demo_instrument_universe(
            publicUniverse=public_universe,
            accountInstrumentsResponse=private_response,
            policy=active_policy,
            now=current,
        )
        if result["status"] == "usable":
            store.save(result)
        return result
    finally:
        store.close()
