"""Deterministic engineering-only execution workflow validation fixture."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def run_workflow_validation_demo_fixture() -> dict[str, Any]:
    stages = (
        ("import", "导入诊断 Release"),
        ("approval", "校验精确 Release 与风险 Hash"),
        ("arm", "验证独立 ARM 门"),
        ("signal", "生成隔离诊断信号"),
        ("order", "生成确定性幂等订单请求"),
        ("position", "验证模拟持仓状态"),
        ("exit", "执行模拟退出生命周期"),
        ("reconciliation", "核对订单、持仓和账本"),
        ("ui", "验证操作台状态投影"),
    )
    return {
        "fixtureVersion": "workflow-validation-demo.v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "ok": True,
        "releaseClassification": "diagnostic_only",
        "strategyQualification": False,
        "formalPass": False,
        "livePromotionEligible": False,
        "timeline": [
            {"sequence": index, "stage": stage, "labelZh": label, "status": "passed"}
            for index, (stage, label) in enumerate(stages, start=1)
        ],
        "evidence": {
            "engineeringOnly": True,
            "formalEvidenceEligible": False,
            "strategyPerformanceEligible": False,
            "promotionEvidenceEligible": False,
        },
        "safetyBoundary": {
            "exchangeNetworkUsed": False,
            "liveOrderCreated": False,
            "credentialsRequired": False,
            "credentialsPersisted": False,
            "withdrawAllowed": False,
            "immutableReleaseBypassed": False,
        },
    }
