from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from .config import SAFETY_BOUNDARY
from .local_sandbox_runner import RISK_UNIT_PERCENT, VIRTUAL_CAPITAL_PER_STRATEGY
from .state_store import (
    list_local_sandbox_daily_reports,
    list_local_sandbox_health_snapshots,
    now_iso,
    save_local_sandbox_daily_report,
)


CONTROL_CONSOLE_VERSION = "V13.7.32"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_32"
BEIJING_TZ = timezone(timedelta(hours=8))


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


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _beijing_date_key(value: Any = None) -> str:
    parsed = _parse_datetime(value) if value is not None else datetime.now(timezone.utc)
    if parsed is None:
        parsed = datetime.now(timezone.utc)
    return parsed.astimezone(BEIJING_TZ).strftime("%Y-%m-%d")


def _parse_outcome_r(value: Any) -> float | None:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        return None
    return _safe_float(match.group(0), 0.0)


def _logs_for_task(task: dict[str, Any]) -> list[dict[str, Any]]:
    rows = task.get("recentLogs") if isinstance(task.get("recentLogs"), list) else []
    return [row for row in rows if isinstance(row, dict)]


def _previous_snapshot_by_task() -> dict[str, dict[str, Any]]:
    snapshots = list_local_sandbox_health_snapshots(500)
    previous: dict[str, dict[str, Any]] = {}
    for row in snapshots:
        task_id = str(row.get("taskId") or "").strip()
        if task_id and task_id not in previous:
            previous[task_id] = row
    return previous


def _health_status(score: float, closed_samples: int, risk_count: int, invalidated_count: int, total_r: float) -> tuple[str, str, str]:
    if risk_count > 0 or invalidated_count > 0:
        return "needs_risk_review", "需要风险复盘", "danger"
    if closed_samples < 5:
        return "collecting_samples", "继续补样本", "warn"
    if score >= 70 and total_r > 0:
        return "healthy_watch", "健康观察", "ok"
    if score >= 50:
        return "continue_observing", "继续观察", "warn"
    return "weak_watch", "弱观察", "danger"


def _trend_from_previous(task_id: str, score: float, previous: dict[str, dict[str, Any]]) -> dict[str, Any]:
    last = previous.get(task_id)
    if not isinstance(last, dict):
        return {"direction": "new", "label": "新快照", "delta": 0}
    last_score = _safe_float(last.get("healthScore"), score)
    delta = round(score - last_score, 2)
    if delta > 1:
        return {"direction": "up", "label": "改善", "delta": delta}
    if delta < -1:
        return {"direction": "down", "label": "转弱", "delta": delta}
    return {"direction": "flat", "label": "稳定", "delta": delta}


def _build_health_row(task: dict[str, Any], date_key: str, previous: dict[str, dict[str, Any]]) -> dict[str, Any]:
    task_id = str(task.get("taskId") or "").strip()
    logs = _logs_for_task(task)
    daily_logs = [log for log in logs if _beijing_date_key(log.get("createdAt")) == date_key]
    outcome_values = [_parse_outcome_r(log.get("outcomeR") if log.get("outcomeR") is not None else log.get("outcome")) for log in logs]
    outcome_values = [value for value in outcome_values if value is not None]
    daily_outcomes = [
        _parse_outcome_r(log.get("outcomeR") if log.get("outcomeR") is not None else log.get("outcome"))
        for log in daily_logs
    ]
    daily_outcomes = [value for value in daily_outcomes if value is not None]
    total_r = round(sum(outcome_values), 2)
    daily_r = round(sum(daily_outcomes), 2)
    closed_samples = len(outcome_values)
    daily_closed = len(daily_outcomes)
    win_count = sum(1 for value in outcome_values if value > 0)
    loss_count = sum(1 for value in outcome_values if value < 0)
    rule_count = sum(1 for log in logs if log.get("ruleMatched") or log.get("logType") == "rule_matched")
    signal_count = sum(1 for log in logs if log.get("signalObserved"))
    risk_count = sum(1 for log in logs if log.get("logType") == "risk_warning")
    invalidated_count = sum(1 for log in logs if log.get("logType") == "invalidated")
    latest_log_at = logs[0].get("createdAt") if logs else None
    latest_dt = _parse_datetime(latest_log_at)
    age_days = None
    if latest_dt is not None:
        age_days = max(0.0, (datetime.now(timezone.utc) - latest_dt.astimezone(timezone.utc)).total_seconds() / 86400)

    plan = task.get("observationPlan") if isinstance(task.get("observationPlan"), dict) else {}
    target_closed = max(1, _safe_int(plan.get("targetClosedSamples"), 25))
    min_rules = max(1, _safe_int(plan.get("minimumRuleMatchedSignals"), 12))
    sample_score = min(closed_samples / target_closed, 1.0) * 30
    rule_score = min(rule_count / min_rules, 1.0) * 25
    outcome_score = max(0.0, min(20.0, 10.0 + total_r * 2.0))
    recency_score = 0.0
    if age_days is not None:
        recency_score = 15.0 if age_days <= 1 else 10.0 if age_days <= 3 else 5.0
    risk_score = max(0.0, 10.0 - (risk_count * 3.0) - (invalidated_count * 3.0))
    health_score = round(sample_score + rule_score + outcome_score + recency_score + risk_score, 2)
    status, status_label, tone = _health_status(health_score, closed_samples, risk_count, invalidated_count, total_r)
    trend = _trend_from_previous(task_id, health_score, previous)
    virtual_equity = round(VIRTUAL_CAPITAL_PER_STRATEGY * (1 + ((total_r * RISK_UNIT_PERCENT) / 100)), 2)
    next_action = "继续每日生成本地观察日志，优先补闭合样本和失效原因。"
    if status == "healthy_watch":
        next_action = "保持本地沙盒观察，继续确认不同市场状态下的稳定性。"
    elif status == "needs_risk_review":
        next_action = "先复盘风险/失效记录，再继续生成新的沙盒样本。"
    elif status == "weak_watch":
        next_action = "暂停升级想法，优先补样本并检查是否只是历史过拟合。"

    return {
        "taskId": task_id,
        "strategyId": task.get("strategyId"),
        "title": task.get("title") or task.get("candidateId") or task_id,
        "timeframe": task.get("timeframe"),
        "family": task.get("family"),
        "dateKey": date_key,
        "healthScore": health_score,
        "healthStatus": status,
        "healthStatusLabel": status_label,
        "healthTone": tone,
        "trend": trend,
        "logCount": len(logs),
        "dailyLogCount": len(daily_logs),
        "closedPaperSampleCount": closed_samples,
        "dailyClosedSampleCount": daily_closed,
        "ruleMatchedCount": rule_count,
        "signalObservedCount": signal_count,
        "riskWarningCount": risk_count,
        "invalidatedCount": invalidated_count,
        "totalR": total_r,
        "dailyR": daily_r,
        "winCount": win_count,
        "lossCount": loss_count,
        "virtualCapital": VIRTUAL_CAPITAL_PER_STRATEGY,
        "virtualEquity": virtual_equity,
        "virtualPnl": round(virtual_equity - VIRTUAL_CAPITAL_PER_STRATEGY, 2),
        "latestLogAt": latest_log_at,
        "targetClosedSamples": target_closed,
        "minimumRuleMatchedSignals": min_rules,
        "scoreComponents": {
            "sampleScore": round(sample_score, 2),
            "ruleScore": round(rule_score, 2),
            "outcomeScore": round(outcome_score, 2),
            "recencyScore": round(recency_score, 2),
            "riskScore": round(risk_score, 2),
        },
        "nextAction": next_action,
        "safetyNote": "Health score describes local sandbox observation completeness, not profit probability or trade safety.",
    }


