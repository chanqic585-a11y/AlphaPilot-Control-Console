"""Build the operator-facing OKX Demo workflow without inventing trade state."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from .demo_evidence import build_demo_evidence_checklist
from .demo_market_scan_service import get_demo_strategy_market_scan
from .demo_strategy_runtime_settings import get_demo_strategy_runtime_settings


VERSION = "V13.27.4"
SOURCE = "demo_workflow_projection_v13_27_1_8"

QUEUE_BY_STAGE = {
    "demo_trial": "waiting",
    "demo_validation_running": "validating",
    "demo_validated": "passed",
    "live_candidate": "liveCandidate",
}

QUEUE_LABELS = {
    "waiting": "待 Demo 模拟",
    "validating": "Demo 验证中",
    "passed": "Demo 模拟通过",
    "liveCandidate": "实盘候选",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _unique(values: list[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in result:
            result.append(text)
    return result


def _candidate_rank(candidate: dict[str, Any]) -> tuple[int, float]:
    status = _text(candidate.get("screeningStatus"))
    status_rank = {"market_ready": 3, "scanned": 2, "strategy_loaded": 1}.get(status, 0)
    return status_rank, _number(candidate.get("score")) or 0.0


def _index_exchange_rows(exchange_demo: dict[str, Any]) -> dict[str, Any]:
    pipeline = _mapping(exchange_demo.get("automationPipeline"))
    evolution = _mapping(exchange_demo.get("evolutionDemo"))

    candidates_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in _rows(pipeline.get("candidates")):
        strategy_id = _text(candidate.get("strategyId"))
        if strategy_id:
            candidates_by_strategy[strategy_id].append(candidate)
    for rows in candidates_by_strategy.values():
        rows.sort(key=_candidate_rank, reverse=True)

    contracts_by_strategy: dict[str, dict[str, Any]] = {}
    strategy_by_release: dict[str, str] = {}
    for contract in _rows(evolution.get("contracts")):
        strategy_id = _text(contract.get("strategyCandidateId") or contract.get("strategyId"))
        release_id = _text(contract.get("demoReleaseId"))
        if strategy_id:
            contracts_by_strategy[strategy_id] = contract
        if strategy_id and release_id:
            strategy_by_release[release_id] = strategy_id

    records_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in _rows(evolution.get("recentRecords")):
        release_id = _text(record.get("demoReleaseId"))
        signal = _mapping(record.get("signal"))
        strategy_id = _text(
            signal.get("strategyCandidateId")
            or signal.get("strategyId")
            or strategy_by_release.get(release_id)
        )
        if strategy_id:
            records_by_strategy[strategy_id].append(record)

    outcomes_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for outcome in _rows(evolution.get("recentOutcomes")):
        strategy_id = _text(outcome.get("strategyCandidateId"))
        if strategy_id:
            outcomes_by_strategy[strategy_id].append(outcome)

    positions_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    portfolio = _mapping(exchange_demo.get("portfolioSnapshot"))
    for position in _rows(portfolio.get("positions")):
        strategy_id = _text(position.get("strategyCandidateId") or position.get("strategyId"))
        if strategy_id:
            positions_by_strategy[strategy_id].append(position)

    return {
        "pipeline": pipeline,
        "evolution": evolution,
        "candidatesByStrategy": candidates_by_strategy,
        "contractsByStrategy": contracts_by_strategy,
        "recordsByStrategy": records_by_strategy,
        "outcomesByStrategy": outcomes_by_strategy,
        "positionsByStrategy": positions_by_strategy,
    }


def _market_view(
    candidate: dict[str, Any],
    latest_record: dict[str, Any],
    latest_position: dict[str, Any],
    market_scan: dict[str, Any],
) -> dict[str, Any]:
    signal = _mapping(latest_record.get("signal"))
    instrument_id = _text(
        latest_position.get("instId")
        or signal.get("instId")
    ) or None
    current_top_candidate = _market_scan_top_candidate(market_scan)
    return {
        "instrumentId": instrument_id,
        "currentTopCandidate": current_top_candidate,
        "symbol": instrument_id or current_top_candidate,
        "side": _text(latest_position.get("side") or signal.get("side") or candidate.get("side")) or None,
        "dataStatus": _text(market_scan.get("matchStatus") or candidate.get("screeningStatus") or candidate.get("marketDataStatus")) or "not_started",
        "markPrice": _number(latest_position.get("markPrice") or latest_position.get("markPx")),
        "updatedAt": latest_position.get("updatedAt") or latest_record.get("updatedAt") or market_scan.get("updatedAt") or None,
    }


def _market_scan_top_candidate(market_scan: dict[str, Any]) -> str | None:
    match_status = _text(market_scan.get("matchStatus"))
    total_instruments = int(_number(market_scan.get("totalInstrumentCount")) or 0)
    if match_status == "not_started" or total_instruments <= 0:
        return None
    return _text(market_scan.get("currentTopCandidate")) or None


def _position_view(latest_record: dict[str, Any], latest_position: dict[str, Any]) -> dict[str, Any]:
    signal = _mapping(latest_record.get("signal"))
    order = _mapping(latest_record.get("orderPayload"))
    return {
        "status": _text(latest_position.get("status") or latest_record.get("status")) or "not_started",
        "side": _text(latest_position.get("side") or signal.get("side")) or None,
        "quantity": _number(
            latest_position.get("quantity")
            or latest_position.get("pos")
            or signal.get("quantity")
            or signal.get("sz")
            or order.get("sz")
        ),
        "entryPrice": _number(latest_position.get("entryPrice") or latest_position.get("avgPx") or signal.get("entryPrice")),
        "markPrice": _number(latest_position.get("markPrice") or latest_position.get("markPx")),
        "stopLossPrice": _number(latest_position.get("stopLossPrice") or signal.get("stopLossPrice")),
        "takeProfitPrice": _number(latest_position.get("takeProfitPrice") or signal.get("takeProfitPrice")),
        "openedAt": latest_position.get("openedAt") or latest_record.get("createdAt") or None,
    }


def _position_summaries(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for position in positions:
        view = _position_view({}, position)
        summaries.append(
            {
                "instrumentId": _text(position.get("instId") or position.get("symbol")) or None,
                **view,
                "unrealizedPnl": _number(position.get("unrealizedPnl") or position.get("upl")),
                "realizedPnl": _number(position.get("realizedPnl")),
                "updatedAt": position.get("updatedAt") or position.get("reconciledAt") or None,
            }
        )
    return summaries


def _performance_view(outcomes: list[dict[str, Any]], latest_position: dict[str, Any]) -> dict[str, Any]:
    realized_pnl = 0.0
    fees = 0.0
    slippage = 0.0
    wins = 0
    losses = 0
    for row in outcomes:
        payload = _mapping(row.get("outcome"))
        trade = _mapping(payload.get("trade"))
        net = _number(trade.get("netPnl"))
        fee = _number(trade.get("feePaid"))
        slip = _number(trade.get("slippagePaid"))
        if net is not None:
            realized_pnl += net
            wins += int(net > 0)
            losses += int(net < 0)
        if fee is not None:
            fees += fee
        if slip is not None:
            slippage += slip
    return {
        "realizedPnl": realized_pnl if outcomes else None,
        "unrealizedPnl": _number(latest_position.get("unrealizedPnl") or latest_position.get("upl")),
        "fees": fees if outcomes else None,
        "slippage": slippage if outcomes else None,
        "closedTradeCount": len(outcomes),
        "winCount": wins,
        "lossCount": losses,
    }


def _process_steps(
    *,
    stage: str,
    candidate: dict[str, Any],
    contract: dict[str, Any],
    records: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    runtime_ready: bool,
    readonly_status: str,
) -> list[dict[str, Any]]:
    market_ready = _text(candidate.get("screeningStatus")) == "market_ready"
    release_ready = bool(contract) or stage in {"demo_validation_running", "demo_validated", "live_candidate"}
    readonly_passed = readonly_status == "passed"
    preflight_complete = runtime_ready and readonly_passed
    preflight_status = "completed" if preflight_complete else (
        "blocked" if release_ready and readonly_passed else "pending"
    )
    return [
        {"stepId": "strategy_loaded", "label": "策略进入 Demo 队列", "status": "completed"},
        {
            "stepId": "public_market_scan",
            "label": "公共行情与候选币种检查",
            "status": "completed" if market_ready or release_ready else "pending",
        },
        {
            "stepId": "immutable_release",
            "label": "生成不可变 Demo Release",
            "status": "completed" if release_ready else "blocked",
        },
        {
            "stepId": "runtime_preflight",
            "label": "凭据、只读和风险闸门检查",
            "status": preflight_status,
        },
        {
            "stepId": "demo_execution",
            "label": "OKX Demo 信号、订单与持仓",
            "status": "completed" if outcomes else ("running" if records else "pending"),
        },
        {
            "stepId": "evidence_review",
            "label": "闭合交易复核",
            "status": "completed" if stage in {"demo_validated", "live_candidate"} else "pending",
        },
    ]


def _next_action(
    *,
    stage: str,
    candidate: dict[str, Any],
    contract: dict[str, Any],
    runtime_ready: bool,
    credentials_configured: bool,
    private_enabled: bool,
    order_enabled: bool,
    automation_enabled: bool,
    readonly_status: str,
) -> dict[str, Any]:
    market_ready = _text(candidate.get("screeningStatus")) == "market_ready"
    if stage == "demo_trial" and not market_ready:
        return {
            "actionId": "scan_public_market",
            "label": "检查 Demo 行情",
            "description": "先用 OKX 公共行情检查策略候选币种；不会下单。",
            "enabled": True,
        }
    if stage == "demo_trial" and not contract:
        return {
            "actionId": "prepare_demo_release",
            "label": "检查 Demo Release 条件",
            "description": "核对回测、前向样本和不可变证据；不满足时会列出缺项。",
            "enabled": True,
        }
    if not credentials_configured or not private_enabled:
        return {
            "actionId": "start_with_demo_credentials",
            "label": "用 Demo 凭据重启",
            "description": "使用进程环境变量启动；页面不会保存 API Key。",
            "enabled": False,
            "command": "powershell -ExecutionPolicy Bypass -File scripts\\start_okx_demo_console.ps1",
        }
    if readonly_status != "passed":
        return {
            "actionId": "run_demo_preflight",
            "label": "运行 Demo 前检查",
            "description": "先验证 OKX Demo 只读连接、账户配置、模拟余额和模拟持仓。",
            "enabled": True,
        }
    if not order_enabled or not automation_enabled:
        return {
            "actionId": "restart_with_demo_automation",
            "label": "开启 Demo 自动化启动器",
            "description": "只读已通过；请用订单和自动化闸门重启，仍只连接 OKX Demo，不启用实盘。",
            "enabled": False,
            "command": (
                "powershell -ExecutionPolicy Bypass -File "
                "scripts\\start_okx_demo_console.ps1 -EnableOrder -EnableAutomation"
            ),
        }
    if not runtime_ready:
        return {
            "actionId": "resolve_demo_runtime_blockers",
            "label": "处理 Demo 运行阻塞",
            "description": "凭据和执行闸门已开启，但 Release、风险包或停止开关仍阻塞运行。",
            "enabled": False,
        }
    if stage == "demo_validation_running":
        return {
            "actionId": "run_demo_cycle",
            "label": "运行一次 Demo 验证",
            "description": "从冻结 Release 读取信号并在 OKX Demo 执行；实盘保持关闭。",
            "enabled": True,
        }
    if stage == "demo_validated":
        return {
            "actionId": "review_live_candidate",
            "label": "复核实盘候选",
            "description": "只生成候选复核，不会启用实盘。",
            "enabled": False,
        }
    return {
        "actionId": "review_live_candidate",
        "label": "查看实盘候选",
        "description": "等待人工发布复核。",
        "enabled": False,
    }


def _progress(
    *,
    stage: str,
    candidate: dict[str, Any],
    contract: dict[str, Any],
    records: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    runtime_ready: bool,
    readonly_status: str,
) -> dict[str, Any]:
    if stage == "demo_trial":
        market_ready = _text(candidate.get("screeningStatus")) == "market_ready"
        return {
            "phase": "release_preparation" if market_ready else "market_preflight",
            "label": "等待不可变 Demo Release" if market_ready else "等待 Demo 行情检查",
            "completed": 2 if market_ready else 1,
            "required": 6,
            "percent": 33 if market_ready else 17,
        }
    if stage == "demo_validation_running":
        preflight_complete = runtime_ready and readonly_status == "passed"
        completed = 3 + int(preflight_complete) + int(bool(records) and preflight_complete)
        return {
            "phase": "demo_execution" if preflight_complete else "runtime_preflight",
            "label": "正在收集 Demo 闭合交易" if preflight_complete else "等待 Demo 运行前检查",
            "completed": completed,
            "required": 6,
            "percent": min(83, round(completed / 6 * 100)),
        }
    return {
        "phase": "completed",
        "label": "Demo 验证已通过" if stage == "demo_validated" else "已进入实盘候选复核",
        "completed": 6,
        "required": 6,
        "percent": 100,
    }


def _failure_view(
    *,
    stage: str,
    lifecycle_item: dict[str, Any],
    contract: dict[str, Any],
    evolution_blockers: list[Any],
    latest_record: dict[str, Any],
) -> dict[str, Any]:
    blockers = _unique([*list(lifecycle_item.get("blockers") or []), *evolution_blockers])
    record_status = _text(latest_record.get("status"))
    if stage == "demo_trial" and not contract:
        return {
            "status": "blocked",
            "category": "release_missing",
            "reason": "no_eligible_demo_release",
            "analysis": "尚未生成不可变 Demo Release，因此还没有交易所订单、持仓或 Demo 盈亏。",
            "suggestions": [
                "先完成公共行情检查。",
                "核对正式回测和本地前向闭合样本证据。",
                "证据齐全后生成不可变 Demo Release。",
            ],
            "blockers": _unique(["no_eligible_demo_release", *blockers]),
            "canRetrySameVersion": True,
            "canOptimize": True,
        }
    if record_status in {"unknown", "rejected", "canceled", "mmp_canceled"} or blockers:
        return {
            "status": "failed" if record_status in {"rejected", "canceled", "mmp_canceled"} else "blocked",
            "category": "demo_runtime",
            "reason": record_status or (blockers[0] if blockers else "demo_runtime_blocked"),
            "analysis": "Demo 运行证据显示阻塞或失败；先处理连接、风控或订单状态，再决定同版本重试或参数优化。",
            "suggestions": ["复核运行闸门与订单状态。", "运行对账后再恢复。"],
            "blockers": blockers,
            "canRetrySameVersion": True,
            "canOptimize": True,
        }
    return {
        "status": "none",
        "category": None,
        "reason": None,
        "analysis": None,
        "suggestions": [],
        "blockers": [],
        "canRetrySameVersion": False,
        "canOptimize": True,
    }


def _build_item(
    lifecycle_item: dict[str, Any],
    exchange_demo: dict[str, Any],
    indexes: dict[str, Any],
    market_scan_loader: Callable[[str], dict[str, Any]],
    settings_loader: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    strategy_id = _text(lifecycle_item.get("strategyId"))
    stage = _text(lifecycle_item.get("currentStage"))
    candidates = indexes["candidatesByStrategy"].get(strategy_id, [])
    candidate = candidates[0] if candidates else {}
    market_scan = market_scan_loader(strategy_id)
    settings = settings_loader(strategy_id)
    effective_candidate = dict(candidate)
    if int(_number(market_scan.get("totalInstrumentCount")) or 0) > 0 and not list(market_scan.get("errors") or []):
        effective_candidate["screeningStatus"] = "market_ready"
    contract = indexes["contractsByStrategy"].get(strategy_id, {})
    records = indexes["recordsByStrategy"].get(strategy_id, [])
    outcomes = indexes["outcomesByStrategy"].get(strategy_id, [])
    positions = indexes["positionsByStrategy"].get(strategy_id, [])
    latest_record = records[-1] if records else {}
    latest_position = positions[-1] if positions else {}
    summary = _mapping(exchange_demo.get("summary"))
    evolution = indexes["evolution"]
    runtime_gates = _mapping(evolution.get("runtimeGates"))
    runtime_ready = bool(_mapping(evolution.get("summary")).get("ready"))
    credentials_configured = bool(summary.get("credentialsConfigured"))
    private_enabled = bool(runtime_gates.get("privateEnabled", summary.get("demoPrivateEnabled")))
    order_enabled = bool(runtime_gates.get("orderEnabled", summary.get("demoOrderEnabled")))
    automation_enabled = bool(runtime_gates.get("automationEnabled"))
    readonly_status = _text(_mapping(exchange_demo.get("readonlySummary")).get("status"))
    queue = QUEUE_BY_STAGE[stage]
    active_profile_record = _mapping(evolution.get("activeRiskProfile"))
    active_profile = _mapping(active_profile_record.get("profile"))
    contract_limits = _mapping(contract.get("riskEnvelope"))
    requested_symbols = max(1, int(_number(settings.get("maxConcurrentSymbols")) or 1))
    profile_position_limit = max(
        1,
        int(_number(contract_limits.get("maxPositionsPerStrategy") or active_profile.get("maxPositionsPerStrategy")) or 1),
    )
    profile_portfolio_limit = max(
        1,
        int(_number(contract_limits.get("maxConcurrentPositions") or active_profile.get("maxConcurrentPositions")) or 1),
    )
    effective_configured_maximum = min(requested_symbols, profile_position_limit, profile_portfolio_limit)
    evidence_checklist = build_demo_evidence_checklist(
        lifecycle_item,
        contract=contract,
        runtime={
            "credentialsConfigured": credentials_configured,
            "privateEnabled": private_enabled,
            "orderEnabled": order_enabled,
            "automationReady": runtime_ready,
            "closedTradeCount": len(outcomes),
        },
    )
    return {
        "strategyId": strategy_id,
        "displayName": lifecycle_item.get("displayName") or strategy_id,
        "currentStage": stage,
        "queue": queue,
        "queueLabel": QUEUE_LABELS[queue],
        "timeframe": lifecycle_item.get("timeframe"),
        "direction": lifecycle_item.get("direction"),
        "metrics": _mapping(lifecycle_item.get("metrics")),
        "evidenceChecklist": evidence_checklist,
        "marketUniverse": {
            "marketScope": market_scan.get("marketScope") or "okx_usdt_linear_perpetual_full_market",
            "totalInstrumentCount": int(_number(market_scan.get("totalInstrumentCount")) or 0),
            "liveUsdtLinearSwapCount": int(_number(market_scan.get("liveUsdtLinearSwapCount")) or 0),
            "liquidityEligibleCount": int(_number(market_scan.get("liquidityEligibleCount")) or 0),
            "deepScreenedCount": int(_number(market_scan.get("deepScreenedCount")) or 0),
            "strategyMatchedCount": market_scan.get("strategyMatchedCount"),
            "currentTopCandidate": _market_scan_top_candidate(market_scan),
            "rankedCandidates": list(market_scan.get("rankedCandidates") or []),
            "progress": _mapping(market_scan.get("progress")),
            "matchStatus": market_scan.get("matchStatus") or "not_started",
            "updatedAt": market_scan.get("updatedAt"),
        },
        "executionLimits": {
            "requestedMaxConcurrentSymbols": requested_symbols,
            "profileMaxPositionsPerStrategy": profile_position_limit,
            "profileMaxConcurrentPositions": profile_portfolio_limit,
            "effectiveConfiguredMaximum": effective_configured_maximum,
            "currentOpenPositions": len(positions),
            "availableConfiguredSlots": max(0, effective_configured_maximum - len(positions)),
            "note": "实际可开仓数还会取剩余组合风险、重复币种和相关性闸门的更低值。",
        },
        "release": {
            "formal": bool(contract),
            "demoReleaseId": contract.get("demoReleaseId"),
            "status": contract.get("status"),
        },
        "progress": _progress(
            stage=stage,
            candidate=effective_candidate,
            contract=contract,
            records=records,
            outcomes=outcomes,
            runtime_ready=runtime_ready,
            readonly_status=readonly_status,
        ),
        "processSteps": _process_steps(
            stage=stage,
            candidate=effective_candidate,
            contract=contract,
            records=records,
            outcomes=outcomes,
            runtime_ready=runtime_ready,
            readonly_status=readonly_status,
        ),
        "market": _market_view(effective_candidate, latest_record, latest_position, market_scan),
        "position": _position_view(latest_record, latest_position),
        "positions": _position_summaries(positions),
        "performance": _performance_view(outcomes, latest_position),
        "reconciliation": {
            "status": _text(latest_position.get("reconciliationStatus")) or ("not_started" if not records else "pending"),
            "updatedAt": latest_position.get("reconciledAt"),
        },
        "failure": _failure_view(
            stage=stage,
            lifecycle_item=lifecycle_item,
            contract=contract,
            evolution_blockers=list(evolution.get("blockers") or []),
            latest_record=latest_record,
        ),
        "nextAction": _next_action(
            stage=stage,
            candidate=effective_candidate,
            contract=contract,
            runtime_ready=runtime_ready,
            credentials_configured=credentials_configured,
            private_enabled=private_enabled,
            order_enabled=order_enabled,
            automation_enabled=automation_enabled,
            readonly_status=readonly_status,
        ),
        "stageEnteredAt": lifecycle_item.get("stageEnteredAt"),
    }


def build_demo_workflow_projection(
    *,
    lifecycle: dict[str, Any],
    exchange_demo: dict[str, Any],
    market_scan_loader: Callable[[str], dict[str, Any]] = get_demo_strategy_market_scan,
    settings_loader: Callable[[str], dict[str, Any]] = get_demo_strategy_runtime_settings,
) -> dict[str, Any]:
    """Project lifecycle and actual Demo evidence into four exclusive queues."""

    indexes = _index_exchange_rows(exchange_demo)
    queues: dict[str, list[dict[str, Any]]] = {
        "waiting": [],
        "validating": [],
        "passed": [],
        "liveCandidate": [],
    }
    for lifecycle_item in _rows(lifecycle.get("items")):
        stage = _text(lifecycle_item.get("currentStage"))
        queue = QUEUE_BY_STAGE.get(stage)
        if not queue:
            continue
        queues[queue].append(
            _build_item(
                lifecycle_item,
                exchange_demo,
                indexes,
                market_scan_loader,
                settings_loader,
            )
        )

    for rows in queues.values():
        rows.sort(key=lambda item: (_text(item.get("displayName")), _text(item.get("strategyId"))))

    return {
        "version": VERSION,
        "source": SOURCE,
        "generatedAt": _now_iso(),
        "summary": {
            "waitingCount": len(queues["waiting"]),
            "validatingCount": len(queues["validating"]),
            "passedCount": len(queues["passed"]),
            "liveCandidateCount": len(queues["liveCandidate"]),
        },
        "queues": queues,
        "runtime": {
            "credentialsConfigured": bool(_mapping(exchange_demo.get("summary")).get("credentialsConfigured")),
            "privateEnabled": bool(_mapping(exchange_demo.get("summary")).get("demoPrivateEnabled")),
            "orderEnabled": bool(_mapping(exchange_demo.get("summary")).get("demoOrderEnabled")),
            "readonlyStatus": _text(_mapping(exchange_demo.get("readonlySummary")).get("status")) or "not_run",
            "automationReady": bool(_mapping(indexes["evolution"].get("summary")).get("ready")),
            "blockers": list(indexes["evolution"].get("blockers") or []),
        },
        "safetyBoundary": {
            "okxDemoOnly": True,
            "liveExecutionAllowed": False,
            "withdrawAllowed": False,
            "fabricatedTradeDataAllowed": False,
        },
    }
