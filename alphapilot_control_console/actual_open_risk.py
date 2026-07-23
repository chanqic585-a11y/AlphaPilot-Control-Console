"""Conservative reconciliation of intended risk and actual exchange positions."""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping


_ACTIVE_RECORD_STATUSES = {
    "prepared",
    "submitted",
    "live",
    "partially_filled",
    "filled",
    "unknown",
}


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    result: dict[str, Any] = {}
    for key in ("instrumentId", "status", "signal"):
        if hasattr(value, key):
            result[key] = getattr(value, key)
    return result


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _record_risk(record: Mapping[str, Any]) -> float | None:
    signal = record.get("signal") if isinstance(record.get("signal"), Mapping) else {}
    explicit = _number(signal.get("riskUsdt"))
    if explicit is not None and explicit >= 0:
        return explicit
    quantity = _number(signal.get("quantity") or signal.get("sz"))
    entry = _number(signal.get("entryPrice"))
    stop = _number(signal.get("stopLossPrice"))
    if quantity is None or entry is None or stop is None:
        return None
    return abs(quantity) * abs(entry - stop)


def _position_risk(
    position: Mapping[str, Any],
    records: list[Mapping[str, Any]],
) -> float | None:
    quantity = _number(position.get("quantity") or position.get("pos"))
    entry = _number(position.get("entryPrice") or position.get("avgPx"))
    if quantity is None or entry is None:
        return None
    stop: float | None = None
    for record in records:
        signal = record.get("signal") if isinstance(record.get("signal"), Mapping) else {}
        stop = _number(signal.get("stopLossPrice"))
        if stop is not None:
            break
    if stop is None:
        return None
    return abs(quantity) * abs(entry - stop)


def _has_exchange_protection(instrument_id: str, orders: Iterable[Mapping[str, Any]]) -> bool:
    for order in orders:
        if str(order.get("instId") or order.get("instrumentId") or "") != instrument_id:
            continue
        reduce_only = str(order.get("reduceOnly") or "").lower() in {"true", "1"}
        has_stop = any(
            str(order.get(key) or "").strip()
            for key in ("slTriggerPx", "slOrdPx", "stopLossPrice", "triggerPx")
        )
        if reduce_only and has_stop:
            return True
    return False


def build_actual_open_risk(
    *,
    positions: Iterable[Mapping[str, Any]],
    records: Iterable[Any],
    open_orders: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    active_records = [
        _mapping(record)
        for record in records
        if str(_mapping(record).get("status") or "") in _ACTIVE_RECORD_STATUSES
    ]
    order_rows = [dict(order) for order in open_orders if isinstance(order, Mapping)]
    expected_values = [risk for risk in (_record_risk(record) for record in active_records) if risk is not None]

    exchange_values: list[float] = []
    protected_values: list[float] = []
    unprotected_values: list[float] = []
    exchange_unknown = 0
    unprotected_unknown = 0
    unknown_protection_count = 0
    position_count = 0
    for raw_position in positions:
        position = dict(raw_position)
        instrument_id = str(position.get("instrumentId") or position.get("instId") or "")
        quantity = _number(position.get("quantity") or position.get("pos")) or 0.0
        if not instrument_id or abs(quantity) <= 0:
            continue
        position_count += 1
        matching_records = [
            record
            for record in active_records
            if str(record.get("instrumentId") or "") == instrument_id
        ]
        risk = _position_risk(position, matching_records)
        protected = _has_exchange_protection(instrument_id, order_rows)
        if risk is None:
            exchange_unknown += 1
        else:
            exchange_values.append(risk)
        if protected:
            if risk is not None:
                protected_values.append(risk)
        else:
            unknown_protection_count += 1
            if risk is None:
                unprotected_unknown += 1
            else:
                unprotected_values.append(risk)

    complete = exchange_unknown == 0 and unknown_protection_count == 0
    return {
        "schemaVersion": "alphapilot_actual_open_risk_v1",
        "expectedOpenRisk": round(sum(expected_values), 8),
        "exchangePositionRisk": None if exchange_unknown else round(sum(exchange_values), 8),
        "protectedOpenRisk": round(sum(protected_values), 8),
        "unprotectedPositionRisk": (
            None if unprotected_unknown else round(sum(unprotected_values), 8)
        ),
        "unknownProtectionCount": unknown_protection_count,
        "exchangePositionCount": position_count,
        "complete": complete,
        "newEntriesAllowed": complete,
        "route": "actual_open_risk_verified" if complete else "actual_open_risk_unverified",
    }
