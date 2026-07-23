from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_factory_continuous_runner import (
    DEFAULT_RESEARCH_CYCLE,
    StrategyFactoryContinuousRunner,
)


class FakeFactory:
    def __init__(self) -> None:
        self.runs: dict[str, dict] = {}
        self.created_payloads: list[dict] = []
        self.closed = False

    def list_runs(self, *, limit: int = 20) -> list[dict]:
        return list(self.runs.values())[:limit]

    def create_run(self, payload: dict) -> dict:
        self.created_payloads.append(dict(payload))
        run_id = f"run-{len(self.created_payloads)}"
        run = {
            "runId": run_id,
            "status": "queued",
            "resultClass": None,
            "executionBoundary": {
                "approvalCount": 0,
                "demoArm": False,
                "orderCount": 0,
            },
        }
        self.runs[run_id] = run
        return dict(run)

    def start_run(self, run_id: str) -> dict:
        self.runs[run_id]["status"] = "running"
        return dict(self.runs[run_id])

    def refresh_run(self, run_id: str) -> dict:
        return dict(self.runs[run_id])

    def close(self) -> None:
        self.closed = True


class StrategyFactoryContinuousRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.factory = FakeFactory()
        self.runner = StrategyFactoryContinuousRunner(
            state_path=self.root / "continuous_research.json",
            factory_builder=lambda: self.factory,
            cycle=DEFAULT_RESEARCH_CYCLE,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_enabled_runner_starts_one_bounded_run_and_persists_state(self) -> None:
        enabled = self.runner.enable()
        status = self.runner.run_once()

        self.assertTrue(enabled["enabled"])
        self.assertEqual(status["phase"], "running")
        self.assertEqual(status["currentRunId"], "run-1")
        self.assertEqual(self.factory.created_payloads[0]["timeframe"], "5m")
        self.assertEqual(self.factory.created_payloads[0]["operation"], "generate")
        self.assertNotIn("approval", self.factory.created_payloads[0])
        self.assertNotIn("demoArm", self.factory.created_payloads[0])
        self.assertNotIn("order", self.factory.created_payloads[0])
        persisted = json.loads(
            (self.root / "continuous_research.json").read_text(encoding="utf-8")
        )
        self.assertEqual(persisted["currentRunId"], "run-1")

    def test_runner_advances_after_formal_handoff_without_approving_it(self) -> None:
        self.runner.enable()
        first = self.runner.run_once()
        self.factory.runs[first["currentRunId"]].update(
            {
                "status": "completed",
                "resultClass": "needs_forward_validation",
            }
        )

        next_status = self.runner.run_once()

        self.assertEqual(next_status["currentRunId"], "run-2")
        self.assertEqual(self.factory.created_payloads[1]["timeframe"], "15m")
        self.assertEqual(next_status["lastResultClass"], "needs_forward_validation")
        self.assertEqual(next_status["completedRunCount"], 1)

    def test_runner_does_not_treat_awaiting_formal_validation_as_complete(self) -> None:
        self.runner.enable()
        first = self.runner.run_once()
        self.factory.runs[first["currentRunId"]].update(
            {
                "status": "awaiting_formal_validation",
                "resultClass": "needs_forward_validation",
            }
        )

        status = self.runner.run_once()

        self.assertEqual(status["phase"], "waiting_current_run")
        self.assertEqual(status["currentRunId"], first["currentRunId"])
        self.assertEqual(status["completedRunCount"], 0)
        self.assertEqual(len(self.factory.created_payloads), 1)

    def test_enable_guard_blocks_continuous_research_before_real_closure(self) -> None:
        guarded = StrategyFactoryContinuousRunner(
            state_path=self.root / "guarded_continuous_research.json",
            factory_builder=lambda: self.factory,
            cycle=DEFAULT_RESEARCH_CYCLE,
            enable_guard=lambda: (_ for _ in ()).throw(
                ValueError("continuous_research_real_trial_closure_required")
            ),
        )

        with self.assertRaisesRegex(
            ValueError, "continuous_research_real_trial_closure_required"
        ):
            guarded.enable()

        self.assertFalse(guarded.status()["enabled"])

    def test_runner_waits_for_existing_manual_run(self) -> None:
        self.factory.runs["manual-run"] = {
            "runId": "manual-run",
            "status": "running",
            "resultClass": None,
        }
        self.runner.enable()

        status = self.runner.run_once()

        self.assertEqual(status["phase"], "waiting_existing_run")
        self.assertEqual(status["blockingRunId"], "manual-run")
        self.assertEqual(self.factory.created_payloads, [])

    def test_disable_stops_future_launches_but_does_not_cancel_current_run(self) -> None:
        self.runner.enable()
        running = self.runner.run_once()

        disabled = self.runner.disable()

        self.assertFalse(disabled["enabled"])
        self.assertEqual(disabled["currentRunId"], running["currentRunId"])
        self.assertEqual(self.factory.runs[running["currentRunId"]]["status"], "running")

    def test_disabled_runner_reconciles_completed_run_without_launching_next(self) -> None:
        self.runner.enable()
        running = self.runner.run_once()
        run_id = running["currentRunId"]
        self.runner.disable()
        self.factory.runs[run_id].update(
            {
                "status": "completed",
                "resultClass": "failed",
            }
        )

        status = self.runner.run_once()

        self.assertFalse(status["enabled"])
        self.assertEqual(status["phase"], "disabled")
        self.assertIsNone(status["currentRunId"])
        self.assertEqual(status["lastRunId"], run_id)
        self.assertEqual(status["lastResultClass"], "failed")
        self.assertEqual(status["completedRunCount"], 1)
        self.assertEqual(status["nextIndex"], 1)
        self.assertEqual(len(self.factory.created_payloads), 1)


if __name__ == "__main__":
    unittest.main()
