from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import SAFETY_BOUNDARY
from .no_key_pre_live import (
    MAX_LOCAL_OBSERVATION_NOTIONAL_USDT,
    build_no_key_pre_live_workbench,
    scan_no_key_pre_live_candidates,
)
from .state_store import (
    list_auto_execution_records,
    list_auto_execution_runs,
    now_iso,
    save_auto_execution_records,
    save_auto_execution_run,
)


CONTROL_CONSOLE_VERSION = "V13.10.2"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_10_2"
DEFAULT_MAX_EXECUTIONS_PER_RUN = 5
DEFAULT_COOLDOWN_MINUTES = 30
MIN_TARGET_R = 2.0
MIN_SCORE = 50.0
MIN_TRADE_COUNT = 5
MIN_PROFIT_FACTOR = 1.0


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


def _direction_label(candidate: dict[str, Any]) -> str:
    direction = str(candidate.get("direction") or "").lower()
    side = str(candidate.get("side") or "").lower()
    if direction == "short" or side == "sell":
        return "空头观察"
    if direction in {"long", "long_research"} or side == "buy":
        return "多头观察"
    return "方向待确认"


def _candidate_score(candidate: dict[str, Any]) -> float:
    score = _safe_float(candidate.get("score"))
    profit_factor = _safe_float(candidate.get("profitFactor"))
    trade_count = _safe_int(candidate.get("tradeCount"))
    target_r = _safe_float(candidate.get("targetR"), 2.0)
    return score + min(profit_factor, 3.0) * 8 + min(trade_count, 100) * 0.1 + target_r * 3


def _record_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(candidate.get("strategyId") or ""),
        str(candidate.get("instId") or candidate.get("symbol") or ""),
        str(candidate.get("side") or candidate.get("direction") or ""),
    )


def _has_recent_duplicate(candidate: dict[str, Any], recent_records: list[dict[str, Any]]) -> bool:
    key = _record_key(candidate)
    for record in recent_records:
        if not isinstance(record, dict):
            continue
        if _record_key(record) != key:
            continue
        if record.get("executionStatus") in {"local_simulated_open", "local_tp_sl_watch"}:
            return True
    return False


def _risk_gate(candidate: dict[str, Any], notional_usdt: float) -> tuple[str, list[str], list[str]]:
    passed: list[str] = []
    blockers: list[str] = []
    target_r = _safe_float(candidate.get("targetR"), 2.0)
    score = _safe_float(candidate.get("score"))
    trade_count = _safe_int(candidate.get("tradeCount"))
    profit_factor = _safe_float(candidate.get("profitFactor"))

    if candidate.get("screeningStatus") == "market_ready":
        passed.append("public_market_ready")
    else:
        blockers.append("public_market_not_ready")

    if target_r >= MIN_TARGET_R:
        passed.append("target_r_at_least_2")
    else:
        blockers.append("target_r_below_2")

    if score >= MIN_SCORE:
        passed.append("score_gate_passed")
    else:
        blockers.append("score_below_gate")

    if trade_count >= MIN_TRADE_COUNT:
        passed.append("sample_gate_passed")
    else:
        blockers.append("trade_count_below_gate")

    if profit_factor >= MIN_PROFIT_FACTOR:
        passed.append("profit_factor_gate_passed")
    else:
        blockers.append("profit_factor_below_gate")

    if 0 < notional_usdt <= MAX_LOCAL_OBSERVATION_NOTIONAL_USDT:
        passed.append("notional_within_local_cap")
    else:
        blockers.append("notional_above_local_cap")

    return ("passed" if not blockers else "blocked", passed, blockers)


