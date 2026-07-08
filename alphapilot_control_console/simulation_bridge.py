from __future__ import annotations

from typing import Any

from .config import SAFETY_BOUNDARY
from .local_sandbox_runner import VIRTUAL_CAPITAL_PER_STRATEGY
from .sandbox_auto_runner import get_local_sandbox_auto_runner_status
from .state_store import (
    list_local_sandbox_daily_reports,
    list_local_sandbox_learning_snapshots,
    list_paper_observation_logs,
)
from .usable_strategy_catalog import build_usable_strategy_catalog


CONTROL_CONSOLE_VERSION = "V13.7.45"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_45"
MIN_CLOSED_SAMPLES_FOR_SIM_REVIEW = 30
MIN_RULE_MATCHES_FOR_SIM_REVIEW = 12
MIN_HEALTH_SCORE_FOR_SIM_REVIEW = 65
MIN_CLOSED_SAMPLES_FOR_BASELINE_LEARNING = 100


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


def _latest_daily_report() -> dict[str, Any]:
    reports = list_local_sandbox_daily_reports(1)
    return reports[0] if reports and isinstance(reports[0], dict) else {}


def _health_rows_by_task(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = report.get("strategyHealthRows") if isinstance(report.get("strategyHealthRows"), list) else []
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("taskId") or "").strip()
        if task_id:
            result[task_id] = row
    return result


def _count_logs(task_id: str) -> dict[str, int]:
    logs = list_paper_observation_logs(task_id)
    rows = logs if isinstance(logs, list) else []
    return {
        "logCount": len(rows),
        "signalObservedCount": sum(1 for row in rows if isinstance(row, dict) and row.get("signalObserved")),
        "ruleMatchedCount": sum(1 for row in rows if isinstance(row, dict) and row.get("ruleMatched")),
        "riskWarningCount": sum(1 for row in rows if isinstance(row, dict) and row.get("logType") == "risk_warning"),
        "invalidatedCount": sum(1 for row in rows if isinstance(row, dict) and row.get("logType") == "invalidated"),
    }


def _row_stage(health: dict[str, Any], counts: dict[str, int]) -> tuple[str, str, str, list[str]]:
    closed_samples = _safe_int(health.get("closedPaperSampleCount"))
    rule_matches = _safe_int(health.get("ruleMatchedCount"), counts.get("ruleMatchedCount", 0))
    health_score = _safe_float(health.get("healthScore"))
    risk_count = _safe_int(health.get("riskWarningCount"), counts.get("riskWarningCount", 0))
    invalidated_count = _safe_int(health.get("invalidatedCount"), counts.get("invalidatedCount", 0))
    blockers: list[str] = []
    if closed_samples < MIN_CLOSED_SAMPLES_FOR_SIM_REVIEW:
        blockers.append(f"closed_samples_below_{MIN_CLOSED_SAMPLES_FOR_SIM_REVIEW}")
    if rule_matches < MIN_RULE_MATCHES_FOR_SIM_REVIEW:
        blockers.append(f"rule_matches_below_{MIN_RULE_MATCHES_FOR_SIM_REVIEW}")
    if health_score < MIN_HEALTH_SCORE_FOR_SIM_REVIEW:
        blockers.append(f"health_score_below_{MIN_HEALTH_SCORE_FOR_SIM_REVIEW}")
    if risk_count > 0:
        blockers.append("risk_warning_needs_review")
    if invalidated_count > 0:
        blockers.append("invalidated_samples_need_review")
    if blockers:
        return "local_simulation_collecting", "本地模拟盘收样中", "warn", blockers
    return "simulation_review_candidate", "可进入模拟盘复核", "ok", []


def _build_strategy_rows(catalog: dict[str, Any], report: dict[str, Any]) -> list[dict[str, Any]]:
    strategies = catalog.get("strategies") if isinstance(catalog.get("strategies"), list) else []
    health_map = _health_rows_by_task(report)
    rows: list[dict[str, Any]] = []
    for item in strategies:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("taskId") or item.get("catalogId") or item.get("candidateId") or item.get("strategyId") or "").strip()
        if not task_id:
            continue
        health = health_map.get(task_id, {})
        counts = _count_logs(task_id)
        stage, stage_label, tone, blockers = _row_stage(health, counts)
        closed_samples = _safe_int(health.get("closedPaperSampleCount"))
        total_r = _safe_float(health.get("totalR"))
        virtual_equity = _safe_float(
            health.get("virtualEquity"),
            VIRTUAL_CAPITAL_PER_STRATEGY * (1 + (total_r / 100)),
        )
        rows.append({
            "taskId": task_id,
            "strategyId": item.get("strategyId") or item.get("candidateId"),
            "name": item.get("name") or item.get("shortName") or item.get("strategyId") or task_id,
            "timeframe": item.get("timeframe"),
            "frequencyBucket": item.get("frequencyBucket"),
            "frequencyLabel": item.get("frequencyLabel"),
            "targetR": item.get("targetR") or 2,
            "selectedPairCount": len(item.get("selectedPairs") if isinstance(item.get("selectedPairs"), list) else []),
            "stage": stage,
            "stageLabel": stage_label,
            "tone": tone,
            "blockers": blockers,
            "logCount": counts["logCount"],
            "signalObservedCount": counts["signalObservedCount"],
            "ruleMatchedCount": _safe_int(health.get("ruleMatchedCount"), counts["ruleMatchedCount"]),
            "closedSampleCount": closed_samples,
            "riskWarningCount": _safe_int(health.get("riskWarningCount"), counts["riskWarningCount"]),
            "invalidatedCount": _safe_int(health.get("invalidatedCount"), counts["invalidatedCount"]),
            "healthScore": _safe_float(health.get("healthScore")),
            "totalR": total_r,
            "virtualCapital": VIRTUAL_CAPITAL_PER_STRATEGY,
            "virtualEquity": round(virtual_equity, 2),
            "latestLogAt": health.get("latestLogAt"),
            "nextAction": (
                "继续累计闭合样本和失败样本；不进入交易所 testnet。"
                if blockers
                else "可以进入模拟盘复核队列；仍然不能创建真实订单。"
            ),
        })
    rows.sort(key=lambda row: (row["stage"] != "simulation_review_candidate", -row["closedSampleCount"], -row["healthScore"]))
    return rows


