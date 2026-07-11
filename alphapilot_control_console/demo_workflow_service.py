"""Coordinate the next legal OKX Demo workflow step without bypassing gates."""

from __future__ import annotations

from typing import Any

from .demo_override_release import authorize_demo_override
from .demo_market_scan_service import scan_demo_strategy_public_universe
from .demo_strategy_runtime_settings import update_demo_strategy_runtime_settings
from .demo_workflow_projection import build_demo_workflow_projection
from .evolution_demo_service import run_evolution_demo_cycle
from .exchange_demo_simulation import (
    build_exchange_demo_simulation,
    run_exchange_demo_readonly_check,
)
from .strategy_lifecycle_projection import build_strategy_lifecycle_projection


SAFETY_BOUNDARY = {
    "okxDemoOnly": True,
    "createsOrder": False,
    "liveExecutionAllowed": False,
    "withdrawAllowed": False,
    "rawCredentialStorageAllowed": False,
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _build_sources() -> tuple[dict[str, Any], dict[str, Any]]:
    return build_strategy_lifecycle_projection(), build_exchange_demo_simulation()


def build_demo_workflow_status() -> dict[str, Any]:
    lifecycle, exchange_demo = _build_sources()
    return build_demo_workflow_projection(lifecycle=lifecycle, exchange_demo=exchange_demo)


def _find_lifecycle_item(lifecycle: dict[str, Any], strategy_id: str) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in lifecycle.get("items", [])
            if isinstance(row, dict) and _text(row.get("strategyId")) == strategy_id
        ),
        None,
    )


def _find_contract(exchange_demo: dict[str, Any], strategy_id: str) -> dict[str, Any] | None:
    evolution = exchange_demo.get("evolutionDemo") if isinstance(exchange_demo.get("evolutionDemo"), dict) else {}
    return next(
        (
            row
            for row in evolution.get("contracts", [])
            if isinstance(row, dict)
            and _text(row.get("strategyCandidateId") or row.get("strategyId")) == strategy_id
        ),
        None,
    )


def _response_workflow(
    lifecycle: dict[str, Any] | None = None,
    exchange_demo: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if lifecycle is None or exchange_demo is None:
        lifecycle, exchange_demo = _build_sources()
    return build_demo_workflow_projection(lifecycle=lifecycle, exchange_demo=exchange_demo)


def _blocked(
    *,
    message: str,
    blockers: list[str],
    workflow: dict[str, Any],
    readiness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "blocked",
        "message": message,
        "blockers": blockers,
        "readiness": readiness or {},
        "workflow": workflow,
        "safetyBoundary": SAFETY_BOUNDARY,
    }


def _release_readiness(item: dict[str, Any], exchange_demo: dict[str, Any]) -> dict[str, Any]:
    metrics = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}
    optimization = item.get("optimizationContext") if isinstance(item.get("optimizationContext"), dict) else {}
    definition = optimization.get("definition") if isinstance(optimization.get("definition"), dict) else {}
    parameters = optimization.get("parameters") if isinstance(optimization.get("parameters"), dict) else {}
    closed_samples = int(_number(metrics.get("closedSamples")))
    trade_count = int(_number(metrics.get("tradeCount")))
    target_r = _number(
        definition.get("targetR")
        or parameters.get("targetRewardRiskRatio")
        or parameters.get("targetR"),
        0.0,
    )
    strategy_definition_complete = bool(
        str(definition.get("family") or "").strip()
        and str(definition.get("direction") or item.get("direction") or "").strip()
        and str(definition.get("timeframe") or item.get("timeframe") or "").strip()
        and parameters
    )
    contract = _find_contract(exchange_demo, _text(item.get("strategyId")))
    readiness = {
        "strategyId": item.get("strategyId"),
        "historicalBacktestAvailable": trade_count > 0,
        "historicalTradeCount": trade_count,
        "closedSamples": closed_samples,
        "reviewStartSamples": 30,
        "localForwardReviewStartReached": closed_samples >= 30,
        "targetR": target_r,
        "targetRPassed": target_r >= 2.0,
        "strategyDefinitionComplete": strategy_definition_complete,
        "formalStrategyCandidateRegistered": bool(contract),
        "immutableDemoReleaseAvailable": bool(contract),
        "note": "30 个闭合样本只是正式复核起点，不代表自动通过全部 Demo 硬门槛。",
    }
    return readiness


