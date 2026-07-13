from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import alphapilot_control_console.http_app as http_app
import alphapilot_control_console.workflow_client as workflow_client


class WorkflowStartupRecoveryTests(unittest.TestCase):
    def test_startup_recovers_backtests_as_one_serial_batch(self) -> None:
        projection = {
            "items": [
                {
                    "stage": "backtest",
                    "status": "running",
                    "workflowRunId": "workflow_run_first",
                },
                {
                    "stage": "backtest",
                    "status": "queued",
                    "workflowRunId": "workflow_run_second",
                },
                {
                    "stage": "backtest",
                    "status": "paused",
                    "workflowRunId": "workflow_run_paused",
                },
            ]
        }
        quant_root = Path("D:/Codex-Workspace/AlphaPilot-Quant-Engine")

        with patch.object(
            workflow_client,
            "build_workflow_projection",
            return_value=projection,
        ), patch.object(
            workflow_client,
            "spawn_workflow_batch",
            return_value={"started": True, "alreadyRunning": False},
        ) as batch, patch.object(
            workflow_client,
            "spawn_workflow_run",
        ) as single:
            result = workflow_client.resume_incomplete_workflow_runs(
                quant_root=quant_root
            )

        batch.assert_called_once_with(
            ["workflow_run_first", "workflow_run_second"],
            quant_root=quant_root,
        )
        single.assert_not_called()
        self.assertEqual(result["candidateCount"], 2)
        self.assertEqual(result["startedCount"], 2)
        self.assertEqual(result["errorCount"], 0)

    def test_server_startup_recovers_interrupted_workflows(self) -> None:
        server = Mock()
        lifecycle: list[str] = []
        server.serve_forever.side_effect = lambda: lifecycle.append("serve")

        with patch.object(
            http_app, "ThreadingHTTPServer", return_value=server
        ), patch.object(http_app, "start_local_sandbox_auto_runner"), patch.object(
            http_app, "stop_local_sandbox_auto_runner"
        ), patch.object(
            http_app, "start_unified_auto_execution_runner"
        ) as start_auto, patch.object(
            http_app, "stop_unified_auto_execution_runner"
        ) as stop_auto, patch.object(
            http_app, "resume_incomplete_workflow_runs"
        ) as resume, patch.object(
            http_app,
            "start_demo_market_runtime",
            side_effect=lambda **_kwargs: lifecycle.append("market_start") or {"started": True},
        ) as start_market, patch.object(
            http_app,
            "stop_demo_market_runtime",
            side_effect=lambda: lifecycle.append("market_stop"),
        ) as stop_market:
            start_auto.side_effect = lambda: lifecycle.append("auto_start")
            stop_auto.side_effect = lambda: lifecycle.append("auto_stop")
            http_app.run_server("127.0.0.1", 8877)

        resume.assert_called_once_with()
        start_auto.assert_called_once_with()
        stop_auto.assert_called_once_with()
        start_market.assert_called_once()
        stop_market.assert_called_once_with()
        server.serve_forever.assert_called_once_with()
        self.assertEqual(
            lifecycle,
            ["market_start", "auto_start", "serve", "auto_stop", "market_stop"],
        )

    def test_health_payload_reports_startup_recovery_state(self) -> None:
        recovery = {
            "status": "completed",
            "candidateCount": 1,
            "startedCount": 1,
            "errorCount": 0,
        }
        with patch.object(
            http_app, "get_startup_workflow_recovery_status", return_value=recovery
        ):
            payload = http_app.build_health_payload()

        self.assertEqual(payload["workflowRecovery"], recovery)
        self.assertEqual(payload["version"], "V13.27.9")


if __name__ == "__main__":
    unittest.main()
