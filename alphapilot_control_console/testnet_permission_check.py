from __future__ import annotations

import json
from typing import Any

from .config import SAFETY_BOUNDARY
from .exchange_connectors.public_exchange_registry import list_public_exchange_sources
from .pre_live_preparation_pack import REFERENCE_INPUTS
from .state_store import now_iso, read_exchange_probe_results
from .testnet_audit import build_testnet_audit_pack


CONTROL_CONSOLE_VERSION = "V13.9.0"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_9_0"


PERMISSION_CHECKS = [
    {
        "checkId": "public_probe_available",
        "label": "公共行情探测",
        "required": True,
        "description": "至少有一次 public market probe 作为只读连通性证据。",
    },
    {
        "checkId": "credential_vault_absent",
        "label": "凭据保险箱未启用",
        "required": True,
        "description": "当前没有密钥输入或保险箱，因此不能连接私有 testnet。",
    },
    {
        "checkId": "withdraw_forbidden",
        "label": "Withdraw 权限禁止",
        "required": True,
        "description": "未来任何 testnet 凭据都必须禁止提现权限。",
    },
    {
        "checkId": "trade_api_disabled",
        "label": "Trade API 保持关闭",
        "required": True,
        "description": "当前版本不启用交易 API 适配器。",
    },
    {
        "checkId": "manual_unlock_missing",
        "label": "人工解锁未完成",
        "required": True,
        "description": "未来连接 testnet 前必须有人工解锁和二次确认。",
    },
    {
        "checkId": "small_order_path_local_only",
        "label": "小额订单路径仅本地模拟",
        "required": True,
        "description": "V13.9.1 只允许本地模拟小额 testnet 订单票据。",
    },
]


def _check_status(check_id: str, has_public_probe: bool) -> tuple[bool, str]:
    if check_id == "public_probe_available":
        return has_public_probe, "已有 public probe" if has_public_probe else "尚未完成 public probe"
    if check_id == "credential_vault_absent":
        return True, "未启用凭据输入，私有连接保持关闭"
    if check_id == "withdraw_forbidden":
        return True, "提现权限在设计上禁止"
    if check_id == "trade_api_disabled":
        return SAFETY_BOUNDARY.get("tradeApiAllowed") is False, "Trade API 当前关闭"
    if check_id == "manual_unlock_missing":
        return False, "人工解锁尚未实现，所以不能连接私有 testnet"
    if check_id == "small_order_path_local_only":
        return True, "只允许本地模拟票据，不发真实网络订单"
    return False, "未知检查项"


def build_testnet_permission_check() -> dict[str, Any]:
    probe = read_exchange_probe_results() or {}
    sources = list_public_exchange_sources()
    audit = build_testnet_audit_pack()
    has_public_probe = bool(probe)
    checks = []
    for item in PERMISSION_CHECKS:
        passed, detail = _check_status(str(item["checkId"]), has_public_probe)
        checks.append({
            **item,
            "passed": passed,
            "status": "passed" if passed else "blocked",
            "detail": detail,
        })
    hard_blockers = [
        item["label"]
        for item in checks
        if item["required"] and not item["passed"]
    ]
    testnet_private_blockers = [
        "credential_vault_not_implemented",
        "manual_unlock_not_implemented",
        "trade_api_disabled_by_boundary",
        "order_creation_disabled_by_boundary",
    ]
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "stage": "read_only_permission_check",
            "stageLabel": "只读权限检查",
            "canRunPublicProbe": True,
            "canConnectPrivateTestnet": False,
            "canInputApiKey": False,
            "canStoreApiKey": False,
            "canCreateTestnetOrder": False,
            "canRunSmallOrderSimulation": True,
            "publicProbeReady": has_public_probe,
            "publicSourceCount": len(sources.get("sources", [])) if isinstance(sources, dict) else 0,
            "passedCheckCount": sum(1 for item in checks if item["passed"]),
            "blockedCheckCount": len(hard_blockers),
            "nextAction": (
                "可以继续做 V13.9.1 本地小额 Testnet 模拟票据；仍不能输入 API Key 或连接私有接口。"
            ),
        },
        "checks": checks,
        "hardBlockers": hard_blockers,
        "testnetPrivateBlockers": testnet_private_blockers,
        "latestPublicProbe": probe,
        "publicSources": sources.get("sources", []) if isinstance(sources, dict) else [],
        "referenceInputs": REFERENCE_INPUTS,
        "auditSummary": audit.get("summary", {}),
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Permission check is read-only. It does not accept API keys, connect private testnet endpoints, create orders, or trade automatically.",
    }


if __name__ == "__main__":
    print(json.dumps(build_testnet_permission_check(), ensure_ascii=False, indent=2))