def run_demo_workflow_action(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    action = _text(payload.get("action"))
    strategy_id = _text(payload.get("strategyId"))
    lifecycle, exchange_demo = _build_sources()
    item = _find_lifecycle_item(lifecycle, strategy_id)
    if not strategy_id or item is None:
        return _blocked(
            message="找不到要操作的 Demo 策略。",
            blockers=["demo_strategy_not_found"],
            workflow=_response_workflow(lifecycle, exchange_demo),
        )

    if action == "scan_public_market":
        scan_result = scan_demo_strategy_public_universe(strategy_id)
        return {
            "ok": bool(scan_result.get("ok")),
            "status": "completed" if scan_result.get("ok") else "failed",
            "message": "OKX USDT 永续全市场公共行情检查完成。" if scan_result.get("ok") else "OKX 全市场公共行情检查失败。",
            "workflow": build_demo_workflow_status(),
            "scan": scan_result.get("scan") or {},
            "safetyBoundary": SAFETY_BOUNDARY,
        }

    if action == "prepare_demo_release":
        readiness = _release_readiness(item, exchange_demo)
        blockers: list[str] = []
        if not readiness["historicalBacktestAvailable"]:
            blockers.append("formal_backtest_evidence_missing")
        if not readiness["localForwardReviewStartReached"]:
            blockers.append("local_forward_evidence_incomplete")
        if not readiness["targetRPassed"]:
            blockers.append("target_r_below_2r")
        if not readiness["strategyDefinitionComplete"]:
            blockers.append("strategy_definition_incomplete")
        if not readiness["formalStrategyCandidateRegistered"]:
            blockers.append("formal_strategy_candidate_not_registered")
        if not readiness["immutableDemoReleaseAvailable"]:
            blockers.append("immutable_demo_release_missing")
        if blockers:
            return _blocked(
                message="这条策略尚不能进入交易所 Demo 下单；请先补齐下面的正式证据。",
                blockers=blockers,
                readiness=readiness,
                workflow=_response_workflow(lifecycle, exchange_demo),
            )
        return {
            "ok": True,
            "status": "ready",
            "message": "不可变 Demo Release 已存在，可以继续运行前检查。",
            "readiness": readiness,
            "workflow": _response_workflow(lifecycle, exchange_demo),
            "safetyBoundary": SAFETY_BOUNDARY,
        }

    if action == "authorize_demo_override":
        result = authorize_demo_override(
            item,
            reason=_text(payload.get("reason")),
            confirmation=_text(payload.get("confirmation")),
        )
        return {
            "ok": bool(result.get("ok")),
            "status": result.get("status") or ("ready" if result.get("ok") else "blocked"),
            "message": (
                "受控 Demo-only Release 已生成；实盘晋级仍锁定。"
                if result.get("ok")
                else "受控 Demo 放行未通过硬门槛。"
            ),
            "blockers": list(result.get("blockers") or []),
            "override": result,
            "workflow": build_demo_workflow_status() if result.get("ok") else _response_workflow(lifecycle, exchange_demo),
            "safetyBoundary": SAFETY_BOUNDARY,
        }

    if action == "update_demo_strategy_settings":
        try:
            settings = update_demo_strategy_runtime_settings(
                strategy_id,
                payload.get("maxConcurrentSymbols", 1),
            )
        except (TypeError, ValueError) as error:
            return _blocked(
                message="每策略同时开仓币种数必须是 1 到 10 的整数。",
                blockers=[str(error)],
                workflow=_response_workflow(lifecycle, exchange_demo),
            )
        return {
            "ok": True,
            "status": "completed",
            "message": "每策略同时开仓币种上限已保存；组合风险上限仍优先。",
            "settings": settings,
            "workflow": build_demo_workflow_status(),
            "safetyBoundary": SAFETY_BOUNDARY,
        }

    if action == "run_demo_preflight":
        result = run_exchange_demo_readonly_check()
        updated_exchange = result.get("exchangeDemoSimulation")
        if not isinstance(updated_exchange, dict):
            updated_exchange = build_exchange_demo_simulation()
        return {
            "ok": bool(result.get("ok")),
            "status": "completed" if result.get("ok") else "blocked",
            "message": "OKX Demo 运行前检查通过。" if result.get("ok") else "OKX Demo 运行前检查未通过。",
            "blockers": list((result.get("event") or {}).get("blockers") or []),
            "workflow": _response_workflow(lifecycle, updated_exchange),
            "safetyBoundary": SAFETY_BOUNDARY,
        }

    if action in {"run_demo_cycle", "retry_demo_cycle"}:
        contract = _find_contract(exchange_demo, strategy_id)
        if contract is None:
            return _blocked(
                message="没有匹配这条策略的不可变 Demo Release，禁止提交 Demo 订单。",
                blockers=["immutable_demo_release_missing"],
                workflow=_response_workflow(lifecycle, exchange_demo),
            )
        release_id = _text(contract.get("demoReleaseId"))
        result = run_evolution_demo_cycle({"demoReleaseId": release_id})
        return {
            "ok": bool(result.get("ok")),
            "status": "completed" if result.get("ok") else "blocked",
            "message": "Demo 验证周期已完成。" if result.get("ok") else "Demo 验证周期被闸门阻塞。",
            "blockers": list(result.get("blockers") or []),
            "cycle": result,
            "workflow": build_demo_workflow_status(),
            "safetyBoundary": {
                **SAFETY_BOUNDARY,
                "createsOrder": bool(result.get("created")),
            },
        }

    return _blocked(
        message="不支持这个 Demo 工作流动作。",
        blockers=["unsupported_demo_workflow_action"],
        workflow=_response_workflow(lifecycle, exchange_demo),
    )
