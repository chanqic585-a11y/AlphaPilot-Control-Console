from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from alphapilot_control_console.strategy_factory_orchestrator import (
    StrategyFactoryOrchestrator,
)


FIXED_NOW = datetime(2026, 7, 22, 1, 30, tzinfo=UTC)


class StrategyFactoryOutcomeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.quant_root = self.root / "quant"
        registry = self.quant_root / "research/source_registry/strategy_research_source_registry.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            json.dumps(
                {
                    "schemaVersion": "fixture-v1",
                    "registryId": "fixture-registry",
                    "families": [
                        {
                            "familyId": "family-a",
                            "variants": [
                                {"candidateId": "candidate-a"},
                                {"candidateId": "candidate-b"},
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.orchestrator = StrategyFactoryOrchestrator(
            state_path=self.root / "factory.sqlite",
            artifact_root=self.root / "runs",
            quant_root=self.quant_root,
            source_registry_path=registry,
            python_executable=self.root / "python.exe",
            launcher=lambda **_kwargs: {"pid": 4242, "started": True},
            clock=lambda: FIXED_NOW,
        )

    def tearDown(self) -> None:
        self.orchestrator.close()
        self.temp.cleanup()

    def _create_run(self) -> dict:
        return self.orchestrator.create_run(
            {
                "operation": "generate",
                "timeframe": "15m",
                "mode": "quick",
                "maxCandidateCount": 2,
                "maxTrialBudget": 8,
            }
        )

    def test_survivor_creates_review_request_without_approval_arm_or_order(self) -> None:
        run = self._create_run()
        campaign_root = Path(run["artifactPath"]) / run["campaignId"]
        campaign_root.mkdir(parents=True)
        summary_path = campaign_root / "campaign_summary.json"
        summary_path.write_text("{}\n", encoding="utf-8")
        (campaign_root / "immutable_releases.json").write_text(
            json.dumps(
                {
                    "schemaVersion": "v36_immutable_release_set_v1",
                    "campaignId": run["campaignId"],
                    "releaseCount": 1,
                    "approved": False,
                    "demoArm": False,
                    "orders": 0,
                    "releases": [
                        {
                            "campaignId": run["campaignId"],
                            "candidateId": "candidate-a",
                            "trialId": "candidate-a-trial-1",
                            "outcome": "formal_pass",
                            "immutableReleaseHash": "immutable-release-a",
                            "approved": False,
                            "demoArm": False,
                            "orders": 0,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        result = self.orchestrator.record_receipt(
            run["runId"],
            {
                "status": "immutable_release_ready",
                "campaignId": run["campaignId"],
                "releaseCount": 1,
                "eligibleCandidateCount": 1,
                "artifactPath": str(summary_path),
                "receiptHash": "receipt-survivor",
                "approvalCount": 0,
                "demoArm": False,
                "orderCount": 0,
            },
        )

        self.assertEqual(result["resultClass"], "can_enter_demo")
        self.assertEqual(result["candidateReviewRequestCount"], 1)
        self.assertEqual(result["archivedFailureCount"], 1)
        self.assertEqual(result["approvalCount"], 0)
        self.assertFalse(result["demoArm"])
        self.assertEqual(result["orderCount"], 0)
        request_bundle = json.loads(
            Path(result["candidateReviewRequestPath"]).read_text(encoding="utf-8")
        )
        request = request_bundle["requests"][0]
        self.assertEqual(request["immutableReleaseHash"], "immutable-release-a")
        self.assertEqual(request["status"], "pending_human_review")
        self.assertTrue(request["approvalRequestActionable"])
        self.assertFalse(request["automaticApprovalAllowed"])
        self.assertFalse(request["demoReleaseCreated"])
        self.assertFalse(request["demoArm"])
        self.assertEqual(request["orderCount"], 0)
        event_count = self.orchestrator.connection.execute(
            "SELECT COUNT(*) FROM StrategyFactoryEvents WHERE runId = ? AND eventType = 'candidate_review_required'",
            (run["runId"],),
        ).fetchone()[0]
        self.assertEqual(event_count, 1)

        pending = self.orchestrator.list_candidate_review_requests()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["candidateId"], "candidate-a")
        self.assertEqual(pending[0]["runId"], run["runId"])
        self.assertFalse(pending[0]["automaticApprovalAllowed"])
        self.assertFalse(pending[0]["demoArm"])
        self.assertEqual(pending[0]["orderCount"], 0)

    def test_zero_survivor_archives_all_candidates_without_review_request(self) -> None:
        run = self._create_run()

        result = self.orchestrator.record_receipt(
            run["runId"],
            {
                "status": "research_zero_qualified",
                "campaignId": run["campaignId"],
                "releaseCount": 0,
                "eligibleCandidateCount": 0,
                "receiptHash": "receipt-zero",
                "approvalCount": 0,
                "demoArm": False,
                "orderCount": 0,
            },
        )

        self.assertEqual(result["resultClass"], "failed")
        self.assertEqual(result["candidateReviewRequestCount"], 0)
        self.assertEqual(result["archivedFailureCount"], 2)
        archive = json.loads(
            Path(result["failureArchivePath"]).read_text(encoding="utf-8")
        )
        self.assertEqual(
            {item["candidateId"] for item in archive["archivedCandidates"]},
            {"candidate-a", "candidate-b"},
        )
        self.assertTrue(all(item["reason"] == "research_zero_qualified" for item in archive["archivedCandidates"]))
        self.assertEqual(result["approvalCount"], 0)
        self.assertFalse(result["demoArm"])
        self.assertEqual(result["orderCount"], 0)
        self.assertEqual(self.orchestrator.list_candidate_review_requests(), [])

    def test_development_stable_candidate_waits_for_formal_instead_of_being_archived(self) -> None:
        run = self._create_run()
        campaign_root = Path(run["artifactPath"]) / run["campaignId"]
        campaign_root.mkdir(parents=True)
        summary_path = campaign_root / "campaign_summary.json"
        summary_path.write_text(
            json.dumps(
                {
                    "campaignId": run["campaignId"],
                    "status": "awaiting_formal_validation",
                    "stableSelectionCount": 1,
                    "formalRunCount": 0,
                    "releaseCount": 0,
                }
            ),
            encoding="utf-8",
        )
        (campaign_root / "neighborhood_selection.json").write_text(
            json.dumps(
                {
                    "campaignId": run["campaignId"],
                    "eligibleSelectionCount": 1,
                    "selections": [
                        {
                            "candidateId": "candidate-a",
                            "eligible": True,
                            "selectedTrialId": "trial-a",
                            "reason": "stable_parameter_neighborhood",
                        },
                        {
                            "candidateId": "candidate-b",
                            "eligible": False,
                            "selectedTrialId": None,
                            "reason": "unstable_parameter_neighborhood",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        (campaign_root / "formal_handoff.json").write_text(
            json.dumps(
                {
                    "campaignId": run["campaignId"],
                    "status": "ready_to_freeze",
                    "handoffHash": "formal-handoff-ready",
                    "formalReadyCandidateCount": 1,
                    "blockedCandidateCount": 0,
                    "readyCandidates": [
                        {
                            "candidateId": "candidate-a",
                            "selectedTrialId": "trial-a",
                            "readinessStatus": "ready",
                            "blockers": [],
                        }
                    ],
                    "blockedCandidates": [],
                    "formalRunCount": 0,
                    "formalInputReadCount": 0,
                    "resultReadCount": 0,
                    "lockedOosAccessCount": 0,
                    "releaseCount": 0,
                    "approvalCount": 0,
                    "demoArm": False,
                    "orderCount": 0,
                }
            ),
            encoding="utf-8",
        )

        result = self.orchestrator.record_receipt(
            run["runId"],
            {
                "status": "awaiting_formal_validation",
                "campaignId": run["campaignId"],
                "releaseCount": 0,
                "eligibleCandidateCount": 2,
                "artifactPath": str(summary_path),
                "receiptHash": "receipt-formal-pending",
                "approvalCount": 0,
                "demoArm": False,
                "orderCount": 0,
            },
        )

        self.assertEqual(result["resultClass"], "needs_forward_validation")
        self.assertEqual(result["status"], "awaiting_formal_validation")
        self.assertEqual(result["stage"], "formal_handoff")
        self.assertLess(result["progressPercent"], 100)
        self.assertIsNone(result["completedAt"])
        self.assertEqual(result["survivorCount"], 1)
        self.assertEqual(result["formalValidationCandidateCount"], 1)
        self.assertEqual(result["formalReadyCandidateCount"], 1)
        self.assertEqual(result["formalBlockedCandidateCount"], 0)
        self.assertEqual(result["formalHandoffStatus"], "ready_to_freeze")
        self.assertEqual(result["archivedFailureCount"], 1)
        inventory = json.loads(
            Path(result["candidateInventoryPath"]).read_text(encoding="utf-8")
        )
        self.assertEqual(
            inventory["formalValidationCandidates"][0]["candidateId"],
            "candidate-a",
        )
        self.assertEqual(
            inventory["formalValidationCandidates"][0]["status"],
            "ready_to_freeze",
        )
        self.assertEqual(
            inventory["archivedCandidates"][0]["candidateId"],
            "candidate-b",
        )
        self.assertEqual(result["candidateReviewRequestCount"], 0)

    def test_formal_data_blocker_remains_visible_and_is_not_archived(self) -> None:
        run = self._create_run()
        campaign_root = Path(run["artifactPath"]) / run["campaignId"]
        campaign_root.mkdir(parents=True)
        summary_path = campaign_root / "campaign_summary.json"
        summary_path.write_text("{}\n", encoding="utf-8")
        (campaign_root / "neighborhood_selection.json").write_text(
            json.dumps(
                {
                    "campaignId": run["campaignId"],
                    "eligibleSelectionCount": 1,
                    "selections": [
                        {
                            "candidateId": "candidate-a",
                            "eligible": True,
                            "selectedTrialId": "trial-a",
                        },
                        {
                            "candidateId": "candidate-b",
                            "eligible": False,
                            "selectedTrialId": None,
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        (campaign_root / "formal_handoff.json").write_text(
            json.dumps(
                {
                    "campaignId": run["campaignId"],
                    "status": "blocked_before_freeze",
                    "handoffHash": "formal-handoff-blocked",
                    "formalReadyCandidateCount": 0,
                    "blockedCandidateCount": 1,
                    "readyCandidates": [],
                    "blockedCandidates": [
                        {
                            "candidateId": "candidate-a",
                            "selectedTrialId": "trial-a",
                            "readinessStatus": "blocked",
                            "blockers": [
                                "purged_walk_forward_capacity_insufficient"
                            ],
                        }
                    ],
                    "formalRunCount": 0,
                    "formalInputReadCount": 0,
                    "resultReadCount": 0,
                    "lockedOosAccessCount": 0,
                    "releaseCount": 0,
                    "approvalCount": 0,
                    "demoArm": False,
                    "orderCount": 0,
                }
            ),
            encoding="utf-8",
        )

        result = self.orchestrator.record_receipt(
            run["runId"],
            {
                "status": "awaiting_formal_validation",
                "campaignId": run["campaignId"],
                "releaseCount": 0,
                "artifactPath": str(summary_path),
                "receiptHash": "receipt-formal-blocked",
                "approvalCount": 0,
                "demoArm": False,
                "orderCount": 0,
            },
        )

        self.assertEqual(result["resultClass"], "data_insufficient")
        self.assertEqual(result["formalReadyCandidateCount"], 0)
        self.assertEqual(result["formalBlockedCandidateCount"], 1)
        inventory = json.loads(
            Path(result["candidateInventoryPath"]).read_text(encoding="utf-8")
        )
        pending = inventory["formalValidationCandidates"][0]
        self.assertEqual(pending["candidateId"], "candidate-a")
        self.assertEqual(pending["status"], "blocked_before_freeze")
        self.assertEqual(
            pending["blockers"],
            ["purged_walk_forward_capacity_insufficient"],
        )
        self.assertEqual(
            {item["candidateId"] for item in inventory["archivedCandidates"]},
            {"candidate-b"},
        )

    def test_release_artifacts_must_stay_inside_the_run_output_root(self) -> None:
        run = self._create_run()
        outside = self.root / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "artifact_path_outside_run"):
            self.orchestrator.record_receipt(
                run["runId"],
                {
                    "status": "immutable_release_ready",
                    "campaignId": run["campaignId"],
                    "releaseCount": 1,
                    "artifactPath": str(outside),
                    "receiptHash": "receipt-outside",
                    "approvalCount": 0,
                    "demoArm": False,
                    "orderCount": 0,
                },
            )


if __name__ == "__main__":
    unittest.main()
