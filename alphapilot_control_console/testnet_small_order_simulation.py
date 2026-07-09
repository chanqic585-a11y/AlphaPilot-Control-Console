from __future__ import annotations

import json
from typing import Any

from .config import SAFETY_BOUNDARY
from .pre_live_preparation_pack import REFERENCE_INPUTS
from .state_store import list_testnet_simulated_orders, now_iso, save_testnet_simulated_order
from .strategy_asset_playbook import build_strategy_asset_playbook
from .testnet_permission_check import build_testnet_permission_check


CONTROL_CONSOLE_VERSION = "V13.9.1"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_9_1"
VIRTUAL_TESTNET_ACCOUNT_USDT = 1000
DEFAULT_SMALL_ORDER_NOTIONAL_USDT = 5
MAX_SMALL_ORDER_NOTIONAL_USDT = 5
MAX_SMALL_ORDER_RISK_R = 0.1


SIMULATED_ORDER_PATH = [
    {
        "stageId": "candidate_selected",
        "label": "选择候选策略",
        "description": "从本地策略资产中选择一个观察候选。",
    },
    {
        "stageId": "permission_snapshot",
        "label": "权限快照",
        "description": "确认 API Key、Trade API、Withdraw API 和私有连接仍关闭。",
    },
    {
        "stageId": "small_order_ticket",
        "label": "小额模拟票据",
        "description": "生成 5 USDT 上限的本地 testnet 模拟票据，不是交易所订单。",
    },
    {
        "stageId": "local_risk_check",
        "label": "本地风控检查",
        "description": "检查虚拟本金、单次风险、重复路径和人工确认字段。",
    },
    {
        "stageId": "manual_simulation_approval",
        "label": "人工模拟确认",
        "description": "只有 approve_simulation 才进入本地模拟接受路径。",
    },
    {
        "stageId": "simulated_accept",
        "label": "本地模拟接受",
        "description": "只写入本地状态，不发送任何网络订单。",
    },
    {
        "stageId": "simulated_fill_preview",
        "label": "本地成交预览",
        "description": "只生成预览数据，不改变真实账户或真实持仓。",
    },
    {
        "stageId": "audit_closeout",
        "label": "审计收尾",
        "description": "保存安全边界、拒绝原因和下一步检查项。",
    },
]


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _pick_default_strategy() -> dict[str, Any]:
    playbook = build_strategy_asset_playbook()
    rows = playbook.get("strategies") if isinstance(playbook.get("strategies"), list) else []
    for row in rows:
        if isinstance(row, dict):
            return row
    return {}


def _build_path(passed: bool) -> list[dict[str, Any]]:
    path = []
    for stage in SIMULATED_ORDER_PATH:
        state = "passed" if passed else "checked"
        if stage["stageId"] in {"simulated_accept", "simulated_fill_preview"}:
            state = "simulated" if passed else "skipped"
        if stage["stageId"] == "audit_closeout":
            state = "saved_local_audit"
        path.append({**stage, "state": state})
    return path


def build_testnet_small_order_simulation() -> dict[str, Any]:
    permission = build_testnet_permission_check()
    recent = list_testnet_simulated_orders(limit=12)
    strategy = _pick_default_strategy()
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "stage": "small_testnet_order_simulation",
            "stageLabel": "小额 Testnet 模拟",
            "virtualAccountUsdt": VIRTUAL_TESTNET_ACCOUNT_USDT,
            "defaultNotionalUsdt": DEFAULT_SMALL_ORDER_NOTIONAL_USDT,
            "maxNotionalUsdt": MAX_SMALL_ORDER_NOTIONAL_USDT,
            "maxRiskR": MAX_SMALL_ORDER_RISK_R,
            "recentSimulationCount": len(recent),
            "canCreateExchangeOrder": False,
            "canConnectPrivateTestnet": False,
            "nextAction": "可以保存本地小额 testnet 模拟票据；真实 testnet 下单仍需单独完成凭据保险箱和人工解锁。",
        },
        "defaultTicket": {
            "strategyId": strategy.get("taskId") or strategy.get("strategyId") or "local_testnet_small_order_candidate",
            "readableName": strategy.get("readableName") or strategy.get("plainName") or "本地候选策略",
            "symbol": strategy.get("symbol") or "BTC/USDT:USDT",
            "side": "research_simulated_long",
            "notionalUsdt": DEFAULT_SMALL_ORDER_NOTIONAL_USDT,
            "riskR": 0.05,
        },
        "orderPath": SIMULATED_ORDER_PATH,
        "recentSimulations": recent,
        "referenceInputs": REFERENCE_INPUTS,
        "permissionSummary": permission.get("summary", {}),
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Small order simulation is local-only. It is not an exchange order and cannot connect private testnet endpoints.",
    }


