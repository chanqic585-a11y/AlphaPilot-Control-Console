from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import alphapilot_control_console.http_app as http_app


class WorkflowStartupRecoveryTests(unittest.TestCase):
    def test_server_startup_recovers_interrupted_workflows(self) -> None:
        server = Mock()

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
        ) as resume:
            http_app.run_server("127.0.0.1", 8877)

        resume.assert_called_once_with()
        start_auto.assert_called_once_with()
        stop_auto.assert_called_once_with()
        server.serve_forever.assert_called_once_with()

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
        self.assertEqual(payload["version"], "V13.27.3")


if __name__ == "__main__":
    unittest.main()