def build_local_sandbox_daily_report(learning_loop: dict[str, Any] | None = None, date_key: str | None = None) -> dict[str, Any]:
    if not isinstance(learning_loop, dict):
        from .importer import scan_quant_engine

        learning_loop = scan_quant_engine().get("strategyLearningLoop") or {}
    date_key = date_key or _beijing_date_key()
    pack = learning_loop.get("paperObservationTaskPack") if isinstance(learning_loop.get("paperObservationTaskPack"), dict) else {}
    tasks = pack.get("paperObservationTasks") if isinstance(pack.get("paperObservationTasks"), list) else []
    previous = _previous_snapshot_by_task()
    rows = [_build_health_row(task, date_key, previous) for task in tasks if isinstance(task, dict)]
    rows.sort(key=lambda row: (float(row.get("healthScore") or 0), float(row.get("totalR") or 0)), reverse=True)
    daily_log_count = sum(_safe_int(row.get("dailyLogCount")) for row in rows)
    daily_closed_count = sum(_safe_int(row.get("dailyClosedSampleCount")) for row in rows)
    total_closed_count = sum(_safe_int(row.get("closedPaperSampleCount")) for row in rows)
    total_r = round(sum(_safe_float(row.get("totalR")) for row in rows), 2)
    daily_r = round(sum(_safe_float(row.get("dailyR")) for row in rows), 2)
    improving_count = sum(1 for row in rows if row.get("trend", {}).get("direction") == "up")
    declining_count = sum(1 for row in rows if row.get("trend", {}).get("direction") == "down")
    average_health = round(sum(_safe_float(row.get("healthScore")) for row in rows) / len(rows), 2) if rows else 0
    report = {
        "reportId": f"local_sandbox_daily::{date_key}::{datetime.now(timezone.utc).strftime('%H%M%S')}",
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "dateKey": date_key,
        "summary": {
            "strategyCount": len(rows),
            "dailyLogCount": daily_log_count,
            "dailyClosedSampleCount": daily_closed_count,
            "totalClosedSampleCount": total_closed_count,
            "dailyR": daily_r,
            "totalR": total_r,
            "averageHealthScore": average_health,
            "improvingCount": improving_count,
            "decliningCount": declining_count,
            "bestStrategyTitle": rows[0].get("title") if rows else None,
            "bestStrategyHealthScore": rows[0].get("healthScore") if rows else None,
            "nextAction": "继续本地沙盒观察；优先看健康分趋势、闭合样本数量和风险复盘记录。",
        },
        "strategyHealthRows": rows,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Daily sandbox report is a local review artifact only; it does not create orders or enable testnet/live execution.",
    }
    return save_local_sandbox_daily_report(report)
