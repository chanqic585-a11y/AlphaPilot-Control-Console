from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path

from alphapilot_control_console.adaptive_learning_readiness_snapshot import (
    REQUIRED_CAPABILITIES,
    build_adaptive_learning_readiness_snapshot,
)
from scripts.build_v59_readiness_snapshot import collect_artifact_evidence


def _observer_policy() -> dict:
    return {
        "modelMode": "observer",
        "modelHash": "observer-model",
        "modelPolicyHash": "observer-policy",
        "featureSchemaHash": "feature-schema",
        "factorRegistryHash": "factor-registry",
        "lifecycleStatus": "shadow_approved",
    }


class AdaptiveLearningReadinessSnapshotTests(unittest.TestCase):
    def test_collector_preserves_not_run_and_missing_artifact_truth(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "model_validation_report.json").write_text(
                json.dumps({"status": "not_run", "passed": None}),
                encoding="utf-8",
            )

            result = collect_artifact_evidence(root)

            self.assertEqual(result["adaptiveMlTrainingReady"]["status"], "not_run")
            self.assertEqual(
                result["adaptiveMlTrainingReady"]["evidenceRef"],
                "model_validation_report.json",
            )
            self.assertEqual(result["alpha101Ready"]["status"], "not_run")
            self.assertEqual(result["alpha101Ready"]["reason"], "artifact_missing")

    def test_snapshot_reports_every_required_capability_without_promoting_not_run(self) -> None:
        result = build_adaptive_learning_readiness_snapshot(
            generated_at="2026-07-21T12:00:00Z",
            model_policy=_observer_policy(),
            factor_registry={
                "factorRegistryHash": "factor-registry",
                "pointInTimeOnly": True,
                "factors": [{"factorId": "return_1"}],
                "alpha191Compatibility": {
                    "allFactorsProductionValidated": False,
                },
            },
            registry_audit={
                "formalFactorRunCount": 10,
                "liveEligibleModelCount": 0,
                "formalDataSnapshotCount": 162,
                "auditHash": "registry-audit",
            },
            offline_evidence={
                "offlineEvidenceHash": "offline-evidence",
                "eligibleFactorCount": 0,
                "evidence": {
                    "realFactorBenchReady": True,
                    "validatedCryptoFactorSubsetReady": False,
                    "qlibCampaignReady": False,
                },
            },
            artifact_evidence={
                "boundedFactorMiningReady": {
                    "status": "not_run",
                    "passed": None,
                    "evidenceRef": "factor_mining_trial_ledger.parquet",
                },
                "shadowInferenceReady": {
                    "status": "not_run",
                    "passed": None,
                    "evidenceRef": "demo_shadow_decision_ledger.parquet",
                },
            },
        )

        rows = {row["capability"]: row for row in result["capabilities"]}
        self.assertEqual(set(rows), set(REQUIRED_CAPABILITIES))
        self.assertEqual(rows["factorProductionReady"]["status"], "ready")
        self.assertEqual(rows["realFactorBenchReady"]["status"], "ready")
        self.assertEqual(rows["boundedFactorMiningReady"]["status"], "not_run")
        self.assertEqual(rows["shadowInferenceReady"]["status"], "not_run")
        self.assertEqual(rows["modelRegistryReady"]["status"], "blocked")
        self.assertFalse(result["passed"])
        self.assertEqual(result["readyCount"], 2)
        self.assertEqual(result["totalCount"], len(REQUIRED_CAPABILITIES))
        self.assertIn("live_model_mode_not_decision_participating", result["blockers"])
        self.assertFalse(result["grantsLiveAuthority"])

    def test_explicit_completed_technical_evidence_does_not_wait_for_exact_approval(self) -> None:
        artifact_evidence = {
            capability: {
                "status": "completed",
                "passed": True,
                "evidenceRef": f"{capability}.json",
            }
            for capability in REQUIRED_CAPABILITIES
        }
        result = build_adaptive_learning_readiness_snapshot(
            generated_at="2026-07-21T12:00:00Z",
            model_policy={
                **_observer_policy(),
                "modelMode": "veto_only",
                "modelHash": "validated-model",
            },
            factor_registry={
                "factorRegistryHash": "factor-registry",
                "pointInTimeOnly": True,
                "factors": [{"factorId": "return_1"}],
                "alpha191Compatibility": {
                    "allFactorsProductionValidated": True,
                },
            },
            registry_audit={
                "formalFactorRunCount": 10,
                "liveEligibleModelCount": 1,
                "formalDataSnapshotCount": 162,
                "auditHash": "registry-audit",
            },
            offline_evidence={
                "offlineEvidenceHash": "offline-evidence",
                "eligibleFactorCount": 3,
                "evidence": {
                    "realFactorBenchReady": True,
                    "validatedCryptoFactorSubsetReady": True,
                    "qlibCampaignReady": True,
                },
            },
            artifact_evidence=artifact_evidence,
        )

        rows = {row["capability"]: row for row in result["capabilities"]}
        self.assertNotIn("exactModelReleaseApprovalReady", rows)
        self.assertIn("modelReleaseBindingReady", rows)
        self.assertTrue(result["passed"])
        self.assertEqual(result["readyCount"], len(REQUIRED_CAPABILITIES))

    def test_alpha191_formula_compatibility_does_not_require_all_191_predictive_factors(self) -> None:
        result = build_adaptive_learning_readiness_snapshot(
            generated_at="2026-07-21T12:00:00Z",
            model_policy=_observer_policy(),
            factor_registry={
                "factorRegistryHash": "factor-registry",
                "pointInTimeOnly": True,
                "factors": [{"factorId": "alpha191_014"}],
                "alpha191Compatibility": {
                    "catalogCount": 191,
                    "formulaReviewedCount": 8,
                    "numericCrossvalidatedCount": 8,
                    "productionValidatedCount": 0,
                    "allFactorsProductionValidated": False,
                },
            },
            registry_audit={
                "formalFactorRunCount": 10,
                "liveEligibleModelCount": 0,
                "formalDataSnapshotCount": 162,
                "auditHash": "registry-audit",
            },
            offline_evidence={
                "offlineEvidenceHash": "offline-evidence",
                "eligibleFactorCount": 0,
                "evidence": {
                    "realFactorBenchReady": True,
                    "validatedCryptoFactorSubsetReady": False,
                    "qlibCampaignReady": False,
                },
            },
            artifact_evidence={
                "alpha191CompatibilityReady": {
                    "status": "passed",
                    "passed": True,
                    "evidenceRef": "alpha191_compatibility_audit.json",
                }
            },
        )

        rows = {row["capability"]: row for row in result["capabilities"]}
        self.assertEqual(rows["alpha191CompatibilityReady"]["status"], "ready")
        self.assertTrue(rows["alpha191CompatibilityReady"]["ready"])
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
