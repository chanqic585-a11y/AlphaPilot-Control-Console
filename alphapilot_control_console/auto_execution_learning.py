from __future__ import annotations

from collections import defaultdict
from typing import Any

from .auto_execution_lifecycle import normalize_auto_execution_record
from .auto_execution_lifecycle_advancer import list_projected_auto_execution_records
from .config import SAFETY_BOUNDARY
from .state_store import list_auto_execution_lifecycle_events, now_iso


CONTROL_CONSOLE_VERSION = "V13.10.5"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_10_5"
CLOSED_LANES = {"take_profit_2r", "stop_loss_1r", "expired_exit"}
MIN_INITIAL_SAMPLE = 30
MIN_SERIOUS_SAMPLE = 100
MIN_STABILITY_SAMPLE = 300


def _optional_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _direction_label(record: dict[str, Any]) -> str:
    direction = str(record.get("direction") or "").lower()
    side = str(record.get("side") or "").lower()
    if direction in {"long", "long_research"} or side == "buy":
        return "做多"
    if direction == "short" or side == "sell":
        return "做空"
    return "未知方向"


def _sample_stage(count: int) -> tuple[str, str]:
    if count <= 0:
        return "等待闭合样本", "先推进本地生命周期；当前不能判断策略有效性。"
    if count < MIN_INITIAL_SAMPLE:
        return "闭合样本不足", f"还需至少 {MIN_INITIAL_SAMPLE - count} 条闭合结果才能初步评估。"
    if count < MIN_SERIOUS_SAMPLE:
        return "初步观察", "可以描述结果分布，但不能自动晋级、淘汰或训练交易模型。"
    if count < MIN_STABILITY_SAMPLE:
        return "严肃复核", "可做分段和集中度复核，仍需人工确认与独立样本验证。"
    return "稳定性复核", "样本量达到稳定性复核门槛，但不代表可用于实盘。"


def _max_consecutive_losses(rows: list[dict[str, Any]]) -> int:
    maximum = 0
    current = 0
    for row in sorted(rows, key=lambda item: str(item.get("exitAt") or item.get("updatedAt") or "")):
        value = _optional_float(row.get("resultR"))
        if value is not None and value < 0:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    results = [value for value in (_optional_float(row.get("resultR")) for row in rows) if value is not None]
    positive = [value for value in results if value > 0]
    negative = [value for value in results if value < 0]
    take_profit = sum(1 for row in rows if row.get("laneId") == "take_profit_2r")
    stop_loss = sum(1 for row in rows if row.get("laneId") == "stop_loss_1r")
    expired = sum(1 for row in rows if row.get("laneId") == "expired_exit")
    stage, next_action = _sample_stage(len(rows))
    return {
        "closedSamples": len(rows),
        "takeProfitCount": take_profit,
        "stopLossCount": stop_loss,
        "expiredCount": expired,
        "positiveResultCount": len(positive),
        "negativeResultCount": len(negative),
        "winRatePct": round(len(positive) / len(results) * 100, 2) if results else None,
        "averageR": round(sum(results) / len(results), 4) if results else None,
        "totalR": round(sum(results), 4) if results else None,
        "profitFactorR": round(sum(positive) / abs(sum(negative)), 4) if negative else None,
        "maxConsecutiveLosses": _max_consecutive_losses(rows),
        "sampleStage": stage,
        "nextAction": next_action,
        "initialEvaluationReady": len(rows) >= MIN_INITIAL_SAMPLE,
        "seriousReviewReady": len(rows) >= MIN_SERIOUS_SAMPLE,
        "stabilityReviewReady": len(rows) >= MIN_STABILITY_SAMPLE,
    }


def _group_rows(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if field == "strategy":
            key = str(row.get("strategyId") or row.get("strategyName") or "unknown")
        elif field == "direction":
            key = _direction_label(row)
        else:
            key = str(row.get("symbol") or row.get("instId") or "--")
        grouped[key].append(row)
    output: list[dict[str, Any]] = []
    for key, group in grouped.items():
        first = group[0]
        output.append({
            "key": key,
            "label": first.get("strategyName") if field == "strategy" else key,
            **_aggregate(group),
        })
    return sorted(output, key=lambda row: (-int(row.get("closedSamples") or 0), str(row.get("label") or "")))


def build_auto_execution_learning() -> dict[str, Any]:
    projected = [row for row in list_projected_auto_execution_records(limit=500) if isinstance(row, dict)]
    normalized = [normalize_auto_execution_record(row) for row in projected]
    closed = [
        {**raw, **view}
        for raw, view in zip(projected, normalized)
        if view.get("laneId") in CLOSED_LANES
    ]
    active = sum(1 for row in normalized if row.get("laneId") in {"waiting_trigger", "simulated_holding"})
    blocked = sum(1 for row in normalized if row.get("laneId") == "blocked")
    summary = {
        **_aggregate(closed),
        "totalRecords": len(projected),
        "activeRecords": active,
        "blockedRecords": blocked,
        "lifecycleEventCount": len(list_auto_execution_lifecycle_events(limit=2000)),
        "learningMode": "descriptive_only" if len(closed) < MIN_INITIAL_SAMPLE else "review_only",
        "modelTrainingAllowed": False,
        "automaticStrategyPromotion": False,
    }
    warnings = []
    if len(closed) < MIN_INITIAL_SAMPLE:
        warnings.append("闭合样本不足 30 条，仅展示描述性统计，不训练模型。")
    if closed and len({str(row.get("symbol") or "") for row in closed}) < 3:
        warnings.append("闭合样本币种集中度较高，需要扩大独立样本覆盖。")
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "title": "本地闭合样本学习报告",
        "summary": summary,
        "byStrategy": _group_rows(closed, "strategy"),
        "bySymbol": _group_rows(closed, "symbol"),
        "byDirection": _group_rows(closed, "direction"),
        "recentClosedSamples": closed[:30],
        "warnings": warnings,
        "sampleThresholds": {
            "initialEvaluation": MIN_INITIAL_SAMPLE,
            "seriousReview": MIN_SERIOUS_SAMPLE,
            "stabilityReview": MIN_STABILITY_SAMPLE,
            "rule": "门槛只允许进入更深入人工复核，不自动晋级到 Demo 或实盘。",
        },
        "safetyBoundary": {
            **SAFETY_BOUNDARY,
            "publicMarketOnly": True,
            "modelTrainingAllowed": False,
            "automaticStrategyPromotion": False,
            "createsExchangeOrder": False,
            "createsDemoOrder": False,
            "liveTradingApproved": False,
        },
        "safetyNote": "学习报告只分析本地闭合观察样本，不训练交易模型、不修改策略、不创建订单。",
    }
