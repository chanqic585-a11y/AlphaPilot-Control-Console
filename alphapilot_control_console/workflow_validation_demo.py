"""Deterministic engineering-only execution workflow validation fixture."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def run_workflow_validation_demo_fixture() -> dict[str, Any]:
    stages = (
        ("discover", "发现冻结候选"),
        ("authorize", "校验 Release、风险和运行授权"),
        ("submit", "生成确定性幂等请求"),
        ("inspect", "检查模拟响应和未知状态"),
        ("exit", "执行模拟退出生命周期"),
        ("reconcile", "核对订单、持仓和账本"),
        ("report", "生成工程验证摘要"),
    )
    return {
        "fixtureVersion": "workflow-validation-demo.v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "ok": True,
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
