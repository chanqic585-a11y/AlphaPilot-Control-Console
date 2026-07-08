from __future__ import annotations

from typing import Any

from .candidate_promotion_gate import build_candidate_promotion_gate_v2
from .config import SAFETY_BOUNDARY
from .exchange_connectors.public_exchange_registry import list_public_exchange_sources
from .simulation_command_center import build_simulation_command_center
from .state_store import now_iso, read_exchange_probe_results


CONTROL_CONSOLE_VERSION = "V13.8.1"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8_1"


REQUIRED_TESTNET_CONTROLS = [
    {
        "controlId": "credential_vault_design",
        "label": "Testnet 凭据隔离设计",
        "required": True,
        "implemented": False,
        "reason": "当前版本不保存 API Key，也不设计密钥输入框。",
    },
    {
        "controlId": "trade_api_adapter_disabled",
        "label": "Trade API 适配器默认关闭",
        "required": True,
        "implemented": True,
        "reason": "当前 SAFETY_BOUNDARY 明确禁止 Trade API 和订单创建。",
    },
    {
        "controlId": "order_lifecycle_simulator",
        "label": "订单生命周期模拟器",
        "required": True,
        "implemented": False,
        "reason": "当前只有本地虚拟观察日志，没有 testnet 订单状态机。",
    },
    {
        "controlId": "kill_switch",
        "label": "一键停止和全局熔断",
        "required": True,
        "implemented": False,
        "reason": "当前只有本地沙盒开关，还不是交易所级 kill switch。",
    },
    {
        "controlId": "max_order_and_loss_limits",
        "label": "最大订单和最大亏损限制",
        "required": True,
        "implemented": False,
        "reason": "当前没有订单额度模型，因为不创建订单。",
    },
    {
        "controlId": "manual_confirmation_gate",
        "label": "人工确认闸门",
        "required": True,
        "implemented": False,
        "reason": "当前只做研究任务确认，不允许发出 testnet order intent。",
    },
    {
        "controlId": "audit_trail",
        "label": "审计日志",
        "required": True,
        "implemented": True,
        "reason": "本地 audit_log.jsonl 已记录研究状态变更。",
    },
    {
        "controlId": "public_data_probe",
        "label": "公共行情连通性检查",
        "required": True,
        "implemented": True,
        "reason": "已有 public exchange probe，仅限 public data。",
    },
]


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def build_testnet_readiness_pack() -> dict[str, Any]:
    command = build_simulation_command_center()
    promotion = build_candidate_promotion_gate_v2()
    public_sources = list_public_exchange_sources()
    probe = read_exchange_probe_results() or {}
    promotion_summary = promotion.get("summary") if isinstance(promotion.get("summary"), dict) else {}
    testnet_candidates = _safe_int(promotion_summary.get("testnetReadinessCandidateCount"))
    missing_controls = [
        item
        for item in REQUIRED_TESTNET_CONTROLS
        if item.get("required") and not item.get("implemented")
    ]
    blockers = [item.get("label") for item in missing_controls]
    if testnet_candidates <= 0:
        blockers.append("没有策略达到 testnet readiness candidate 门槛")
    if not probe:
        blockers.append("尚未完成本地 public exchange probe 复核")
    readiness_stage = "blocked"
    if not blockers:
        readiness_stage = "design_review_only"
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "readinessStage": readiness_stage,
            "readinessStageLabel": "阻塞中" if readiness_stage == "blocked" else "仅可进入设计复核",
            "testnetCandidateCount": testnet_candidates,
            "implementedControlCount": sum(1 for item in REQUIRED_TESTNET_CONTROLS if item.get("implemented")),
            "missingRequiredControlCount": len(missing_controls),
            "blockerCount": len(blockers),
            "publicSourceCount": len(public_sources.get("sources", [])) if isinstance(public_sources, dict) else 0,
            "hasPublicProbe": bool(probe),
            "testnetEnabled": False,
            "dryRunApproved": False,
            "liveTradingApproved": False,
            "nextAction": (
                "先完成 testnet 凭据隔离、订单生命周期模拟、kill switch 和限额模型设计。"
                if blockers
                else "可以写 testnet 设计文档，但仍不能接密钥或下单。"
            ),
        },
        "blockers": blockers,
        "controls": REQUIRED_TESTNET_CONTROLS,
        "strategyGatePreview": promotion.get("rows", [])[:5],
        "commandCenterSummary": command.get("summary") if isinstance(command.get("summary"), dict) else {},
        "publicExchangeSources": public_sources,
        "latestPublicProbe": probe,
        "testnetEnabled": False,
        "apiKeyInputEnabled": False,
        "orderCreationEnabled": False,
        "exchangeDryRunEnabled": False,
        "liveTradingEnabled": False,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Testnet readiness pack is a design checklist only. It does not store credentials or create testnet orders.",
    }
