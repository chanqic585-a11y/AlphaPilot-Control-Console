from __future__ import annotations

from typing import Any

from .auto_execution_lifecycle_advancer import list_projected_auto_execution_records
from .config import SAFETY_BOUNDARY
from .state_store import list_auto_execution_runs, now_iso


CONTROL_CONSOLE_VERSION = "V13.10.5"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_10_5"

LANE_ORDER = [
    "waiting_trigger",
    "simulated_holding",
    "take_profit_2r",
    "stop_loss_1r",
    "expired_exit",
    "blocked",
]

LANE_LABELS = {
    "waiting_trigger": "等待触发",
    "simulated_holding": "本地模拟持有",
    "take_profit_2r": "达到 2R",
    "stop_loss_1r": "触发 -1R",
    "expired_exit": "过期退出",
    "blocked": "已阻塞",
}

EXIT_STATUS_TO_LANE = {
    "take_profit_2r": "take_profit_2r",
    "target_2r_hit": "take_profit_2r",
    "tp_hit": "take_profit_2r",
    "stop_loss_1r": "stop_loss_1r",
    "stop_loss_hit": "stop_loss_1r",
    "sl_hit": "stop_loss_1r",
    "expired_exit": "expired_exit",
    "timeout_exit": "expired_exit",
    "expired": "expired_exit",
}

BLOCKER_LABELS = {
    "public_market_not_ready": "公共行情筛选未就绪",
    "target_r_below_2": "目标收益风险比低于 2R",
    "score_below_gate": "候选评分未达门槛",
    "trade_count_below_gate": "回测样本数未达门槛",
    "profit_factor_below_gate": "盈亏因子未达门槛",
    "notional_above_local_cap": "本地名义金额超过上限",
    "cooldown_duplicate_open_record": "已有同类活跃记录，当前处于冷却中",
    "max_executions_per_run_reached": "本轮本地观察名额已满",
}


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        if value is None:
            return fallback
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _blocker_label(value: Any) -> str:
    code = str(value or "").strip()
    if code in BLOCKER_LABELS:
        return BLOCKER_LABELS[code]
    if code.startswith("higher_rank_candidate_selected_for_"):
        return "同币种已有更高排名候选入选"
    return "未标准化原因"


def _record_lane(record: dict[str, Any]) -> str:
    execution_status = str(record.get("executionStatus") or "").strip()
    route_status = str(record.get("routeStatus") or "").strip()
    risk_status = str(record.get("riskStatus") or "").strip()
    exit_status = str(record.get("exitStatus") or record.get("localExitStatus") or "").strip()

    if exit_status in EXIT_STATUS_TO_LANE:
        return EXIT_STATUS_TO_LANE[exit_status]
    if execution_status in EXIT_STATUS_TO_LANE:
        return EXIT_STATUS_TO_LANE[execution_status]
    if route_status == "blocked" or risk_status == "blocked" or execution_status == "blocked_before_local_execution":
        return "blocked"
    if execution_status in {"local_tp_sl_watch", "local_simulated_open"}:
        return "simulated_holding"
    if route_status == "selected" and risk_status == "passed":
        return "waiting_trigger"
    return "blocked"


