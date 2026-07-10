from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import alphapilot_control_console.workflow_client as client


class WorkflowClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.quant_root = Path(self.temp.name) / "AlphaPilot-Quant-Engine"
        (self.quant_root / ".venv" / "Scripts").mkdir(parents=True)
        (self.quant_root / ".venv" / "Scripts" / "python.exe").write_bytes(b"")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_command_uses_fixed_quant_module_and_local_registry(self) -> None:
        command = client.build_workflow_command(
            ["projection"],
            quant_root=self.quant_root,
        )

        self.assertEqual(command[0], str(self.quant_root / ".venv" / "Scripts" / "python.exe"))
        self.assertEqual(
            command[1:3],
            ["-m", "alphapilot.evolution.workflow.cli"],
        )
        self.assertIn(str(self.quant_root / "data" / "evolution_registry.sqlite"), command)
        warehouse_index = command.index("--warehouse-root")
        self.assertEqual(
            command[warehouse_index + 1],
            r"D:\Codex-Workspace\回测数据",
        )
        self.assertEqual(command[-1], "projection")

    def test_request_run_queues_then_starts_one_background_worker(self) -> None:
        with patch.object(client, "run_workflow_cli") as run_cli, patch.object(
            client, "spawn_workflow_run"
        ) as spawn:
            run_cli.return_value = {
                "workflowRunId": "run-1",
                "status": "queued",
            }
            spawn.return_value = {"started": True, "workflowRunId": "run-1"}

            result = client.request_dual_layer_backtest(
                "run-1", quant_root=self.quant_root
            )

        run_cli.assert_not_called()
        spawn.assert_called_once_with("run-1", quant_root=self.quant_root)
        self.assertTrue(result["worker"]["started"])

    def test_dual_layer_action_ignores_endpoint_module_and_credentials_payload(self) -> None:
        with patch.object(client, "request_dual_layer_backtest") as request:
            request.return_value = {"workflowRunId": "run-1"}
            result = client.request_workflow_action(
                "run-dual-layer",
                {
                    "workflowRunId": "run-1",
                    "endpoint": "https://evil.invalid",
                    "pythonModule": "evil.module",
                    "apiKey": "must-not-flow",
                },
                quant_root=self.quant_root,
            )

        request.assert_called_once_with("run-1", quant_root=self.quant_root)
        self.assertEqual(result["workflowRunId"], "run-1")

    def test_run_all_only_starts_awaiting_backtests(self) -> None:
        projection = {
            "items": [
                {"workflowRunId": "run-1", "stage": "backtest", "status": "awaiting"},
                {"workflowRunId": "run-2", "stage": "backtest", "status": "failed"},
                {"workflowRunId": "run-3", "stage": "local_forward", "status": "awaiting"},
            ]
        }
        with patch.object(
            client, "build_workflow_projection", return_value=projection
        ), patch.object(client, "request_dual_layer_backtest") as request:
            request.return_value = {"workflowRunId": "run-1"}
            result = client.request_all_awaiting_backtests(
                quant_root=self.quant_root
            )

        request.assert_called_once_with("run-1", quant_root=self.quant_root)
        self.assertEqual(result["requestedCount"], 1)


if __name__ == "__main__":
    unittest.main()
