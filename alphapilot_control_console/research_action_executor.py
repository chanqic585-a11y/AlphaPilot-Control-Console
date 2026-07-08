from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .config import SAFETY_BOUNDARY
from .state_store import (
    list_research_action_execution_runs,
    now_iso,
    save_research_action_execution_run,
    update_weakness_action_task,
)
from .weakness_action_board import build_weakness_action_board


CONTROL_CONSOLE_VERSION = "V13.8"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8"
MIN_RESEARCH_SAMPLE_COUNT = 30
MIN_STABLE_SAMPLE_COUNT = 80
MIN_REVIEW_SCORE = 55.0
MIN_STABLE_REVIEW_SCORE = 65.0


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


def _build_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"research_action_executor_v13_8::{stamp}"


def _check_status(passed: bool, blocked: bool = False) -> str:
    if blocked:
        return "blocked"
    return "passed" if passed else "needs_work"


def _build_checks(action: dict[str, Any]) -> list[dict[str, Any]]:
    sample_count = _safe_int(action.get("sampleCount"))
    weakness_count = _safe_int(action.get("weaknessCount"))
    average_score = _safe_float(action.get("averageReviewScore"))
    code = str(action.get("weaknessCode") or "")
    severity = str(action.get("severity") or "warning")
    blocked_upgrade = bool(action.get("blockedUpgrade"))
    path_missing = code == "path_missing"
    checks = [
        {
            "checkId": "sample_expansion",
            "label": "样本扩展检查",
            "status": _check_status(sample_count >= MIN_RESEARCH_SAMPLE_COUNT, path_missing),
            "evidence": f"当前样本 {sample_count}/{MIN_RESEARCH_SAMPLE_COUNT}",
            "nextAction": (
                "先补齐路径字段和唯一样本键，再继续扩样本。"
                if path_missing
                else "继续让本地沙盒运行，优先补足闭合样本。"
                if sample_count < MIN_RESEARCH_SAMPLE_COUNT
                else "样本数达到基础复核线，进入拆分检查。"
            ),
        },
        {
            "checkId": "parameter_stress",
            "label": "参数压力检查",
            "status": _check_status(average_score >= MIN_REVIEW_SCORE, severity == "danger" and average_score < 45),
            "evidence": f"平均复盘分 {average_score:.2f}/{MIN_REVIEW_SCORE:.0f}",
            "nextAction": "不要放宽 2R；只允许收紧过滤、缩短低效率持有或降低触发频率。",
        },
        {
            "checkId": "regime_breakdown",
            "label": "行情状态拆分",
            "status": _check_status(sample_count >= MIN_RESEARCH_SAMPLE_COUNT and weakness_count <= max(1, sample_count // 2)),
            "evidence": f"弱点次数 {weakness_count}，样本 {sample_count}",
            "nextAction": "按 pair、direction、BTC regime 和 volatility bucket 拆分弱点集中区。",
        },
        {
            "checkId": "cost_slippage_stress",
            "label": "滑点手续费压力",
            "status": _check_status(code != "cost_drag_high" and average_score >= MIN_REVIEW_SCORE),
            "evidence": f"弱点类型 {code or 'unknown'}",
            "nextAction": "若成本拖累重复出现，应降低交易频率或提高最小 ATR/成交量过滤。",
        },
        {
            "checkId": "strategy_simplification",
            "label": "策略简化对比",
            "status": _check_status(not blocked_upgrade and average_score >= MIN_STABLE_REVIEW_SCORE),
            "evidence": f"阻止升级={blocked_upgrade}，稳定线 {average_score:.2f}/{MIN_STABLE_REVIEW_SCORE:.0f}",
            "nextAction": "如果弱点仍阻止升级，优先删减复杂触发条件，保留最可解释规则。",
        },
    ]
    return checks


def _target_status(action: dict[str, Any], checks: list[dict[str, Any]]) -> tuple[str, str]:
    sample_count = _safe_int(action.get("sampleCount"))
    average_score = _safe_float(action.get("averageReviewScore"))
    blocked = bool(action.get("blockedUpgrade"))
    code = str(action.get("weaknessCode") or "")
    failed = [row for row in checks if row.get("status") != "passed"]
    if code == "path_missing" or sample_count < MIN_RESEARCH_SAMPLE_COUNT:
        return "needs_more_samples", "证据不足或路径字段不足，先补样本和字段。"
    if blocked or failed:
        return "in_progress", "行动项仍阻止升级，需要继续执行本地研究检查。"
    if sample_count >= MIN_STABLE_SAMPLE_COUNT and average_score >= MIN_STABLE_REVIEW_SCORE:
        return "resolved", "样本和复盘分达到缓解线，可标记为已处理但仍需后续复核。"
    return "in_progress", "基础检查通过一部分，但还没有达到稳定缓解线。"


def _build_execution_row(action: dict[str, Any], apply_updates: bool) -> dict[str, Any]:
    checks = _build_checks(action)
    target_status, conclusion = _target_status(action, checks)
    current_status = str(action.get("taskStatus") or "todo")
    note = (
        f"V13.8 自动研究执行：{conclusion} "
        f"样本={_safe_int(action.get('sampleCount'))}，平均复盘分={_safe_float(action.get('averageReviewScore')):.2f}。"
    )
    updated = None
    if apply_updates and current_status not in {"resolved", "archived"}:
        updated = update_weakness_action_task(
            action_id=str(action.get("actionId") or ""),
            task_status=target_status,
            note=note,
            owner="research_action_executor",
        )
    return {
        "actionId": action.get("actionId"),
        "strategyId": action.get("strategyId"),
        "taskId": action.get("taskId"),
        "strategyName": action.get("strategyName"),
        "weaknessCode": action.get("weaknessCode"),
        "weaknessLabel": action.get("weaknessLabel"),
        "priorityTone": action.get("priorityTone"),
        "priorityScore": action.get("priorityScore"),
        "currentTaskStatus": current_status,
        "targetTaskStatus": target_status,
        "targetTaskStatusLabel": {
            "todo": "待处理",
            "in_progress": "处理中",
            "needs_more_samples": "待更多样本",
            "resolved": "已处理",
            "archived": "已归档",
        }.get(target_status, target_status),
        "conclusion": conclusion,
        "checks": checks,
        "updatedTask": updated,
        "safetyNote": "研究执行器只写本地任务状态，不修改策略代码，不创建订单。",
    }


def build_research_action_executor(apply_updates: bool = False, limit: int = 200) -> dict[str, Any]:
    board = build_weakness_action_board(limit=limit)
    actions = [
        action
        for action in board.get("actions", [])
        if isinstance(action, dict) and action.get("taskStatus") not in {"archived"}
    ]
    rows = [_build_execution_row(action, apply_updates=apply_updates) for action in actions]
    updated_count = sum(1 for row in rows if row.get("updatedTask"))
    needs_more = sum(1 for row in rows if row.get("targetTaskStatus") == "needs_more_samples")
    in_progress = sum(1 for row in rows if row.get("targetTaskStatus") == "in_progress")
    resolved = sum(1 for row in rows if row.get("targetTaskStatus") == "resolved")
    blocked = sum(
        1
        for row in rows
        for check in row.get("checks", [])
        if isinstance(check, dict) and check.get("status") == "blocked"
    )
    run = {
        "runId": _build_run_id(),
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "applyUpdates": apply_updates,
        "summary": {
            "actionCount": len(rows),
            "updatedTaskCount": updated_count,
            "needsMoreSamplesCount": needs_more,
            "inProgressCount": in_progress,
            "resolvedCandidateCount": resolved,
            "blockedCheckCount": blocked,
            "dryRunApproved": False,
            "liveTradingApproved": False,
            "nextAction": (
                "已把研究行动项转为本地检查结果；优先处理 blocked 和待更多样本的弱点。"
                if rows
                else "等待弱点行动项生成。"
            ),
        },
        "executions": rows,
        "latestRuns": list_research_action_execution_runs(5),
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Research action executor is local research only. No API keys, Trade API, exchange Dry-run, or orders.",
    }
    if apply_updates:
        run = save_research_action_execution_run(run)
    return run
