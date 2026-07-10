"""Portfolio-level risk arbitration shared by Demo and Live runtimes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PortfolioRiskDecision:
    passed: bool
    reasonCodes: tuple[str, ...]
    projectedOpenRiskPercent: float
    projectedPositionCount: int
    projectedActiveStrategyCount: int


def normalize_risk_profile(value: dict[str, Any] | None) -> dict[str, Any]:
    source = dict(value or {})
    return {
        **source,
        "schemaVersion": source.get("schemaVersion") or "risk_profile_v1",
        "capitalLimitUsdt": float(source.get("capitalLimitUsdt") or source.get("initialEquityUsdt") or 1000.0),
        "maxActiveStrategies": int(source.get("maxActiveStrategies") or 1),
        "maxConcurrentPositions": int(source.get("maxConcurrentPositions") or 1),
        "maxPositionsPerStrategy": int(source.get("maxPositionsPerStrategy") or source.get("maxConcurrentPositions") or 1),
        "maxPositionsPerSymbol": int(source.get("maxPositionsPerSymbol") or 1),
        "maxOrderNotionalUsdt": float(source.get("maxOrderNotionalUsdt") or 100.0),
        "maxLeverage": int(source.get("maxLeverage") or source.get("defaultMaxLeverage") or 1),
        "marginMode": str(source.get("marginMode") or "isolated"),
        "riskPerTradePercent": float(source.get("riskPerTradePercent") or 0.25),
        "maxOpenRiskPercent": float(source.get("maxOpenRiskPercent") or 1.0),
        "maxStrategyOpenRiskPercent": float(source.get("maxStrategyOpenRiskPercent") or source.get("maxOpenRiskPercent") or 1.0),
        "maxSymbolOpenRiskPercent": float(source.get("maxSymbolOpenRiskPercent") or source.get("maxOpenRiskPercent") or 1.0),
        "maxDirectionOpenRiskPercent": float(source.get("maxDirectionOpenRiskPercent") or source.get("maxOpenRiskPercent") or 1.0),
        "maxCorrelatedOpenRiskPercent": float(source.get("maxCorrelatedOpenRiskPercent") or source.get("maxOpenRiskPercent") or 1.0),
        "dailyLossStopPercent": float(source.get("dailyLossStopPercent") or 1.0),
        "maxDrawdownStopPercent": float(source.get("maxDrawdownStopPercent") or source.get("demoDrawdownPausePercent") or 2.5),
        "canaryLossStopUsdt": float(source.get("canaryLossStopUsdt") or 25.0),
        "cooldownAfterLossMinutes": int(source.get("cooldownAfterLossMinutes") or 0),
        "rewardRiskRatio": float(source.get("rewardRiskRatio") or 2.0),
        "allowNewEntries": bool(source.get("allowNewEntries", True)),
        "allowedStrategyIds": list(source.get("allowedStrategyIds") or []),
    }


def _number(mapping: dict[str, Any], key: str) -> float:
    try:
        value = float(mapping.get(key) or 0)
    except (TypeError, ValueError):
        return math.nan
    return value


def evaluate_portfolio_risk(
    *,
    profile: dict[str, Any],
    intent: dict[str, Any],
    portfolio: dict[str, Any],
) -> PortfolioRiskDecision:
    limits = normalize_risk_profile(profile)
    strategy_id = str(intent.get("strategyId") or intent.get("candidateId") or "").strip()
    symbol = str(intent.get("instId") or intent.get("symbol") or "").strip()
    side = str(intent.get("side") or "").lower()
    correlation_group = str(intent.get("correlationGroup") or "").strip()
    notional = _number(intent, "notionalUsdt")
    leverage = _number(intent, "leverage")
    risk_percent = _number(intent, "riskPercent")
    reasons: list[str] = []

    active_strategies = {str(item) for item in portfolio.get("activeStrategyIds", []) if str(item)}
    if strategy_id:
        active_strategies.add(strategy_id)
    position_count = int(portfolio.get("openPositionCount") or 0)
    positions_by_strategy = dict(portfolio.get("positionsByStrategy") or {})
    positions_by_symbol = dict(portfolio.get("positionsBySymbol") or {})
    open_risk = _number(portfolio, "openRiskPercent")
    risk_by_strategy = dict(portfolio.get("openRiskByStrategy") or {})
    risk_by_symbol = dict(portfolio.get("openRiskBySymbol") or {})
    risk_by_direction = dict(portfolio.get("openRiskByDirection") or {})
    risk_by_correlation = dict(portfolio.get("openRiskByCorrelationGroup") or {})

    numeric_values = (notional, leverage, risk_percent, open_risk)
    if not all(math.isfinite(value) for value in numeric_values):
        reasons.append("risk_input_non_finite")
    if not strategy_id or not symbol or side not in {"buy", "sell", "long", "short"}:
        reasons.append("incomplete_portfolio_intent")
    if not limits["allowNewEntries"]:
        reasons.append("new_entries_disabled")
    allowed = {str(item) for item in limits["allowedStrategyIds"] if str(item)}
    if allowed and strategy_id not in allowed:
        reasons.append("strategy_not_allowed")
    if notional <= 0 or notional > limits["maxOrderNotionalUsdt"]:
        reasons.append("max_order_notional")
    available_equity = _number(portfolio, "availableEquityUsdt")
    if not math.isfinite(available_equity) or available_equity <= 0 or notional > available_equity:
        reasons.append("insufficient_equity")
    if leverage < 1 or leverage > limits["maxLeverage"]:
        reasons.append("max_leverage")
    if risk_percent <= 0 or risk_percent > limits["riskPerTradePercent"]:
        reasons.append("risk_per_trade")
    if open_risk + max(risk_percent, 0) > limits["maxOpenRiskPercent"]:
        reasons.append("max_open_risk")
    if len(active_strategies) > limits["maxActiveStrategies"]:
        reasons.append("max_active_strategies")
    if position_count + 1 > limits["maxConcurrentPositions"]:
        reasons.append("max_concurrent_positions")
    if int(positions_by_strategy.get(strategy_id, 0)) + 1 > limits["maxPositionsPerStrategy"]:
        reasons.append("max_positions_per_strategy")
    if int(positions_by_symbol.get(symbol, 0)) + 1 > limits["maxPositionsPerSymbol"]:
        reasons.append("max_positions_per_symbol")
    direction_key = "long" if side in {"buy", "long"} else "short"
    grouped_limits = (
        (risk_by_strategy, strategy_id, "maxStrategyOpenRiskPercent", "max_strategy_open_risk"),
        (risk_by_symbol, symbol, "maxSymbolOpenRiskPercent", "max_symbol_open_risk"),
        (risk_by_direction, direction_key, "maxDirectionOpenRiskPercent", "max_direction_open_risk"),
    )
    for values, key, limit_name, reason in grouped_limits:
        if float(values.get(key, 0) or 0) + max(risk_percent, 0) > limits[limit_name]:
            reasons.append(reason)
    if correlation_group and (
        float(risk_by_correlation.get(correlation_group, 0) or 0) + max(risk_percent, 0)
        > limits["maxCorrelatedOpenRiskPercent"]
    ):
        reasons.append("max_correlated_open_risk")
    if _number(portfolio, "dailyLossPercent") >= limits["dailyLossStopPercent"]:
        reasons.append("daily_loss_stop")
    if _number(portfolio, "drawdownPercent") >= limits["maxDrawdownStopPercent"]:
        reasons.append("drawdown_stop")
    if _number(portfolio, "canaryLossUsdt") >= limits["canaryLossStopUsdt"]:
        reasons.append("canary_loss_stop")
    if portfolio.get("cooldownActive") is True:
        reasons.append("loss_cooldown_active")
    if portfolio.get("dataFresh") is not True:
        reasons.append("market_data_stale")
    if portfolio.get("liquidityPassed") is not True:
        reasons.append("liquidity_gate_failed")
    return PortfolioRiskDecision(
        passed=not reasons,
        reasonCodes=tuple(dict.fromkeys(reasons)),
        projectedOpenRiskPercent=open_risk + max(risk_percent, 0),
        projectedPositionCount=position_count + 1,
        projectedActiveStrategyCount=len(active_strategies),
    )
