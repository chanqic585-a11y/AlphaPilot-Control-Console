from __future__ import annotations

import unittest

from alphapilot_control_console.strategy_factory_lifecycle import (
    build_failure_attributions,
    project_strategy_factory_lifecycle,
)


class StrategyFactoryLifecycleTests(unittest.TestCase):
    def test_zero_trial_completion_is_blocked(self) -> None:
        result = project_strategy_factory_lifecycle(
            legacy_status="completed",
            config={"candidateIds": ["candidate-a"], "familyIds": ["family-a"]},
            receipt={"status": "research_zero_qualified"},
            execution_evidence={
                "development": {"status": "completed", "trialCount": 0},
                "formal": {"formalRunCount": 0, "resultReadCount": 0},
            },
            outcome={"formalValidationCandidateCount": 0, "candidateReviewRequestCount": 0},
        )

        self.assertEqual(result["state"], "blocked")
        self.assertEqual(result["completedTrialCount"], 0)
        self.assertIn("completed_trial_count_zero", result["blockers"])
        self.assertFalse(result["developmentComplete"])

    def test_real_trials_can_finish_development_with_zero_survivors(self) -> None:
        result = project_strategy_factory_lifecycle(
            legacy_status="completed",
            config={"candidateIds": ["candidate-a"], "familyIds": ["family-a"]},
            receipt={"status": "research_zero_qualified"},
            execution_evidence={
                "development": {"status": "completed", "trialCount": 4},
                "formal": {"formalRunCount": 0, "resultReadCount": 0},
            },
            outcome={"formalValidationCandidateCount": 0, "candidateReviewRequestCount": 0},
        )

        self.assertEqual(result["state"], "development_complete")
        self.assertTrue(result["developmentComplete"])
        self.assertEqual(result["completedTrialCount"], 4)
        self.assertEqual(result["survivorCount"], 0)

    def test_formal_chain_requires_job_claim_attempt_result_and_read(self) -> None:
        base = {
            "development": {"status": "completed", "trialCount": 3},
            "formal": {
                "formalJobCount": 1,
                "formalClaimCount": 1,
                "formalAttemptCount": 1,
                "formalResultCount": 1,
                "resultReadCount": 0,
            },
        }
        queued = project_strategy_factory_lifecycle(
            legacy_status="awaiting_formal_validation",
            config={"candidateIds": ["candidate-a"], "familyIds": ["family-a"]},
            receipt={"status": "awaiting_formal_validation"},
            execution_evidence=base,
            outcome={"formalValidationCandidateCount": 1, "candidateReviewRequestCount": 0},
        )
        self.assertEqual(queued["state"], "formal_running")
        self.assertFalse(queued["formalComplete"])
        self.assertEqual(queued["formalMissing"], ["Formal Read"])

        complete_evidence = {
            **base,
            "formal": {**base["formal"], "resultReadCount": 1},
        }
        complete = project_strategy_factory_lifecycle(
            legacy_status="completed",
            config={"candidateIds": ["candidate-a"], "familyIds": ["family-a"]},
            receipt={"status": "immutable_release_ready", "releaseCount": 1},
            execution_evidence=complete_evidence,
            outcome={"formalValidationCandidateCount": 1, "candidateReviewRequestCount": 1},
        )
        self.assertEqual(complete["state"], "demo_release_draft")
        self.assertTrue(complete["formalComplete"])
        self.assertEqual(complete["formalMissing"], [])

    def test_failure_attribution_uses_seven_layer_taxonomy(self) -> None:
        result = build_failure_attributions(
            config={
                "candidateIds": ["candidate-a"],
                "familyIds": ["family-a"],
                "timeframe": "15m",
            },
            receipt={
                "status": "research_blocked_data",
                "reasonCodes": ["missing_partition"],
                "instrument": "BTC-USDT-SWAP",
                "requiredRows": 1000,
                "availableRows": 600,
            },
            execution_evidence={"development": {"trialCount": 1}},
            outcome={"archivedFailureCount": 1},
        )

        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertEqual(item["failureLayer"], "Data / PIT")
        self.assertEqual(item["reasonCodes"], ["missing_partition"])
        self.assertEqual(item["requiredRows"], 1000)
        self.assertEqual(item["availableRows"], 600)
        self.assertEqual(item["nextSingleVariableExperiment"]["maximumChangedVariables"], 1)
        self.assertIn("lower_gate_after_result", item["prohibitedRepair"])
        self.assertTrue(item["familyFingerprint"].startswith("family_fingerprint_"))


if __name__ == "__main__":
    unittest.main()
