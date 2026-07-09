from __future__ import annotations

import json
from typing import Any

from .config import SAFETY_BOUNDARY
from .state_store import list_pre_live_rehearsals, now_iso
from .strategy_asset_playbook import build_strategy_asset_playbook


CONTROL_CONSOLE_VERSION = "V13.8.9"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8_9"
VIRTUAL_ACCOUNT_USDT = 1000


ORDER_LIFECYCLE_DRILL = [
    {
        "stageId": "candidate_selected",
        "label": "选择候选策略",
        "state": "local_only",
        "description": "从策略资产闸门里选择一条研究候选，不自动生成订单。",
    },
    {
        "stageId": "intent_draft",
        "label": "生成本地意图草稿",
        "state": "local_only",
        "description": "只生成本地演练字段，不包含交易所订单字段。",
    },
    {
        "stageId": "risk_check",
        "label": "风控检查",
        "state": "local_only",
        "description": "检查 1000 USDT 虚拟账户、单次 1R、日内 -2R、冷却和重复意图。",
    },
    {
        "stageId": "manual_confirm",
        "label": "人工确认",
        "state": "required",
        "description": "未来任何 testnet 或真实动作都必须先由用户手动确认。",
    },
    {
        "stageId": "simulated_submit",
        "label": "本地模拟提交",
        "state": "local_only",
        "description": "只写本地审计记录，不发送网络请求。",
    },
    {
        "stageId": "accepted_or_rejected",
        "label": "本地接受或拒绝",
        "state": "local_only",
        "description": "根据风控结果模拟 accepted / rejected，不调用交易所。",
    },
    {
        "stageId": "filled_or_cancelled",
        "label": "本地成交或取消",
        "state": "local_only",
        "description": "只演练状态机，不产生真实 fill，不改变真实持仓。",
    },
    {
        "stageId": "audit_closeout",
        "label": "审计收尾",
        "state": "required",
        "description": "记录结果、拒绝原因、人工确认和安全边界。",
    },
]


RISK_TEMPLATE = [
    {
        "itemId": "virtual_account",
        "label": "单策略虚拟账户",
        "value": f"{VIRTUAL_ACCOUNT_USDT} USDT",
        "status": "required",
    },
    {
        "itemId": "single_risk",
        "label": "单次风险",
        "value": "1R / 约 1%",
        "status": "required",
    },
    {
        "itemId": "reward_risk",
        "label": "目标盈亏比",
        "value": "2R，不降低",
        "status": "required",
    },
    {
        "itemId": "daily_stop",
        "label": "日内熔断",
        "value": "-2R 暂停",
        "status": "required",
    },
    {
        "itemId": "strategy_pause",
        "label": "单策略暂停",
        "value": "连续异常或数据缺口时暂停",
        "status": "required",
    },
]


