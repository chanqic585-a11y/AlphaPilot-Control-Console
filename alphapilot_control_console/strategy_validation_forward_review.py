"""Forward review derived only from reconciled strategy-validation closed trades."""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

from .strategy_validation_demo_store import StrategyValidationDemoStore


def build_strategy_validation_forward_review(
    *, store: StrategyValidationDemoStore, release_id: str | None = None
) -> dict[str, Any]:
    trades = store.list_closed_trades(release_id)
    count = len(trades)
    if count >= 100:
        status = "serious_review_available"
    elif count >= 30:
        status = "preliminary_review_available"
    else:
        status = "collecting"
    net_pnl = sum(float(row["netPnl"]) for row in trades)
    net_rs = [float(row["netR"]) for row in trades]
    release_concentration = Counter(str(row["releaseId"]) for row in trades)
    return {
        "releaseId": release_id,
        "closedTradeCount": count,
        "reviewStatus": status,
        "netPnl": net_pnl,
        "averageNetR": mean(net_rs) if net_rs else None,
        "winningTradeCount": sum(1 for value in net_rs if value > 0),
        "losingTradeCount": sum(1 for value in net_rs if value < 0),
        "releaseConcentration": dict(release_concentration),
        "engineeringSmokeCount": 0,
        "shadowObservationCount": 0,
        "legacyDiagnosticCount": 0,
        "localSimulationCount": 0,
        "liveApprovalCreated": False,
        "liveCandidateCreated": False,
        "riskIncreased": False,
    }
