"""Pure close-to-order latency policy for automatic OKX Demo entries."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


TARGET_LATENCY_MS = 5_000
CONDITIONAL_LATENCY_MS = 10_000
ABSOLUTE_EXPIRY_MS = 30_000
MAX_QUOTE_AGE_MS = 2_000
MAX_SPREAD_FRACTION = 0.002
MAX_ADVERSE_DRIFT_PERCENT = 0.20
STOP_DISTANCE_DRIFT_FRACTION = 0.10
MIN_NET_REWARD_RISK = 2.0


@dataclass(frozen=True)
class DemoEntryLatencyDecision:
    passed: bool
    latencyClass: str
    reasonCode: str | None
    closeToReadyMs: int
    quoteAgeMs: int | None = None
    adverseDriftPercent: float | None = None
    allowedAdverseDriftPercent: float | None = None
    recalculatedNetRewardRisk: float | None = None


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str) and value.strip():
        try:
            result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if result.tzinfo is None:
        return result.replace(tzinfo=UTC)
    return result.astimezone(UTC)


def _positive_number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result > 0 else None


def _decision(
    *,
    passed: bool,
    latency_class: str,
    reason_code: str | None,
    close_to_ready_ms: int,
    quote_age_ms: int | None = None,
    adverse_drift_percent: float | None = None,
    allowed_adverse_drift_percent: float | None = None,
    reward_risk: float | None = None,
) -> DemoEntryLatencyDecision:
    return DemoEntryLatencyDecision(
        passed=passed,
        latencyClass=latency_class,
        reasonCode=reason_code,
        closeToReadyMs=close_to_ready_ms,
        quoteAgeMs=quote_age_ms,
        adverseDriftPercent=adverse_drift_percent,
        allowedAdverseDriftPercent=allowed_adverse_drift_percent,
        recalculatedNetRewardRisk=reward_risk,
    )


def evaluate_demo_entry_latency(
    signal: dict[str, Any],
    quote: dict[str, Any],
    *,
    close_received_at: datetime | str,
    order_ready_at: datetime | str,
    fee_rate: float,
    slippage_rate: float,
) -> DemoEntryLatencyDecision:
    """Classify latency and fail closed when a late entry would chase price."""

    close_time = _datetime(close_received_at)
    ready_time = _datetime(order_ready_at)
    if close_time is None or ready_time is None or ready_time < close_time:
        return _decision(
            passed=False,
            latency_class="invalid",
            reason_code="latency_timestamp_invalid",
            close_to_ready_ms=-1,
        )
    close_to_ready_ms = int(round((ready_time - close_time).total_seconds() * 1000))
    if close_to_ready_ms <= TARGET_LATENCY_MS:
        return _decision(
            passed=True,
            latency_class="on_target",
            reason_code=None,
            close_to_ready_ms=close_to_ready_ms,
        )
    if close_to_ready_ms <= CONDITIONAL_LATENCY_MS:
        return _decision(
            passed=True,
            latency_class="delayed",
            reason_code=None,
            close_to_ready_ms=close_to_ready_ms,
        )
    if close_to_ready_ms > ABSOLUTE_EXPIRY_MS:
        return _decision(
            passed=False,
            latency_class="expired",
            reason_code="signal_expired",
            close_to_ready_ms=close_to_ready_ms,
        )

    quote_time = _datetime(quote.get("receivedAt"))
    quote_age_ms = (
        int(round((ready_time - quote_time).total_seconds() * 1000))
        if quote_time is not None
        else None
    )
    conditional_values = {
        "passed": False,
        "latency_class": "conditional",
        "close_to_ready_ms": close_to_ready_ms,
        "quote_age_ms": quote_age_ms,
    }
    if quote_age_ms is None or quote_age_ms < 0 or quote_age_ms > MAX_QUOTE_AGE_MS:
        return _decision(
            **conditional_values,
            reason_code="conditional_quote_stale",
        )
    if quote.get("liquidityPassed") is not True:
        return _decision(
            **conditional_values,
            reason_code="conditional_liquidity_failed",
        )
    try:
        spread = float(quote.get("spreadPct"))
    except (TypeError, ValueError):
        spread = math.inf
    if not math.isfinite(spread) or spread < 0 or spread > MAX_SPREAD_FRACTION:
        return _decision(
            **conditional_values,
            reason_code="conditional_spread_exceeded",
        )

    reference = _positive_number(signal.get("entryPrice"))
    stop = _positive_number(signal.get("stopLossPrice"))
    target = _positive_number(signal.get("takeProfitPrice"))
    side = str(signal.get("side") or "").lower()
    is_long = side in {"buy", "long"}
    is_short = side in {"sell", "short"}
    executable = _positive_number(quote.get("askPrice" if is_long else "bidPrice"))
    if reference is None or stop is None or target is None or not (is_long or is_short):
        return _decision(
            **conditional_values,
            reason_code="conditional_stop_distance_missing",
        )
    if executable is None:
        return _decision(
            **conditional_values,
            reason_code="conditional_quote_stale",
        )

    stop_distance_percent = abs(reference - stop) / reference * 100.0
    if stop_distance_percent <= 0:
        return _decision(
            **conditional_values,
            reason_code="conditional_stop_distance_missing",
        )
    allowed_drift = min(
        MAX_ADVERSE_DRIFT_PERCENT,
        stop_distance_percent * STOP_DISTANCE_DRIFT_FRACTION,
    )
    raw_drift = (
        (executable - reference) / reference * 100.0
        if is_long
        else (reference - executable) / reference * 100.0
    )
    adverse_drift = max(0.0, raw_drift)
    drift_values = {
        **conditional_values,
        "adverse_drift_percent": adverse_drift,
        "allowed_adverse_drift_percent": allowed_drift,
    }
    if adverse_drift > allowed_drift:
        return _decision(
            **drift_values,
            reason_code="conditional_price_drift_exceeded",
        )

    gross_reward = target - executable if is_long else executable - target
    gross_risk = executable - stop if is_long else stop - executable
    try:
        total_rate = max(0.0, float(fee_rate)) + max(0.0, float(slippage_rate))
    except (TypeError, ValueError):
        total_rate = math.inf
    round_trip_cost = executable * total_rate * 2.0
    net_reward = gross_reward - round_trip_cost
    net_risk = gross_risk + round_trip_cost
    reward_risk = net_reward / net_risk if net_reward > 0 and net_risk > 0 else 0.0
    if not math.isfinite(reward_risk) or reward_risk < MIN_NET_REWARD_RISK:
        return _decision(
            **drift_values,
            reason_code="conditional_reward_risk_below_2r",
            reward_risk=reward_risk,
        )
    passed_values = {**drift_values, "passed": True}
    return _decision(
        **passed_values,
        reason_code=None,
        reward_risk=reward_risk,
    )
