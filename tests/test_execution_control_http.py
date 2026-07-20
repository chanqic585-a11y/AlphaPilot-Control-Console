from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from unittest.mock import patch

from alphapilot_control_console.http_app import ConsoleHandler


class ExecutionControlHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ConsoleHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_status_action_and_workflow_fixture_are_routed(self) -> None:
        status = {
            "schemaVersion": "execution-control.v1",
            "environments": {"demo": {}, "live": {}},
        }
        action_result = {"ok": True, "requestId": "req-001", "idempotentReplay": False}
        fixture = {"ok": True, "evidence": {"engineeringOnly": True}}
        with patch(
            "alphapilot_control_console.http_app.get_execution_control_status",
            return_value=status,
            create=True,
        ), patch(
            "alphapilot_control_console.http_app.run_execution_control_action",
            return_value=action_result,
            create=True,
        ) as action, patch(
            "alphapilot_control_console.http_app.run_workflow_validation_demo_fixture",
            return_value=fixture,
            create=True,
        ):
            with urlopen(self.base_url + "/api/execution-control/status", timeout=2) as response:
                status_payload = json.loads(response.read().decode("utf-8"))
            request_body = {
                "requestId": "req-001",
                "environment": "okx_demo",
                "action": "start",
            }
            request = Request(
                self.base_url + "/api/execution-control/action",
                data=json.dumps(request_body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=2) as response:
                action_payload = json.loads(response.read().decode("utf-8"))
            with urlopen(
                self.base_url + "/api/execution-control/workflow-validation-demo",
                timeout=2,
            ) as response:
                fixture_payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(status_payload, status)
        self.assertEqual(action_payload, action_result)
        self.assertEqual(fixture_payload, fixture)
        action.assert_called_once_with(request_body)
        serialized = json.dumps([status_payload, action_payload, fixture_payload])
        self.assertNotIn("apiKey", serialized)
        self.assertNotIn("passphrase", serialized)


if __name__ == "__main__":
    unittest.main()
