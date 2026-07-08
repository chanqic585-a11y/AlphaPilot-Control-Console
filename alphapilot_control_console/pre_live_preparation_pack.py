from __future__ import annotations

from typing import Any

from .config import SAFETY_BOUNDARY
from .state_store import list_pre_live_rehearsals, now_iso, save_pre_live_rehearsal
from .testnet_design_boundary import build_testnet_design_boundary


CONTROL_CONSOLE_VERSION = "V13.8.3"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8_3"


REFERENCE_INPUTS = [
    {
        "sourceId": "alpha101_reference",
        "label": "alpha101 factor research workflow",
        "storedUse": "factor inspiration only",
        "usableIdea": "把候选策略拆成可解释因子、分桶、稳定性和样本覆盖检查。",
        "boundary": "不复制源码，不把股票因子直接当作币圈实盘信号。",
    },
    {
        "sourceId": "crypto_agent_pro_reference",
        "label": "CryptoAgentPro.beta execution architecture reference",
        "storedUse": "execution safety reference only",
        "usableIdea": "记录 API key 配置、order endpoint、testnet、紧急平仓和自动执行能力的风险点，用于反向设计权限隔离。",
        "boundary": "当前版本不接这些能力，只把它们作为未来权限隔离和审计设计参考。",
    },
    {
        "sourceId": "trading_agents_reference",
        "label": "TradingAgents multi-agent review reference",
        "storedUse": "review workflow reference only",
        "usableIdea": "把策略升级前的研究、风控、执行、复盘拆成不同角色的检查清单。",
        "boundary": "不接真实 AI 自动决策，不让 agent 直接创建订单。",
    },
    {
        "sourceId": "quantdigger_reference",
        "label": "QuantDigger event-driven backtest reference",
        "storedUse": "event lifecycle reference only",
        "usableIdea": "用事件状态机思维描述 signal -> risk check -> manual ticket -> simulated fill -> audit closeout。",
        "boundary": "本地演练不连接交易所，不生成真实订单事件。",
    },
]


ORDER_LIFECYCLE_STAGES = [
    {
        "stageId": "research_candidate_selected",
        "label": "选择研究候选",
        "status": "implemented_local_preview",
        "description": "从已通过复核的策略候选中选择一个观察对象，只读取本地研究数据。",
        "auditRequired": True,
    },
    {
        "stageId": "local_order_intent_draft",
        "label": "本地意图草稿",
        "status": "implemented_local_preview",
        "description": "生成本地演练意图字段，不是订单，不包含交易所字段。",
        "auditRequired": True,
    },
    {
        "stageId": "pre_trade_risk_check",
        "label": "预交易风控检查",
        "status": "implemented_local_preview",
        "description": "检查单笔名义金额、每日亏损、连续失败、重复意图、冷却时间和熔断状态。",
        "auditRequired": True,
    },
    {
        "stageId": "manual_confirmation_ticket",
        "label": "人工确认票据",
        "status": "implemented_local_preview",
        "description": "任何未来 testnet 或实盘动作都必须先变成人工确认票据。",
        "auditRequired": True,
    },
    {
        "stageId": "simulated_submit",
        "label": "本地模拟提交",
        "status": "implemented_local_preview",
        "description": "只在本地返回 submitted preview，不发送网络请求。",
        "auditRequired": True,
    },
    {
        "stageId": "simulated_accept_or_reject",
        "label": "本地接受或拒绝",
        "status": "implemented_local_preview",
        "description": "用风险检查结果模拟 accepted / rejected，不调用交易所。",
        "auditRequired": True,
    },
    {
        "stageId": "simulated_fill_or_cancel",
        "label": "本地成交或取消",
        "status": "implemented_local_preview",
        "description": "只生成演练状态路径，不写真实 fill，不改变持仓。",
        "auditRequired": True,
    },
    {
        "stageId": "audit_closeout",
        "label": "审计收尾",
        "status": "implemented_local_preview",
        "description": "复核所有拒绝原因、人工确认、模拟结果和安全边界。",
        "auditRequired": True,
    },
]


