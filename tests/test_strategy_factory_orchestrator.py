from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from alphapilot_control_console.strategy_factory_orchestrator import (
    StrategyFactoryOrchestrator,
    build_research_worker_environment,
)


FIXED_NOW = datetime(2026, 7, 21, 2, 0, tzinfo=UTC)


class StrategyFactoryOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.quant_root = self.root / "quant"
        self.quant_root.mkdir()
        (self.quant_root / "research/source_registry").mkdir(parents=True)
        self.registry_path = (
            self.quant_root
            / "research/source_registry/strategy_research_source_registry.json"
        )
        self.registry_path.write_text(
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
                        },
                        {
                            "familyId": "family-b",
                            "variants": [{"candidateId": "candidate-c"}],
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.launches: list[dict] = []

        def fake_launcher(*, command: list[str], cwd: Path, log_path: Path) -> dict:
            self.launches.append(
                {"command": command, "cwd": cwd, "logPath": log_path}
            )
            return {"pid": 4242, "started": True}

        self.orchestrator = StrategyFactoryOrchestrator(
            state_path=self.root / "factory.sqlite",
            artifact_root=self.root / "artifacts",
            quant_root=self.quant_root,
            source_registry_path=self.registry_path,
            python_executable=self.root / "python.exe",
            launcher=fake_launcher,
            clock=lambda: FIXED_NOW,
            negative_memory_path=self.root / "negative_research_memory.jsonl",
        )

    def tearDown(self) -> None:
        self.orchestrator.close()
        self.temp.cleanup()

    def test_create_run_freezes_bounded_job_without_execution_side_effects(self) -> None:
        run = self.orchestrator.create_run(
            {
                "operation": "generate",
                "timeframe": "15m",
                "mode": "quick",
                "maxCandidateCount": 2,
                "maxTrialBudget": 12,
            }
        )

        self.assertEqual(run["status"], "queued")
        self.assertEqual(run["stage"], "prepare_material")
        self.assertEqual(run["progressPercent"], 0)
        self.assertEqual(run["candidateIds"], ["candidate-a", "candidate-b"])
        self.assertEqual(run["maxCandidateCount"], 2)
        self.assertEqual(run["maxTrialBudget"], 12)
        self.assertFalse(run["automaticPromotionAllowed"])
        self.assertFalse(run["forcePassAllowed"])
        self.assertFalse(run["lockedOosTuningAllowed"])
        self.assertEqual(run["lifecycleState"], "trial_queued")
        self.assertEqual(run["lifecycle"]["completedTrialCount"], 0)
        self.assertEqual(run["failureAttributions"], [])

        job = json.loads(Path(run["jobJsonPath"]).read_text(encoding="utf-8"))
        self.assertEqual(job["campaignId"], run["campaignId"])
        self.assertEqual(job["candidateIds"], ["candidate-a", "candidate-b"])
        self.assertEqual(job["experimentBudget"]["maximumTrials"], 12)
        self.assertEqual(job["executionBoundary"]["demoReleaseCount"], 0)
        self.assertEqual(job["executionBoundary"]["approvalCount"], 0)
        self.assertFalse(job["executionBoundary"]["demoArm"])
        self.assertEqual(job["executionBoundary"]["orderCount"], 0)
        self.assertEqual(job["workerPolicy"]["marketDataAccess"], "read_only")
        self.assertFalse(job["workerPolicy"]["privateApiAccess"])
        self.assertFalse(job["workerPolicy"]["orderAccess"])
        self.assertEqual(job["workerPolicy"]["maximumConcurrentRuns"], 1)
        self.assertFalse(job["aiResearchGovernance"]["executionAuthorized"])
        self.assertEqual(
            job["aiResearchGovernance"]["draftTypes"],
            ["HypothesisDraft", "CandidateDraft", "ExperimentDraft"],
        )
        self.assertEqual(
            job["aiResearchGovernance"]["familyContexts"][0]["memoryHitCount"],
            0,
        )

    def test_candidate_selection_respects_requested_timeframe(self) -> None:
        self.registry_path.write_text(
            json.dumps(
                {
                    "schemaVersion": "fixture-v1",
                    "registryId": "fixture-registry",
                    "families": [
                        {
                            "familyId": "intraday-family",
                            "parameters": {"timeframes": ["5m", "15m"]},
                            "variants": [{"candidateId": "intraday-candidate"}],
                        },
                        {
                            "familyId": "swing-family",
                            "parameters": {"timeframes": ["4h", "1d"]},
                            "variants": [{"candidateId": "swing-candidate"}],
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        run = self.orchestrator.create_run(
            {
                "operation": "generate",
                "timeframe": "15m",
                "mode": "quick",
                "maxCandidateCount": 2,
                "maxTrialBudget": 6,
            }
        )

        self.assertEqual(run["familyIds"], ["intraday-family"])
        self.assertEqual(run["candidateIds"], ["intraday-candidate"])

    def test_generate_excludes_context_only_family(self) -> None:
        self.registry_path.write_text(
            json.dumps(
                {
                    "schemaVersion": "fixture-v1",
                    "registryId": "fixture-registry",
                    "families": [
                        {
                            "familyId": "signal-family",
                            "parameters": {"timeframes": ["15m"]},
                            "variants": [{"candidateId": "signal-candidate"}],
                        },
                        {
                            "familyId": "context-family",
                            "parameters": {
                                "timeframes": ["15m"],
                                "role": "context_only",
                            },
                            "variants": [{"candidateId": "context-candidate"}],
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        run = self.orchestrator.create_run(
            {
                "operation": "generate",
                "timeframe": "15m",
                "mode": "quick",
                "maxCandidateCount": 2,
                "maxTrialBudget": 6,
            }
        )

        self.assertEqual(run["familyIds"], ["signal-family"])
        self.assertEqual(run["candidateIds"], ["signal-candidate"])

    def test_configured_development_profile_is_frozen_into_one_click_job(self) -> None:
        snapshot_manifest = self.root / "snapshot.json"
        snapshot_manifest.write_text(
            json.dumps(
                {
                    "snapshotId": "snapshot-fixture",
                    "status": "verified",
                }
            ),
            encoding="utf-8",
        )
        profile_path = self.root / "development-profile.json"
        profile_path.write_text(
            json.dumps(
                {
                    "schemaVersion": "strategy_factory_development_profile_v1",
                    "profileId": "development-profile-fixture",
                    "comparisonPanel": {
                        "developmentStart": "2021-02-01T00:00:00Z",
                        "developmentEnd": "2025-01-01T00:00:00Z",
                        "dataSnapshotId": "snapshot-fixture",
                        "costPolicyHash": "cost-policy-fixture",
                        "capitalPolicyHash": "capital-policy-fixture",
                        "benchmarkPolicyHash": "benchmark-policy-fixture",
                        "randomSeed": 56,
                    },
                    "developmentReplay": {
                        "snapshotManifestPath": str(snapshot_manifest),
                        "roundTripCostRate": 0.0012,
                    },
                }
            ),
            encoding="utf-8",
        )
        orchestrator = StrategyFactoryOrchestrator(
            state_path=self.root / "profile-factory.sqlite",
            artifact_root=self.root / "profile-artifacts",
            quant_root=self.quant_root,
            source_registry_path=self.registry_path,
            python_executable=self.root / "python.exe",
            development_profile_path=profile_path,
            launcher=lambda **_kwargs: {"pid": 4243, "started": True},
            clock=lambda: FIXED_NOW,
        )
        try:
            run = orchestrator.create_run(
                {
                    "operation": "generate",
                    "timeframe": "15m",
                    "mode": "quick",
                    "maxCandidateCount": 2,
                    "maxTrialBudget": 12,
                }
            )
            job = json.loads(Path(run["jobJsonPath"]).read_text(encoding="utf-8"))

            self.assertEqual(job["comparisonPanel"]["dataSnapshotId"], "snapshot-fixture")
            self.assertEqual(
                job["developmentReplay"]["snapshotManifestPath"],
                str(snapshot_manifest),
            )
            self.assertEqual(
                job["developmentProfile"]["profileId"],
                "development-profile-fixture",
            )
            self.assertTrue(job["developmentProfile"]["profileHash"].startswith("strategy_factory_development_profile_"))

            with self.assertRaisesRegex(
                ValueError,
                "strategy_factory_development_profile_mismatch",
            ):
                orchestrator.create_run(
                    {
                        "operation": "generate",
                        "timeframe": "15m",
                        "mode": "quick",
                        "maxCandidateCount": 2,
                        "maxTrialBudget": 12,
                        "dataSnapshotId": "different-snapshot",
                    }
                )
        finally:
            orchestrator.close()

    def test_explicit_development_profile_path_must_exist(self) -> None:
        orchestrator = StrategyFactoryOrchestrator(
            state_path=self.root / "missing-profile-factory.sqlite",
            artifact_root=self.root / "missing-profile-artifacts",
            quant_root=self.quant_root,
            source_registry_path=self.registry_path,
            python_executable=self.root / "python.exe",
            development_profile_path=self.root / "missing-profile.json",
            launcher=lambda **_kwargs: {"pid": 4244, "started": True},
            clock=lambda: FIXED_NOW,
        )
        try:
            with self.assertRaises(FileNotFoundError):
                orchestrator.create_run(
                    {
                        "operation": "generate",
                        "timeframe": "15m",
                        "mode": "quick",
                        "maxCandidateCount": 2,
                        "maxTrialBudget": 12,
                    }
                )
        finally:
            orchestrator.close()

    def test_development_profile_snapshot_must_match_manifest(self) -> None:
        snapshot_manifest = self.root / "mismatched-snapshot.json"
        snapshot_manifest.write_text(
            json.dumps({"snapshotId": "snapshot-in-manifest"}),
            encoding="utf-8",
        )
        profile_path = self.root / "mismatched-development-profile.json"
        profile_path.write_text(
            json.dumps(
                {
                    "schemaVersion": "strategy_factory_development_profile_v1",
                    "profileId": "mismatched-profile-fixture",
                    "comparisonPanel": {
                        "developmentStart": "2021-02-01T00:00:00Z",
                        "developmentEnd": "2025-01-01T00:00:00Z",
                        "dataSnapshotId": "different-snapshot",
                        "costPolicyHash": "cost-policy-fixture",
                        "capitalPolicyHash": "capital-policy-fixture",
                        "benchmarkPolicyHash": "benchmark-policy-fixture",
                        "randomSeed": 56,
                    },
                    "developmentReplay": {
                        "snapshotManifestPath": str(snapshot_manifest),
                        "roundTripCostRate": 0.0012,
                    },
                }
            ),
            encoding="utf-8",
        )
        orchestrator = StrategyFactoryOrchestrator(
            state_path=self.root / "mismatched-profile-factory.sqlite",
            artifact_root=self.root / "mismatched-profile-artifacts",
            quant_root=self.quant_root,
            source_registry_path=self.registry_path,
            python_executable=self.root / "python.exe",
            development_profile_path=profile_path,
            launcher=lambda **_kwargs: {"pid": 4245, "started": True},
            clock=lambda: FIXED_NOW,
        )
        try:
            with self.assertRaisesRegex(
                ValueError,
                "strategy_factory_development_profile_snapshot_mismatch",
            ):
                orchestrator.create_run(
                    {
                        "operation": "generate",
                        "timeframe": "15m",
                        "mode": "quick",
                        "maxCandidateCount": 2,
                        "maxTrialBudget": 12,
                    }
                )
        finally:
            orchestrator.close()

    def test_research_worker_environment_strips_private_credentials(self) -> None:
        environment = build_research_worker_environment(
            {
                "PATH": "fixture",
                "OKX_API_KEY": "secret",
                "ALPHAPILOT_OKX_DEMO_SECRET_KEY": "secret",
                "ALPHAPILOT_OKX_LIVE_PASSPHRASE": "secret",
                "UNRELATED_VALUE": "kept",
            }
        )

        self.assertEqual(environment["PATH"], "fixture")
        self.assertEqual(environment["UNRELATED_VALUE"], "kept")
        self.assertNotIn("OKX_API_KEY", environment)
        self.assertNotIn("ALPHAPILOT_OKX_DEMO_SECRET_KEY", environment)
        self.assertNotIn("ALPHAPILOT_OKX_LIVE_PASSPHRASE", environment)
        self.assertEqual(environment["ALPHAPILOT_RESEARCH_WORKER"], "1")
        self.assertEqual(environment["ALPHAPILOT_ORDER_ACCESS"], "0")
        self.assertEqual(environment["ALPHAPILOT_PRIVATE_API_ACCESS"], "0")

    def test_only_one_research_worker_can_run_at_a_time(self) -> None:
        first = self.orchestrator.create_run(
            {
                "operation": "generate",
                "timeframe": "5m",
                "mode": "quick",
                "maxCandidateCount": 1,
                "maxTrialBudget": 4,
            }
        )
        second = self.orchestrator.create_run(
            {
                "operation": "combine",
                "timeframe": "15m",
                "mode": "quick",
                "maxCandidateCount": 1,
                "maxTrialBudget": 4,
            }
        )

        self.orchestrator.start_run(first["runId"])
        with self.assertRaisesRegex(ValueError, "strategy_factory_concurrency_limit"):
            self.orchestrator.start_run(second["runId"])

    def test_start_pause_resume_and_checkpoint_are_persistent(self) -> None:
        created = self.orchestrator.create_run(
            {
                "operation": "combine",
                "timeframe": "1h",
                "mode": "standard",
                "maxCandidateCount": 3,
                "maxTrialBudget": 24,
            }
        )
        started = self.orchestrator.start_run(created["runId"])
        self.assertEqual(started["status"], "running")
        self.assertEqual(started["pid"], 4242)
        self.assertEqual(len(self.launches), 1)
        self.assertIn("alphapilot.scripts.run_v36_candidate_research", self.launches[0]["command"])
        self.assertIn("--job-json", self.launches[0]["command"])
        self.assertIn("--pause-file", self.launches[0]["command"])

        pause_requested = self.orchestrator.pause_run(created["runId"])
        self.assertEqual(pause_requested["status"], "pause_requested")
        self.assertTrue(Path(pause_requested["pauseMarkerPath"]).is_file())

        receipt_path = (
            Path(pause_requested["jobJsonPath"]).parent
            / "state/research_cycle_receipts.jsonl"
        )
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(
                {
                    "status": "paused",
                    "campaignId": created["campaignId"],
                    "candidateCount": 3,
                    "releaseCount": 0,
                    "approvalCount": 0,
                    "demoArm": False,
                    "orderCount": 0,
                    "receiptHash": "paused-receipt-1",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        Path(pause_requested["workerExitMarkerPath"]).parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        Path(pause_requested["workerExitMarkerPath"]).write_text(
            "{}\n",
            encoding="utf-8",
        )
        paused = self.orchestrator.refresh_run(created["runId"])
        self.assertEqual(paused["status"], "paused")

        resumed = self.orchestrator.resume_run(created["runId"])
        self.assertEqual(resumed["status"], "running")
        self.assertFalse(Path(resumed["pauseMarkerPath"]).exists())
        self.assertFalse(Path(resumed["workerExitMarkerPath"]).exists())
        self.assertEqual(len(self.launches), 2)

        checkpoint = self.orchestrator.record_checkpoint(
            created["runId"],
            stage="tuning_backtest",
            completed_count=3,
            total_count=7,
            current_candidate="candidate-b",
        )
        self.assertEqual(checkpoint["stage"], "tuning_backtest")
        self.assertEqual(checkpoint["progressPercent"], 43)
        self.assertEqual(
            self.orchestrator.get_run(created["runId"])["currentCandidate"],
            "candidate-b",
        )

    def test_pause_receipt_waits_for_worker_handoff_marker(self) -> None:
        created = self.orchestrator.create_run(
            {
                "operation": "generate",
                "timeframe": "5m",
                "mode": "quick",
                "maxCandidateCount": 1,
                "maxTrialBudget": 4,
            }
        )
        running = self.orchestrator.start_run(created["runId"])
        self.orchestrator.pause_run(created["runId"])
        receipt_path = Path(running["jobJsonPath"]).parent / "state/research_cycle_receipts.jsonl"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(
                {
                    "status": "paused",
                    "campaignId": created["campaignId"],
                    "candidateCount": 1,
                    "receiptHash": "pause-before-exit",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        waiting = self.orchestrator.refresh_run(created["runId"])

        self.assertEqual(waiting["status"], "pause_requested")
        with self.assertRaisesRegex(ValueError, "pause_handoff"):
            self.orchestrator.resume_run(created["runId"])

    def test_refresh_imports_matching_quant_receipt_once(self) -> None:
        created = self.orchestrator.create_run(
            {
                "operation": "generate",
                "timeframe": "15m",
                "mode": "quick",
                "maxCandidateCount": 1,
                "maxTrialBudget": 4,
            }
        )
        started = self.orchestrator.start_run(created["runId"])
        receipt_path = Path(started["jobJsonPath"]).parent / "state/research_cycle_receipts.jsonl"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(
                {
                    "status": "research_blocked_data",
                    "campaignId": created["campaignId"],
                    "candidateCount": 1,
                    "eligibleCandidateCount": 0,
                    "releaseCount": 0,
                    "approvalCount": 0,
                    "demoArm": False,
                    "orderCount": 0,
                    "receiptHash": "receipt-1",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        refreshed = self.orchestrator.refresh_run(created["runId"])
        repeated = self.orchestrator.refresh_run(created["runId"])

        self.assertEqual(refreshed["status"], "completed")
        self.assertEqual(refreshed["resultClass"], "data_insufficient")
        self.assertEqual(refreshed["progressPercent"], 100)
        self.assertEqual(repeated, refreshed)
        event_count = self.orchestrator.connection.execute(
            "SELECT COUNT(*) FROM StrategyFactoryEvents WHERE runId = ? AND eventType = 'completed'",
            (created["runId"],),
        ).fetchone()[0]
        self.assertEqual(event_count, 1)

    def test_receipt_allows_zero_survivors_but_never_auto_promotes(self) -> None:
        created = self.orchestrator.create_run(
            {
                "operation": "generate",
                "timeframe": "5m",
                "mode": "quick",
                "maxCandidateCount": 1,
                "maxTrialBudget": 6,
            }
        )
        result = self.orchestrator.record_receipt(
            created["runId"],
            {
                "status": "research_blocked_data",
                "candidateCount": 1,
                "eligibleCandidateCount": 1,
                "trialCount": 1,
                "formalRunCount": 0,
                "resultReadCount": 0,
                "lockedOosReadCount": 0,
                "releaseCount": 0,
                "demoReleaseCount": 0,
                "approvalCount": 0,
                "demoArm": False,
                "orderCount": 0,
                "tradeApiUsed": False,
                "withdrawApiUsed": False,
                "privateAccountReadUsed": False,
            },
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["resultClass"], "data_insufficient")
        self.assertEqual(result["survivorCount"], 0)
        self.assertFalse(result["automaticPromotionAllowed"])
        self.assertEqual(result["approvalCount"], 0)
        self.assertFalse(result["demoArm"])
        self.assertEqual(result["orderCount"], 0)

    def test_receipt_projects_matchability_forward_and_factor_readiness(self) -> None:
        created = self.orchestrator.create_run(
            {
                "operation": "generate",
                "timeframe": "1h",
                "mode": "quick",
                "maxCandidateCount": 1,
                "maxTrialBudget": 6,
            }
        )
        result = self.orchestrator.record_receipt(
            created["runId"],
            {
                "status": "research_blocked_data",
                "candidateCount": 1,
                "trialCount": 6,
                "releaseCount": 0,
                "approvalCount": 0,
                "demoArm": False,
                "orderCount": 0,
                "matchability": {
                    "requestedUniverse": 100,
                    "publicUniverse": 98,
                    "exchangeTradable": 90,
                    "eligibleUniverse": 80,
                    "componentCompatible": 70,
                    "lookbackReady": 60,
                    "dataReady": 50,
                    "evaluated": 50,
                    "rawSignals": 8,
                    "identityPassed": 6,
                    "cooldownRejected": 1,
                    "riskRejected": 1,
                    "orderEligible": 4,
                    "orders": 2,
                    "fills": 2,
                    "closedTrades": 1,
                },
                "forwardTask": {
                    "taskId": "forward-fixture",
                    "releaseId": "release-fixture",
                    "releaseHash": "release-hash-fixture",
                    "startedAt": "2026-07-21T02:00:00Z",
                    "status": "collecting",
                    "closedTradeCount": 31,
                    "effectiveSampleSize": 27.5,
                    "symbolCoverage": 0.4,
                    "regimeCoverage": 0.3,
                    "costCompleteness": 1.0,
                },
                "factorModelReadiness": {
                    "factorRegistry": "passed",
                    "demoDecisionMode": "rank_only",
                },
            },
        )

        self.assertEqual(result["matchability"]["status"], "positions_open_or_reconciliation_pending")
        self.assertEqual(result["forwardTask"]["reviewHint"], "preliminary_review_available")
        self.assertFalse(result["forwardTask"]["automaticPromotionAllowed"])
        self.assertEqual(result["factorModelReadiness"]["status"], "not_ready")
        self.assertEqual(result["factorModelReadiness"]["effectiveDecisionMode"], "rule_only")
        self.assertFalse(result["factorModelReadiness"]["liveEligible"])

    def test_failed_receipt_persists_deduplicated_negative_research_memory(self) -> None:
        created = self.orchestrator.create_run(
            {
                "operation": "generate",
                "timeframe": "5m",
                "mode": "quick",
                "maxCandidateCount": 1,
                "maxTrialBudget": 4,
            }
        )
        receipt = {
            "status": "no_stable_candidates",
            "candidateCount": 1,
            "eligibleCandidateCount": 1,
            "trialCount": 4,
            "reasonCodes": ["minimumProfitFactor", "costStress"],
            "profitFactor": 0.82,
            "averageNetR": -0.14,
            "maximumDrawdownR": 19.2,
            "releaseCount": 0,
            "demoReleaseCount": 0,
            "approvalCount": 0,
            "demoArm": False,
            "orderCount": 0,
            "tradeApiUsed": False,
            "withdrawApiUsed": False,
            "privateAccountReadUsed": False,
        }

        first = self.orchestrator.record_receipt(created["runId"], receipt)
        self.orchestrator.record_receipt(created["runId"], receipt)
        rows = [
            json.loads(line)
            for line in (self.root / "negative_research_memory.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

        self.assertEqual(first["negativeResearchMemory"]["recordCount"], 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["strategyId"], "candidate-a")
        self.assertEqual(rows[0]["failureLayer"], "Cost / Capacity")
        self.assertIn("lower_gate_after_result", rows[0]["prohibitedRepeats"])

    def test_receipt_rejects_any_execution_track_side_effect(self) -> None:
        created = self.orchestrator.create_run(
            {
                "operation": "generate",
                "timeframe": "4h",
                "mode": "quick",
                "maxCandidateCount": 1,
                "maxTrialBudget": 4,
            }
        )

        with self.assertRaisesRegex(ValueError, "execution_boundary"):
            self.orchestrator.record_receipt(
                created["runId"],
                {
                    "status": "immutable_release_ready",
                    "demoReleaseCount": 1,
                    "approvalCount": 0,
                    "demoArm": False,
                    "orderCount": 0,
                },
            )

    def test_budget_caps_are_enforced(self) -> None:
        for field, value in (
            ("maxCandidateCount", 13),
            ("maxTrialBudget", 97),
        ):
            payload = {
                "operation": "generate",
                "timeframe": "15m",
                "mode": "standard",
                "maxCandidateCount": 2,
                "maxTrialBudget": 12,
            }
            payload[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.orchestrator.create_run(payload)


if __name__ == "__main__":
    unittest.main()
