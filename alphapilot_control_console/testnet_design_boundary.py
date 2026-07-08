from __future__ import annotations

from typing import Any

from .config import SAFETY_BOUNDARY
from .state_store import now_iso
from .testnet_readiness_pack import REQUIRED_TESTNET_CONTROLS


CONTROL_CONSOLE_VERSION = "V13.8.2"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8_2"


FUTURE_TESTNET_SEQUENCE = [
    {
        "stepId": "design_only",
        "label": "设计冻结",
        "status": "available_now",
        "description": "只确认权限边界、订单生命周期、人工确认和审计字段，不连接交易所。",
    },
    {
        "stepId": "credential_vault_spec",
        "label": "凭据保险箱规格",
        "status": "blocked",
        "description": "未来若接 testnet，密钥必须本地加密、权限隔离、禁止 withdraw 权限。",
    },
    {
        "stepId": "order_lifecycle_simulator",
        "label": "订单生命周期模拟",
        "status": "blocked",
        "description": "先在本地模拟 pending / accepted / filled / rejected / cancelled 状态机。",
    },
    {
        "stepId": "kill_switch_and_limits",
        "label": "熔断和限额模型",
        "status": "blocked",
        "description": "先设计全局停止、单笔限额、单日亏损限额和连续失败暂停。",
    },
    {
        "stepId": "manual_confirmation_gate",
        "label": "人工确认闸门",
        "status": "blocked",
        "description": "任何 testnet 意图都必须先变成人工确认票据，不能自动发出。",
    },
    {
        "stepId": "testnet_probe_readonly",
        "label": "Testnet 只读探测",
        "status": "future_only",
        "description": "只能在以上控制完成后考虑。V13.8.1 不实现。",
    },
]


DISABLED_ACTIONS = [
    {
        "actionId": "api_key_input",
        "label": "输入 Testnet API Key",
        "enabled": False,
        "reason": "V13.8.1 不提供 API Key 输入框，也不保存 raw API Key。",
    },
    {
        "actionId": "connect_testnet",
        "label": "连接交易所 Testnet",
        "enabled": False,
        "reason": "凭据隔离、订单模拟、熔断和人工确认尚未完成。",
    },
    {
        "actionId": "create_testnet_order",
        "label": "创建 Testnet 订单",
        "enabled": False,
        "reason": "当前版本禁止订单创建，Testnet readiness pack 只是清单。",
    },
    {
        "actionId": "exchange_dry_run",
        "label": "启动 Exchange Dry-run",
        "enabled": False,
        "reason": "当前只允许本地沙盒模拟，不运行交易所 dry-run。",
    },
]


def build_testnet_design_boundary() -> dict[str, Any]:
    required_controls = [
        item for item in REQUIRED_TESTNET_CONTROLS if isinstance(item, dict) and item.get("required")
    ]
    missing_controls = [item for item in required_controls if not item.get("implemented")]
    implemented_controls = [item for item in required_controls if item.get("implemented")]
    blockers = [item.get("label") for item in missing_controls]
    blockers.append("没有策略达到 testnet readiness candidate 门槛")

    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "stage": "design_locked",
            "stageLabel": "仅设计准备，交易关闭",
            "testnetEnabled": False,
            "apiKeyInputEnabled": False,
            "orderCreationEnabled": False,
            "exchangeDryRunEnabled": False,
            "implementedControlCount": len(implemented_controls),
            "missingRequiredControlCount": len(missing_controls),
            "testnetCandidateCount": 0,
            "blockerCount": len(blockers),
            "nextAction": "先补齐凭据隔离、订单生命周期模拟、熔断限额和人工确认设计，再讨论 testnet。",
        },
        "readinessPack": {
            "version": CONTROL_CONSOLE_VERSION,
            "source": CONTROL_CONSOLE_SOURCE,
            "summary": {
                "readinessStage": "blocked",
                "readinessStageLabel": "阻塞中",
                "testnetEnabled": False,
                "apiKeyInputEnabled": False,
                "orderCreationEnabled": False,
                "exchangeDryRunEnabled": False,
            },
            "blockers": blockers,
            "controls": REQUIRED_TESTNET_CONTROLS,
        },
        "requiredControls": required_controls,
        "missingControls": missing_controls,
        "disabledActions": DISABLED_ACTIONS,
        "futureSequence": FUTURE_TESTNET_SEQUENCE,
        "uiCopy": {
            "title": "Testnet 准备中心（未启用）",
            "subtitle": "这里只做未来接入前的设计检查。当前不输入密钥、不连接交易所、不创建订单。",
            "warning": "所有 Testnet 操作在 V13.8.1 都是灰显状态；控制台仍只做本地研究和沙盒观察。",
        },
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Testnet design boundary is read-only. It cannot store API keys, connect Trade API, run exchange Dry-run, or create orders.",
    }
