from __future__ import annotations

import unittest

from alphapilot_control_console.adaptive_learning_feature_parity import (
    build_feature_pipeline_parity_evidence,
)


class AdaptiveLearningFeatureParityTests(unittest.TestCase):
    def test_same_input_has_same_feature_hash_across_demo_and_live(self) -> None:
        factor_registry = {
            "factorRegistryHash": "factor-registry-hash",
            "factors": [
                {
                    "factorId": "rsi14",
                    "definitionHash": "definition-hash",
                    "implementationHash": "implementation-hash",
                    "pointInTimeReady": True,
                }
            ],
        }
        feature_schema = {
            "factorRegistryHash": "factor-registry-hash",
            "featureSchemaHash": "feature-schema-hash",
        }
        model_policy = {
            "factorRegistryHash": "factor-registry-hash",
            "featureSchemaHash": "feature-schema-hash",
            "modelHash": "observer-model-hash",
            "modelPolicyHash": "observer-policy-hash",
            "modelMode": "observer",
        }

        result = build_feature_pipeline_parity_evidence(
            factor_registry=factor_registry,
            feature_schema=feature_schema,
            model_policy=model_policy,
        )

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["passed"])
        self.assertTrue(result["featureVectorHashEqual"])
        self.assertTrue(result["sharedCoreImplementation"])
        self.assertFalse(result["grantsLiveAuthority"])
        self.assertFalse(result["createsOrders"])


if __name__ == "__main__":
    unittest.main()
