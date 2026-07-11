from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from unittest.mock import patch

from alphapilot_control_console.http_app import ConsoleHandler


class UnifiedAutoExecutionHttpTests(unittest.TestCase):
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

    def test_runtime_get_and_action_post_are_routed(self) -> None:
        runtime = {"running": True, "environments": {"okx_demo": {"status": "waiting"}}}
        action_result = {"ok": True, "runtime": runtime}
        with patch(
            "alphapilot_control_console.http_app.get_unified_auto_execution_status",
            return_value=runtime,
        ), patch(
            "alphapilot_control_console.http_app.run_unified_auto_execution_action",
            return_value=action_result,
        ) as action:
            with urlopen(self.base_url + "/api/auto-execution/runtime", timeout=2) as response:
                get_payload = json.loads(response.read().decode("utf-8"))
            request = Request(
                self.base_url + "/api/auto-execution/action",
                data=json.dumps({"environment": "okx_demo", "action": "start"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=2) as response:
                post_payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(get_payload, runtime)
        self.assertTrue(post_payload["ok"])
        action.assert_called_once_with({"environment": "okx_demo", "action": "start"})

    def test_mobile_projection_includes_readonly_automatic_execution_state(self) -> None:
        runtime = {"running": True, "environments": {"okx_demo": {"status": "waiting"}}}
        with patch(
            "alphapilot_control_console.http_app.scan_quant_engine",
            return_value={},
        ), patch(
            "alphapilot_control_console.http_app.build_mobile_status",
            return_value={"version": "test", "safetyBoundary": {}},
        ), patch(
            "alphapilot_control_console.http_app.get_unified_auto_execution_status",
            return_value=runtime,
        ):
            with urlopen(self.base_url + "/api/mobile/status?fresh=1", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload["automaticExecution"], runtime)
        self.assertNotIn("apiKey", json.dumps(payload))

    def test_existing_live_arm_route_also_arms_the_unified_current_process(self) -> None:
        automatic = {
            "ok": True,
            "armResult": {"ok": True, "liveCanary": {"summary": {"canaryOrderReady": True}}},
            "runtime": {"environments": {"okx_live": {"armedForCurrentProcess": True}}},
        }
        with patch(
            "alphapilot_control_console.http_app.run_unified_auto_execution_action",
            return_value=automatic,
        ) as action:
            request = Request(
                self.base_url + "/api/live-canary/arm",
                data=json.dumps({"confirmation": "ARM_OKX_LIVE_CANARY", "actor": "user_manual"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["automaticExecution"]["environments"]["okx_live"]["armedForCurrentProcess"])
        action.assert_called_once_with({
            "confirmation": "ARM_OKX_LIVE_CANARY",
            "actor": "user_manual",
            "environment": "okx_live",
            "action": "arm",
        })


if __name__ == "__main__":
    unittest.main()
