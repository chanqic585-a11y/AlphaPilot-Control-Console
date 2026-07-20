"""Causal, daily-frozen OKX Demo TOP200 universe contracts."""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from .demo_instrument_identity import canonicalize_demo_instrument


POLICY_ID = "okx_demo_top200_liquid_usdt_swap_forward_v1"
MAXIMUM_INSTRUMENT_COUNT = 200
RANKING_WINDOW_COMPLETE_UTC_DAYS = 30
QUOTE_TURNOVER_SOURCE = "okx_completed_1Dutc_volCcyQuote"


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _stable_hash(value: Any, *, prefix: str) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()}"


def _rows(value: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _instrument_id(row: Mapping[str, Any]) -> str:
    try:
        return canonicalize_demo_instrument(dict(row)).instId
    except (TypeError, ValueError):
        return ""


def build_dynamic_top200_policy() -> dict[str, Any]:
    core = {
        "schemaVersion": "okx_demo_top200_universe_policy_v1",
        "policyId": POLICY_ID,
        "purpose": "provisional_forward_collection",
        "maximumInstrumentCount": MAXIMUM_INSTRUMENT_COUNT,
        "refreshCadence": "daily_frozen_snapshot",
        "instrumentType": "SWAP",
        "settleCurrency": "USDT",
        "assetClass": "crypto_native",
        "rankingMetric": "medianDailyQuoteTurnover",
        "rankingWindowCompleteUtcDays": RANKING_WINDOW_COMPLETE_UTC_DAYS,
        "quoteTurnoverSource": QUOTE_TURNOVER_SOURCE,
        "rankingDirection": "descending",
        "tieBreak": "canonical_instrument_id_ascending",
        "resultBasedSelectionAllowed": False,
        "historicalBacktestMutationAllowed": False,
        "eligibleIntersection": [
            "okx_public_live_usdt_swap",
            "authenticated_demo_account_instrument",
            "runtime_market_data_ready",
            "component_lookback_ready",
            "exact_quote_turnover_ready",
            "capacity_ready",
            "instrument_constraints_ready",
        ],
        "excludedAssetClasses": [
            "tokenized_equity",
            "stablecoin_fx_like",
            "unknown_asset_class",
        ],
    }
    return {**core, "policyHash": _stable_hash(core, prefix="top200_universe_policy")}


def _snapshot_identity(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": snapshot.get("schemaVersion"),
        "utcDate": snapshot.get("utcDate"),
        "policyId": snapshot.get("policyId"),
        "policyHash": snapshot.get("policyHash"),
        "maximumInstrumentCount": snapshot.get("maximumInstrumentCount"),
        "actualInstrumentCount": snapshot.get("actualInstrumentCount"),
        "instrumentIds": list(snapshot.get("instrumentIds") or []),
        "rankedInstruments": list(snapshot.get("rankedInstruments") or []),
        "status": snapshot.get("status"),
    }


def _validate_snapshot_hash(snapshot: Mapping[str, Any]) -> None:
    expected = _stable_hash(
        _snapshot_identity(snapshot), prefix="demo_top200_universe_snapshot"
    )
    if snapshot.get("snapshotHash") != expected:
        raise ValueError("snapshot_hash_mismatch")


def _public_eligibility(row: Mapping[str, Any]) -> str | None:
    if str(row.get("instType") or "").upper() != "SWAP":
        return "invalid_instrument_identity"
    if str(row.get("settleCcy") or "").upper() != "USDT":
        return "invalid_instrument_identity"
    if str(row.get("ctType") or "").lower() != "linear":
        return "invalid_instrument_identity"
    if str(row.get("state") or "").lower() != "live":
        return "state_not_live"
    if not _instrument_id(row):
        return "invalid_instrument_identity"
    return None


def _numbers(values: Any) -> list[float]:
    if not isinstance(values, list):
        return []
    result: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return []
        if number < 0:
            return []
        result.append(number)
    return result


def build_dynamic_top200_snapshot(
    *,
    public_instruments: Iterable[Mapping[str, Any]],
    authenticated_instruments: Iterable[Mapping[str, Any]],
    market_readiness: Iterable[Mapping[str, Any]],
    utc_date: str,
    generated_at: str,
    maximum_instrument_count: int = MAXIMUM_INSTRUMENT_COUNT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a result-independent TOP200 snapshot and its readiness audit."""

    policy = build_dynamic_top200_policy()
    maximum = min(MAXIMUM_INSTRUMENT_COUNT, max(1, int(maximum_instrument_count)))
    public_rows = _rows(public_instruments)
    authenticated_rows = _rows(authenticated_instruments)
    market_rows = _rows(market_readiness)
    authenticated_by_id = {
        inst_id: row
        for row in authenticated_rows
        if (inst_id := _instrument_id(row))
    }
    market_by_id = {
        str(row.get("instId") or "").strip().upper(): row
        for row in market_rows
        if str(row.get("instId") or "").strip()
    }
    rejection_counts: Counter[str] = Counter()
    rejections: list[dict[str, str]] = []
    eligible: list[dict[str, Any]] = []

    def reject(inst_id: str, reason: str) -> None:
        rejection_counts[reason] += 1
        rejections.append({"instId": inst_id or "--", "reason": reason})

    for public_row in public_rows:
        raw_id = str(public_row.get("instId") or "").strip().upper()
        public_blocker = _public_eligibility(public_row)
        if public_blocker:
            reject(raw_id, public_blocker)
            continue
        inst_id = _instrument_id(public_row)
        authenticated = authenticated_by_id.get(inst_id)
        if authenticated is None:
            reject(inst_id, "authenticated_demo_instrument_missing")
            continue
        market = market_by_id.get(inst_id)
        if market is None:
            reject(inst_id, "history_not_ready")
            continue
        if str(market.get("assetClass") or "unknown_asset_class") != "crypto_native":
            reject(inst_id, "asset_class_not_crypto_native")
            continue
        if market.get("runtimeMarketDataReady") is not True:
            reject(inst_id, "stale_market_data")
            continue
        if market.get("componentLookbackReady") is not True:
            reject(inst_id, "history_not_ready")
            continue
        if str(market.get("quoteTurnoverSource") or "") != QUOTE_TURNOVER_SOURCE:
            reject(inst_id, "exact_quote_turnover_unavailable")
            continue
        turnover = _numbers(market.get("completedDailyQuoteTurnover"))
        if len(turnover) < RANKING_WINDOW_COMPLETE_UTC_DAYS:
            reject(inst_id, "history_not_ready")
            continue
        if market.get("capacityReady") is not True:
            reject(inst_id, "capacity_unavailable")
            continue
        constraints = {
            key: str(authenticated.get(key) or public_row.get(key) or "")
            for key in ("tickSz", "lotSz", "minSz")
        }
        if any(not value for value in constraints.values()):
            reject(inst_id, "instrument_constraints_unavailable")
            continue
        median_turnover = float(
            statistics.median(turnover[-RANKING_WINDOW_COMPLETE_UTC_DAYS:])
        )
        eligible.append(
            {
                "instId": inst_id,
                "medianDailyQuoteTurnover": median_turnover,
                "completeUtcDayCount": RANKING_WINDOW_COMPLETE_UTC_DAYS,
                "quoteTurnoverSource": QUOTE_TURNOVER_SOURCE,
                "tickSz": constraints["tickSz"],
                "lotSz": constraints["lotSz"],
                "minSz": constraints["minSz"],
                "assetClass": "crypto_native",
                "state": "live",
            }
        )

    eligible.sort(
        key=lambda row: (-float(row["medianDailyQuoteTurnover"]), str(row["instId"]))
    )
    selected = eligible[:maximum]
    status = "ready" if selected else "blocked_empty_universe"
    identity = {
        "schemaVersion": "okx_demo_top200_universe_snapshot_v1",
        "utcDate": str(utc_date),
        "policyId": policy["policyId"],
        "policyHash": policy["policyHash"],
        "maximumInstrumentCount": maximum,
        "actualInstrumentCount": len(selected),
        "instrumentIds": [row["instId"] for row in selected],
        "rankedInstruments": selected,
        "status": status,
    }
    snapshot = {
        **identity,
        "generatedAt": str(generated_at),
        "resultIndependent": True,
        "dailyFrozen": True,
        "snapshotHash": _stable_hash(
            identity, prefix="demo_top200_universe_snapshot"
        ),
    }
    audit = {
        "schemaVersion": "okx_demo_top200_universe_readiness_audit_v1",
        "generatedAt": str(generated_at),
        "utcDate": str(utc_date),
        "policyId": policy["policyId"],
        "policyHash": policy["policyHash"],
        "publicInstrumentCount": len(public_rows),
        "authenticatedInstrumentCount": len(authenticated_by_id),
        "marketReadinessCount": len(market_by_id),
        "eligibleBeforeLimitCount": len(eligible),
        "selectedCount": len(selected),
        "maximumInstrumentCount": maximum,
        "rejectionReasonCounts": dict(sorted(rejection_counts.items())),
        "rejections": rejections,
        "snapshotHash": snapshot["snapshotHash"],
        "status": status,
    }
    return snapshot, audit


def freeze_daily_top200_snapshot(
    snapshot_dir: Path | str,
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Write once per UTC day; an existing valid snapshot always wins."""

    _validate_snapshot_hash(snapshot)
    if snapshot.get("status") != "ready" or int(snapshot.get("actualInstrumentCount") or 0) < 1:
        raise ValueError("snapshot_not_ready")
    target_dir = Path(snapshot_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    utc_date = str(snapshot.get("utcDate") or "")
    matches = sorted(target_dir.glob(f"demo_top200_universe_snapshot_{utc_date}_*.json"))
    if len(matches) > 1:
        raise RuntimeError("multiple_daily_top200_snapshots")
    if matches:
        existing = json.loads(matches[0].read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            raise ValueError("daily_snapshot_invalid")
        _validate_snapshot_hash(existing)
        if existing.get("policyHash") != snapshot.get("policyHash"):
            raise ValueError("daily_snapshot_policy_mismatch")
        return {"reused": True, "path": str(matches[0]), "snapshot": existing}

    digest = str(snapshot["snapshotHash"]).rsplit("_", 1)[-1][:16]
    target = target_dir / f"demo_top200_universe_snapshot_{utc_date}_{digest}.json"
    target.write_text(
        json.dumps(dict(snapshot), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"reused": False, "path": str(target), "snapshot": dict(snapshot)}
