"""Select a bounded Live smoke instrument and execute the approved lifecycle."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_UP
from pathlib import Path
from typing import Any, Iterable, Mapping

from .exchange_connectors.okx_live_client import OkxLiveClient
from .exchange_connectors.public_exchange_registry import fetch_okx_public_payload
from .live_engineering_smoke_service import run_live_engineering_smoke


_MAJOR_PREFERENCE = (
    "ETH-USDT-SWAP",
    "SOL-USDT-SWAP",
    "XRP-USDT-SWAP",
    "DOGE-USDT-SWAP",
    "BTC-USDT-SWAP",
)


def _positive_decimal(value: Any) -> Decimal | None:
    try:
        result = Decimal(str(value))
    except Exception:
        return None
    return result if result.is_finite() and result > 0 else None


def _minimum_notional(instrument: Mapping[str, Any], quote: Mapping[str, Any]) -> Decimal | None:
    bid = _positive_decimal(quote.get("bidPx"))
    lot = _positive_decimal(instrument.get("lotSz"))
    minimum = _positive_decimal(instrument.get("minSz"))
    contract_value = _positive_decimal(instrument.get("ctVal"))
    if None in {bid, lot, minimum, contract_value}:
        return None
    assert bid is not None and lot is not None and minimum is not None and contract_value is not None
    size = (minimum / lot).to_integral_value(rounding=ROUND_UP) * lot
    return bid * Decimal("0.9") * size * contract_value


def select_live_smoke_instrument(
    account_instruments: Iterable[Mapping[str, Any]],
    tickers: Iterable[Mapping[str, Any]],
    *,
    maximum_notional_usdt: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Choose one liquid major that the account can trade within the frozen cap."""

    maximum = Decimal(str(maximum_notional_usdt))
    ticker_by_id = {
        str(row.get("instId") or ""): dict(row)
        for row in tickers
        if isinstance(row, Mapping)
    }
    eligible: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for row in account_instruments:
        instrument = dict(row)
        instrument_id = str(instrument.get("instId") or "")
        if (
            not instrument_id.endswith("-USDT-SWAP")
            or str(instrument.get("state") or "").lower() != "live"
            or str(instrument.get("ctType") or "").lower() != "linear"
            or str(instrument.get("settleCcy") or "").upper() != "USDT"
        ):
            continue
        quote = ticker_by_id.get(instrument_id)
        notional = _minimum_notional(instrument, quote or {})
        if quote is not None and notional is not None and notional <= maximum:
            eligible[instrument_id] = (instrument, quote)
    for instrument_id in _MAJOR_PREFERENCE:
        if instrument_id in eligible:
            return eligible[instrument_id]
    raise RuntimeError("No eligible major OKX USDT swap fits the approved Live smoke cap")


def _payload_rows(response: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    if str(response.get("code") or "") != "0":
        raise RuntimeError(f"OKX Live {name} failed")
    data = response.get("data")
    if not isinstance(data, list):
        raise RuntimeError(f"OKX Live {name} returned invalid data")
    return [dict(row) for row in data if isinstance(row, Mapping)]


def _public_tickers() -> list[dict[str, Any]]:
    response = fetch_okx_public_payload(
        "/api/v5/market/tickers",
        {"instType": "SWAP"},
    )
    if not response.get("ok"):
        raise RuntimeError("OKX public ticker preflight failed")
    payload = response.get("payload")
    if not isinstance(payload, Mapping):
        raise RuntimeError("OKX public ticker payload is invalid")
    return _payload_rows(payload, "public tickers")


def _public_instruments() -> list[dict[str, Any]]:
    response = fetch_okx_public_payload(
        "/api/v5/public/instruments",
        {"instType": "SWAP"},
    )
    if not response.get("ok"):
        raise RuntimeError("OKX public instrument preflight failed")
    payload = response.get("payload")
    if not isinstance(payload, Mapping):
        raise RuntimeError("OKX public instrument payload is invalid")
    return _payload_rows(payload, "public instruments")


def run_approved_live_engineering_smoke(
    *,
    client: OkxLiveClient,
    contract: Mapping[str, Any],
    approval: Mapping[str, Any],
    result_path: Path,
    attempt_path: Path,
) -> dict[str, Any]:
    account_instruments = _payload_rows(
        client.get_account_instruments("SWAP"),
        "account instruments",
    )
    account_instrument_ids = {
        str(row.get("instId") or "")
        for row in account_instruments
        if str(row.get("instId") or "").endswith("-USDT-SWAP")
    }
    public_instruments = [
        row
        for row in _public_instruments()
        if str(row.get("instId") or "") in account_instrument_ids
    ]
    instrument, quote = select_live_smoke_instrument(
        public_instruments,
        _public_tickers(),
        maximum_notional_usdt=float(contract["maximumNotionalUsdt"]),
    )
    return run_live_engineering_smoke(
        client=client,
        contract=contract,
        approval=approval,
        instrument=instrument,
        quote=quote,
        output_path=result_path,
        attempt_path=attempt_path,
    )


def build_artifact_manifest(root: Path, *, generated_at: str, status: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        if path.name == "artifact_manifest.json":
            continue
        rows.append(
            {
                "path": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "sizeBytes": path.stat().st_size,
            }
        )
    return {
        "schemaVersion": "alphapilot_v58_live_engineering_smoke_manifest_v2",
        "generatedAt": generated_at,
        "status": status,
        "artifactCount": len(rows),
        "artifacts": rows,
        "rawCredentialsPersisted": False,
        "privateAccountValuesPersisted": False,
        "withdrawAllowed": False,
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)
