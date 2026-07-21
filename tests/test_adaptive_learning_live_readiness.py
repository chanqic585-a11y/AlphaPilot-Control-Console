from __future__ import annotations

import unittest
from importlib import import_module

from alphapilot_control_console.adaptive_learning_live_readiness import (
    REQUIRED_EVIDENCE,
    AdaptiveLearningLiveReadinessGate,
)


class AdaptiveLearningLiveReadinessTests(unittest.TestCase):
    def test_technical_readiness_does_not_depend_on_exact_human_approval(self) -> None:
        self.assertNotIn("exactModelReleaseApprovalReady", REQUIRED_EVIDENCE)
        self.assertIn("modelReleaseBindingReady", REQUIRED_EVIDENCE)
        evidence = {key: True for key in REQUIRED_EVIDENCE}
        evidence["exactHumanApproval"] = False

        result = AdaptiveLearningLiveReadinessGate().evaluate(
            model_policy={
                "modelMode": "veto_only",
                "modelHash": "model-hash",
                "modelPolicyHash": "policy-hash",
                "featureSchemaHash": "schema-hash",
                "factorRegistryHash": "registry-hash",
                "lifecycleStatus": "shadow_approved",
            },
            evidence=evidence,
        )

        self.assertTrue(result["passed"])
        self.assertNotIn("exactHumanApproval", result["evidenceStatus"])
        self.assertFalse(result["exactApprovalEvaluated"])

    def test_three_governance_gates_are_independent_and_fail_closed(self) -> None:
        technical_module = import_module(
            "alphapilot_control_console.adaptive_learning_technical_readiness"
        )
        approval_module = import_module(
            "alphapilot_control_console.exact_live_release_approval_gate"
        )
        arm_module = import_module("alphapilot_control_console.live_arm_gate")

        technical = technical_module.AdaptiveLearningTechnicalReadinessGate().evaluate(
            model_policy={"modelMode": "observer"},
            evidence={},
        )
        self.assertFalse(technical["passed"])

        bundle = {
            "adaptiveLearningTechnicalReadiness": technical,
            "liveRelease": {
                "releaseHash": "release-hash",
                "executionBoundary": {
                    "mechanicalExecutionAllowedAfterExactApproval": False,
                },
            },
            "riskOverlay": {
                "riskOverlayHash": "risk-hash",
                "profile": {"maximumAcceptedLossUSDT": 25.0},
            },
            "approvalRequest": {
                "approvalRequestActionable": False,
                "requiredConfirmation": None,
            },
        }
        approval = approval_module.ExactLiveReleaseApprovalGate().evaluate(
            bundle=bundle,
            approval=None,
        )
        self.assertFalse(approval["passed"])
        self.assertIn("adaptive_learning_technical_readiness_not_passed", approval["blockers"])
        self.assertIn("approval_request_not_actionable", approval["blockers"])

        arm = arm_module.LiveArmGate().evaluate(
            bundle=bundle,
            approval_gate=approval,
            runtime={
                "credentialsConfigured": True,
                "privateReadReady": True,
                "reconciliationMatched": True,
                "zeroOpenPositions": True,
                "zeroOpenOrders": True,
            },
        )
        self.assertFalse(arm["passed"])
        self.assertIn("exact_live_release_approval_gate_not_passed", arm["blockers"])

    def test_observer_only_is_never_live_ready(self) -> None:
        gate = AdaptiveLearningLiveReadinessGate()
        result = gate.evaluate(
            model_policy={"modelMode": "observer", "modelPolicyHash": "policy-hash"},
            evidence={},
        )
        self.assertFalse(result["passed"])
        self.assertIn("live_model_mode_not_decision_participating", result["blockers"])

    def test_live_requires_complete_hash_bound_evidence(self) -> None:
        gate = AdaptiveLearningLiveReadinessGate()
        result = gate.evaluate(
            model_policy={
                "modelMode": "veto_only",
                "modelHash": "model-hash",
                "modelPolicyHash": "policy-hash",
                "featureSchemaHash": "schema-hash",
                "factorRegistryHash": "registry-hash",
                "lifecycleStatus": "shadow_approved",
            },
            evidence={
                "factorProductionReady": True,
                "realFactorBenchReady": True,
                "alpha101Ready": True,
                "alpha191CompatibilityReady": True,
                "validatedCryptoFactorSubsetReady": True,
                "boundedFactorMiningReady": True,
                "adaptiveMlTrainingReady": True,
                "qlibOfflineCampaignReady": True,
                "modelRegistryReady": True,
                "continuousLearningDatasetReady": True,
                "demoOutcomeToTrainingSampleReady": True,
                "shadowInferenceReady": True,
                "demoDecisionModeValidated": True,
                "modelDriftMonitoringReady": True,
                "modelRollbackReady": True,
                "onlineInferenceLatencyReady": True,
                "liveFeaturePipelineReady": True,
                "liveModelInferenceReady": True,
                "modelReleaseBindingReady": True,
            },
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["readinessContractVersion"], "v3")

    def test_legacy_evidence_names_are_reported_but_cannot_hide_new_missing_gates(self) -> None:
        gate = AdaptiveLearningLiveReadinessGate()
        result = gate.evaluate(
            model_policy={
                "modelMode": "veto_only",
                "modelHash": "model-hash",
                "modelPolicyHash": "policy-hash",
                "featureSchemaHash": "schema-hash",
                "factorRegistryHash": "registry-hash",
                "lifecycleStatus": "shadow_approved",
            },
            evidence={
                "productionFactorRegistryReady": True,
                "realFactorBenchReady": True,
                "alpha191CompatibilityReady": True,
                "validatedCryptoFactorSubsetReady": True,
                "trainingDatasetReady": True,
                "purgedWalkForwardReady": True,
                "modelValidationReady": True,
                "qlibCampaignReady": True,
                "featurePipelineParityReady": True,
                "driftWithinLimits": True,
                "rollbackReady": True,
                "modelArtifactFresh": True,
                "modelHashVerified": True,
                "releaseHashBindsModelPolicy": True,
                "exactHumanApproval": True,
                "riskOverlayVerified": True,
            },
        )

        self.assertFalse(result["passed"])
        self.assertTrue(result["evidenceStatus"]["factorProductionReady"])
        self.assertTrue(result["evidenceStatus"]["qlibOfflineCampaignReady"])
        self.assertIn(
            "adaptive_evidence_not_ready:boundedFactorMiningReady",
            result["blockers"],
        )
        self.assertIn(
            "adaptive_evidence_not_ready:demoOutcomeToTrainingSampleReady",
            result["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