RISK_LIMITS = [
    {
        "limitId": "per_account_virtual_capital",
        "label": "单账户模拟本金",
        "value": "1000 USDT",
        "severity": "required",
        "description": "延续本地沙盒约束，避免用过大的虚拟本金误导判断。",
    },
    {
        "limitId": "max_order_risk",
        "label": "单次风险上限",
        "value": "1R / 1%",
        "severity": "required",
        "description": "任何演练意图都不能超过本地定义的单次风险单位。",
    },
    {
        "limitId": "fixed_reward_risk",
        "label": "目标盈亏比",
        "value": "2R target",
        "severity": "required",
        "description": "候选策略继续以 2R 目标作为核心复核约束。",
    },
    {
        "limitId": "daily_loss_limit",
        "label": "单日虚拟亏损熔断",
        "value": "-2R",
        "severity": "required",
        "description": "本地演练路径中如果达到日内亏损阈值，后续意图必须被拒绝。",
    },
    {
        "limitId": "max_open_intents",
        "label": "最大未结意图数",
        "value": "1 per strategy",
        "severity": "required",
        "description": "每条策略同一时间只允许一个本地演练意图，避免重复触发。",
    },
    {
        "limitId": "cooldown_after_reject",
        "label": "拒绝后冷却",
        "value": "30 minutes",
        "severity": "required",
        "description": "风险拒绝后必须进入冷却，不允许连续提交演练意图。",
    },
]


KILL_SWITCH_CONTROLS = [
    {
        "controlId": "global_execution_lock",
        "label": "全局执行锁",
        "state": "locked",
        "description": "Trade API、Withdraw API、订单创建和 exchange Dry-run 全部关闭。",
    },
    {
        "controlId": "strategy_level_pause",
        "label": "策略级暂停",
        "state": "designed",
        "description": "任一策略出现连续失效、样本污染或风控争议时应能暂停。",
    },
    {
        "controlId": "manual_kill_switch",
        "label": "人工熔断按钮",
        "state": "designed_not_connected",
        "description": "未来可以在控制台设置全局暂停；当前只展示设计，不连接交易所。",
    },
    {
        "controlId": "network_authority_block",
        "label": "网络交易权限阻断",
        "state": "locked",
        "description": "本地预演接口不能访问私有交易端点。",
    },
]


CREDENTIAL_VAULT_DESIGN = [
    {
        "itemId": "no_raw_secret_storage",
        "label": "禁止保存 raw secret",
        "status": "required_future",
        "description": "未来如果接 testnet，密钥必须加密、脱敏展示、禁止日志输出。",
    },
    {
        "itemId": "withdraw_permission_forbidden",
        "label": "禁止 Withdraw 权限",
        "status": "required_future",
        "description": "任何交易所凭据都必须明确拒绝提现权限。",
    },
    {
        "itemId": "testnet_scope_first",
        "label": "Testnet 范围优先",
        "status": "required_future",
        "description": "真实交易前必须先完成 testnet 只读探测、testnet 小额演练和人工确认。",
    },
    {
        "itemId": "manual_unlock",
        "label": "人工解锁",
        "status": "required_future",
        "description": "凭据启用必须由用户显式操作，不能由策略、AI 或后台任务自动启用。",
    },
]


DISABLED_PRE_LIVE_ACTIONS = [
    {
        "actionId": "enter_api_key",
        "label": "输入交易所 API Key",
        "enabled": False,
        "reason": "V13.8.3 不提供密钥输入，也不保存 raw API Key。",
    },
    {
        "actionId": "connect_private_exchange",
        "label": "连接交易所私有接口",
        "enabled": False,
        "reason": "当前只允许 public data 和本地研究状态，不访问账户或持仓。",
    },
    {
        "actionId": "submit_exchange_order",
        "label": "提交交易所订单",
        "enabled": False,
        "reason": "本版本只有生命周期演练，不创建真实或 testnet 订单。",
    },
    {
        "actionId": "cancel_exchange_order",
        "label": "撤销交易所订单",
        "enabled": False,
        "reason": "没有订单连接，因此也没有撤单能力。",
    },
    {
        "actionId": "emergency_close_position",
        "label": "紧急平仓",
        "enabled": False,
        "reason": "紧急平仓属于真实交易权限，当前仅记录未来设计约束。",
    },
    {
        "actionId": "auto_execute_strategy",
        "label": "策略自动执行",
        "enabled": False,
        "reason": "AI、策略、沙盒和控制台都不能自动发出交易动作。",
    },
]


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _build_rehearsal_summary(rehearsals: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rehearsals)
    passed = sum(1 for row in rehearsals if row.get("riskPassed") is True)
    rejected = sum(1 for row in rehearsals if row.get("riskPassed") is not True)
    latest = rehearsals[0] if rehearsals else {}
    has_success_path = passed > 0
    has_rejection_path = rejected > 0
    closure_blockers = []
    if total == 0:
        closure_blockers.append("no_local_rehearsal_saved")
    if not has_success_path:
        closure_blockers.append("success_path_not_saved")
    if not has_rejection_path:
        closure_blockers.append("rejection_path_not_saved")
    closure_blockers.extend([
        "credential_vault_not_implemented",
        "exchange_execution_disabled",
    ])
    local_paths_complete = has_success_path and has_rejection_path
    return {
        "totalRehearsals": total,
        "passedRehearsals": passed,
        "rejectedRehearsals": rejected,
        "latestRehearsalAt": latest.get("createdAt") or latest.get("generatedAt"),
        "latestFinalState": latest.get("finalState"),
        "latestStrategyId": latest.get("strategyId"),
        "latestSymbol": latest.get("symbol"),
        "hasSuccessfulRehearsal": has_success_path,
        "hasRejectedRehearsal": has_rejection_path,
        "localLifecyclePathsComplete": local_paths_complete,
        "blockerCount": len(closure_blockers),
        "blockers": closure_blockers,
        "upgradeVerdict": (
            "local_rehearsal_paths_complete_execution_still_disabled"
            if local_paths_complete
            else "needs_local_rehearsal_samples_execution_disabled"
        ),
    }