def _select_candidates(candidates: list[dict[str, Any]], max_executions: int, recent_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    blocked: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("screeningStatus") != "market_ready":
            blocked.append({**candidate, "routerReasons": ["public_market_not_ready"], "routerBlockers": ["public_market_not_ready"]})
            continue
        inst_id = str(candidate.get("instId") or candidate.get("symbol") or "")
        if not inst_id:
            continue
        grouped[inst_id].append(candidate)

    winners: list[dict[str, Any]] = []
    for inst_id, rows in grouped.items():
        sorted_rows = sorted(rows, key=_candidate_score, reverse=True)
        winner = sorted_rows[0]
        winner_reasons = ["best_score_for_symbol"]
        if len({str(row.get("side") or row.get("direction") or "") for row in rows}) > 1:
            winner_reasons.append("direction_conflict_resolved")
        if _has_recent_duplicate(winner, recent_records):
            blocked.append({**winner, "routerReasons": winner_reasons, "routerBlockers": ["cooldown_duplicate_open_record"]})
        else:
            winners.append({**winner, "routerReasons": winner_reasons, "routerBlockers": []})
        for loser in sorted_rows[1:]:
            blocked.append({**loser, "routerReasons": ["same_symbol_lower_rank"], "routerBlockers": [f"higher_rank_candidate_selected_for_{inst_id}"]})

    winners.sort(key=_candidate_score, reverse=True)
    selected = winners[:max_executions]
    overflow = winners[max_executions:]
    blocked.extend({**row, "routerReasons": row.get("routerReasons") or ["over_max_execution_limit"], "routerBlockers": ["max_executions_per_run_reached"]} for row in overflow)
    return selected, blocked


def _build_record(candidate: dict[str, Any], run_id: str, notional_usdt: float, route_status: str, risk_status: str, passed: list[str], blockers: list[str]) -> dict[str, Any]:
    target_r = _safe_float(candidate.get("targetR"), 2.0)
    side = str(candidate.get("side") or "")
    lifecycle = "local_tp_sl_watch" if route_status == "selected" and risk_status == "passed" else "blocked_before_local_execution"
    return {
        "runId": run_id,
        "candidateId": candidate.get("candidateId"),
        "strategyId": candidate.get("strategyId"),
        "strategyName": candidate.get("strategyName"),
        "instId": candidate.get("instId"),
        "symbol": candidate.get("symbol"),
        "direction": candidate.get("direction"),
        "directionLabel": _direction_label(candidate),
        "side": side,
        "timeframe": candidate.get("timeframe"),
        "frequencyLabel": candidate.get("frequencyLabel"),
        "score": _safe_float(candidate.get("score")),
        "targetR": target_r,
        "winRatePct": _safe_float(candidate.get("winRatePct")),
        "profitFactor": _safe_float(candidate.get("profitFactor")),
        "tradeCount": _safe_int(candidate.get("tradeCount")),
        "notionalUsdt": notional_usdt,
        "routeStatus": route_status,
        "riskStatus": risk_status,
        "executionStatus": lifecycle,
        "executionMode": "local_auto_simulation",
        "tpSlPolicy": {
            "takeProfitR": target_r,
            "stopLossR": 1.0,
            "targetRewardRisk": "2R_or_better",
            "autoClose": True,
            "priceSource": "public_market_probe_without_private_account",
        },
        "lifecycle": [
            {"stepId": "candidate_loaded", "label": "候选已加载", "status": "completed"},
            {"stepId": "router", "label": "策略仲裁", "status": route_status},
            {"stepId": "risk_gate", "label": "风险门检查", "status": risk_status},
            {"stepId": "local_lifecycle", "label": "本地止盈止损观察", "status": lifecycle},
        ],
        "routerReasons": candidate.get("routerReasons") if isinstance(candidate.get("routerReasons"), list) else [],
        "routerBlockers": candidate.get("routerBlockers") if isinstance(candidate.get("routerBlockers"), list) else [],
        "riskPassed": passed,
        "riskBlockers": blockers,
        "manualTicketRequired": False,
        "userFacingTicketWorkflow": False,
        "internalAuditRecordOnly": True,
        "apiKeyUsed": False,
        "ordersCreated": False,
        "demoOrderCreated": False,
        "liveTrading": False,
        "withdrawEnabled": False,
        "note": "Local auto-execution lifecycle record only. It is not an exchange order.",
    }


def _summarize(records: list[dict[str, Any]], runs: list[dict[str, Any]]) -> dict[str, Any]:
    open_records = [row for row in records if row.get("executionStatus") == "local_tp_sl_watch"]
    blocked_records = [row for row in records if row.get("riskStatus") == "blocked" or row.get("routeStatus") == "blocked"]
    latest_run = runs[0] if runs else {}
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "stage": "no_ticket_auto_execution",
        "stageLabel": "无票据自动执行",
        "latestRunId": latest_run.get("runId"),
        "latestRunAt": latest_run.get("createdAt"),
        "totalRecentRecords": len(records),
        "openLifecycleRecords": len(open_records),
        "blockedRecords": len(blocked_records),
        "latestSelectedCount": latest_run.get("selectedCount") or 0,
        "latestBlockedCount": latest_run.get("blockedCount") or 0,
        "latestRecordCount": latest_run.get("recordCount") or 0,
        "defaultNotionalUsdt": MAX_LOCAL_OBSERVATION_NOTIONAL_USDT,
        "maxExecutionsPerRun": DEFAULT_MAX_EXECUTIONS_PER_RUN,
        "cooldownMinutes": DEFAULT_COOLDOWN_MINUTES,
        "userFacingTicketWorkflow": False,
        "liveAutoTradingLocked": True,
        "nextAction": "运行自动执行引擎后，系统会自动筛选、仲裁和保存本地模拟生命周期记录。",
    }


