"""Execute one approved OKX Live engineering smoke and isolate its evidence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from pathlib import Path
from typing import Any, Callable, Mapping

from .live_engineering_smoke_contract import (
    validate_live_engineering_smoke_approval,
    validate_live_engineering_smoke_contract,
)


class LiveSmokePreflightError(RuntimeError):
    """A redacted, user-actionable failure that occurs before order reservation."""

    def __init__(
        self,
        safe_code: str,
        *,
        safe_instrument_id: str | None = None,
    ):
        super().__init__("Live engineering smoke preflight blocked")
        self.safe_code = safe_code
        self.safe_instrument_id = safe_instrument_id


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def _decimal(value: Any, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise ValueError(f"Invalid {name}") from error
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _quantize_step(value: Decimal, step: Decimal, rounding: str) -> Decimal:
    units = (value / step).to_integral_value(rounding=rounding)
    return units * step


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _rows(response: Mapping[str, Any], endpoint: str) -> list[dict[str, Any]]:
    if str(response.get("code") or "") != "0":
        raise RuntimeError(f"OKX Live {endpoint} failed")
    data = response.get("data")
    if not isinstance(data, list):
        raise RuntimeError(f"OKX Live {endpoint} returned invalid data")
    return [row for row in data if isinstance(row, dict)]


def _nonzero_positions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        try:
            if Decimal(str(row.get("pos") or "0")) != 0:
                result.append(row)
        except Exception:
            result.append(row)
    return result


def _available_usdt(rows: list[dict[str, Any]]) -> Decimal:
    for account in rows:
        details = account.get("details")
        if not isinstance(details, list):
            continue
        for detail in details:
            if not isinstance(detail, dict) or str(detail.get("ccy") or "") != "USDT":
                continue
            for key in ("availBal", "availEq", "cashBal"):
                raw = detail.get(key)
                if raw in {None, ""}:
                    continue
                try:
                    value = Decimal(str(raw))
                except Exception as error:
                    raise RuntimeError("OKX Live USDT balance is invalid") from error
                if value.is_finite() and value >= 0:
                    return value
    raise RuntimeError("OKX Live available USDT balance is unavailable")


def _require_private_preflight(
    *,
    client: Any,
    instrument_id: str,
    required_notional: Decimal,
) -> str:
    try:
        config_rows = _rows(client.get_account_config(), "account config")
    except Exception as error:
        raise LiveSmokePreflightError("account_config_unavailable") from error
    if len(config_rows) != 1:
        raise LiveSmokePreflightError("account_config_invalid")
    position_mode = str(config_rows[0].get("posMode") or "")
    if position_mode not in {"net_mode", "long_short_mode"}:
        raise LiveSmokePreflightError("unsupported_position_mode")
    try:
        available_usdt = _available_usdt(
            _rows(client.get_balance(currency="USDT"), "balance")
        )
    except Exception as error:
        raise LiveSmokePreflightError("available_usdt_unavailable") from error
    if available_usdt < required_notional:
        raise LiveSmokePreflightError("insufficient_available_usdt")
    try:
        position_rows = _rows(client.get_positions(), "positions")
    except Exception as error:
        raise LiveSmokePreflightError("positions_unavailable") from error
    if _nonzero_positions(position_rows):
        raise LiveSmokePreflightError("nonzero_initial_positions")
    try:
        open_order_rows = _rows(client.get_open_orders(), "open orders")
    except Exception as error:
        raise LiveSmokePreflightError("open_orders_unavailable") from error
    if open_order_rows:
        raise LiveSmokePreflightError("nonzero_initial_open_orders")
    try:
        leverage_rows = _rows(
            client.get_leverage(instId=instrument_id, marginMode="isolated"),
            "leverage",
        )
    except Exception as error:
        raise LiveSmokePreflightError("leverage_unavailable") from error
    relevant_leverage_rows = [
        row
        for row in leverage_rows
        if position_mode == "net_mode"
        or str(row.get("posSide") or "") in {"", "net", "long"}
    ]
    try:
        leverage_is_valid = bool(relevant_leverage_rows) and all(
            str(row.get("mgnMode") or "") == "isolated"
            and Decimal(str(row.get("lever") or "0")) == Decimal("1")
            for row in relevant_leverage_rows
        )
    except Exception as error:
        raise LiveSmokePreflightError("leverage_unavailable") from error
    if not leverage_is_valid:
        raise LiveSmokePreflightError("isolated_leverage_not_1x")
    return position_mode


def _build_order_payload(
    *,
    contract: Mapping[str, Any],
    instrument: Mapping[str, Any],
    quote: Mapping[str, Any],
) -> tuple[dict[str, Any], Decimal]:
    if str(instrument.get("state") or "").lower() != "live":
        raise ValueError("Live engineering smoke instrument must be tradable")
    instrument_id = str(instrument.get("instId") or "").strip()
    if not instrument_id.endswith("-USDT-SWAP"):
        raise ValueError("Live engineering smoke requires an OKX USDT perpetual instrument")
    bid = _decimal(quote.get("bidPx"), "bidPx")
    tick = _decimal(instrument.get("tickSz"), "tickSz")
    lot = _decimal(instrument.get("lotSz"), "lotSz")
    minimum_size = _decimal(instrument.get("minSz"), "minSz")
    contract_value = _decimal(instrument.get("ctVal"), "ctVal")
    offset = Decimal(str(contract["limitOffsetBps"])) / Decimal("10000")
    limit_price = _quantize_step(bid * (Decimal("1") - offset), tick, ROUND_DOWN)
    order_size = _quantize_step(minimum_size, lot, ROUND_UP)
    notional = limit_price * order_size * contract_value
    if notional > Decimal(str(contract["maximumNotionalUsdt"])):
        raise ValueError("Exchange minimum order exceeds the approved Live smoke notional")
    take_profit = _quantize_step(limit_price * Decimal("1.01"), tick, ROUND_UP)
    stop_loss = _quantize_step(limit_price * Decimal("0.99"), tick, ROUND_DOWN)
    client_id = "apsmoke" + str(contract["contractHash"]).rsplit("_", 1)[-1][:24]
    payload = {
        "instId": instrument_id,
        "tdMode": "isolated",
        "side": "buy",
        "ordType": "limit",
        "px": _plain(limit_price),
        "sz": _plain(order_size),
        "clOrdId": client_id,
        "attachAlgoOrds": [
            {
                "tpTriggerPx": _plain(take_profit),
                "tpOrdPx": "-1",
                "slTriggerPx": _plain(stop_loss),
                "slOrdPx": "-1",
            }
        ],
    }
    return payload, notional


def run_live_engineering_smoke(
    *,
    client: Any,
    contract: Mapping[str, Any],
    approval: Mapping[str, Any],
    instrument: Mapping[str, Any],
    quote: Mapping[str, Any],
    output_path: Path | str | None = None,
    attempt_path: Path | str | None = None,
    authority_assertion: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Run exactly one approved order lifecycle; never treat it as strategy evidence."""

    validated_contract = validate_live_engineering_smoke_contract(contract)
    validate_live_engineering_smoke_approval(validated_contract, approval)
    (authority_assertion or (lambda: None))()
    attempt_state_path = Path(attempt_path) if attempt_path is not None else None
    if attempt_state_path is not None and attempt_state_path.exists():
        raise PermissionError("Live engineering smoke attempt has already been reserved")
    order_payload, notional = _build_order_payload(
        contract=validated_contract,
        instrument=instrument,
        quote=quote,
    )
    instrument_id = str(order_payload["instId"])
    try:
        position_mode = _require_private_preflight(
            client=client,
            instrument_id=instrument_id,
            required_notional=notional,
        )
    except LiveSmokePreflightError as error:
        raise LiveSmokePreflightError(
            error.safe_code,
            safe_instrument_id=instrument_id,
        ) from error
    if position_mode == "long_short_mode":
        order_payload["posSide"] = "long"
    attempt_state = {
        "schemaVersion": "alphapilot_live_engineering_smoke_attempt_v1",
        "generatedAt": _now(),
        "status": "attempt_reserved",
        "environment": "okx_live",
        "contractHash": validated_contract["contractHash"],
        "instrumentId": instrument_id,
        "orderAttemptCount": 1,
        "rawCredentialsPersisted": False,
        "privateAccountValuesPersisted": False,
        "withdrawAllowed": False,
    }
    if attempt_state_path is not None:
        _atomic_write(attempt_state_path, attempt_state)

    try:
        submitted = client.place_protected_order(order_payload)
        submitted_rows = _rows(submitted, "order submission")
        if len(submitted_rows) != 1 or not str(submitted_rows[0].get("ordId") or ""):
            raise RuntimeError("Live engineering smoke did not receive one exchange order id")
        order_id = str(submitted_rows[0]["ordId"])
        attempt_state = {
            **attempt_state,
            "generatedAt": _now(),
            "status": "order_submitted_cancel_pending",
            "exchangeOrderId": order_id,
            "clientOrderId": order_payload["clOrdId"],
        }
        if attempt_state_path is not None:
            _atomic_write(attempt_state_path, attempt_state)
        first_order = _rows(
            client.get_order(instId=instrument_id, ordId=order_id),
            "order query",
        )
        initial_state = str(first_order[0].get("state") or "unknown") if first_order else "unknown"
        cancel_rows = _rows(
            client.cancel_order(instId=instrument_id, ordId=order_id),
            "order cancellation",
        )
        cancel_accepted = bool(cancel_rows) and str(cancel_rows[0].get("sCode") or "0") == "0"
        final_order_rows = _rows(
            client.get_order(instId=instrument_id, ordId=order_id),
            "post-cancel order query",
        )
        final_order_state = str(final_order_rows[0].get("state") or "unknown") if final_order_rows else "unknown"
        final_positions = _nonzero_positions(_rows(client.get_positions(), "final positions"))
        final_orders = _rows(client.get_open_orders(), "final open orders")
        cancel_confirmed = cancel_accepted and final_order_state in {"canceled", "cancelled"}
        reconciled = cancel_confirmed and not final_positions and not final_orders
        status = (
            "completed_canceled_and_reconciled"
            if reconciled
            else "blocked_unexpected_live_state_requires_manual_recovery"
        )
        result = {
            "schemaVersion": "alphapilot_live_engineering_smoke_result_v1",
            "generatedAt": _now(),
            "status": status,
            "environment": "okx_live",
            "contractHash": validated_contract["contractHash"],
            "instrumentId": instrument_id,
            "orderAttemptCount": 1,
            "exchangeOrderId": order_id,
            "clientOrderId": order_payload["clOrdId"],
            "orderNotionalUsdt": float(notional),
            "initialOrderState": initial_state,
            "finalOrderState": final_order_state,
            "cancelConfirmed": cancel_confirmed,
            "finalOpenPositionCount": len(final_positions),
            "finalOpenOrderCount": len(final_orders),
            "finalReconciliationMatched": reconciled,
            "strategyQualification": False,
            "promotionEligible": False,
            "liveCanaryEvidenceEligible": False,
            "privateAccountValuesPersisted": False,
            "rawCredentialsPersisted": False,
            "withdrawAllowed": False,
        }
        if output_path is not None:
            _atomic_write(Path(output_path), result)
        attempt_state = result
        if attempt_state_path is not None:
            _atomic_write(attempt_state_path, result)
        if not reconciled:
            raise RuntimeError("Live engineering smoke did not reconcile to zero state")
        return result
    except Exception as error:
        if attempt_state_path is not None:
            blocked_state = {
                **attempt_state,
                "generatedAt": _now(),
                "status": "blocked_requires_manual_review",
                "errorType": type(error).__name__,
            }
            _atomic_write(attempt_state_path, blocked_state)
        raise