def _build_pre_live_closure_report(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "checkId": "local_rehearsal_saved",
            "label": "本地演练记录",
            "status": "passed" if summary["totalRehearsals"] > 0 else "blocked",
            "description": "至少保存一条本地生命周期演练记录，用于之后复盘。",
        },
        {
            "checkId": "success_path_saved",
            "label": "通过路径记录",
            "status": "passed" if summary["hasSuccessfulRehearsal"] else "blocked",
            "description": "需要有一条风险通过、人工确认通过的本地演练记录。",
        },
        {
            "checkId": "rejection_path_saved",
            "label": "拒绝路径记录",
            "status": "passed" if summary["hasRejectedRehearsal"] else "blocked",
            "description": "需要有一条因风险或人工拒绝而被拦截的本地演练记录。",
        },
        {
            "checkId": "manual_confirmation_required",
            "label": "人工确认",
            "status": "passed",
            "description": "任何未来 testnet 或实盘动作都必须先经过人工确认。",
        },
        {
            "checkId": "credential_vault",
            "label": "凭据保险箱",
            "status": "future_required",
            "description": "当前未实现密钥保险箱，因此不能输入或保存交易所 API Key。",
        },
        {
            "checkId": "exchange_execution",
            "label": "交易执行权限",
            "status": "disabled",
            "description": "当前没有 Trade API、Withdraw API、真实账户、持仓或订单能力。",
        },
    ]


def _build_operational_runbook(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "stepId": "run_local_sandbox",
            "label": "运行本地沙盒",
            "description": "继续让候选策略生成虚拟观察样本和闭合样本。",
            "status": "available_local_only",
        },
        {
            "stepId": "save_pre_live_rehearsal",
            "label": "保存本地生命周期演练",
            "description": "在控制台保存通过路径和拒绝路径，形成可复盘证据。",
            "status": "complete" if summary["localLifecyclePathsComplete"] else "needs_more_rehearsal",
        },
        {
            "stepId": "review_closure_report",
            "label": "复核闭环报告",
            "description": "检查本地演练、人工确认、凭据边界和执行权限是否符合预期。",
            "status": "available_local_only",
        },
        {
            "stepId": "future_testnet_design_review",
            "label": "未来 Testnet 设计评审",
            "description": "只有在单独版本完成密钥隔离、权限开关和人工确认后，才能考虑 testnet。",
            "status": "future_required",
        },
    ]