def _lane_note(lane_id: str, record: dict[str, Any]) -> str:
    if lane_id == "waiting_trigger":
        return "策略已通过本地门槛，等待下一次本地观察刷新。"
    if lane_id == "simulated_holding":
        return "本地模拟生命周期观察中，等待 2R、-1R 或过期条件。"
    if lane_id == "take_profit_2r":
        return "本地模拟记录显示达到 2R 条件。"
    if lane_id == "stop_loss_1r":
        return "本地模拟记录显示触发 -1R 条件。"
    if lane_id == "expired_exit":
        return "本地模拟记录显示观察窗口过期退出。"
    blockers = [_blocker_label(item) for item in [*_as_list(record.get("routerBlockers")), *_as_list(record.get("riskBlockers"))] if item]
    return f"被本地路由或风控阻塞：{' / '.join(blockers[:3])}" if blockers else "被本地路由或风控阻塞。"


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    lane_id = _record_lane(record)
    blockers = [str(item) for item in [*_as_list(record.get("routerBlockers")), *_as_list(record.get("riskBlockers"))] if item]
    lifecycle = _as_list(record.get("lifecycle"))
    return {
        "recordId": record.get("recordId"),
        "runId": record.get("runId"),
        "candidateId": record.get("candidateId"),
        "strategyId": record.get("strategyId"),
        "strategyName": record.get("strategyName") or record.get("strategyId") or "--",
        "instId": record.get("instId") or record.get("symbol") or "--",
        "symbol": record.get("symbol") or record.get("instId") or "--",
        "side": record.get("side") or record.get("direction") or "--",
        "direction": record.get("direction"),
        "directionLabel": record.get("directionLabel") or ("空头观察" if record.get("side") == "sell" else "多头观察"),
        "timeframe": record.get("timeframe") or "--",
        "score": _safe_float(record.get("score")),
        "targetR": _safe_float(record.get("targetR"), 2.0),
        "winRatePct": _safe_float(record.get("winRatePct")),
        "profitFactor": _safe_float(record.get("profitFactor")),
        "tradeCount": _safe_int(record.get("tradeCount")),
        "notionalUsdt": _safe_float(record.get("notionalUsdt"), 1000.0),
        "routeStatus": record.get("routeStatus"),
        "riskStatus": record.get("riskStatus"),
        "executionStatus": record.get("executionStatus"),
        "laneId": lane_id,
        "laneLabel": LANE_LABELS[lane_id],
        "lifecycleNote": _lane_note(lane_id, record),
        "lifecycle": lifecycle,
        "blockers": blockers,
        "createdAt": record.get("createdAt"),
        "updatedAt": record.get("updatedAt") or record.get("createdAt"),
        "stateSource": "local_record_projection",
        "isLocalSimulation": True,
        "notRealizedPnl": True,
        "apiKeyUsed": False,
        "ordersCreated": False,
        "demoOrderCreated": False,
        "liveTrading": False,
    }


def normalize_auto_execution_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return the stable local lifecycle projection used by read-only review modules."""
    return _normalize_record(record)


def _build_lanes(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = {lane_id: [] for lane_id in LANE_ORDER}
    for record in records:
        if not isinstance(record, dict):
            continue
        normalized = _normalize_record(record)
        grouped[normalized["laneId"]].append(normalized)
    return [
        {
            "laneId": lane_id,
            "label": LANE_LABELS[lane_id],
            "count": len(grouped[lane_id]),
            "records": grouped[lane_id][:12],
        }
        for lane_id in LANE_ORDER
    ]


def build_auto_execution_lifecycle_monitor() -> dict[str, Any]:
    records = list_projected_auto_execution_records(limit=200)
    runs = list_auto_execution_runs(limit=10)
    normalized_records = [_normalize_record(row) for row in records if isinstance(row, dict)]
    lanes = _build_lanes(records)
    lane_counts = {lane["laneId"]: lane["count"] for lane in lanes}
    latest_run = runs[0] if runs else {}
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "stage": "local_auto_execution_lifecycle_monitor",
            "stageLabel": "本地自动执行生命周期",
            "latestRunId": latest_run.get("runId"),
            "latestRunAt": latest_run.get("createdAt"),
            "totalRecords": len(normalized_records),
            "activeRecords": lane_counts.get("waiting_trigger", 0) + lane_counts.get("simulated_holding", 0),
            "blockedRecords": lane_counts.get("blocked", 0),
            "takeProfitCount": lane_counts.get("take_profit_2r", 0),
            "stopLossCount": lane_counts.get("stop_loss_1r", 0),
            "expiredCount": lane_counts.get("expired_exit", 0),
            "userFacingTicketWorkflow": False,
            "liveTradingLocked": True,
            "demoOrderLocked": True,
            "nextAction": "观察本地生命周期分布：优先复核本地模拟持有和阻塞原因，再决定是否进入 Demo 阶段。",
        },
        "lanes": lanes,
        "records": normalized_records[:60],
        "recentRuns": runs,
        "safetyBoundary": {
            **SAFETY_BOUNDARY,
            "publicMarketOnly": True,
            "apiKeyRequired": False,
            "rawApiKeyStorageAllowed": False,
            "createsExchangeOrder": False,
            "demoOrderCreated": False,
            "liveTrading": False,
            "userFacingTicketWorkflow": False,
            "internalAuditRecordsOnly": True,
        },
        "safetyNote": "Lifecycle monitor reads local simulation records only. It does not create Demo or live exchange orders.",
    }