def _learning_status(rows: list[dict[str, Any]]) -> dict[str, Any]:
    closed_samples = sum(_safe_int(row.get("closedSampleCount")) for row in rows)
    ready = closed_samples >= MIN_CLOSED_SAMPLES_FOR_BASELINE_LEARNING
    latest_snapshots = list_local_sandbox_learning_snapshots(1)
    latest = latest_snapshots[0] if latest_snapshots and isinstance(latest_snapshots[0], dict) else {}
    return {
        "status": "baseline_learning_ready" if ready else "collecting_simulation_samples",
        "statusLabel": "可做基线学习" if ready else "继续收集模拟样本",
        "closedSampleCount": closed_samples,
        "minimumBaselineSamples": MIN_CLOSED_SAMPLES_FOR_BASELINE_LEARNING,
        "latestSnapshotId": latest.get("snapshotId"),
        "featureFamilies": [
            "strategy_family",
            "timeframe",
            "health_score",
            "rule_match_count",
            "risk_warning_count",
            "invalidated_count",
            "total_r",
            "virtual_equity",
        ],
        "labelFields": [
            "outcome_r",
            "closed_sample_win_loss",
            "risk_invalidated",
            "next_snapshot_health_delta",
        ],
        "nextAction": (
            "样本已达到基线学习门槛，可以开始训练研究用基线模型；模型仍不能直接下单。"
            if ready
            else "继续让本地模拟盘运行，优先收集闭合样本、失败原因和风险标签。"
        ),
    }


def build_simulation_bridge() -> dict[str, Any]:
    catalog = build_usable_strategy_catalog()
    report = _latest_daily_report()
    rows = _build_strategy_rows(catalog, report)
    runner_payload = get_local_sandbox_auto_runner_status()
    runner = runner_payload.get("autoRunner") if isinstance(runner_payload.get("autoRunner"), dict) else {}
    candidate_count = sum(1 for row in rows if row.get("stage") == "simulation_review_candidate")
    total_closed = sum(_safe_int(row.get("closedSampleCount")) for row in rows)
    total_equity = round(sum(_safe_float(row.get("virtualEquity")) for row in rows), 2)
    total_capital = round(sum(_safe_float(row.get("virtualCapital")) for row in rows), 2)
    local_ready = len(rows) > 0
    runner_enabled = bool(runner.get("enabled"))
    bridge_stage = "local_simulation_running" if runner_enabled else "local_simulation_ready" if local_ready else "waiting_for_strategy_catalog"
    summary = {
        "strategyCount": len(rows),
        "localSimulationReady": local_ready,
        "localSimulationRunning": runner_enabled,
        "simulationReviewCandidateCount": candidate_count,
        "totalClosedSampleCount": total_closed,
        "totalVirtualCapital": total_capital,
        "totalVirtualEquity": total_equity,
        "stage": bridge_stage,
        "stageLabel": (
            "本地模拟盘运行中"
            if runner_enabled
            else "本地模拟盘可启动"
            if local_ready
            else "等待策略目录"
        ),
        "nextAction": (
            "保持控制台运行，继续累计闭合样本；达到门槛后再讨论 testnet。"
            if runner_enabled
            else "点击启动本地沙盒，让候选策略进入持续模拟观察。"
            if local_ready
            else "先导入策略报告，再建立本地模拟盘任务。"
        ),
    }
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "summary": summary,
        "autoRunner": runner,
        "strategyRows": rows,
        "learningStatus": _learning_status(rows),
        "simulationContract": {
            "localSandboxAvailable": local_ready,
            "exchangeTestnetEnabled": False,
            "exchangeTestnetAllowedInThisVersion": False,
            "paperOrderCreationAllowed": False,
            "realOrderCreationAllowed": False,
            "apiKeyStorageAllowed": False,
            "requiredBeforeExchangeTestnet": [
                "manual approval",
                "separate testnet credential vault",
                "order lifecycle simulator",
                "kill switch",
                "max loss and max order limits",
                "at least 30 closed samples per promoted strategy",
                "risk and invalidation review completed",
            ],
            "note": "This bridge makes local simulation observable and learnable. It does not connect Trade API, store API keys, or create orders.",
        },
        "safetyBoundary": SAFETY_BOUNDARY,
    }
