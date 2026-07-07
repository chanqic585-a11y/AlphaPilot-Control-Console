from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from .config import SAFETY_BOUNDARY
from .state_store import list_manual_execution_tickets, now_iso, save_manual_execution_ticket


CONTROL_CONSOLE_VERSION = "V13.7.36"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_36"
BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")
LIVE_READINESS_REVIEW_DATE = date(2026, 7, 10)
LIVE_READINESS_REVIEW_LABEL = "2026年7月10日（北京时间）"

MIN_QUALITY_SCORE = 60
MIN_LOG_COUNT = 10
MIN_RULE_MATCHED = 3
MIN_CLOSED_SAMPLES = 5
MIN_HISTORICAL_TRADES = 30
MIN_PROFIT_FACTOR = 1.25
MIN_REWARD_RISK = 1.8
MAX_DRAWDOWN_PCT = 25
MAX_RISK_WARNINGS = 1
MAX_INVALIDATIONS = 0


def _safe_number(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    return int(_safe_number(value, fallback))


def _today_beijing() -> date:
    return datetime.now(BEIJING_TZ).date()


def _days_until_review() -> int:
    return max(0, (LIVE_READINESS_REVIEW_DATE - _today_beijing()).days)


def _build_metric_checks(metrics: dict[str, Any]) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    blockers: list[str] = []
    trade_count = _safe_int(metrics.get("tradeCount") or metrics.get("filledSignalCount"))
    profit_factor = _safe_number(metrics.get("profitFactor"))
    reward_risk = _safe_number(metrics.get("rewardRiskRatio") or metrics.get("targetRewardRiskRatio"))
    max_drawdown = _safe_number(metrics.get("maxDrawdownPct"))

    if trade_count >= MIN_HISTORICAL_TRADES:
        passed.append(f"历史样本 {trade_count} >= {MIN_HISTORICAL_TRADES}")
    else:
        blockers.append(f"历史样本不足：{trade_count}/{MIN_HISTORICAL_TRADES}")

    if profit_factor >= MIN_PROFIT_FACTOR:
        passed.append(f"PF {profit_factor:.2f} >= {MIN_PROFIT_FACTOR:.2f}")
    else:
        blockers.append(f"PF 不足：{profit_factor:.2f}/{MIN_PROFIT_FACTOR:.2f}")

    if reward_risk >= MIN_REWARD_RISK:
        passed.append(f"盈亏比 {reward_risk:.2f} >= {MIN_REWARD_RISK:.2f}")
    else:
        blockers.append(f"盈亏比不足：{reward_risk:.2f}/{MIN_REWARD_RISK:.2f}")

    if max_drawdown <= MAX_DRAWDOWN_PCT:
        passed.append(f"最大回撤 {max_drawdown:.2f}% <= {MAX_DRAWDOWN_PCT}%")
    else:
        blockers.append(f"最大回撤过高：{max_drawdown:.2f}%")

    return passed, blockers


def _build_observation_checks(task: dict[str, Any], quality_row: dict[str, Any]) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    blockers: list[str] = []
    local_observation = task.get("localObservation") if isinstance(task.get("localObservation"), dict) else {}
    quality_score = _safe_number(quality_row.get("qualityScore"))
    log_count = _safe_int(quality_row.get("logCount") or local_observation.get("logCount"))
    rule_count = _safe_int(quality_row.get("ruleMatchedCount") or local_observation.get("ruleMatchedCount"))
    closed_count = _safe_int(
        quality_row.get("closedPaperSampleCount") or local_observation.get("closedPaperSampleCount")
    )
    risk_count = _safe_int(quality_row.get("riskWarningCount") or local_observation.get("riskWarningCount"))
    invalidated_count = _safe_int(quality_row.get("invalidatedCount") or local_observation.get("invalidatedCount"))

    if quality_score >= MIN_QUALITY_SCORE:
        passed.append(f"观察质量 {quality_score:.0f} >= {MIN_QUALITY_SCORE}")
    else:
        blockers.append(f"观察质量不足：{quality_score:.0f}/{MIN_QUALITY_SCORE}")

    if log_count >= MIN_LOG_COUNT:
        passed.append(f"观察日志 {log_count} >= {MIN_LOG_COUNT}")
    else:
        blockers.append(f"观察日志不足：{log_count}/{MIN_LOG_COUNT}")

    if rule_count >= MIN_RULE_MATCHED:
        passed.append(f"规则匹配 {rule_count} >= {MIN_RULE_MATCHED}")
    else:
        blockers.append(f"规则匹配不足：{rule_count}/{MIN_RULE_MATCHED}")

    if closed_count >= MIN_CLOSED_SAMPLES:
        passed.append(f"闭合样本 {closed_count} >= {MIN_CLOSED_SAMPLES}")
    else:
        blockers.append(f"闭合样本不足：{closed_count}/{MIN_CLOSED_SAMPLES}")

    if risk_count <= MAX_RISK_WARNINGS:
        passed.append(f"风险记录 {risk_count} <= {MAX_RISK_WARNINGS}")
    else:
        blockers.append(f"风险记录过多：{risk_count}")

    if invalidated_count <= MAX_INVALIDATIONS:
        passed.append("暂无未处理失效记录")
    else:
        blockers.append(f"存在失效记录：{invalidated_count}")

    return passed, blockers


def _task_key(task: dict[str, Any]) -> str:
    return str(task.get("taskId") or task.get("candidateId") or task.get("strategyId") or "").strip()


def _readiness_scores(metrics: dict[str, Any], quality_row: dict[str, Any]) -> float:
    observation_score = min(
        100.0,
        (_safe_number(quality_row.get("qualityScore")) * 0.45)
        + min(_safe_int(quality_row.get("closedPaperSampleCount")) / MIN_CLOSED_SAMPLES, 1) * 25
        + min(_safe_int(quality_row.get("ruleMatchedCount")) / MIN_RULE_MATCHED, 1) * 15
        + min(_safe_int(quality_row.get("logCount")) / MIN_LOG_COUNT, 1) * 15,
    )
    metric_score = 0.0
    metric_score += min(_safe_number(metrics.get("profitFactor")) / max(MIN_PROFIT_FACTOR, 0.1), 1) * 30
    metric_score += min(_safe_number(metrics.get("rewardRiskRatio")) / max(MIN_REWARD_RISK, 0.1), 1) * 25
    metric_score += min(
        _safe_number(metrics.get("tradeCount") or metrics.get("filledSignalCount")) / MIN_HISTORICAL_TRADES,
        1,
    ) * 25
    drawdown = _safe_number(metrics.get("maxDrawdownPct"), MAX_DRAWDOWN_PCT + 1)
    metric_score += 20 if drawdown <= MAX_DRAWDOWN_PCT else max(0, 20 - (drawdown - MAX_DRAWDOWN_PCT))
    return round((observation_score * 0.55) + (metric_score * 0.45), 2)


def _build_readiness_row(task: dict[str, Any], quality_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    task_id = _task_key(task)
    quality_row = quality_map.get(task_id, {})
    metrics = task.get("historicalMetrics") if isinstance(task.get("historicalMetrics"), dict) else {}
    if not metrics:
        metrics = quality_row.get("historicalMetrics") if isinstance(quality_row.get("historicalMetrics"), dict) else {}

    metric_passed, metric_blockers = _build_metric_checks(metrics)
    observation_passed, observation_blockers = _build_observation_checks(task, quality_row)
    blockers = metric_blockers + observation_blockers
    passed = metric_passed + observation_passed

    days_until = _days_until_review()
    if days_until > 0:
        blockers.append(f"等待 {LIVE_READINESS_REVIEW_LABEL} 前向复核")

    hard_execution_blockers = [
        "Trade API 未接入",
        "Withdraw API 未接入",
        "不保存 API Key",
        "不读取真实账户或真实持仓",
        "不创建真实订单",
    ]
    readiness_score = _readiness_scores(metrics, quality_row)

    if blockers:
        status = "shadow_observation"
        label = "继续影子观察"
        tone = "warn"
    else:
        status = "manual_ticket_ready"
        label = "可生成人工票据"
        tone = "ok"
    if any(("风险记录过多" in item or "失效记录" in item or "回撤过高" in item) for item in blockers):
        status = "blocked_for_review"
        label = "先暂停复核"
        tone = "danger"

    return {
        "taskId": task_id,
        "strategyId": task.get("strategyId"),
        "title": task.get("title") or task.get("candidateId") or task_id,
        "candidateId": task.get("candidateId"),
        "timeframe": task.get("timeframe"),
        "recommendedPairs": task.get("recommendedPairs") if isinstance(task.get("recommendedPairs"), list) else [],
        "metrics": metrics,
        "quality": {
            "qualityScore": quality_row.get("qualityScore"),
            "qualityLabel": quality_row.get("qualityLabelCn") or quality_row.get("qualityLabel"),
            "logCount": quality_row.get("logCount"),
            "ruleMatchedCount": quality_row.get("ruleMatchedCount"),
            "closedPaperSampleCount": quality_row.get("closedPaperSampleCount"),
            "riskWarningCount": quality_row.get("riskWarningCount"),
            "invalidatedCount": quality_row.get("invalidatedCount"),
            "latestLogAt": quality_row.get("latestLogAt"),
        },
        "readinessScore": readiness_score,
        "status": status,
        "statusLabel": label,
        "tone": tone,
        "passedChecks": passed,
        "blockers": blockers,
        "hardExecutionBlockers": hard_execution_blockers,
        "manualTicketAllowed": status == "manual_ticket_ready",
        "nextAction": (
            "可以生成本地人工票据；票据只用于人工复核和记录，不会连接交易所。"
            if status == "manual_ticket_ready"
            else "继续收集 7月10日 前后真实前向观察、规则匹配、闭合结果和风险失效记录。"
        ),
    }


def build_live_readiness(payload: dict[str, Any]) -> dict[str, Any]:
    learning = payload.get("strategyLearningLoop") if isinstance(payload.get("strategyLearningLoop"), dict) else {}
    task_pack = learning.get("paperObservationTaskPack") if isinstance(learning.get("paperObservationTaskPack"), dict) else {}
    quality_panel = learning.get("paperObservationQualityPanel") if isinstance(learning.get("paperObservationQualityPanel"), dict) else {}
    tasks = task_pack.get("paperObservationTasks") if isinstance(task_pack.get("paperObservationTasks"), list) else []
    quality_rows = quality_panel.get("qualityRows") if isinstance(quality_panel.get("qualityRows"), list) else []
    quality_map = {str(row.get("taskId") or ""): row for row in quality_rows if isinstance(row, dict)}
    rows = [_build_readiness_row(task, quality_map) for task in tasks if isinstance(task, dict)]
    rows.sort(key=lambda item: (item["status"] != "manual_ticket_ready", item["status"] == "blocked_for_review", -item["readinessScore"]))

    tickets = list_manual_execution_tickets(20)
    manual_ready = sum(1 for row in rows if row["status"] == "manual_ticket_ready")
    blocked = sum(1 for row in rows if row["status"] == "blocked_for_review")
    shadow = sum(1 for row in rows if row["status"] == "shadow_observation")
    days_until = _days_until_review()
    if manual_ready:
        next_action = "已有策略可生成本地人工票据；仍禁止自动下单，需用户在交易所外部手动决策。"
    elif days_until > 0:
        next_action = f"等待 {LIVE_READINESS_REVIEW_LABEL} 前向数据，当前只做影子观察和本地票据准备。"
    else:
        next_action = "7月10日复核窗口已到，优先补齐观察日志、规则匹配和闭合样本。"

    return {
        "version": CONTROL_CONSOLE_VERSION,
        "generatedAt": now_iso(),
        "source": CONTROL_CONSOLE_SOURCE,
        "reviewDate": LIVE_READINESS_REVIEW_DATE.isoformat(),
        "reviewDateLabel": LIVE_READINESS_REVIEW_LABEL,
        "daysUntilReview": days_until,
        "summary": {
            "candidateCount": len(rows),
            "manualTicketReadyCount": manual_ready,
            "shadowObservationCount": shadow,
            "blockedForReviewCount": blocked,
            "ticketCount": len(tickets),
            "nextAction": next_action,
        },
        "thresholds": {
            "minQualityScore": MIN_QUALITY_SCORE,
            "minLogCount": MIN_LOG_COUNT,
            "minRuleMatched": MIN_RULE_MATCHED,
            "minClosedSamples": MIN_CLOSED_SAMPLES,
            "minHistoricalTrades": MIN_HISTORICAL_TRADES,
            "minProfitFactor": MIN_PROFIT_FACTOR,
            "minRewardRisk": MIN_REWARD_RISK,
            "maxDrawdownPct": MAX_DRAWDOWN_PCT,
            "maxRiskWarnings": MAX_RISK_WARNINGS,
            "maxInvalidations": MAX_INVALIDATIONS,
        },
        "rows": rows,
        "tickets": tickets,
        "safetyBoundary": {
            **SAFETY_BOUNDARY,
            "manualTicketsOnly": True,
            "ticketIsNotOrder": True,
            "liveTradingApproved": False,
        },
        "safetyNotes": [
            "人工票据只是本地复核记录，不是订单。",
            "本版本不保存 API Key，不接 Trade API，不接 Withdraw API。",
            "本版本不读取真实账户或真实持仓，不创建真实订单。",
            "如果用户未来选择手动操作，系统只记录研究上下文和结果。",
        ],
    }


def create_manual_execution_ticket(payload: dict[str, Any], scan_payload: dict[str, Any]) -> dict[str, Any]:
    task_id = str(payload.get("taskId") or "").strip()
    if not task_id:
        raise ValueError("taskId_required")
    readiness = build_live_readiness(scan_payload)
    row = next((item for item in readiness["rows"] if item.get("taskId") == task_id), None)
    if not row:
        raise ValueError("task_not_found")
    if not row.get("manualTicketAllowed"):
        raise PermissionError("manual_ticket_not_allowed")

    ticket = {
        "ticketId": f"manual_ticket::{task_id}::{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "taskId": task_id,
        "strategyId": row.get("strategyId"),
        "title": row.get("title"),
        "status": "draft_manual_review",
        "timeframe": row.get("timeframe"),
        "selectedPair": str(payload.get("selectedPair") or "").strip() or None,
        "manualContextNote": str(payload.get("note") or "").strip(),
        "readinessScore": row.get("readinessScore"),
        "metrics": row.get("metrics"),
        "quality": row.get("quality"),
        "riskPlan": {
            "targetRMultiple": 2,
            "requiresUserManualDecision": True,
            "requiresExternalExchangeManualAction": True,
            "noAutomation": True,
        },
        "checklist": [
            "确认 7月10日 前向数据和当前市场状态。",
            "确认信号仍满足策略说明书中的适用行情。",
            "确认 2R 目标和失效条件已写入备注。",
            "确认这不是交易建议，也不是自动订单。",
        ],
    }
    return save_manual_execution_ticket(ticket)
