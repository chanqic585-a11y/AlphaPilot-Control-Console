from __future__ import annotations

import unittest

from alphapilot_control_console.live_admission_service import LiveAdmissionService


class RecordingGate:
    def __init__(self, name: str, passed: bool, calls: list[str]) -> None:
        self.name = name
        self.passed = passed
        self.calls = calls

    def evaluate(self, **_: object) -> dict:
        self.calls.append(self.name)
        return {"passed": self.passed, "blockers": [] if self.passed else [f"{self.name}_blocked"]}


class LiveAdmissionServiceTests(unittest.TestCase):
    def test_technical_failure_is_non_actionable_and_stops_the_sequence(self) -> None:
        calls: list[str] = []
        service = LiveAdmissionService(
            technical_gate=RecordingGate("technical", False, calls),
            approval_gate=RecordingGate("approval", True, calls),
            arm_gate=RecordingGate("arm", True, calls),
        )

        result = service.evaluate(bundle={}, approval=None, runtime={})

        self.assertEqual(calls, ["technical"])
        self.assertEqual(result["status"], "draft_blocked_technical_readiness")
        self.assertFalse(result["approvalRequestActionable"])
        self.assertFalse(result["mechanicalExecutionAllowed"])

    def test_sequence_is_technical_then_approval_then_arm_then_lease(self) -> None:
        calls: list[str] = []
        service = LiveAdmissionService(
            technical_gate=RecordingGate("technical", True, calls),
            approval_gate=RecordingGate("approval", True, calls),
            arm_gate=RecordingGate("arm", True, calls),
        )

        result = service.evaluate(
            bundle={"modelPolicy": {}, "technicalEvidence": {}},
            approval={},
            runtime={},
            execution_lease={"valid": True, "environment": "okx_live"},
        )

        self.assertEqual(calls, ["technical", "approval", "arm"])
        self.assertEqual(result["gateSequence"], [
            "AdaptiveLearningTechnicalReadinessGate",
            "ExactLiveReleaseApprovalGate",
            "LiveArmGate",
            "ExecutionRuntimeLease",
        ])
        self.assertEqual(result["status"], "ready_for_live_runtime")
        self.assertTrue(result["mechanicalExecutionAllowed"])

    def test_missing_lease_never_arms_or_creates_orders(self) -> None:
        calls: list[str] = []
        service = LiveAdmissionService(
            technical_gate=RecordingGate("technical", True, calls),
            approval_gate=RecordingGate("approval", True, calls),
            arm_gate=RecordingGate("arm", True, calls),
        )

        result = service.evaluate(bundle={}, approval={}, runtime={})

        self.assertEqual(result["status"], "blocked_execution_runtime_lease")
        self.assertFalse(result["mechanicalExecutionAllowed"])
        self.assertFalse(result["createsOrders"])
        self.assertFalse(result["armsRuntime"])


if __name__ == "__main__":
    unittest.main()
