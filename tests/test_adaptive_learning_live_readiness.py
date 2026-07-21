from __future__ import annotations

import unittest

from alphapilot_control_console.adaptive_learning_live_readiness import (
    AdaptiveLearningLiveReadinessGate,
)


class AdaptiveLearningLiveReadinessTests(unittest.TestCase):
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
        self.assertTrue(result["passed"])
        self.assertEqual(result["blockers"], [])


if __name__ == "__main__":
    unittest.main()
