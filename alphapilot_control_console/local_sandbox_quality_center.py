from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .config import SAFETY_BOUNDARY
from .sandbox_auto_runner import get_local_sandbox_auto_runner_status
from .simulation_review import build_simulation_review
from .state_store import list_local_sandbox_daily_reports, list_paper_observation_logs, now_iso, read_exchange_probe_results


CONTROL_CONSOLE_VERSION = "V13.8.5"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8_5"


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


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _extract_outcome_r(row: dict[str, Any]) -> float | None:
    if row.get("outcomeR") is not None:
        return _safe_float(row.get("outcomeR"))
    text = str(row.get("outcome") or "").strip().upper().replace(" ", "")
    if not text.endswith("R"):
        return None
    return _safe_float(text[:-1])


def _average_holding_minutes(logs: list[dict[str, Any]]) -> float | None:
    values = []
    for row in logs:
        value = row.get("holdingTimeMinutes")
        if value is None:
            continue
        parsed = _safe_float(value, -1)
        if parsed >= 0:
            values.append(parsed)
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _latest_trigger(logs: list[dict[str, Any]]) -> dict[str, Any]:
    if not logs:
        return {
            "latestLogAt": None,
            "latestPair": None,
            "latestTimeframe": None,
            "latestOutcomeR": None,
            "latestReason": "暂无触发记录",
            "latestReplayWindowId": None,
        }
    latest = sorted(logs, key=lambda item: str(item.get("createdAt") or ""), reverse=True)[0]
    return {
        "latestLogAt": latest.get("createdAt"),
        "latestPair": latest.get("pair"),
        "latestTimeframe": latest.get("timeframe"),
        "latestOutcomeR": _extract_outcome_r(latest),
        "latestReason": latest.get("note") or latest.get("outcomeReason") or latest.get("logType") or "最近本地沙盒观察",
        "latestReplayWindowId": latest.get("replayWindowId"),
    }


def _status_from_review(row: dict[str, Any], metrics: dict[str, Any], warnings: list[str]) -> tuple[str, str, str, str]:
    closed = _safe_int(metrics.get("closedSamples"))
    risk_count = _safe_int(metrics.get("riskWarningCount"))
    invalidated_count = _safe_int(metrics.get("invalidatedCount"))
    profit_factor = metrics.get("profitFactor")
    status = str(row.get("status") or "")
    if risk_count > 0 or invalidated_count > 0:
        return ("pause_for_risk_review", "先暂停复盘", "danger", "存在风险或失效样本，先解释失败原因。")
    if closed < 30:
        return ("insufficient_samples", "样本不足", "warn", "先补到 30 个闭合样本，再做晋级判断。")
    if status == "promoted_candidate":
        return ("testnet_prep_candidate", "Testnet 准备候选", "ok", "满足本地复核门槛，但仍不能连接交易所或创建订单。")
    if profit_factor is not None and _safe_float(profit_factor) < 0.8:
        return ("pause_observation", "暂停观察", "danger", "收益质量偏弱，先降级为参考样本。")
    if "concentration_risk" in warnings:
        return ("continue_with_concentration_review", "继续但查集中度", "warn", "样本过于集中，先扩展币种或窗口。")
    return ("continue_observing", "继续观察", "ok", "可以继续沙盒观察，补不同市场状态下的闭合样本。")


def _row_by_task_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("taskId") or "").strip()
        if task_id:
            result[task_id] = row
    return result