DISABLED_EXECUTION = [
    "API Key input disabled",
    "Trade API disabled",
    "Withdraw API disabled",
    "Real account reads disabled",
    "Real position reads disabled",
    "Order creation disabled",
    "Exchange dry-run disabled",
    "Automatic trading disabled",
]


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _rehearsal_summary(rehearsals: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(1 for row in rehearsals if row.get("riskPassed") is True)
    rejected = sum(1 for row in rehearsals if row.get("riskPassed") is not True)
    latest = rehearsals[0] if rehearsals else {}
    local_paths_complete = passed > 0 and rejected > 0
    blockers = []
    if passed <= 0:
        blockers.append("missing_success_rehearsal_path")
    if rejected <= 0:
        blockers.append("missing_rejection_rehearsal_path")
    blockers.extend([
        "credential_vault_not_implemented",
        "manual_unlock_not_implemented",
        "exchange_execution_disabled",
    ])
    return {
        "total": len(rehearsals),
        "passed": passed,
        "rejected": rejected,
        "latestAt": latest.get("createdAt") or latest.get("generatedAt"),
        "latestState": latest.get("finalState"),
        "latestStrategyId": latest.get("strategyId"),
        "latestSymbol": latest.get("symbol"),
        "localPathsComplete": local_paths_complete,
        "blockers": blockers,
    }


def _strategy_stage(asset: dict[str, Any]) -> str:
    gate = asset.get("gate") if isinstance(asset.get("gate"), dict) else {}
    evidence = asset.get("evidence") if isinstance(asset.get("evidence"), dict) else {}
    if gate.get("canEnterTestnetReadiness"):
        return "testnet_drill_candidate"
    if _safe_int(evidence.get("closedSamples")) >= _safe_int(evidence.get("reviewMinimum"), 30):
        return "local_review_candidate"
    return "observation_only"


def build_testnet_drill() -> dict[str, Any]:
    playbook = build_strategy_asset_playbook()
    strategies = playbook.get("strategies") if isinstance(playbook.get("strategies"), list) else []
    rehearsals = list_pre_live_rehearsals(limit=20)
    rehearsal_summary = _rehearsal_summary(rehearsals)
    staged = []
    for asset in strategies:
        if not isinstance(asset, dict):
            continue
        gate = asset.get("gate") if isinstance(asset.get("gate"), dict) else {}
        evidence = asset.get("evidence") if isinstance(asset.get("evidence"), dict) else {}
        staged.append({
            "taskId": asset.get("taskId"),
            "strategyId": asset.get("strategyId"),
            "plainName": asset.get("plainName"),
            "readableName": asset.get("readableName"),
            "timeframe": asset.get("timeframe"),
            "stage": _strategy_stage(asset),
            "stageLabel": (
                "Testnet 演练候选"
                if gate.get("canEnterTestnetReadiness")
                else "本地复核候选"
                if _safe_int(evidence.get("closedSamples")) >= _safe_int(evidence.get("reviewMinimum"), 30)
                else "继续观察"
            ),
            "closedSamples": evidence.get("closedSamples"),
            "winRate": evidence.get("winRate"),
            "profitFactor": evidence.get("profitFactor"),
            "totalR": evidence.get("totalR"),
            "nextAction": asset.get("nextAction"),
        })
    stage_counts = {
        "observationOnly": sum(1 for row in staged if row["stage"] == "observation_only"),
        "localReviewCandidate": sum(1 for row in staged if row["stage"] == "local_review_candidate"),
        "testnetDrillCandidate": sum(1 for row in staged if row["stage"] == "testnet_drill_candidate"),
    }
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "strategyCount": len(staged),
            "virtualAccountUsdt": VIRTUAL_ACCOUNT_USDT,
            "stageCounts": stage_counts,
            "rehearsalCount": rehearsal_summary["total"],
            "passedRehearsals": rehearsal_summary["passed"],
            "rejectedRehearsals": rehearsal_summary["rejected"],
            "localPathsComplete": rehearsal_summary["localPathsComplete"],
            "executionLocked": True,
            "testnetEnabled": False,
            "orderCreationEnabled": False,
            "blockerCount": len(rehearsal_summary["blockers"]),
            "nextAction": (
                "先保存通过路径和拒绝路径的本地生命周期演练；即使闭环补齐，也必须继续保持交易所执行关闭。"
            ),
        },
        "strategies": staged,
        "orderLifecycle": ORDER_LIFECYCLE_DRILL,
        "riskTemplate": RISK_TEMPLATE,
        "killSwitch": {
            "globalState": "locked",
            "strategyPauseDesigned": True,
            "manualKillSwitchDesigned": True,
            "networkExecutionBlocked": True,
        },
        "rehearsalSummary": rehearsal_summary,
        "recentRehearsals": rehearsals[:8],
        "disabledExecution": DISABLED_EXECUTION,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Testnet Drill is local rehearsal only. It cannot store API keys, connect private endpoints, run exchange dry-run, create orders, or trade automatically.",
    }


if __name__ == "__main__":
    print(json.dumps(build_testnet_drill(), ensure_ascii=False, indent=2))
