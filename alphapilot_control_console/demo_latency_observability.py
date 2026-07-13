"""Redacted latency-stage summaries for the OKX Demo execution path."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _duration_ms(start: Any, end: Any) -> float | None:
    start_at = _timestamp(start)
    end_at = _timestamp(end)
    if start_at is None or end_at is None:
        return None
    milliseconds = (end_at - start_at).total_seconds() * 1000.0
    return round(milliseconds, 3) if milliseconds >= 0 else None


def build_latency_stage_metrics(
    *,
    close_received_at: Any,
    evaluation_started_at: Any,
    evaluation_finished_at: Any = None,
    arbitration_started_at: Any = None,
    arbitration_finished_at: Any = None,
    risk_started_at: Any = None,
    risk_finished_at: Any = None,
    order_ready_at: Any = None,
    order_sent_at: Any = None,
    exchange_response_at: Any = None,
) -> dict[str, float | None]:
    """Build stage durations without exposing quotes, orders, or credentials."""

    return {
        "closeToEvaluationMs": _duration_ms(close_received_at, evaluation_started_at),
        "evaluationMs": _duration_ms(evaluation_started_at, evaluation_finished_at),
        "arbitrationMs": _duration_ms(arbitration_started_at, arbitration_finished_at),
        "riskMs": _duration_ms(risk_started_at, risk_finished_at),
        "orderSendMs": _duration_ms(order_ready_at, order_sent_at),
        "exchangeResponseMs": _duration_ms(order_sent_at, exchange_response_at),
        "closeToOrderSendMs": _duration_ms(close_received_at, order_sent_at),
        "closeToExchangeResponseMs": _duration_ms(close_received_at, exchange_response_at),
    }
