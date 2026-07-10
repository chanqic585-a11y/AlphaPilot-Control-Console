"""Fixed 1000 USDT OKX Demo risk envelope."""

from __future__ import annotations

import math
from dataclasses import dataclass


DEFAULT_DEMO_RISK_ENVELOPE = {
    "initialEquityUsdt": 1000.0,
    "riskPerTradePercent": 0.25,
    "maxOpenRiskPercent": 1.0,
    "maxOrderNotionalUsdt": 250.0,
    "maxConcurrentPositions": 3,
    "defaultMaxLeverage": 2,
    "hardMaxLeverage": 5,
    "dailyLossStopPercent": 2.0,
    "demoDrawdownPausePercent": 5.0,
}


@dataclass(frozen=True)
class DemoRiskDecision:
    passed: bool
    reasonCodes: tuple[str, ...]
    equityUsdt: float
    maxOrderNotionalUsdt: float


def evaluate_demo_order_risk(
    *,
    notionalUsdt: float,
    leverage: int,
    riskPercent: float,
    openRiskPercent: float,
    openPositionCount: int,
    dailyLossPercent: float,
    drawdownPercent: float,
    dataFresh: bool,
    liquidityPassed: bool,
    envelope: dict | None = None,
    availableEquityUsdt: float | None = None,
) -> DemoRiskDecision:
    limits = {**DEFAULT_DEMO_RISK_ENVELOPE, **(envelope or {})}
    available_equity = (
        float(limits["initialEquityUsdt"])
        if availableEquityUsdt is None
        else float(availableEquityUsdt)
    )
    numbers = (
        notionalUsdt,
        riskPercent,
        openRiskPercent,
        dailyLossPercent,
        drawdownPercent,
        available_equity,
    )
    if not all(math.isfinite(float(value)) for value in numbers):
        raise ValueError("Demo risk input contains non-finite values")
    reasons: list[str] = []
    if notionalUsdt <= 0 or notionalUsdt > float(limits["maxOrderNotionalUsdt"]):
        reasons.append("max_order_notional")
    if available_equity <= 0 or notionalUsdt > available_equity:
        reasons.append("insufficient_demo_equity")
    if leverage < 1 or leverage > int(limits["defaultMaxLeverage"]):
        reasons.append("max_leverage")
    if riskPercent <= 0 or riskPercent > float(limits["riskPerTradePercent"]):
        reasons.append("risk_per_trade")
    if openRiskPercent + max(riskPercent, 0) > float(limits["maxOpenRiskPercent"]):
        reasons.append("max_open_risk")
    if openPositionCount >= int(limits["maxConcurrentPositions"]):
        reasons.append("max_concurrent_positions")
    if dailyLossPercent >= float(limits["dailyLossStopPercent"]):
        reasons.append("daily_loss_stop")
    if drawdownPercent >= float(limits["demoDrawdownPausePercent"]):
        reasons.append("demo_drawdown_stop")
    if not dataFresh:
        reasons.append("market_data_stale")
    if not liquidityPassed:
        reasons.append("liquidity_gate_failed")
    return DemoRiskDecision(
        passed=not reasons,
        reasonCodes=tuple(reasons),
        equityUsdt=float(limits["initialEquityUsdt"]),
        maxOrderNotionalUsdt=float(limits["maxOrderNotionalUsdt"]),
    )