def create_testnet_small_order_simulation(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    default_pack = build_testnet_small_order_simulation()
    default_ticket = default_pack.get("defaultTicket") if isinstance(default_pack.get("defaultTicket"), dict) else {}
    strategy_id = str(payload.get("strategyId") or default_ticket.get("strategyId") or "local_testnet_small_order_candidate")
    symbol = str(payload.get("symbol") or default_ticket.get("symbol") or "BTC/USDT:USDT")
    side = str(payload.get("side") or default_ticket.get("side") or "research_simulated_long")
    notional = _safe_float(payload.get("notionalUsdt"), DEFAULT_SMALL_ORDER_NOTIONAL_USDT)
    risk_r = _safe_float(payload.get("riskR"), 0.05)
    manual_decision = str(payload.get("manualDecision") or "approve_simulation")

    rejection_reasons: list[str] = []
    if notional <= 0:
        rejection_reasons.append("notional_must_be_positive")
    if notional > MAX_SMALL_ORDER_NOTIONAL_USDT:
        rejection_reasons.append("notional_exceeds_5_usdt_local_cap")
    if risk_r < 0:
        rejection_reasons.append("risk_r_must_not_be_negative")
    if risk_r > MAX_SMALL_ORDER_RISK_R:
        rejection_reasons.append("risk_r_exceeds_small_order_cap")
    if manual_decision != "approve_simulation":
        rejection_reasons.append("manual_simulation_approval_missing")
    if SAFETY_BOUNDARY.get("tradeApiAllowed") is not False:
        rejection_reasons.append("safety_boundary_trade_api_unexpected")

    passed = not rejection_reasons
    record = {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "strategyId": strategy_id,
        "symbol": symbol,
        "side": side,
        "notionalUsdt": notional,
        "riskR": risk_r,
        "manualDecision": manual_decision,
        "status": "simulated_fill_preview" if passed else "simulated_rejected",
        "riskPassed": passed,
        "rejectionReasons": rejection_reasons,
        "path": _build_path(passed),
        "virtualAccountUsdt": VIRTUAL_TESTNET_ACCOUNT_USDT,
        "createdExchangeOrder": False,
        "connectedExchange": False,
        "storedApiKey": False,
        "privateEndpointUsed": False,
        "safetyBoundary": {
            "localRecordOnly": True,
            "notAnExchangeOrder": True,
            "apiKeyUsed": False,
            "tradeApiUsed": False,
            "withdrawApiUsed": False,
            "realAccountRead": False,
            "realPositionRead": False,
            "createdExchangeOrder": False,
        },
        "safetyNote": "This is a local testnet small-order simulation ticket only. No exchange request was sent.",
    }
    saved = save_testnet_simulated_order(record)
    pack = build_testnet_small_order_simulation()
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "simulation": saved,
        "testnetSmallOrderSimulation": pack,
        "safetyBoundary": SAFETY_BOUNDARY,
    }


if __name__ == "__main__":
    print(json.dumps(build_testnet_small_order_simulation(), ensure_ascii=False, indent=2))
