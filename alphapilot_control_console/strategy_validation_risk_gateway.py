"""Immutable-profile risk checks for strategy-validation Demo orders."""

from __future__ import annotations

from typing import Any, Mapping

from .strategy_validation_risk_store import StrategyValidationRiskStore


PAUSE_EVENTS = {
    "maximum_daily_loss": "daily_loss_pause",
    "maximum_weekly_loss": "weekly_loss_pause",
    "maximum_consecutive_losses": "consecutive_loss_pause",
    "maximum_demo_drawdown": "drawdown_pause",
    "reconciliation_unhealthy": "reconciliation_pause",
}


class StrategyValidationRiskGateway:
    def __init__(self, store: StrategyValidationRiskStore):
        self.store = store

    def evaluate(
        self,
        *,
        releaseId: str,
        profile: Mapping[str, Any],
        requestedRiskR: float,
        snapshot: Mapping[str, Any],
    ) -> dict[str, Any]:
        if self.store.state()["paused"]:
            return {"passed": False, "blockers": ["risk_pause_active"], "paused": True}
        blockers: list[str] = []
        requested = float(requestedRiskR)
        if requested <= 0 or requested > float(profile["riskPerTradeR"]):
            blockers.append("maximum_single_trade_risk")
        if float(snapshot.get("openRiskR") or 0) + max(requested, 0) > float(profile["maximumOpenRiskR"]):
            blockers.append("maximum_open_risk")
        if float(snapshot.get("singleSymbolRiskR") or 0) + max(requested, 0) > float(profile["maximumSingleSymbolRiskR"]):
            blockers.append("maximum_single_symbol_risk")
        if float(snapshot.get("correlatedClusterRiskR") or 0) + max(requested, 0) > float(profile["maximumCorrelatedClusterRiskR"]):
            blockers.append("maximum_correlated_cluster_risk")
        if int(snapshot.get("openPositionCount") or 0) >= int(profile["maximumConcurrentPositions"]):
            blockers.append("maximum_concurrent_positions")
        if float(snapshot.get("marginUtilizationPct") or 0) > float(profile.get("maximumMarginUtilizationPct") or 100.0):
            blockers.append("maximum_margin_utilization")
        if float(snapshot.get("dailyLossR") or 0) >= float(profile["maximumDailyLossR"]):
            blockers.append("maximum_daily_loss")
        if float(snapshot.get("weeklyLossR") or 0) >= float(profile["maximumWeeklyLossR"]):
            blockers.append("maximum_weekly_loss")
        if int(snapshot.get("consecutiveLosses") or 0) >= int(profile["maximumConsecutiveLosses"]):
            blockers.append("maximum_consecutive_losses")
        if float(snapshot.get("demoDrawdownPct") or 0) >= float(profile["maximumDemoDrawdownPct"]):
            blockers.append("maximum_demo_drawdown")
        if snapshot.get("reconciliationHealthy") is not True:
            blockers.append("reconciliation_unhealthy")
        if snapshot.get("dataFresh") is not True:
            blockers.append("data_stale")

        if blockers:
            pause_blocker = next((item for item in blockers if item in PAUSE_EVENTS), None)
            event_type = PAUSE_EVENTS.get(pause_blocker, "risk_rejected")
            paused = pause_blocker is not None
            event = self.store.append(
                eventType=event_type,
                releaseId=releaseId,
                blockers=blockers,
                reason="Immutable Demo risk gate rejected the order.",
                pausedAfter=paused,
            )
            return {"passed": False, "blockers": blockers, "paused": paused, "riskEvent": event}
        event = self.store.append(
            eventType="risk_check_passed",
            releaseId=releaseId,
            blockers=[],
            reason="Immutable Demo risk gate passed.",
            pausedAfter=False,
        )
        return {"passed": True, "blockers": [], "paused": False, "riskEvent": event}
