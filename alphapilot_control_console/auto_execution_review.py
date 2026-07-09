from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from .auto_execution_lifecycle_advancer import list_projected_auto_execution_records
from .auto_execution_lifecycle import normalize_auto_execution_record
from .config import SAFETY_BOUNDARY
from .state_store import now_iso


CONTROL_CONSOLE_VERSION = "V13.10.5"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_10_5"

CLOSED_LANES = {"take_profit_2r", "stop_loss_1r", "expired_exit"}
PRIORITY_ORDER = {"高": 3, "中": 2, "低": 1}


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _optional_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        if value is None:
            return fallback
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique_text(values: list[Any]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in output:
            output.append(text)
    return output


def _first_value(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value is not None and value != "":
            return value
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _duration_label(start_value: Any, end_value: Any = None) -> str:
    start = _parse_datetime(start_value)
    end = _parse_datetime(end_value) or datetime.now(timezone.utc)
    if start is None:
        return "时间未知"
    minutes = max(0, int((end - start).total_seconds() // 60))
    if minutes < 60:
        return f"{minutes} 分钟"
    hours, minute_remainder = divmod(minutes, 60)
    if hours < 24:
        return f"{hours} 小时 {minute_remainder} 分钟"
    days, hour_remainder = divmod(hours, 24)
    return f"{days} 天 {hour_remainder} 小时"


def _direction_label(record: dict[str, Any]) -> str:
    direction = str(record.get("direction") or "").lower()
    side = str(record.get("side") or "").lower()
    if direction in {"long", "long_research"} or side == "buy":
        return "做多"
    if direction == "short" or side == "sell":
        return "做空"
    return "未知方向"


def _blocker_info(raw_reason: Any) -> dict[str, Any]:
    reason = str(raw_reason or "").strip()
    lowered = reason.lower()

    if lowered.startswith("higher_rank_candidate_selected_for_"):
        symbol = reason[len("higher_rank_candidate_selected_for_") :] or "同币种"
        return _reason("策略未允许", f"{symbol} 已有更高排名候选入选", "预期阻塞，可忽略", "低")
    if lowered == "max_executions_per_run_reached":
        return _reason("策略未允许", "本轮本地观察名额已满", "检查阻塞原因", "低")
    if lowered in {"cooldown_duplicate_open_record", "duplicate_signal"}:
        return _reason("重复信号", "同策略、币种和方向已有活跃记录，当前处于冷却中", "预期阻塞，可忽略", "低")
    if lowered in {"cooldown_active", "cooldown_blocked"}:
        return _reason("冷却中", "当前信号仍在冷却期", "预期阻塞，可忽略", "低")
    if lowered in {"trade_count_below_gate", "data_quality_failed", "public_market_not_ready"}:
        detail = "回测样本数未达到本地门槛" if lowered == "trade_count_below_gate" else "公共行情或数据质量未达到本地门槛"
        return _reason("数据质量不合格", detail, "继续收集样本", "中")
    if lowered in {"profit_factor_below_gate", "score_below_gate", "target_r_below_2", "risk_gate_blocked"}:
        details = {
            "profit_factor_below_gate": "盈亏因子未达到本地风控门槛",
            "score_below_gate": "候选评分未达到本地风控门槛",
            "target_r_below_2": "目标收益风险比低于 2R",
            "risk_gate_blocked": "本地风险门未通过",
        }
        return _reason("风控拦截", details.get(lowered, "本地风险门未通过"), "复核风控阈值", "高")
    if lowered in {"liquidity_gate_blocked", "liquidity_failed"}:
        return _reason("流动性拦截", "流动性条件未达到本地门槛", "检查阻塞原因", "高")
    if lowered in {"signal_expired", "expired"}:
        return _reason("信号过期", "候选信号已超过有效观察窗口", "复核策略信号质量", "中")
    if lowered in {"missing_price", "price_missing"}:
        return _reason("缺少价格", "缺少可用于本地复核的价格", "修复缺少价格", "高")
    if lowered in {"invalid_stop_or_target", "stop_or_target_invalid"}:
        return _reason("止损止盈无效", "止损或止盈参数无法用于本地生命周期复核", "复核风控阈值", "高")
    if lowered in {"position_size_invalid", "notional_above_local_cap", "notional_invalid"}:
        return _reason("仓位无效", "本地模拟名义金额或仓位参数无效", "复核风控阈值", "高")
    if lowered in {"strategy_not_allowed", "strategy_disabled"}:
        return _reason("策略未允许", "策略未通过当前本地仲裁规则", "复核策略信号质量", "中")
    if lowered in {"lifecycle_data_missing", "missing_lifecycle_data"}:
        return _reason("生命周期数据缺失", "生命周期复核所需字段不完整", "继续收集样本", "高")

    if "缺少价格" in reason:
        return _reason("缺少价格", "缺少可用于本地复核的价格", "修复缺少价格", "高")
    if "流动性" in reason:
        return _reason("流动性拦截", "流动性条件未达到本地门槛", "检查阻塞原因", "高")
    if "风控" in reason:
        return _reason("风控拦截", "本地风险门未通过", "复核风控阈值", "高")
    if "重复" in reason or "冷却" in reason:
        return _reason("重复信号", "重复信号或冷却期阻塞", "预期阻塞，可忽略", "低")
    return _reason("未知原因", "现有记录未提供可标准化的阻塞原因", "检查阻塞原因", "高", standardized=False)


def _reason(
    label: str,
    detail: str,
    recommendation: str,
    priority: str,
    *,
    standardized: bool = True,
) -> dict[str, Any]:
    return {
        "label": label,
        "detail": detail,
        "recommendation": recommendation,
        "priority": priority,
        "standardized": standardized,
    }


def _extract_blockers(record: dict[str, Any]) -> list[dict[str, Any]]:
    raw_values = _unique_text([
        *_as_list(record.get("routerBlockers")),
        *_as_list(record.get("riskBlockers")),
    ])
    if not raw_values:
        fallback_values = [
            record.get("reason"),
            record.get("message"),
            record.get("statusDetail"),
            record.get("notes"),
        ]
        raw_values = _unique_text(fallback_values)
    return [_blocker_info(value) for value in raw_values] or [_blocker_info("unknown")]


def _record_base(raw: dict[str, Any], normalized: dict[str, Any]) -> dict[str, Any]:
    return {
        "recordId": normalized.get("recordId"),
        "strategyId": normalized.get("strategyId"),
        "strategyName": normalized.get("strategyName") or normalized.get("strategyId") or "--",
        "symbol": normalized.get("symbol") or normalized.get("instId") or "--",
        "direction": _direction_label(raw),
        "timeframe": normalized.get("timeframe") or "--",
    }


def _build_active_row(raw: dict[str, Any], normalized: dict[str, Any]) -> dict[str, Any]:
    base = _record_base(raw, normalized)
    entry_time = _first_value(raw, "entryReferenceAt", "entryAt", "openedAt", "signalAt", "createdAt")
    updated_at = _first_value(raw, "updatedAt", "lastObservedAt", "createdAt")
    entry_price = _optional_float(_first_value(raw, "entryReferencePrice", "entryPrice", "filledPrice", "openPrice", "signalPrice"))
    current_price = _optional_float(_first_value(raw, "currentPrice", "markPrice", "latestPrice"))
    current_r = _optional_float(_first_value(raw, "currentR", "unrealizedR", "markR"))
    target_r = _safe_float(raw.get("targetR"), 2.0)
    policy = raw.get("tpSlPolicy") if isinstance(raw.get("tpSlPolicy"), dict) else {}
    stop_r = _safe_float(raw.get("stopR") or policy.get("stopLossR"), 1.0)
    warnings: list[str] = []
    if entry_price is None:
        warnings.append("缺少入场价")
    if current_price is None:
        warnings.append("缺少当前价格")
    if current_r is None:
        warnings.append("暂不能计算当前 R")
    return {
        **base,
        "status": "本地模拟持有",
        "entryTime": entry_time,
        "entryPrice": entry_price,
        "currentPrice": current_price,
        "currentR": current_r,
        "targetR": target_r,
        "stopR": stop_r,
        "holdDuration": _duration_label(entry_time, updated_at),
        "distanceToTargetR": None if current_r is None else round(target_r - current_r, 4),
        "distanceToStopR": None if current_r is None else round(current_r + stop_r, 4),
        "statusDuration": _duration_label(entry_time, updated_at),
        "warnings": warnings,
        "warning": "；".join(warnings) if warnings else "本地观察字段完整",
    }


def _build_closed_row(raw: dict[str, Any], normalized: dict[str, Any]) -> dict[str, Any]:
    base = _record_base(raw, normalized)
    lane_id = str(normalized.get("laneId") or "")
    target_r = _safe_float(raw.get("targetR"), 2.0)
    policy = raw.get("tpSlPolicy") if isinstance(raw.get("tpSlPolicy"), dict) else {}
    stop_r = _safe_float(raw.get("stopR") or policy.get("stopLossR"), 1.0)
    result_r = _optional_float(_first_value(raw, "resultR", "realizedR", "exitR"))
    if result_r is None and lane_id == "take_profit_2r":
        result_r = target_r
    elif result_r is None and lane_id == "stop_loss_1r":
        result_r = -stop_r
    entry_time = _first_value(raw, "entryReferenceAt", "entryAt", "openedAt", "signalAt", "createdAt")
    exit_time = _first_value(raw, "exitAt", "closedAt", "updatedAt", "createdAt")
    return {
        **base,
        "status": normalized.get("laneLabel") or "已结束",
        "entryTime": entry_time,
        "exitTime": exit_time,
        "exitReason": normalized.get("laneLabel") or "已结束",
        "resultR": result_r,
        "holdDuration": _duration_label(entry_time, exit_time),
        "maxFavorableR": _optional_float(_first_value(raw, "maxFavorableR", "maxRunupR", "mfeR")),
        "maxAdverseR": _optional_float(_first_value(raw, "maxAdverseR", "maxDrawdownR", "maeR")),
    }


def _build_blocked_row(raw: dict[str, Any], normalized: dict[str, Any]) -> dict[str, Any]:
    base = _record_base(raw, normalized)
    reasons = _extract_blockers(raw)
    primary = reasons[0]
    review_priority = max(
        (str(reason.get("priority") or "低") for reason in reasons),
        key=lambda value: PRIORITY_ORDER.get(value, 0),
        default="低",
    )
    details = _unique_text([reason["detail"] for reason in reasons])
    secondary = _unique_text([reason["label"] for reason in reasons[1:] if reason["label"] != primary["label"]])
    risk_details = _unique_text([
        _blocker_info(value)["detail"] for value in _as_list(raw.get("riskBlockers"))
    ])
    trade_count = _safe_int(raw.get("tradeCount"))
    profit_factor = _optional_float(raw.get("profitFactor"))
    data_quality = (
        "缺少回测样本，无法完成策略质量复核"
        if trade_count <= 0
        else f"回测样本 {trade_count}，盈亏因子 {profit_factor:.2f}" if profit_factor is not None else f"回测样本 {trade_count}，盈亏因子缺失"
    )
    return {
        **base,
        "status": "已阻塞",
        "signalTime": _first_value(raw, "signalAt", "createdAt"),
        "blockedTime": _first_value(raw, "blockedAt", "updatedAt", "createdAt"),
        "blockReason": primary["label"],
        "blockDetail": "；".join(details),
        "secondaryReasons": secondary,
        "signalScore": _optional_float(raw.get("score")),
        "riskSummary": "；".join(risk_details) if risk_details else "本地路由阻塞，未进入风险执行阶段",
        "dataQualitySummary": data_quality,
        "recommendation": primary["recommendation"],
        "reviewPriority": review_priority,
        "reasonStandardized": all(reason["standardized"] for reason in reasons),
    }


def _build_reason_breakdown(blocked_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in blocked_rows:
        grouped[str(row.get("blockReason") or "未知原因")].append(row)
    total = len(blocked_rows)
    output: list[dict[str, Any]] = []
    for reason, rows in grouped.items():
        priorities = [str(row.get("reviewPriority") or "低") for row in rows]
        priority = max(priorities, key=lambda value: PRIORITY_ORDER.get(value, 0), default="低")
        recommendations = Counter(str(row.get("recommendation") or "检查阻塞原因") for row in rows)
        output.append({
            "blockReason": reason,
            "count": len(rows),
            "percentage": round(len(rows) / total * 100, 2) if total else 0.0,
            "strategies": sorted({str(row.get("strategyName") or "--") for row in rows}),
            "symbols": sorted({str(row.get("symbol") or "--") for row in rows}),
            "directions": sorted({str(row.get("direction") or "未知方向") for row in rows}),
            "strategyCount": len({str(row.get("strategyId") or "") for row in rows}),
            "symbolCount": len({str(row.get("symbol") or "") for row in rows}),
            "reviewPriority": priority,
            "recommendation": recommendations.most_common(1)[0][0] if recommendations else "检查阻塞原因",
            "exampleRecords": [
                {
                    "recordId": row.get("recordId"),
                    "strategyName": row.get("strategyName"),
                    "symbol": row.get("symbol"),
                    "direction": row.get("direction"),
                }
                for row in rows[:3]
            ],
        })
    return sorted(output, key=lambda row: (-int(row["count"]), -PRIORITY_ORDER.get(str(row["reviewPriority"]), 0), str(row["blockReason"])))


def _max_consecutive_losses(rows: list[dict[str, Any]]) -> int:
    maximum = 0
    current = 0
    for row in sorted(rows, key=lambda item: str(item.get("exitTime") or "")):
        result_r = _optional_float(row.get("resultR"))
        if result_r is not None and result_r < 0:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def _strategy_status(total: int, active: int, closed: int, blocked: int) -> tuple[str, str, list[str]]:
    block_rate = blocked / total * 100 if total else 0.0
    warnings: list[str] = []
    if closed == 0:
        warnings.append("暂无闭合结果")
    if block_rate >= 80:
        warnings.append("阻塞高度集中")
    if blocked >= 10 and block_rate >= 60:
        return "需要复核阻塞原因", "复核策略信号质量", warnings
    if active > 0:
        return "样本收集中", "继续收集样本", warnings
    if closed < 30:
        return "闭合样本不足", "继续收集样本", warnings
    return "观察名单", "检查阻塞原因", warnings


def _build_strategy_summary(
    normalized_records: list[dict[str, Any]],
    blocked_rows: list[dict[str, Any]],
    closed_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in normalized_records:
        grouped[str(row.get("strategyId") or row.get("strategyName") or "unknown")].append(row)
    blocked_by_strategy: Counter[str] = Counter(str(row.get("strategyId") or "unknown") for row in blocked_rows)
    closed_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in closed_rows:
        closed_by_strategy[str(row.get("strategyId") or "unknown")].append(row)

    output: list[dict[str, Any]] = []
    for strategy_id, rows in grouped.items():
        total = len(rows)
        active = sum(1 for row in rows if row.get("laneId") in {"waiting_trigger", "simulated_holding"})
        closed = sum(1 for row in rows if row.get("laneId") in CLOSED_LANES)
        blocked = blocked_by_strategy.get(strategy_id, 0)
        take_profit = sum(1 for row in rows if row.get("laneId") == "take_profit_2r")
        stop_loss = sum(1 for row in rows if row.get("laneId") == "stop_loss_1r")
        expired = sum(1 for row in rows if row.get("laneId") == "expired_exit")
        result_values = [
            value for value in (_optional_float(row.get("resultR")) for row in closed_by_strategy.get(strategy_id, [])) if value is not None
        ]
        status, recommendation, warnings = _strategy_status(total, active, closed, blocked)
        first = rows[0]
        output.append({
            "strategyId": strategy_id,
            "strategyName": first.get("strategyName") or strategy_id,
            "totalRecords": total,
            "activeHoldingCount": active,
            "closedResultCount": closed,
            "blockedCount": blocked,
            "blockedRatePct": round(blocked / total * 100, 2) if total else 0.0,
            "takeProfit2RCount": take_profit,
            "stopLoss1RCount": stop_loss,
            "expiredExitCount": expired,
            "rWinRatePct": round(take_profit / closed * 100, 2) if closed else None,
            "averageR": round(sum(result_values) / len(result_values), 4) if result_values else None,
            "maxConsecutiveLosses": _max_consecutive_losses(closed_by_strategy.get(strategy_id, [])),
            "suggestedStatus": status,
            "recommendation": recommendation,
            "warnings": warnings,
        })
    return sorted(output, key=lambda row: (-int(row["blockedCount"]), -int(row["activeHoldingCount"]), str(row["strategyName"])))


def _build_breakdown(normalized_records: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in normalized_records:
        if field == "direction":
            raw_direction = str(row.get("direction") or "").lower()
            side = str(row.get("side") or "").lower()
            key = "做多" if raw_direction in {"long", "long_research"} or side == "buy" else "做空" if raw_direction == "short" or side == "sell" else "未知方向"
        else:
            key = str(row.get("symbol") or row.get("instId") or "--")
        grouped[key].append(row)
    output: list[dict[str, Any]] = []
    for label, rows in grouped.items():
        total = len(rows)
        blocked = sum(1 for row in rows if row.get("laneId") == "blocked")
        active = sum(1 for row in rows if row.get("laneId") in {"waiting_trigger", "simulated_holding"})
        closed = sum(1 for row in rows if row.get("laneId") in CLOSED_LANES)
        output.append({
            field: label,
            "totalRecords": total,
            "blockedCount": blocked,
            "activeHoldingCount": active,
            "closedResultCount": closed,
            "blockedRatePct": round(blocked / total * 100, 2) if total else 0.0,
        })
    return sorted(output, key=lambda row: (-int(row["totalRecords"]), str(row[field])))


def _system_recommendations(
    summary: dict[str, Any],
    reason_breakdown: list[dict[str, Any]],
    strategy_summary: list[dict[str, Any]],
) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    total = int(summary.get("totalRecords") or 0)
    blocked = int(summary.get("blockedRecords") or 0)
    closed = int(summary.get("closedResults") or 0)
    active = int(summary.get("activeHoldingRecords") or 0)
    if total and blocked / total >= 0.6:
        recommendations.append({
            "priority": "高",
            "title": "优先复核阻塞原因",
            "detail": "阻塞记录占比较高，建议优先复核仲裁和风控原因，而不是继续增加策略。",
        })
    if closed < 30:
        recommendations.append({
            "priority": "高",
            "title": "闭合样本不足",
            "detail": "当前不能判断策略有效性；每条策略至少需要 30 个闭合结果才能初步评估。",
        })
    if active:
        recommendations.append({
            "priority": "中",
            "title": "继续观察活跃记录",
            "detail": "存在本地模拟持有记录，需继续观察是否达到 2R、触发 -1R 或过期退出。",
        })
    unknown = next((row for row in reason_breakdown if row.get("blockReason") == "未知原因"), None)
    if unknown:
        recommendations.append({
            "priority": "高",
            "title": "补全阻塞原因",
            "detail": "未知阻塞原因较多，建议补充标准化阻塞字段后再做策略比较。",
        })
    if blocked and strategy_summary:
        top = max(strategy_summary, key=lambda row: int(row.get("blockedCount") or 0))
        top_count = int(top.get("blockedCount") or 0)
        if top_count / blocked >= 0.4:
            recommendations.append({
                "priority": "中",
                "title": "检查策略阻塞集中度",
                "detail": f"{top.get('strategyName') or '--'} 占全部阻塞记录的 {top_count / blocked * 100:.1f}%，建议单独复核信号质量与仲裁匹配。",
            })
    return recommendations


def build_auto_execution_review() -> dict[str, Any]:
    raw_records = [row for row in list_projected_auto_execution_records(limit=500) if isinstance(row, dict)]
    normalized_records = [normalize_auto_execution_record(row) for row in raw_records]
    active_rows: list[dict[str, Any]] = []
    closed_rows: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, Any]] = []
    waiting_count = 0
    for raw, normalized in zip(raw_records, normalized_records):
        lane_id = str(normalized.get("laneId") or "blocked")
        if lane_id == "waiting_trigger":
            waiting_count += 1
        elif lane_id == "simulated_holding":
            active_rows.append(_build_active_row(raw, normalized))
        elif lane_id in CLOSED_LANES:
            closed_rows.append(_build_closed_row(raw, normalized))
        else:
            blocked_rows.append(_build_blocked_row(raw, normalized))

    blocked_rows.sort(key=lambda row: (-PRIORITY_ORDER.get(str(row.get("reviewPriority") or "低"), 0), str(row.get("blockedTime") or "")), reverse=False)
    reason_breakdown = _build_reason_breakdown(blocked_rows)
    strategy_summary = _build_strategy_summary(normalized_records, blocked_rows, closed_rows)
    standardized_count = sum(1 for row in blocked_rows if row.get("reasonStandardized"))
    coverage = round(standardized_count / len(blocked_rows) * 100, 2) if blocked_rows else 100.0
    take_profit_count = sum(1 for row in normalized_records if row.get("laneId") == "take_profit_2r")
    stop_loss_count = sum(1 for row in normalized_records if row.get("laneId") == "stop_loss_1r")
    expired_count = sum(1 for row in normalized_records if row.get("laneId") == "expired_exit")
    priority_counts = Counter(str(row.get("reviewPriority") or "低") for row in blocked_rows)
    summary = {
        "stage": "本地自动执行复核",
        "stageConclusion": "当前是执行链路观察阶段，不是策略晋级阶段。",
        "totalRecords": len(normalized_records),
        "activeHoldingRecords": len(active_rows),
        "blockedRecords": len(blocked_rows),
        "closedResults": len(closed_rows),
        "waitingTriggerRecords": waiting_count,
        "takeProfit2RRecords": take_profit_count,
        "stopLoss1RRecords": stop_loss_count,
        "expiredExitRecords": expired_count,
        "reasonStandardizationCoveragePct": coverage,
        "highPriorityReviewCount": priority_counts.get("高", 0),
        "mediumPriorityReviewCount": priority_counts.get("中", 0),
        "lowPriorityReviewCount": priority_counts.get("低", 0),
        "dryRunApproved": False,
        "liveTradingApproved": False,
    }
    recommendations = _system_recommendations(summary, reason_breakdown, strategy_summary)
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "title": "本地自动执行复核队列",
        "summary": summary,
        "blockedReasonBreakdown": reason_breakdown,
        "strategyLifecycleSummary": strategy_summary,
        "symbolBreakdown": _build_breakdown(normalized_records, "symbol"),
        "directionBreakdown": _build_breakdown(normalized_records, "direction"),
        "activeHoldingQueue": active_rows,
        "closedResultsQueue": closed_rows,
        "blockedReviewQueue": blocked_rows,
        "sampleThresholds": {
            "currentStage": "执行链路观察阶段",
            "blockedReasonReview": "每条策略阻塞原因样本达到 10 条后，可分析阻塞质量。",
            "initialEvaluation": "每条策略闭合结果达到 30 条后，可初步评估。",
            "seriousReview": "每条策略闭合结果达到 100 条后，可严肃复核。",
            "stabilityReview": "每条策略闭合结果达到 300 条后，可做稳定性判断。",
            "currentConclusion": "闭合结果不足时，不自动晋级或淘汰策略。",
        },
        "systemRecommendations": recommendations,
        "safetyBoundary": {
            **SAFETY_BOUNDARY,
            "dryRunApproved": False,
            "liveTradingApproved": False,
            "tradeApiEnabled": False,
            "withdrawApiEnabled": False,
            "apiKeyRequired": False,
            "rawApiKeyStorageAllowed": False,
            "createsExchangeOrder": False,
            "createsDemoOrder": False,
            "automaticStrategyPromotion": False,
            "automaticStrategyElimination": False,
        },
        "safetyNote": "本复核队列只读取本地生命周期记录，不创建 Demo 或实盘订单，也不自动修改策略状态。",
    }