def _build_strategy_quality_row(review_row: dict[str, Any], health_row: dict[str, Any]) -> dict[str, Any]:
    task_id = str(review_row.get("taskId") or review_row.get("strategyId") or "").strip()
    logs = list_paper_observation_logs(task_id)
    if isinstance(logs, dict):
        flat_logs: list[dict[str, Any]] = []
        for values in logs.values():
            if isinstance(values, list):
                flat_logs.extend(item for item in values if isinstance(item, dict))
        logs = flat_logs
    if not isinstance(logs, list):
        logs = []
    logs = [item for item in logs if isinstance(item, dict)]
    metrics = review_row.get("metrics") if isinstance(review_row.get("metrics"), dict) else {}
    warnings = review_row.get("warnings") if isinstance(review_row.get("warnings"), list) else []
    promotion_status, promotion_label, tone, next_action = _status_from_review(review_row, metrics, warnings)
    sample_gate = review_row.get("sampleGate") if isinstance(review_row.get("sampleGate"), dict) else {}
    latest_trigger = _latest_trigger(logs)
    closed_samples = _safe_int(metrics.get("closedSamples"))
    log_count = _safe_int(metrics.get("logCount"), len(logs))
    duplicate_skipped = sum(_safe_int(log.get("skippedDuplicateCount")) for log in logs)
    data_gap_count = sum(1 for log in logs if log.get("dataStatus") in {"missing_data", "data_gap", "unavailable"})
    return {
        "taskId": task_id,
        "strategyId": review_row.get("strategyId"),
        "strategyName": review_row.get("strategyName") or health_row.get("title") or task_id,
        "timeframe": review_row.get("timeframe") or health_row.get("timeframe"),
        "status": review_row.get("status"),
        "statusLabel": review_row.get("statusLabel"),
        "promotionStatus": promotion_status,
        "promotionLabel": promotion_label,
        "tone": tone,
        "nextAction": next_action,
        "qualityScore": health_row.get("healthScore"),
        "qualityStatus": health_row.get("healthStatusLabel"),
        "closedSamples": closed_samples,
        "reviewMinimum": _safe_int(sample_gate.get("reviewMinimum"), 30),
        "dryRunMinimum": _safe_int(sample_gate.get("dryRunMinimum"), 100),
        "winRate": metrics.get("winRate"),
        "profitFactor": metrics.get("profitFactor"),
        "averageWinR": metrics.get("averageWinR"),
        "averageLossR": metrics.get("averageLossR"),
        "totalR": metrics.get("totalR"),
        "maxConsecutiveLosses": metrics.get("maxConsecutiveLosses"),
        "maxDrawdownR": metrics.get("maxDrawdownR"),
        "averageHoldingMinutes": _average_holding_minutes(logs),
        "logCount": log_count,
        "ruleMatchedCount": metrics.get("ruleMatchedCount"),
        "riskWarningCount": metrics.get("riskWarningCount"),
        "invalidatedCount": metrics.get("invalidatedCount"),
        "duplicateSkippedCount": duplicate_skipped,
        "dataGapCount": data_gap_count,
        "warnings": warnings,
        "latestTrigger": latest_trigger,
        "sampleProgress": round(closed_samples / max(1, _safe_int(sample_gate.get("reviewMinimum"), 30)) * 100, 2),
        "detailBullets": [
            f"闭合样本 {closed_samples}/{_safe_int(sample_gate.get('reviewMinimum'), 30)}",
            f"胜率 {metrics.get('winRate') if metrics.get('winRate') is not None else '--'}%",
            f"PF {metrics.get('profitFactor') if metrics.get('profitFactor') is not None else '--'}",
            f"最大连亏 {metrics.get('maxConsecutiveLosses') if metrics.get('maxConsecutiveLosses') is not None else 0}",
        ],
    }


