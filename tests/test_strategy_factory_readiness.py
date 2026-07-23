from __future__ import annotations

import unittest

from alphapilot_control_console.strategy_factory_readiness import (
    build_forward_task,
    build_matchability_funnel,
    project_factor_model_readiness,
)


class StrategyFactoryReadinessTests(unittest.TestCase):
    def test_matchability_funnel_preserves_every_requested_stage(self) -> None:
        result = build_matchability_funnel(
            {
                "requestedUniverse": 200,
                "publicUniverse": 198,
                "exchangeTradable": 190,
                "eligibleUniverse": 170,
                "componentCompatible": 140,
                "lookbackReady": 130,
                "dataReady": 120,
                "evaluated": 120,
                "rawSignals": 9,
                "identityPassed": 8,
                "cooldownRejected": 1,
                "riskRejected": 2,
                "orderEligible": 5,
                "orders": 0,
                "fills": 0,
                "closedTrades": 0,
            }
        )

        self.assertEqual(result["status"], "complete_zero_order")
        self.assertEqual(result["requestedUniverse"], 200)
        self.assertEqual(result["orderEligible"], 5)
        self.assertEqual(result["orders"], 0)
        self.assertFalse(result["executionAuthorized"])

    def test_matchability_rejects_impossible_stage_counts(self) -> None:
        with self.assertRaisesRegex(ValueError, "matchability_stage_count_invalid"):
            build_matchability_funnel(
                {
                    "requestedUniverse": 25,
                    "publicUniverse": 30,
                }
            )

    def test_forward_task_uses_review_hints_not_promotion_gates(self) -> None:
        task = build_forward_task(
            task_id="forward-1",
            release_id="release-1",
            release_hash="sha256:release",
            started_at="2026-07-23T00:00:00Z",
            status="running",
            closed_trade_count=31,
            effective_sample_size=28.5,
            symbol_coverage=0.4,
            regime_coverage=0.5,
            cost_completeness=1.0,
        )

        self.assertEqual(task["reviewHint"], "preliminary_review_available")
        self.assertFalse(task["automaticPromotionAllowed"])
        self.assertEqual(task["nextReviewHintAt"], 50)

    def test_factor_model_readiness_never_promotes_not_run_work(self) -> None:
        readiness = project_factor_model_readiness(
            {
                "factorRegistry": "completed",
                "realFactorBench": "not_run",
                "trainingDataset": "not_run",
                "purgedWalkForward": "not_run",
                "qlibCampaign": "not_run",
                "modelValidation": "not_run",
                "driftMonitor": "not_run",
                "rollback": "not_run",
                "demoDecisionMode": "observer_only",
            }
        )

        self.assertEqual(readiness["status"], "not_ready")
        self.assertEqual(readiness["effectiveDecisionMode"], "rule_only")
        self.assertIn("realFactorBench", readiness["missing"])
        self.assertFalse(readiness["liveEligible"])


if __name__ == "__main__":
    unittest.main()
