"""Fail-closed Demo drift and reconciliation guard before new entries."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class DemoRuntimeGuard:
    passed: bool
    pauseRequired: bool
    severity: str
    reasonCodes: tuple[str, ...]


def evaluate_demo_runtime_guard(
    portfolio: dict[str, Any],
    *,
    recovered_statuses: Iterable[str],
    checksums_match: bool,
    approval_checksums_match: bool = True,
) -> DemoRuntimeGuard:
    daily_loss = float(portfolio.get("dailyLossPercent") or 0)
    drawdown = float(portfolio.get("drawdownPercent") or 0)
    available_equity = float(portfolio.get("availableEquityUsdt") or 0)
    rolling_profit_factor = float(portfolio.get("rollingProfitFactor") or 0)
    consecutive_losses = int(portfolio.get("consecutiveLosses") or 0)
    observed_slippage = float(portfolio.get("observedSlippageBps") or 0)
    assumed_slippage = float(portfolio.get("assumedSlippageBps") or 2.0)
    if not all(
        math.isfinite(value)
        for value in (
            daily_loss,
            drawdown,
            available_equity,
            rolling_profit_factor,
            observed_slippage,
            assumed_slippage,
        )
    ):
        raise ValueError("Demo runtime guard received non-finite account metrics")
    statuses = {str(value) for value in recovered_statuses}
    reasons: list[str] = []
    if not checksums_match:
        reasons.append("release_checksum_mismatch")
    if not approval_checksums_match:
        reasons.append("approval_checksum_mismatch")
    if not bool(portfolio.get("marketDataFresh", portfolio.get("dataFresh", True))):
        reasons.append("demo_market_data_stale")
    if not bool(portfolio.get("accountDataFresh", True)):
        reasons.append("demo_account_data_stale")
    if not bool(portfolio.get("authenticationHealthy", True)):
        reasons.append("demo_authentication_failure")
    if int(portfolio.get("orphanPositionCount") or 0) > 0:
        reasons.append("orphan_demo_position")
    if not bool(portfolio.get("reconciliationMatched")):
        reasons.append("demo_reconciliation_mismatch")
    if statuses & {"prepared", "unknown"}:
        reasons.append("unresolved_demo_order_state")
    if available_equity <= 0:
        reasons.append("demo_equity_unavailable")
    if daily_loss >= 2.0:
        reasons.append("demo_daily_loss_stop")
    if drawdown >= 5.0:
        reasons.append("demo_drawdown_stop")
    if int(portfolio.get("closedOutcomeCount") or 0) >= 10 and rolling_profit_factor < 1.0:
        reasons.append("demo_rolling_profit_factor_drift")
    if consecutive_losses >= 5:
        reasons.append("demo_consecutive_loss_stop")
    if assumed_slippage <= 0 or observed_slippage >= assumed_slippage * 3.0:
        reasons.append("demo_slippage_drift")
    return DemoRuntimeGuard(
        passed=not reasons,
        pauseRequired=bool(reasons),
        severity="critical" if reasons else "none",
        reasonCodes=tuple(reasons),
    )
