"""Read-only OKX Demo pre-ARM audit for an exact provisional release."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Protocol

from .credential_runtime import load_okx_demo_credentials
from .demo_credential_bootstrap import bootstrap_demo_credentials
from .exchange_connectors.okx_demo_client import OkxDemoClient
from .strategy_validation_hashing import stable_hash


TARGET_INSTRUMENTS = (
    "BTC-USDT-SWAP",
    "DOGE-USDT-SWAP",
    "ETH-USDT-SWAP",
    "SOL-USDT-SWAP",
    "XRP-USDT-SWAP",
)


class ReadOnlyDemoClient(Protocol):
    site: str
    base_url: str

    def synchronize_server_time(self) -> dict[str, Any]: ...

    def get_account_config(self) -> dict[str, Any]: ...

    def get_account_instruments(self, instrumentType: str = "SWAP") -> dict[str, Any]: ...

    def get_balance(self, currency: str = "USDT") -> dict[str, Any]: ...

    def get_positions(
        self, instrumentId: str | None = None, instrumentType: str | None = None
    ) -> dict[str, Any]: ...

    def get_open_orders(self, instrumentId: str | None = None) -> dict[str, Any]: ...

    def get_fills(
        self, instrumentId: str | None = None, limit: int = 100
    ) -> dict[str, Any]: ...


def _rows(response: dict[str, Any], endpoint: str) -> list[dict[str, Any]]:
    if str(response.get("code") or "") != "0":
        raise RuntimeError(f"okx_private_read_failed:{endpoint}:{response.get('code')}")
    rows = response.get("data")
    if not isinstance(rows, list):
        raise RuntimeError(f"okx_private_read_invalid:{endpoint}")
    return [dict(row) for row in rows if isinstance(row, dict)]


def _normalized(values: Iterable[str]) -> list[str]:
    return sorted({str(value).strip().upper() for value in values if str(value).strip()})


def build_private_read_audit(
    client: ReadOnlyDemoClient,
    *,
    expected_instruments: Iterable[str],
    expected_intersection_hash: str,
    generated_at: str,
) -> dict[str, Any]:
    expected = _normalized(expected_instruments)
    time_sync = client.synchronize_server_time()
    config_rows = _rows(client.get_account_config(), "account_config")
    instrument_rows = _rows(
        client.get_account_instruments(instrumentType="SWAP"), "account_instruments"
    )
    balance_rows = _rows(client.get_balance(currency="USDT"), "balance")
    position_rows = _rows(
        client.get_positions(instrumentType="SWAP"), "positions"
    )
    pending_rows = _rows(client.get_open_orders(), "pending_orders")
    fill_rows = _rows(client.get_fills(limit=100), "recent_fills")

    instruments = {
        str(row.get("instId") or "").strip().upper(): row
        for row in instrument_rows
        if str(row.get("instId") or "").strip()
    }
    checks = []
    for instrument_id in expected:
        row = instruments.get(instrument_id) or {}
        checks.append(
            {
                "instrumentId": instrument_id,
                "present": bool(row),
                "instrumentType": str(row.get("instType") or ""),
                "settleCurrency": str(row.get("settleCcy") or ""),
                "state": str(row.get("state") or ""),
                "tradable": bool(row)
                and str(row.get("instType") or "").upper() == "SWAP"
                and str(row.get("settleCcy") or "").upper() == "USDT"
                and str(row.get("state") or "").lower() == "live",
            }
        )
    verified = [row["instrumentId"] for row in checks if row["tradable"]]
    computed_hash = stable_hash(verified, "demo_execution_intersection")
    account_identity = {
        key: config_rows[0].get(key)
        for key in ("uid", "mainUid", "acctLv", "posMode", "acctStpMode", "roleType")
        if config_rows and config_rows[0].get(key) not in (None, "")
    }
    intersection_matches = computed_hash == str(expected_intersection_hash)
    all_tradable = verified == expected
    private_verified = all_tradable and intersection_matches
    return {
        "schemaVersion": "provisional_demo_pre_arm_private_read_audit_v1",
        "generatedAt": generated_at,
        "status": "verified" if private_verified else "blocked_execution_universe_mismatch",
        "environment": "okx_demo",
        "accountSite": str(client.site),
        "demoHeaderRequired": True,
        "serverTimeRead": {
            "status": "verified",
            "roundTripMilliseconds": int(time_sync.get("roundTripMilliseconds") or 0),
            "offsetMilliseconds": int(time_sync.get("offsetMilliseconds") or 0),
        },
        "accountConfigRead": {
            "status": "verified",
            "rowCount": len(config_rows),
            "accountIdentityHash": stable_hash(account_identity, "demo_account_identity"),
        },
        "instrumentRead": {"status": "verified", "rowCount": len(instrument_rows)},
        "balanceRead": {"status": "verified", "rowCount": len(balance_rows)},
        "positionRead": {"status": "verified", "rowCount": len(position_rows)},
        "pendingOrderRead": {"status": "verified", "rowCount": len(pending_rows)},
        "recentFillRead": {"status": "verified", "rowCount": len(fill_rows)},
        "expectedInstruments": expected,
        "verifiedInstruments": verified,
        "verifiedInstrumentCount": len(verified),
        "instrumentChecks": checks,
        "expectedExecutionIntersectionHash": str(expected_intersection_hash),
        "observedExecutionIntersectionHash": computed_hash,
        "executionIntersectionHashMatches": intersection_matches,
        "privateReadVerified": private_verified,
        "networkRequestMade": True,
        "readOnly": True,
        "orderRequestMade": False,
        "credentialsRetained": False,
        "signatureHeadersRetained": False,
        "rawResponsesRetained": False,
        "live": False,
        "withdraw": False,
    }


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the V46 read-only OKX Demo pre-ARM audit.")
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generated-at")
    args = parser.parse_args(argv)
    generated_at = args.generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    release = json.loads(args.release.read_text(encoding="utf-8"))

    bootstrap = bootstrap_demo_credentials()
    if not bootstrap.get("ok"):
        audit = {
            "schemaVersion": "provisional_demo_pre_arm_private_read_audit_v1",
            "generatedAt": generated_at,
            "status": "blocked_demo_credentials_unavailable",
            "privateReadVerified": False,
            "networkRequestMade": False,
            "readOnly": True,
            "orderRequestMade": False,
            "credentialsRetained": False,
            "signatureHeadersRetained": False,
            "rawResponsesRetained": False,
            "blocker": str(bootstrap.get("category") or "credential_unavailable"),
            "live": False,
            "withdraw": False,
        }
        _write(args.output, audit)
        return 2

    client = OkxDemoClient(load_okx_demo_credentials(), site="global")
    try:
        audit = build_private_read_audit(
            client,
            expected_instruments=release.get("executionInstruments") or TARGET_INSTRUMENTS,
            expected_intersection_hash=str(release.get("executionIntersectionHash") or ""),
            generated_at=generated_at,
        )
    except (PermissionError, RuntimeError, TypeError, ValueError) as error:
        audit = {
            "schemaVersion": "provisional_demo_pre_arm_private_read_audit_v1",
            "generatedAt": generated_at,
            "status": "blocked_private_read_failed",
            "privateReadVerified": False,
            "networkRequestMade": True,
            "readOnly": True,
            "orderRequestMade": False,
            "credentialsRetained": False,
            "signatureHeadersRetained": False,
            "rawResponsesRetained": False,
            "blocker": type(error).__name__,
            "live": False,
            "withdraw": False,
        }
    _write(args.output, audit)
    return 0 if audit.get("privateReadVerified") else 2


if __name__ == "__main__":
    raise SystemExit(main())
