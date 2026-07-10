"""Versioned OKX Demo risk evaluation with compatibility defaults."""

from __future__ import annotations

from dataclasses import dataclass

from .portfolio_risk import evaluate_portfolio_risk, normalize_risk_profile
from .risk_profile_store import default_profile


DEFAULT_DEMO_RISK_ENVELOPE = {
    **default_profile("okx_demo"),
    "initialEquityUsdt": 1000.0,
    "defaultMaxLeverage": 2,
    "hardMaxLeverage": 5,
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
    strategyId: str = "legacy_demo_strategy",
    instrumentId: str = "LEGACY-DEMO",
    side: str = "buy",
    correlationGroup: str = "",
    positionsByStrategy: dict | None = None,
    positionsBySymbol: dict | None = None,
    openRiskByStrategy: dict | None = None,
    openRiskBySymbol: dict | None = None,
    openRiskByDirection: dict | None = None,
    openRiskByCorrelationGroup: dict | None = None,
    activeStrategyIds: list[str] | None = None,
    canaryLossUsdt: float = 0.0,
    cooldownActive: bool = False,
) -> DemoRiskDecision:
    limits = normalize_risk_profile({**DEFAULT_DEMO_RISK_ENVELOPE, **(envelope or {})})
    available_equity = (
        float(limits["capitalLimitUsdt"])
        if availableEquityUsdt is None
        else float(availableEquityUsdt)
    )
    decision = evaluate_portfolio_risk(
        profile=limits,
        intent={
            "strategyId": strategyId,
            "instId": instrumentId,
            "side": side,
            "correlationGroup": correlationGroup,
            "notionalUsdt": notionalUsdt,
            "leverage": leverage,
            "riskPercent": riskPercent,
        },
        portfolio={
            "availableEquityUsdt": available_equity,
            "activeStrategyIds": activeStrategyIds or ([strategyId] if openPositionCount else []),
            "openPositionCount": openPositionCount,
            "positionsByStrategy": positionsByStrategy or {},
            "positionsBySymbol": positionsBySymbol or {},
            "openRiskPercent": openRiskPercent,
            "openRiskByStrategy": openRiskByStrategy or {},
            "openRiskBySymbol": openRiskBySymbol or {},
            "openRiskByDirection": openRiskByDirection or {},
            "openRiskByCorrelationGroup": openRiskByCorrelationGroup or {},
            "dailyLossPercent": dailyLossPercent,
            "drawdownPercent": drawdownPercent,
            "canaryLossUsdt": canaryLossUsdt,
            "cooldownActive": cooldownActive,
            "dataFresh": dataFresh,
            "liquidityPassed": liquidityPassed,
        },
    )
    compatibility_reasons = tuple(
        "demo_drawdown_stop" if reason == "drawdown_stop" else
        "insufficient_demo_equity" if reason == "insufficient_equity" else reason
        for reason in decision.reasonCodes
    )
    return DemoRiskDecision(
        passed=decision.passed,
        reasonCodes=compatibility_reasons,
        equityUsdt=float(limits["capitalLimitUsdt"]),
        maxOrderNotionalUsdt=float(limits["maxOrderNotionalUsdt"]),
    )
