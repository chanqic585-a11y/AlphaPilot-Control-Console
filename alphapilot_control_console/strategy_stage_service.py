from __future__ import annotations

from typing import Any

from .state_store import (
    list_local_sandbox_learning_snapshots,
    list_paper_observation_logs,
    list_strategy_stage_assignments,
    now_iso,
    set_strategy_stage_assignment,
)
from .usable_strategy_catalog import build_usable_strategy_catalog


CONTROL_CONSOLE_VERSION = "V13.26.1"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_26_1"


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed == parsed else fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _historical_metrics(strategy: dict[str, Any]) -> dict[str, Any]:
    test_metrics = strategy.get("testMetrics") if isinstance(strategy.get("testMetrics"), dict) else {}
    metrics = strategy.get("metrics") if isinstance(strategy.get("metrics"), dict) else {}
    return test_metrics if _safe_int(test_metrics.get("tradeCount")) > 0 else metrics


def _local_sample_summary(task_id: str) -> dict[str, Any]:
    payload = list_paper_observation_logs(task_id)
    rows = payload if isinstance(payload, list) else []
    closed_rows = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("outcomeR") is not None
    ]
    return {
        "logCount": len(rows),
        "closedSampleCount": len(closed_rows),
        "totalR": round(sum(_safe_float(row.get("outcomeR")) for row in closed_rows), 4),
        "latestSampleAt": max((str(row.get("createdAt") or "") for row in rows), default=None),
    }


def build_strategy_stage_board() -> dict[str, Any]:
    catalog = build_usable_strategy_catalog()
    strategies = catalog.get("strategies") if isinstance(catalog.get("strategies"), list) else []
    assignments = list_strategy_stage_assignments()
    rows: list[dict[str, Any]] = []
    for strategy in strategies:
        if not isinstance(strategy, dict):
            continue
        strategy_id = str(strategy.get("strategyId") or strategy.get("candidateId") or "").strip()
        if not strategy_id:
            continue
        assignment = assignments.get(strategy_id, {})
        stage = str(assignment.get("stage") or "local_sandbox")
        metrics = _historical_metrics(strategy)
        task_id = str(strategy.get("taskId") or strategy_id)
        local_samples = _local_sample_summary(task_id)
        selected_pairs = strategy.get("selectedPairs") if isinstance(strategy.get("selectedPairs"), list) else []
        rows.append({
            **strategy,
            "strategyId": strategy_id,
            "taskId": task_id,
            "stage": stage,
            "stageLabel": assignment.get("stageLabel") or ("Demo 观察" if stage == "demo_trial" else "本地沙盒"),
            "stageUpdatedAt": assignment.get("updatedAt"),
            "promotedAt": assignment.get("promotedAt"),
            "promotionReason": assignment.get("reason"),
            "sampleDataPreserved": assignment.get("sampleDataPreserved", True),
            "historicalTradeCount": _safe_int(metrics.get("tradeCount")),
            "historicalWinRatePct": _safe_float(metrics.get("winRatePct")),
            "historicalProfitFactor": _safe_float(metrics.get("profitFactor")),
            "historicalTotalR": _safe_float(metrics.get("totalR")),
            "selectedPairCount": len(selected_pairs),
            "localSampleSummary": local_samples,
        })
    rows.sort(key=lambda item: (-_safe_float(item.get("score")), str(item.get("strategyId"))))
    by_stage = {
        stage: sum(1 for row in rows if row.get("stage") == stage)
        for stage in ("local_sandbox", "demo_trial", "demo_validated", "live_candidate", "archived")
    }
    learning_snapshots = list_local_sandbox_learning_snapshots(100)
    largest_snapshot = max(
        (item for item in learning_snapshots if isinstance(item, dict)),
        key=lambda item: _safe_int(item.get("closedSampleCount")),
        default={},
    )
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "totalStrategyCount": len(rows),
            "localSandboxCount": by_stage["local_sandbox"],
            "demoTrialCount": by_stage["demo_trial"],
            "demoValidatedCount": by_stage["demo_validated"],
            "liveCandidateCount": by_stage["live_candidate"],
            "archivedCount": by_stage["archived"],
            "historicalTradeCount": sum(_safe_int(row.get("historicalTradeCount")) for row in rows),
            "localClosedSampleCount": sum(
                _safe_int((row.get("localSampleSummary") or {}).get("closedSampleCount"))
                for row in rows
            ),
            "historicalSandboxAggregateClosedSampleCount": _safe_int(largest_snapshot.get("closedSampleCount")),
            "historicalSandboxAggregateTotalR": _safe_float(largest_snapshot.get("totalR")),
            "historicalSandboxSnapshotId": largest_snapshot.get("snapshotId"),
        },
        "strategies": rows,
        "safetyNote": "Stage changes move strategy visibility without deleting historical or local sample data.",
    }


def promote_strategies_to_demo_trial(
    strategy_ids: list[str] | None = None,
    reason: str = "manual_demo_trial_promotion",
) -> dict[str, Any]:
    board = build_strategy_stage_board()
    available = {
        str(row.get("strategyId")): row
        for row in board.get("strategies", [])
        if isinstance(row, dict) and row.get("strategyId")
    }
    requested = [str(value).strip() for value in (strategy_ids or list(available)) if str(value).strip()]
    promoted: list[dict[str, Any]] = []
    missing: list[str] = []
    for strategy_id in requested:
        strategy = available.get(strategy_id)
        if not strategy:
            missing.append(strategy_id)
            continue
        promoted.append(set_strategy_stage_assignment(
            strategy_id,
            "demo_trial",
            {
                "taskId": strategy.get("taskId"),
                "strategyName": strategy.get("name"),
                "reason": reason,
                "historicalTradeCountAtPromotion": strategy.get("historicalTradeCount"),
                "localClosedSampleCountAtPromotion": (strategy.get("localSampleSummary") or {}).get("closedSampleCount"),
            },
        ))
    return {
        "status": "completed",
        "promotedCount": len(promoted),
        "promotedStrategyIds": [row.get("strategyId") for row in promoted],
        "missingStrategyIds": missing,
        "stageBoard": build_strategy_stage_board(),
    }


def return_strategies_to_local_sandbox(
    strategy_ids: list[str],
    reason: str = "manual_return_to_sandbox",
) -> dict[str, Any]:
    returned: list[dict[str, Any]] = []
    for strategy_id in strategy_ids:
        normalized = str(strategy_id or "").strip()
        if not normalized:
            continue
        returned.append(set_strategy_stage_assignment(
            normalized,
            "local_sandbox",
            {"reason": reason, "returnedToSandboxAt": now_iso()},
        ))
    return {
        "status": "completed",
        "returnedCount": len(returned),
        "returnedStrategyIds": [row.get("strategyId") for row in returned],
        "stageBoard": build_strategy_stage_board(),
    }
