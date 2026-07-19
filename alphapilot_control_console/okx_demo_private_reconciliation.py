"""Reconcile low-latency OKX Demo private WS state against authoritative REST reads."""

from __future__ import annotations

import math
import threading
from typing import Any, Iterable, Mapping


def _rows(response: Any) -> list[dict[str, Any]]:
    if not isinstance(response, Mapping) or str(response.get("code") or "") != "0":
        return []
    data = response.get("data")
    return [dict(row) for row in data if isinstance(row, Mapping)] if isinstance(data, list) else []


def _nonzero(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and abs(number) > 0


class OkxDemoPrivateState:
    """In-memory private stream cache. It never persists credential material."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._orders: dict[str, dict[str, Any]] = {}
        self._positions: dict[str, dict[str, Any]] = {}
        self._account: dict[str, dict[str, Any]] = {}

    def apply(self, payload: Mapping[str, Any]) -> None:
        argument = payload.get("arg") if isinstance(payload.get("arg"), Mapping) else {}
        channel = str(argument.get("channel") or "")
        data = payload.get("data")
        rows = [dict(row) for row in data if isinstance(row, Mapping)] if isinstance(data, list) else []
        with self._lock:
            if channel == "orders":
                for row in rows:
                    identity = str(row.get("clOrdId") or row.get("ordId") or "")
                    if identity:
                        self._orders[identity] = row
            elif channel == "positions":
                for row in rows:
                    identity = str(row.get("instId") or "")
                    if identity:
                        self._positions[identity] = row
            elif channel == "account":
                for row in rows:
                    details = row.get("details") if isinstance(row.get("details"), list) else []
                    for detail in details:
                        if isinstance(detail, Mapping) and str(detail.get("ccy") or ""):
                            self._account[str(detail["ccy"])] = dict(detail)

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            return {
                "orders": [dict(row) for row in self._orders.values()],
                "positions": [dict(row) for row in self._positions.values()],
                "account": [dict(row) for row in self._account.values()],
            }


def reconcile_okx_demo_private_state(
    client: Any,
    *,
    ws_state: OkxDemoPrivateState,
    expected_client_order_ids: Iterable[str] = (),
    expected_position_instruments: Iterable[str] = (),
) -> dict[str, Any]:
    open_orders_response = client.get_open_orders()
    fills_response = client.get_fills(limit=100)
    positions_response = client.get_positions(instrumentType="SWAP")
    balance_response = client.get_balance("USDT")
    responses = (
        open_orders_response,
        fills_response,
        positions_response,
        balance_response,
    )
    response_ok = all(
        isinstance(response, Mapping) and str(response.get("code") or "") == "0"
        for response in responses
    )
    open_orders = _rows(open_orders_response)
    fills = _rows(fills_response)
    positions = [row for row in _rows(positions_response) if _nonzero(row.get("pos"))]
    expected_orders = {str(value) for value in expected_client_order_ids if str(value)}
    observed_orders = {
        str(row.get("clOrdId") or "")
        for row in (*open_orders, *fills)
        if str(row.get("clOrdId") or "")
    }
    expected_positions = {
        str(value) for value in expected_position_instruments if str(value)
    }
    observed_positions = {
        str(row.get("instId") or "") for row in positions if str(row.get("instId") or "")
    }
    unknown_orders = sorted(expected_orders - observed_orders)
    orphan_positions = sorted(observed_positions - expected_positions)
    ws_snapshot = ws_state.snapshot()
    partial_fill_observed = any(
        str(row.get("state") or "") in {"partially_filled", "partially-filled"}
        or (
            _nonzero(row.get("accFillSz"))
            and float(row.get("accFillSz") or 0) < float(row.get("sz") or 0)
        )
        for row in ws_snapshot["orders"]
    )
    blockers: list[str] = []
    if not response_ok:
        blockers.append("demo_private_rest_error")
    if unknown_orders:
        blockers.append("unresolved_demo_order_state")
    if orphan_positions:
        blockers.append("orphan_demo_position")
    return {
        "matched": not blockers,
        "restReadSucceeded": response_ok,
        "openOrderCount": len(open_orders),
        "fillCount": len(fills),
        "positionCount": len(positions),
        "unknownOrderCount": len(unknown_orders),
        "orphanPositionCount": len(orphan_positions),
        "partialFillObserved": partial_fill_observed,
        "wsOrderCount": len(ws_snapshot["orders"]),
        "wsPositionCount": len(ws_snapshot["positions"]),
        "wsAccountCurrencyCount": len(ws_snapshot["account"]),
        "blockers": blockers,
    }
