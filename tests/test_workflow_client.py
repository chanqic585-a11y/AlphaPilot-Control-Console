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

    def test_projection_exposes_console_batch_capability_separately(self) -> None:
        with patch.object(
            client,
            "run_workflow_cli",
            return_value={"version": "V13.27.6", "items": [], "archivedItems": []},
        ):
            projection = client.build_workflow_projection(quant_root=self.quant_root)

        self.assertEqual(projection["controlConsoleVersion"], "V13.27.9")
        self.assertTrue(projection["capabilities"]["selectedBacktests"])
        self.assertTrue(projection["capabilities"]["selectedForwardCycles"])
        self.assertTrue(projection["capabilities"]["boundedOptimizationRecovery"])
        self.assertTrue(projection["capabilities"]["serialBacktestDrain"])

    def test_request_run_uses_serial_batch_worker_that_drains_queued_runs(self) -> None:
        with patch.object(client, "spawn_workflow_batch") as spawn_batch, patch.object(
            client, "spawn_workflow_run"
        ) as spawn_one:
            spawn_batch.return_value = {
                "started": True,
                "workflowRunIds": ["run-1"],
            }

            result = client.request_dual_layer_backtest(
                "run-1", quant_root=self.quant_root
            )

        spawn_batch.assert_called_once_with(["run-1"], quant_root=self.quant_root)
        spawn_one.assert_not_called()
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
        ), patch.object(client, "request_selected_backtests") as request:
            request.return_value = {
                "requestedCount": 1,
                "workflowRunIds": ["run-1"],
            }
            result = client.request_all_awaiting_backtests(
                quant_root=self.quant_root
            )

        request.assert_called_once_with(["run-1"], quant_root=self.quant_root)
        self.assertEqual(result["requestedCount"], 1)

    def test_run_selected_validates_runs_and_starts_one_serial_worker(self) -> None:
        projection = {
            "items": [
                {"workflowRunId": "run-1", "stage": "backtest", "status": "awaiting"},
                {"workflowRunId": "run-2", "stage": "backtest", "status": "paused"},
                {"workflowRunId": "run-3", "stage": "backtest", "status": "failed"},
            ]
        }
        with patch.object(
            client, "build_workflow_projection", return_value=projection
        ), patch.object(client, "spawn_workflow_batch") as spawn:
            spawn.return_value = {
                "started": True,
                "workflowRunIds": ["run-2", "run-1"],
            }

            result = client.request_selected_backtests(
                ["run-2", "run-1"],
                quant_root=self.quant_root,
            )

        spawn.assert_called_once_with(
            ["run-2", "run-1"],
            quant_root=self.quant_root,
        )
        self.assertEqual(result["requestedCount"], 2)
        self.assertEqual(result["workflowRunIds"], ["run-2", "run-1"])

    def test_run_selected_rejects_duplicate_or_ineligible_runs(self) -> None:
        projection = {
            "items": [
                {"workflowRunId": "run-1", "stage": "backtest", "status": "awaiting"},
                {"workflowRunId": "run-2", "stage": "backtest", "status": "failed"},
            ]
        }
        with patch.object(
            client, "build_workflow_projection", return_value=projection
        ):
            with self.assertRaisesRegex(ValueError, "duplicate_workflow_run_id"):
                client.request_selected_backtests(
                    ["run-1", "run-1"],
                    quant_root=self.quant_root,
                )
            with self.assertRaisesRegex(ValueError, "workflow_run_not_eligible"):
                client.request_selected_backtests(
                    ["run-2"],
                    quant_root=self.quant_root,
                )

    def test_run_selected_action_accepts_run_id_list_only(self) -> None:
        with patch.object(client, "request_selected_backtests") as request:
            request.return_value = {
                "requestedCount": 2,
                "workflowRunIds": ["run-1", "run-2"],
            }
            result = client.request_workflow_action(
                "run-selected",
                {
                    "workflowRunIds": ["run-1", "run-2"],
                    "apiKey": "must-not-flow",
                },
                quant_root=self.quant_root,
            )

        request.assert_called_once_with(
            ["run-1", "run-2"],
            quant_root=self.quant_root,
        )
        self.assertEqual(result["requestedCount"], 2)

    def test_retry_action_restarts_through_the_serial_batch_worker(self) -> None:
        with patch.object(client, "run_workflow_cli") as run_cli, patch.object(
            client, "spawn_workflow_batch"
        ) as spawn_batch, patch.object(client, "spawn_workflow_run") as spawn_one:
            run_cli.return_value = {
                "workflowRunId": "run-restarted",
                "status": "queued",
            }
            spawn_batch.return_value = {
                "started": True,
                "workflowRunIds": ["run-restarted"],
            }

            result = client.request_workflow_action(
                "retry",
                {"workflowRunId": "run-cancelled"},
                quant_root=self.quant_root,
            )

        run_cli.assert_called_once_with(
            ["retry", "--run-id", "run-cancelled"],
            quant_root=self.quant_root,
        )
        spawn_batch.assert_called_once_with(
            ["run-restarted"],
            quant_root=self.quant_root,
        )
        spawn_one.assert_not_called()
        self.assertEqual(result["worker"]["workflowRunIds"], ["run-restarted"])

    def test_auto_optimize_recovers_terminal_result_and_starts_challenger_batch(self) -> None:
        with patch.object(client, "run_workflow_cli") as run_cli, patch.object(
            client, "spawn_workflow_batch"
        ) as spawn_batch:
            run_cli.return_value = {
                "reviewedCount": 1,
                "createdChallengerCount": 1,
                "challengerWorkflowRunIds": ["run-challenger"],
            }
            spawn_batch.return_value = {
                "started": True,
                "workflowRunIds": ["run-challenger"],
            }

            result = client.request_workflow_action(
                "auto-optimize",
                {"strategyVersionId": "strategy-root", "apiKey": "must-not-flow"},
                quant_root=self.quant_root,
            )

        run_cli.assert_called_once_with(
            [
                "recover-bounded-optimizations",
                "--strategy-version-id",
                "strategy-root",
            ],
            quant_root=self.quant_root,
        )
        spawn_batch.assert_called_once_with(
            ["run-challenger"],
            quant_root=self.quant_root,
        )
        self.assertEqual(result["recovery"]["reviewedCount"], 1)
        self.assertNotIn("apiKey", repr(result))

    def test_run_selected_forward_cycles_accepts_only_running_local_runs(self) -> None:
        projection = {
            "items": [
                {"workflowRunId": "forward-1", "stage": "local_forward", "status": "running"},
                {"workflowRunId": "forward-2", "stage": "local_forward", "status": "blocked"},
            ]
        }
        with patch.object(
            client, "build_workflow_projection", return_value=projection
        ), patch.object(client, "spawn_forward_batch") as spawn:
            spawn.return_value = {
                "started": True,
                "workflowRunIds": ["forward-1"],
            }
            result = client.request_selected_forward_cycles(
                ["forward-1"],
                quant_root=self.quant_root,
            )

            with self.assertRaisesRegex(ValueError, "workflow_run_not_eligible"):
                client.request_selected_forward_cycles(
                    ["forward-2"],
                    quant_root=self.quant_root,
                )

        spawn.assert_called_once_with(["forward-1"], quant_root=self.quant_root)
        self.assertEqual(result["requestedCount"], 1)

    def test_run_selected_forward_action_uses_id_list(self) -> None:
        with patch.object(client, "request_selected_forward_cycles") as request:
            request.return_value = {
                "requestedCount": 1,
                "workflowRunIds": ["forward-1"],
            }
            result = client.request_workflow_action(
                "run-selected-forward",
                {"workflowRunIds": ["forward-1"]},
                quant_root=self.quant_root,
            )

        request.assert_called_once_with(
            ["forward-1"],
            quant_root=self.quant_root,
        )
        self.assertEqual(result["requestedCount"], 1)

    def test_startup_recovery_resumes_only_interrupted_backtests(self) -> None:
        projection = {
            "items": [
                {"workflowRunId": "run-running", "stage": "backtest", "status": "running"},
                {"workflowRunId": "run-queued", "stage": "backtest", "status": "queued"},
                {"workflowRunId": "run-paused", "stage": "backtest", "status": "paused"},
                {"workflowRunId": "run-awaiting", "stage": "backtest", "status": "awaiting"},
                {"workflowRunId": "run-forward", "stage": "local_forward", "status": "running"},
            ]
        }
        with patch.object(
            client, "build_workflow_projection", return_value=projection
        ), patch.object(client, "spawn_workflow_batch") as spawn:
            spawn.return_value = {"started": True, "alreadyRunning": False}

            result = client.resume_incomplete_workflow_runs(
                quant_root=self.quant_root
            )

        spawn.assert_called_once_with(
            ["run-running", "run-queued"],
            quant_root=self.quant_root,
        )
        self.assertEqual(result["candidateCount"], 2)
        self.assertEqual(result["startedCount"], 2)
        self.assertEqual(result["errorCount"], 0)

    def test_startup_recovery_records_serial_batch_error(self) -> None:
        projection = {
            "items": [
                {"workflowRunId": "run-1", "stage": "backtest", "status": "running"},
                {"workflowRunId": "run-2", "stage": "backtest", "status": "queued"},
            ]
        }
        with patch.object(
            client, "build_workflow_projection", return_value=projection
        ), patch.object(
            client,
            "spawn_workflow_batch",
            side_effect=RuntimeError("worker unavailable"),
        ):
            result = client.resume_incomplete_workflow_runs(
                quant_root=self.quant_root
            )

        self.assertEqual(result["candidateCount"], 2)
        self.assertEqual(result["startedCount"], 0)
        self.assertEqual(result["errorCount"], 1)
        self.assertEqual(result["errors"][0]["workflowRunId"], "run-1,run-2")

    def test_import_optimized_action_whitelists_fields_and_starts_new_backtest(self) -> None:
        created = {
            "strategyVersionId": "version-2",
            "displayName": "策略优化版",
        }
        projection = {
            "items": [
                {
                    "strategyVersionId": "version-2",
                    "workflowRunId": "run-2",
                    "stage": "backtest",
                    "status": "awaiting",
                }
            ]
        }
        with patch.object(
            client,
            "run_workflow_cli",
            side_effect=[created, projection],
        ) as run_cli, patch.object(
            client,
            "request_dual_layer_backtest",
            return_value={"workflowRunId": "run-2", "worker": {"started": True}},
        ) as start:
            try:
                result = client.request_workflow_action(
                    "import-optimized",
                    {
                        "legacyStrategyId": "legacy-1",
                        "displayName": "策略优化版",
                        "definition": {"timeframe": "1h", "targetR": 2.0},
                        "baseParameters": {"volume_min": 1.2, "targetRMultiple": 2.0},
                        "parameters": {"volume_min": 1.3, "targetRMultiple": 2.0},
                        "startBacktest": True,
                        "apiKey": "must-not-flow",
                        "endpoint": "https://evil.invalid",
                    },
                    quant_root=self.quant_root,
                )
            except ValueError as error:
                self.fail(f"import-optimized action is unavailable: {error}")

        command = run_cli.call_args_list[0].args[0]
        self.assertEqual(command[0], "import-optimized")
        self.assertNotIn("must-not-flow", command)
        self.assertNotIn("https://evil.invalid", command)
        start.assert_called_once_with("run-2", quant_root=self.quant_root)
        self.assertEqual(result["strategyVersionId"], "version-2")
        self.assertTrue(result["backtest"]["worker"]["started"])


if __name__ == "__main__":
    unittest.main()
