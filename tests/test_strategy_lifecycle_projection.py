from __future__ import annotations

import unittest

from alphapilot_control_console.strategy_lifecycle_projection import build_strategy_lifecycle_projection


def empty_sources() -> dict:
    return {
        "catalog": {"strategies": [], "summary": {}},
        "simulation_review": {"queue": [], "summary": {}},
        "promotion_gate": {"buckets": {}, "summary": {}},
        "evolution_demo": {"contracts": [], "summary": {}},
        "live_candidates": {"packages": [], "summary": {}},
        "artifact_index": {"artifacts": [], "summary": {}},
        "promotion_decisions": [],
        "strategy_stage_assignments": {},
    }


class StrategyLifecycleProjectionTests(unittest.TestCase):
    def build(self, **overrides: object) -> dict:
        payloads = empty_sources()
        payloads.update(overrides)
        return build_strategy_lifecycle_projection(**payloads)

    def test_legacy_sample_gate_does_not_promote(self) -> None:
        result = self.build(
            catalog={
                "strategies": [
                    {
                        "strategyId": "strategy-1",
                        "taskId": "task-1",
                        "name": "趋势回撤策略",
                        "timeframe": "1h",
                        "frequencyLabel": "短周期",
                    }
                ],
                "summary": {},
            },
            simulation_review={
                "queue": [
                    {
                        "strategyId": "strategy-1",
                        "taskId": "task-1",
                        "strategyName": "趋势回撤策略",
                        "status": "promoted_candidate",
                        "sampleGate": {"closedSamples": 30, "isReviewReady": True},
                        "metrics": {"closedSamples": 30, "profitFactor": 1.3},
                    }
                ],
                "summary": {"promotedCandidates": 1},
            },
            promotion_gate={
                "buckets": {
                    "survivors": [
                        {
                            "strategyId": "strategy-1",
                            "itemId": "strategy-1",
                            "title": "趋势回撤策略",
                            "bucket": "survivor",
                        }
                    ]
                },
                "summary": {"survivorCount": 1},
            },
        )

        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["currentStage"], "local_simulation_running")
        self.assertEqual(result["summary"]["localSimulationRunningCount"], 1)
        self.assertEqual(result["summary"]["localSimulationPassedCount"], 0)
        self.assertIn("30", result["items"][0]["evidenceSummary"])

    def test_survivor_without_sandbox_is_research_candidate(self) -> None:
        result = self.build(
            promotion_gate={
                "buckets": {
                    "survivors": [
                        {
                            "strategyId": "candidate-1",
                            "itemId": "candidate-1",
                            "title": "候选策略一号",
                            "bucket": "survivor",
                            "reasons": ["历史证据达到观察条件。"],
                        }
                    ]
                },
                "summary": {"survivorCount": 1},
            }
        )

        self.assertEqual(result["summary"]["strategyCandidateCount"], 1)
        self.assertEqual(result["items"][0]["currentStage"], "research_candidate")

    def test_formal_demo_release_moves_strategy_to_demo(self) -> None:
        result = self.build(
            catalog={
                "strategies": [{"strategyId": "strategy-1", "name": "趋势策略"}],
                "summary": {},
            },
            evolution_demo={
                "contracts": [
                    {
                        "demoReleaseId": "release-1",
                        "strategyCandidateId": "strategy-1",
                        "status": "demo_eligible",
                        "contractHash": "contract-hash",
                    }
                ],
                "summary": {"eligibleReleaseCount": 1},
            },
        )

        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["currentStage"], "demo_validation_running")
        self.assertEqual(result["summary"]["localSimulationRunningCount"], 0)
        self.assertEqual(result["summary"]["demoValidationRunningCount"], 1)

    def test_demo_trial_assignment_moves_strategy_out_of_local_page(self) -> None:
        result = self.build(
            catalog={
                "strategies": [
                    {"strategyId": "strategy-1", "name": "趋势策略"},
                    {"strategyId": "strategy-2", "name": "反转策略"},
                ],
                "summary": {},
            },
            strategy_stage_assignments={
                "strategy-1": {
                    "strategyId": "strategy-1",
                    "stage": "demo_trial",
                    "stageLabel": "Demo 观察",
                    "sampleDataPreserved": True,
                },
                "strategy-2": {
                    "strategyId": "strategy-2",
                    "stage": "demo_trial",
                    "stageLabel": "Demo 观察",
                    "sampleDataPreserved": True,
                },
            },
        )

        self.assertEqual(result["summary"]["localSimulationRunningCount"], 0)
        self.assertEqual(result["summary"]["demoTrialCount"], 2)
        self.assertEqual({item["currentStage"] for item in result["items"]}, {"demo_trial"})
        self.assertTrue(all(item["page"] == "demo" for item in result["items"]))
        self.assertTrue(all("历史样本保留" in item["evidenceSummary"] for item in result["items"]))

    def test_local_and_demo_items_include_parameter_optimization_context(self) -> None:
        result = self.build(
            catalog={
                "strategies": [
                    {
                        "strategyId": "strategy-1",
                        "name": "空头上影拒绝",
                        "family": "short_rejection",
                        "direction": "short",
                        "timeframe": "1h",
                        "targetR": 2.0,
                        "params": {
                            "volume_min": 1.2,
                            "max_hold": 12,
                            "targetRMultiple": 2.0,
                        },
                        "metrics": {"profitFactor": 1.05},
                        "validationMetrics": {"profitFactor": 0.9},
                    }
                ],
                "summary": {},
            },
            strategy_stage_assignments={
                "strategy-1": {"strategyId": "strategy-1", "stage": "demo_trial"},
            },
        )

        item = result["items"][0]
        self.assertIn("optimizationContext", item)
        context = item["optimizationContext"]
        self.assertEqual(context["sourceKind"], "legacy_catalog")
        self.assertEqual(context["legacyStrategyId"], "strategy-1")
        self.assertEqual(context["parameters"]["volume_min"], 1.2)
        self.assertEqual(context["definition"]["targetR"], 2.0)
        self.assertEqual(context["validationMetrics"]["profitFactor"], 0.9)

    def test_legacy_target_is_preserved_without_two_r_clamp(self) -> None:
        result = self.build(
            catalog={
                "strategies": [
                    {
                        "strategyId": "strategy-1",
                        "name": "Versioned exit target",
                        "targetR": 1.5,
                        "params": {},
                    }
                ],
                "summary": {},
            },
        )

        context = result["items"][0]["optimizationContext"]
        self.assertEqual(context["definition"]["targetR"], 1.5)
        self.assertEqual(context["parameters"]["targetRewardRiskRatio"], 1.5)

    def test_missing_legacy_target_is_not_synthesized_as_two_r(self) -> None:
        result = self.build(
            catalog={
                "strategies": [{"strategyId": "strategy-1", "name": "No fixed target"}],
                "summary": {},
            },
        )

        context = result["items"][0]["optimizationContext"]
        self.assertIsNone(context["definition"]["targetR"])
        self.assertNotIn("targetRewardRiskRatio", context["parameters"])

    def test_formal_demo_release_supersedes_demo_trial_assignment(self) -> None:
        result = self.build(
            catalog={
                "strategies": [{"strategyId": "strategy-1", "name": "趋势策略"}],
                "summary": {},
            },
            strategy_stage_assignments={
                "strategy-1": {"strategyId": "strategy-1", "stage": "demo_trial"},
            },
            evolution_demo={
                "contracts": [
                    {
                        "demoReleaseId": "release-1",
                        "strategyCandidateId": "strategy-1",
                        "status": "demo_eligible",
                    }
                ],
                "summary": {"eligibleReleaseCount": 1},
            },
        )

        self.assertEqual(result["summary"]["demoTrialCount"], 0)
        self.assertEqual(result["summary"]["demoValidationRunningCount"], 1)
        self.assertEqual(result["items"][0]["currentStage"], "demo_validation_running")

    def test_formal_local_promotion_decision_moves_strategy_to_passed_stage(self) -> None:
        result = self.build(
            catalog={
                "strategies": [{"strategyId": "strategy-1", "name": "趋势策略"}],
                "summary": {},
            },
            promotion_decisions=[
                {
                    "decisionId": "decision-1",
                    "strategyId": "strategy-1",
                    "decision": "local_simulation_passed",
                    "createdAt": "2026-07-10T00:00:00Z",
                }
            ],
        )

        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["currentStage"], "local_simulation_passed")
        self.assertEqual(result["summary"]["localSimulationRunningCount"], 0)
        self.assertEqual(result["summary"]["localSimulationPassedCount"], 1)

    def test_terminal_archive_decision_hides_strategy_from_active_items(self) -> None:
        result = self.build(
            catalog={
                "strategies": [{"strategyId": "strategy-1", "name": "趋势策略"}],
                "summary": {},
            },
            promotion_decisions=[
                {
                    "decisionId": "decision-archive-1",
                    "strategyId": "strategy-1",
                    "decision": "archived",
                    "createdAt": "2026-07-10T00:00:00Z",
                }
            ],
        )

        self.assertEqual(result["items"], [])
        self.assertEqual(len(result["archivedItems"]), 1)
        self.assertEqual(result["archivedItems"][0]["currentStage"], "archived")
        self.assertEqual(result["summary"]["archivedCount"], 1)

    def test_live_package_is_single_current_stage_and_missing_demo_requires_reconciliation(self) -> None:
        result = self.build(
            catalog={
                "strategies": [{"strategyId": "strategy-1", "name": "趋势策略"}],
                "summary": {},
            },
            live_candidates={
                "packages": [
                    {
                        "liveCandidatePackageId": "package-1",
                        "demoReleaseId": "release-1",
                        "packageHash": "package-hash",
                        "package": {
                            "strategyCandidateId": "strategy-1",
                            "manualApprovalRequired": True,
                        },
                    }
                ],
                "summary": {"packageCount": 1},
            },
        )

        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["currentStage"], "live_candidate")
        self.assertEqual(result["items"][0]["consistencyStatus"], "reconciliation_required")
        self.assertEqual(result["summary"]["liveCandidateCount"], 1)
        self.assertEqual(result["summary"]["reconciliationRequiredCount"], 1)

    def test_same_name_with_different_ids_remains_separate(self) -> None:
        result = self.build(
            catalog={
                "strategies": [
                    {"strategyId": "strategy-a", "name": "同名策略", "timeframe": "1h"},
                    {"strategyId": "strategy-b", "name": "同名策略", "timeframe": "4h"},
                ],
                "summary": {},
            }
        )

        self.assertEqual(len(result["items"]), 2)
        self.assertEqual({item["strategyId"] for item in result["items"]}, {"strategy-a", "strategy-b"})
        self.assertEqual(len({item["lifecycleId"] for item in result["items"]}), 2)

    def test_artifacts_are_archived_without_creating_strategy_cards(self) -> None:
        result = self.build(
            artifact_index={
                "artifacts": [
                    {"artifactId": "report-1", "sourceKind": "benchmark_report"},
                    {"artifactId": "report-2", "sourceKind": "factor_report"},
                ],
                "summary": {"totalArtifacts": 2},
            }
        )

        self.assertEqual(result["items"], [])
        self.assertEqual(result["summary"]["archivedCount"], 2)
        self.assertEqual(result["archiveSummary"]["researchArtifactCount"], 2)

    def test_local_forward_stage_exposes_visible_sample_progress(self) -> None:
        result = self.build(
            catalog={
                "strategies": [
                    {
                        "strategyId": "strategy-1",
                        "name": "Forward Strategy",
                        "metrics": {"closedSamples": 12},
                    }
                ],
                "summary": {},
            },
            strategy_stage_assignments={
                "strategy-1": {"strategyId": "strategy-1", "stage": "local_sandbox"}
            },
        )

        progress = result["items"][0]["progress"]
        self.assertEqual(progress["phase"], "local_forward_sampling")
        self.assertEqual(progress["completed"], 12)
        self.assertEqual(progress["required"], 30)
        self.assertEqual(progress["percent"], 40)
        self.assertIn("12/30", progress["label"])
        self.assertIn("复核起点", progress["note"])


if __name__ == "__main__":
    unittest.main()
