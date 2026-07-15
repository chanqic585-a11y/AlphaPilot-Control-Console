from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.local_simulation_retirement import (
    LocalSimulationRetiredError,
    backup_local_history,
    capture_local_history_snapshot,
)
from alphapilot_control_console.local_sandbox_runner import run_local_sandbox
from alphapilot_control_console.sandbox_auto_runner import (
    run_local_sandbox_auto_runner_now,
    start_local_sandbox_auto_runner,
    update_local_sandbox_auto_runner_settings,
)


class LocalSimulationRetirementInvariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name) / "data"
        self.data_dir.mkdir(parents=True)
        state = {
            "localSandboxRuns": [{"runId": "one", "closedSampleCount": 2}],
            "virtualOrders": [{"id": "order"}],
            "virtualFills": [{"id": "fill"}],
            "virtualPositions": [{"id": "position"}],
            "equitySnapshots": [{"id": "equity"}],
            "paperObservationLogs": {
                "strategy": [
                    {"logId": "open", "outcome": ""},
                    {"logId": "closed", "outcome": "win"},
                ]
            },
            "localSandboxLearningSnapshots": [{"id": "learning"}],
            "localSandboxDailyReports": [{"id": "daily"}],
        }
        (self.data_dir / "console_state.json").write_text(
            json.dumps(state, ensure_ascii=False),
            encoding="utf-8",
        )
        connection = sqlite3.connect(self.data_dir / "workflow.sqlite")
        connection.execute("CREATE TABLE WorkflowRuns (id TEXT, stage TEXT)")
        connection.executemany(
            "INSERT INTO WorkflowRuns VALUES (?, ?)",
            [("one", "local_forward"), ("two", "demo")],
        )
        connection.commit()
        connection.close()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_snapshot_counts_history_without_exposing_payloads(self) -> None:
        snapshot = capture_local_history_snapshot(self.data_dir)

        self.assertEqual(
            snapshot["counts"],
            {
                "localRuns": 1,
                "virtualOrders": 1,
                "virtualFills": 1,
                "virtualPositions": 1,
                "equitySnapshots": 1,
                "closedSamples": 1,
                "learningSamples": 1,
                "dailyReports": 1,
                "workflowRowsInRetiredStates": 1,
            },
        )
        serialized = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn('"outcome": "win"', serialized)
        self.assertIn("sha256", serialized)

    def test_online_backup_preserves_counts_and_hashes(self) -> None:
        before = capture_local_history_snapshot(self.data_dir)

        manifest = backup_local_history(
            self.data_dir,
            backup_root=Path(self.temp.name) / "backups",
            timestamp="20260715T120000Z",
        )

        backup_dir = Path(manifest["backupDirectory"])
        self.assertTrue((backup_dir / "workflow.sqlite").exists())
        self.assertTrue((backup_dir / "console_state.json").exists())
        self.assertEqual(manifest["before"]["counts"], before["counts"])
        self.assertEqual(manifest["backup"]["counts"], before["counts"])
        self.assertEqual(
            json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8")),
            manifest,
        )

    def test_all_internal_write_entrypoints_are_retired(self) -> None:
        actions = (
            lambda: run_local_sandbox({}),
            start_local_sandbox_auto_runner,
            lambda: update_local_sandbox_auto_runner_settings({"enabled": True}),
            run_local_sandbox_auto_runner_now,
        )
        for action in actions:
            with self.subTest(action=action):
                with self.assertRaisesRegex(
                    LocalSimulationRetiredError,
                    "local_simulation_retired",
                ):
                    action()


if __name__ == "__main__":
    unittest.main()