def build_pre_live_preparation_pack() -> dict[str, Any]:
    boundary = build_testnet_design_boundary()
    boundary_summary = boundary.get("summary") if isinstance(boundary.get("summary"), dict) else {}
    missing_controls = boundary.get("missingControls") if isinstance(boundary.get("missingControls"), list) else []
    rehearsals = list_pre_live_rehearsals(limit=20)
    rehearsal_summary = _build_rehearsal_summary(rehearsals)
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "stage": "local_pre_live_rehearsal",
            "stageLabel": "实盘前本地演练",
            "orderLifecycleSimulatorReady": True,
            "riskLimitModelReady": True,
            "killSwitchDesigned": True,
            "credentialVaultImplemented": False,
            "manualConfirmationRequired": True,
            "apiKeyInputEnabled": False,
            "privateExchangeConnectionEnabled": False,
            "orderCreationEnabled": False,
            "exchangeDryRunEnabled": False,
            "autoTradingEnabled": False,
            "testnetCandidateCount": boundary_summary.get("testnetCandidateCount", 0),
            "missingTestnetControlCount": len(missing_controls),
            "localRehearsalCount": rehearsal_summary["totalRehearsals"],
            "localRehearsalPathsComplete": rehearsal_summary["localLifecyclePathsComplete"],
            "preLiveUpgradeVerdict": rehearsal_summary["upgradeVerdict"],
            "nextAction": "保存通过路径和拒绝路径的本地演练记录；即使本地闭环完成，交易执行仍保持禁用。",
        },
        "rehearsalSummary": rehearsal_summary,
        "preLiveClosureReport": _build_pre_live_closure_report(rehearsal_summary),
        "operationalRunbook": _build_operational_runbook(rehearsal_summary),
        "recentRehearsals": rehearsals[:10],
        "referenceInputs": REFERENCE_INPUTS,
        "orderLifecycleStages": ORDER_LIFECYCLE_STAGES,
        "riskLimits": RISK_LIMITS,
        "killSwitchControls": KILL_SWITCH_CONTROLS,
        "credentialVaultDesign": CREDENTIAL_VAULT_DESIGN,
        "disabledActions": DISABLED_PRE_LIVE_ACTIONS,
        "testnetDesignBoundarySummary": boundary_summary,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Pre-live preparation is a local rehearsal pack only. It cannot store credentials, connect private endpoints, run exchange Dry-run, or create orders.",
    }


def simulate_pre_live_order_lifecycle(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    notional = _safe_float(payload.get("notional"), 100.0)
    risk_r = _safe_float(payload.get("riskR"), 1.0)
    manual_decision = str(payload.get("manualDecision") or "approve_for_rehearsal").strip()
    risk_notes: list[str] = []

    if notional <= 0:
        risk_notes.append("notional_must_be_positive")
    if notional > 1000:
        risk_notes.append("notional_exceeds_virtual_account_capital")
    if risk_r <= 0:
        risk_notes.append("risk_r_must_be_positive")
    if risk_r > 1:
        risk_notes.append("risk_exceeds_one_r")
    if manual_decision not in {"approve_for_rehearsal", "reject"}:
        risk_notes.append("manual_decision_unknown")

    passed = not risk_notes and manual_decision == "approve_for_rehearsal"
    final_state = "simulated_rejected" if not passed else "simulated_fill_preview"
    path = []
    for stage in ORDER_LIFECYCLE_STAGES:
        state = "passed" if passed else "checked"
        if stage["stageId"] in {"simulated_accept_or_reject", "simulated_fill_or_cancel"}:
            state = "simulated" if passed else "rejected"
        path.append({
            "stageId": stage["stageId"],
            "label": stage["label"],
            "state": state,
            "note": stage["description"],
        })

    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "previewId": f"pre_live_preview::{now_iso()}",
        "strategyId": str(payload.get("strategyId") or "manual_rehearsal_strategy"),
        "symbol": str(payload.get("symbol") or "BTC/USDT:USDT"),
        "notional": notional,
        "riskR": risk_r,
        "manualDecision": manual_decision,
        "riskPassed": passed,
        "riskNotes": risk_notes or [
            "local rehearsal only",
            "manual confirmation required",
            "no exchange request",
            "no order created",
        ],
        "finalState": final_state,
        "lifecyclePath": path,
        "createdExchangeOrder": False,
        "connectedExchange": False,
        "storedApiKey": False,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "This is a local lifecycle preview. It does not persist an order and does not contact any exchange.",
    }


def create_pre_live_rehearsal(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    preview = simulate_pre_live_order_lifecycle(payload)
    created_at = now_iso()
    rehearsal = save_pre_live_rehearsal({
        **preview,
        "previewId": preview.get("previewId"),
        "rehearsalId": f"pre_live_rehearsal::{created_at}",
        "createdAt": created_at,
        "persistedAsRehearsal": True,
        "safetyNote": (
            "This local rehearsal was saved for audit. It is not an order, "
            "does not store credentials, and does not contact any exchange."
        ),
    })
    pack = build_pre_live_preparation_pack()
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "rehearsal": rehearsal,
        "rehearsalSummary": pack.get("rehearsalSummary", {}),
        "preLivePreparationPack": pack,
        "createdExchangeOrder": False,
        "connectedExchange": False,
        "storedApiKey": False,
        "safetyBoundary": SAFETY_BOUNDARY,
    }
