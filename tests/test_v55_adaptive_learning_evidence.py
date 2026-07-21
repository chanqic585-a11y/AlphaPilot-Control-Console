from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from alphapilot_control_console.adaptive_learning_contracts import stable_hash
from alphapilot_control_console.v55_adaptive_learning_evidence import (
    generate_v55_adaptive_learning_evidence,
    package_v55_adaptive_learning_evidence,
)


def factor_registry() -> dict:
    factor = {
        "factorId": "return_1",
        "name": "One-bar return",
        "theme": "momentum",
        "formula": "safe_div(close-delay(close,1),delay(close,1))",
        "canonicalFormula": "safe_div(close-delay(close,1),delay(close,1))",
        "requiredFields": ["close"],
        "pointInTimeReady": True,
        "sourceArtifactId": "fixture",
        "availableAtRule": "confirmed_bar_close",
        "normalizationPolicy": "as_computed",
        "missingValuePolicy": "record_missing_flag",
        "implementationHash": "factor_implementation_fixture",
        "definitionHash": "factor_definition_fixture",
        "sourceClass": "crypto_native",
    }
    core = {
        "schemaVersion": "production_factor_registry_v1",
        "boundedMaximum": 36,
        "factors": [factor],
        "pointInTimeOnly": True,
        "predictiveValueClaimed": False,
        "alpha191Compatibility": {
            "catalogCount": 191,
            "formulaReviewedCount": 0,
            "numericCrossvalidatedCount": 0,
            "productionValidatedCount": 0,
            "validationScope": "not_run",
            "allFactorsProductionValidated": False,
        },
    }
    return {**core, "factorRegistryHash": stable_hash(core, prefix="production_factor_registry")}


class V55AdaptiveLearningEvidenceTests(unittest.TestCase):
    def test_generates_truthful_pre_arm_evidence_and_observer_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "evidence"
            result = generate_v55_adaptive_learning_evidence(
                root,
                generated_at="2026-07-21T00:00:00Z",
                factor_registry=factor_registry(),
                release_identity={
                    "releaseId": "release-fixture",
                    "releaseHash": "release-hash-fixture",
                    "riskOverlayHash": "risk-hash-fixture",
                    "demoArm": False,
                },
                insertion_receipt={
                    "originalV55Commit": "commit-fixture",
                    "safeCheckpointPassed": True,
                    "strategyOrderCount": 0,
                    "nonzeroPositionCount": 0,
                },
            )

            self.assertEqual(result["status"], "complete_pre_arm_observer")
            required = {
                "adaptive_learning_insertion_receipt.json",
                "adaptive_learning_architecture_contract.json",
                "production_factor_registry.json",
                "production_feature_schema.json",
                "model_registry.json",
                "observer_sidecar_binding.json",
                "adaptive_learning_live_readiness.json",
                "artifact_manifest.json",
                "final_closeout_cn.md",
            }
            self.assertTrue(required.issubset({path.name for path in root.iterdir()}))

            binding = json.loads((root / "observer_sidecar_binding.json").read_text(encoding="utf-8"))
            self.assertEqual(binding["releaseHash"], "release-hash-fixture")
            self.assertFalse(binding["altersOrderSemantics"])
            self.assertFalse(binding["createsOrders"])

            model_registry = json.loads((root / "model_registry.json").read_text(encoding="utf-8"))
            self.assertEqual(model_registry["activeDemoModelPolicy"]["modelMode"], "observer")
            self.assertIsNone(model_registry["activeLiveModelPolicy"])

            readiness = json.loads((root / "adaptive_learning_live_readiness.json").read_text(encoding="utf-8"))
            self.assertFalse(readiness["passed"])
            self.assertIn("live_model_mode_not_decision_participating", readiness["blockers"])

            for name in (
                "factor_stability_report.json",
                "training_dataset_manifest.json",
                "qlib_campaign_manifest.json",
                "model_validation_report.json",
                "model_drift_report.json",
                "model_rollback_audit.json",
                "online_inference_latency_audit.json",
                "live_feature_pipeline_parity.json",
                "live_model_inference_audit.json",
            ):
                payload = json.loads((root / name).read_text(encoding="utf-8"))
                self.assertEqual(payload["status"], "not_run", name)

            archive = Path(directory) / "evidence.zip"
            receipt = package_v55_adaptive_learning_evidence(root, archive)
            self.assertTrue(archive.is_file())
            self.assertEqual(len(receipt["sha256"]), 64)
            with zipfile.ZipFile(archive) as bundle:
                self.assertIn("artifact_manifest.json", bundle.namelist())
                self.assertIn("final_closeout_cn.md", bundle.namelist())


if __name__ == "__main__":
    unittest.main()
