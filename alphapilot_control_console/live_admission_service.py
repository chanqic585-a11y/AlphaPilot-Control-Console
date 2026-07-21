"""Ordered, side-effect-free Live admission evaluation."""

from __future__ import annotations

from typing import Any, Mapping

from .adaptive_learning_technical_readiness import AdaptiveLearningTechnicalReadinessGate
from .exact_live_release_approval_gate import ExactLiveReleaseApprovalGate
from .live_arm_gate import LiveArmGate


GATE_SEQUENCE = [
    "AdaptiveLearningTechnicalReadinessGate",
    "ExactLiveReleaseApprovalGate",
    "LiveArmGate",
    "ExecutionRuntimeLease",
]


class LiveAdmissionService:
    """Evaluate admission gates in order without approving, arming, or ordering."""

    def __init__(
        self,
        *,
        technical_gate: Any | None = None,
        approval_gate: Any | None = None,
        arm_gate: Any | None = None,
    ) -> None:
        self.technical_gate = technical_gate or AdaptiveLearningTechnicalReadinessGate()
        self.approval_gate = approval_gate or ExactLiveReleaseApprovalGate()
        self.arm_gate = arm_gate or LiveArmGate()

    def evaluate(
        self,
        *,
        bundle: Mapping[str, Any],
        approval: Mapping[str, Any] | None,
        runtime: Mapping[str, Any],
        execution_lease: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        technical = self.technical_gate.evaluate(
            model_policy=dict(bundle.get("modelPolicy") or {}),
            evidence=dict(bundle.get("technicalEvidence") or {}),
        )
        common = {
            "schemaVersion": "live_admission_service_v1",
            "gateSequence": list(GATE_SEQUENCE),
            "createsOrders": False,
            "armsRuntime": False,
        }
        if technical.get("passed") is not True:
            return {
                **common,
                "status": "draft_blocked_technical_readiness",
                "approvalRequestActionable": False,
                "mechanicalExecutionAllowed": False,
                "technicalReadiness": technical,
                "blockers": list(technical.get("blockers") or []),
            }

        approval_result = self.approval_gate.evaluate(bundle=bundle, approval=approval)
        if approval_result.get("passed") is not True:
            return {
                **common,
                "status": "pending_exact_live_release_approval",
                "approvalRequestActionable": True,
                "mechanicalExecutionAllowed": False,
                "technicalReadiness": technical,
                "exactApproval": approval_result,
                "blockers": list(approval_result.get("blockers") or []),
            }

        arm_result = self.arm_gate.evaluate(
            bundle=bundle,
            approval_gate=approval_result,
            runtime=runtime,
        )
        if arm_result.get("passed") is not True:
            return {
                **common,
                "status": "blocked_live_arm_preconditions",
                "approvalRequestActionable": True,
                "mechanicalExecutionAllowed": False,
                "technicalReadiness": technical,
                "exactApproval": approval_result,
                "liveArm": arm_result,
                "blockers": list(arm_result.get("blockers") or []),
            }

        lease_valid = (
            isinstance(execution_lease, Mapping)
            and execution_lease.get("valid") is True
            and execution_lease.get("environment") == "okx_live"
        )
        return {
            **common,
            "status": "ready_for_live_runtime" if lease_valid else "blocked_execution_runtime_lease",
            "approvalRequestActionable": True,
            "mechanicalExecutionAllowed": lease_valid,
            "technicalReadiness": technical,
            "exactApproval": approval_result,
            "liveArm": arm_result,
            "executionLease": dict(execution_lease or {}),
            "blockers": [] if lease_valid else ["execution_runtime_lease_missing_or_invalid"],
        }