def build_local_sandbox_quality_center() -> dict[str, Any]:
    daily_reports = list_local_sandbox_daily_reports(1)
    latest_daily = daily_reports[0] if daily_reports and isinstance(daily_reports[0], dict) else {}
    health_rows = latest_daily.get("strategyHealthRows") if isinstance(latest_daily.get("strategyHealthRows"), list) else []
    health_by_task = _row_by_task_id(health_rows)
    review = build_simulation_review()
    review_rows = review.get("queue") if isinstance(review.get("queue"), list) else []
    rows = [
        _build_strategy_quality_row(row, health_by_task.get(str(row.get("taskId") or ""), {}))
        for row in review_rows
        if isinstance(row, dict)
    ]
    rows.sort(
        key=lambda row: (
            row["promotionStatus"] != "testnet_prep_candidate",
            row["promotionStatus"] != "continue_observing",
            -_safe_int(row.get("closedSamples")),
            -_safe_float(row.get("profitFactor"), -1),
        )
    )
    auto_runner = get_local_sandbox_auto_runner_status()
    runner = auto_runner.get("autoRunner") if isinstance(auto_runner.get("autoRunner"), dict) else {}
    events = auto_runner.get("events") if isinstance(auto_runner.get("events"), list) else []
    public_probe = read_exchange_probe_results() or {}
    total_closed = sum(_safe_int(row.get("closedSamples")) for row in rows)
    total_data_gaps = sum(_safe_int(row.get("dataGapCount")) for row in rows)
    total_duplicates = sum(_safe_int(row.get("duplicateSkippedCount")) for row in rows)
    summary = {
        "strategyCount": len(rows),
        "totalClosedSamples": total_closed,
        "candidateContinueCount": sum(1 for row in rows if row.get("promotionStatus") == "continue_observing"),
        "testnetPrepCandidateCount": sum(1 for row in rows if row.get("promotionStatus") == "testnet_prep_candidate"),
        "insufficientSampleCount": sum(1 for row in rows if row.get("promotionStatus") == "insufficient_samples"),
        "pauseCount": sum(1 for row in rows if str(row.get("promotionStatus") or "").startswith("pause")),
        "riskReviewCount": sum(1 for row in rows if _safe_int(row.get("riskWarningCount")) > 0 or _safe_int(row.get("invalidatedCount")) > 0),
        "totalDataGapCount": total_data_gaps,
        "totalDuplicateSkippedCount": total_duplicates,
        "averageQualityScore": round(
            sum(_safe_float(row.get("qualityScore")) for row in rows) / max(1, len(rows)),
            2,
        ) if rows else 0,
        "bestStrategyName": rows[0].get("strategyName") if rows else None,
        "sandboxRunning": bool(runner.get("enabled")),
        "runnerStatus": runner.get("status") or "disabled",
        "replayCursor": runner.get("replayCursor"),
        "nextRunAt": runner.get("nextRunAt"),
        "lastRunAt": runner.get("lastRunAt"),
        "lastRunGenerated": events[0].get("generatedLogCount") if events and isinstance(events[0], dict) else None,
        "lastRunClosed": events[0].get("closedSampleCount") if events and isinstance(events[0], dict) else None,
        "lastRunDuplicates": events[0].get("skippedDuplicateCount") if events and isinstance(events[0], dict) else None,
        "lastRunDataGaps": events[0].get("dataGapCount") if events and isinstance(events[0], dict) else None,
        "nextAction": "保持沙盒运行，优先把每条策略补到 30 个闭合样本；达到门槛后再进入 testnet 设计复核。",
    }
    readonly_prep = {
        "stage": "readonly_preparation_only",
        "stageLabel": "只读准备",
        "testnetEnabled": False,
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "apiKeyInputEnabled": False,
        "orderCreationEnabled": False,
        "tradeApiAllowed": bool(SAFETY_BOUNDARY.get("tradeApiAllowed")),
        "withdrawApiAllowed": bool(SAFETY_BOUNDARY.get("withdrawApiAllowed")),
        "publicProbeReady": bool(public_probe),
        "testnetReadinessStage": "阻塞中",
        "testnetBlockers": [
            "Testnet 凭据隔离设计未开放",
            "订单生命周期模拟器未开放",
            "一键停止和全局熔断未开放",
            "最大订单和最大亏损限制未开放",
            "人工确认闸门未开放",
        ],
        "nextAction": "下一阶段只允许补只读行情和权限检查设计；不得接 Trade API、Withdraw API 或订单创建。",
    }
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": summary,
        "strategies": rows,
        "autoRunner": runner,
        "recentAutoEvents": events[:8],
        "readonlyPreparation": readonly_prep,
        "latestDailyReportId": latest_daily.get("reportId"),
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Quality center is local research only. It cannot store API keys, connect private exchange endpoints, create orders, or run automatic trading.",
    }
