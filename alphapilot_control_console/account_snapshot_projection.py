"""Sanitize private account reads into the minimal terminal snapshot."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping, Sequence


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_number(mapping: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _float_or_none(mapping.get(key))
        if value is not None:
            return value
    return None


def _position_side(row: Mapping[str, Any], quantity: float) -> str:
    side = str(row.get("posSide") or "").lower()
    if side in {"long", "short"}:
        return side
    return "short" if quantity < 0 else "long"


def _strategy_identity(
    instrument_id: str,
    strategy_ids_by_instrument: Mapping[str, Sequence[str]],
) -> tuple[str | None, list[str]]:
    strategy_ids = sorted({str(value) for value in strategy_ids_by_instrument.get(instrument_id, ()) if value})
    return (strategy_ids[0] if len(strategy_ids) == 1 else None), strategy_ids


def build_sanitized_account_snapshot(
    *,
    balance_response: Mapping[str, Any],
    positions_response: Mapping[str, Any],
    strategy_ids_by_instrument: Mapping[str, Sequence[str]] | None = None,
    updated_at: str | None = None,
    today_realized_pnl_usdt: float | None = None,
) -> dict[str, Any]:
    """Return a whitelist-only account snapshot suitable for local persistence."""

    if str(balance_response.get("code") or "") != "0":
        raise ValueError("account_balance_response_not_successful")
    if str(positions_response.get("code") or "") != "0":
        raise ValueError("account_positions_response_not_successful")

    balance_rows = balance_response.get("data")
    balance_rows = balance_rows if isinstance(balance_rows, list) else []
    account_row = balance_rows[0] if balance_rows and isinstance(balance_rows[0], dict) else {}
    details = account_row.get("details")
    details = details if isinstance(details, list) else []
    usdt_row = next(
        (row for row in details if isinstance(row, dict) and str(row.get("ccy")) == "USDT"),
        {},
    )

    available = _first_number(usdt_row, "availEq", "availBal")
    if available is None:
        available = _first_number(account_row, "availEq", "availBal") or 0.0
    account_equity = _first_number(usdt_row, "eq")
    if account_equity is None:
        account_equity = _first_number(account_row, "totalEq", "adjEq")
    if account_equity is None:
        account_equity = available

    attribution = strategy_ids_by_instrument or {}
    raw_position_rows = positions_response.get("data")
    raw_position_rows = raw_position_rows if isinstance(raw_position_rows, list) else []
    positions: list[dict[str, Any]] = []
    for raw_row in raw_position_rows:
        if not isinstance(raw_row, dict):
            continue
        signed_quantity = _float_or_none(raw_row.get("pos")) or 0.0
        if abs(signed_quantity) == 0:
            continue
        instrument_id = str(raw_row.get("instId") or "")
        strategy_id, strategy_ids = _strategy_identity(instrument_id, attribution)
        position = {
            "strategyId": strategy_id,
            "strategyIds": strategy_ids,
            "instrumentId": instrument_id,
            "side": _position_side(raw_row, signed_quantity),
            "quantity": abs(signed_quantity),
            "entryPrice": _first_number(raw_row, "avgPx", "openAvgPx"),
            "markPrice": _first_number(raw_row, "markPx", "last"),
            "unrealizedPnlUsdt": _first_number(raw_row, "upl") or 0.0,
            "leverage": _first_number(raw_row, "lever"),
            "marginMode": str(raw_row.get("mgnMode") or "") or None,
            "liquidationPrice": _first_number(raw_row, "liqPx"),
            "updatedAtExchangeMs": str(raw_row.get("uTime") or "") or None,
        }
        positions.append(position)

    return {
        "status": "available",
        "accountEquityUsdt": account_equity,
        "availableEquityUsdt": available,
        "availableBalanceUsdt": available,
        "todayRealizedPnlUsdt": today_realized_pnl_usdt,
        "floatingPnlUsdt": sum(float(position["unrealizedPnlUsdt"]) for position in positions),
        "openPositionCount": len(positions),
        "positions": positions,
        "updatedAt": updated_at or datetime.now(UTC).isoformat(),
        "source": "sanitized_private_account_read",
        "rawExchangePayloadExcluded": True,
    }
