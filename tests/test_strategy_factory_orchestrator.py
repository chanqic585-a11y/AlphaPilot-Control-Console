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
                "eligibleCandidateCount": 0,
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