def build_auto_execution_engine() -> dict[str, Any]:
    runs = list_auto_execution_runs(limit=10)
    records = list_auto_execution_records(limit=40)
    workbench = build_no_key_pre_live_workbench()
    candidates = workbench.get("publicCandidates") if isinstance(workbench.get("publicCandidates"), list) else []
    ready_count = sum(1 for row in candidates if isinstance(row, dict) and row.get("screeningStatus") == "market_ready")
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            **_summarize(records, runs),
            "candidateCount": len(candidates),
            "marketReadyCount": ready_count,
        },
        "routerConfig": {
            "maxExecutionsPerRun": DEFAULT_MAX_EXECUTIONS_PER_RUN,
            "cooldownMinutes": DEFAULT_COOLDOWN_MINUTES,
            "minTargetR": MIN_TARGET_R,
            "minScore": MIN_SCORE,
            "minTradeCount": MIN_TRADE_COUNT,
            "minProfitFactor": MIN_PROFIT_FACTOR,
            "notionalCapUsdt": MAX_LOCAL_OBSERVATION_NOTIONAL_USDT,
        },
        "recentRuns": runs,
        "records": records,
        "workflow": [
            {"stepId": "public_candidates", "label": "公共行情候选", "status": "ready" if ready_count else "waiting"},
            {"stepId": "strategy_router", "label": "策略仲裁器", "status": "ready"},
            {"stepId": "risk_gate", "label": "本地风险门", "status": "ready"},
            {"stepId": "local_lifecycle", "label": "本地止盈止损生命周期", "status": "ready" if records else "waiting"},
            {"stepId": "demo_or_live_order", "label": "交易所订单", "status": "locked"},
        ],
        "safetyBoundary": {
            **SAFETY_BOUNDARY,
            "publicMarketOnly": True,
            "apiKeyRequired": False,
            "rawApiKeyStorageAllowed": False,
            "createsExchangeOrder": False,
            "userFacingTicketWorkflow": False,
            "internalAuditRecordsOnly": True,
        },
        "safetyNote": "This engine creates local simulation lifecycle records only. It does not submit Demo or live exchange orders.",
    }


def run_auto_execution_engine(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    max_executions = max(1, min(_safe_int(payload.get("maxExecutions"), DEFAULT_MAX_EXECUTIONS_PER_RUN), DEFAULT_MAX_EXECUTIONS_PER_RUN))
    notional_usdt = min(
        max(_safe_float(payload.get("notionalUsdt"), MAX_LOCAL_OBSERVATION_NOTIONAL_USDT), 1.0),
        MAX_LOCAL_OBSERVATION_NOTIONAL_USDT,
    )
    if bool(payload.get("refreshPublicScan", True)):
        scan_no_key_pre_live_candidates({"limit": 12})
    workbench = build_no_key_pre_live_workbench()
    candidates = [
        row for row in (workbench.get("publicCandidates") if isinstance(workbench.get("publicCandidates"), list) else [])
        if isinstance(row, dict)
    ]
    recent_records = list_auto_execution_records(limit=120)
    selected, router_blocked = _select_candidates(candidates, max_executions, recent_records)

    run_id = f"auto_execution::{now_iso()}"
    records: list[dict[str, Any]] = []
    for candidate in selected:
        risk_status, passed, blockers = _risk_gate(candidate, notional_usdt)
        route_status = "selected" if risk_status == "passed" else "blocked"
        records.append(_build_record(candidate, run_id, notional_usdt, route_status, risk_status, passed, blockers))
    for candidate in router_blocked:
        risk_status, passed, blockers = _risk_gate(candidate, notional_usdt)
        all_blockers = list(dict.fromkeys([*(candidate.get("routerBlockers") or []), *blockers]))
        records.append(_build_record(candidate, run_id, notional_usdt, "blocked", "blocked", passed, all_blockers))

    created_records = save_auto_execution_records(records)
    selected_count = sum(1 for row in created_records if row.get("routeStatus") == "selected" and row.get("riskStatus") == "passed")
    blocked_count = len(created_records) - selected_count
    run_record = save_auto_execution_run({
        "runId": run_id,
        "version": CONTROL_CONSOLE_VERSION,
        "selectedCount": selected_count,
        "blockedCount": blocked_count,
        "recordCount": len(created_records),
        "candidateCount": len(candidates),
        "notionalUsdt": notional_usdt,
        "maxExecutions": max_executions,
        "refreshPublicScan": bool(payload.get("refreshPublicScan", True)),
        "userFacingTicketWorkflow": False,
        "internalAuditRecordsOnly": True,
    })
    refreshed = build_auto_execution_engine()
    no_key_pre_live = build_no_key_pre_live_workbench()
    return {
        "ok": True,
        "run": run_record,
        "records": created_records,
        "noKeyPreLive": no_key_pre_live,
        "autoExecutionEngine": refreshed,
        "safetyBoundary": refreshed["safetyBoundary"],
    }
