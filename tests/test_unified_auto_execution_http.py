from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from alphapilot_control_console.http_app import ConsoleHandler
from tests.http_write_test_client import secure_json_request


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
            request = secure_json_request(
                self.base_url,
                "/api/auto-execution/action",
                {"environment": "okx_demo", "action": "start"},
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
            request = secure_json_request(
                self.base_url,
                "/api/live-canary/arm",
                {"confirmation": "ARM_OKX_LIVE_CANARY", "actor": "user_manual"},
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

    def test_demo_vault_status_returns_redacted_metadata_for_loopback_only(self) -> None:
        metadata = {
            "supported": True,
            "stored": True,
            "status": "stored",
            "targetLabel": "AlphaPilot OKX Demo",
            "persistence": "local_machine",
        }
        with patch(
            "alphapilot_control_console.http_app.DEMO_CREDENTIAL_VAULT.metadata",
            return_value=metadata,
        ):
            with urlopen(
                self.base_url + "/api/local-control/okx-demo-credential-vault",
                timeout=2,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload, metadata)
        self.assertNotIn("apiKey", json.dumps(payload))
        self.assertNotIn("secretKey", json.dumps(payload))
        self.assertNotIn("passphrase", json.dumps(payload))

    def test_demo_vault_status_rejects_non_loopback_client(self) -> None:
        with patch(
            "alphapilot_control_console.http_app._request_is_loopback",
            return_value=False,
        ):
            with self.assertRaises(HTTPError) as raised:
                urlopen(
                    self.base_url + "/api/local-control/okx-demo-credential-vault",
                    timeout=2,
                )

        self.assertEqual(raised.exception.code, 403)

    def test_demo_vault_delete_requires_exact_confirmation_and_audits_metadata_only(self) -> None:
        audit_events: list[tuple[str, dict[str, object]]] = []
        with patch(
            "alphapilot_control_console.http_app.DEMO_CREDENTIAL_VAULT.delete",
            return_value=True,
        ) as delete, patch(
            "alphapilot_control_console.http_app.DEMO_CREDENTIAL_VAULT.metadata",
            return_value={
                "supported": True,
                "stored": False,
                "status": "missing",
                "targetLabel": "AlphaPilot OKX Demo",
                "persistence": "local_machine",
            },
        ), patch(
            "alphapilot_control_console.http_app.append_audit",
            side_effect=lambda event, payload: audit_events.append((event, payload)) or {},
        ):
            rejected = secure_json_request(
                self.base_url,
                "/api/local-control/delete-okx-demo-credential-vault",
                {"confirmation": "wrong"},
            )
            with self.assertRaises(HTTPError) as raised:
                urlopen(rejected, timeout=2)
            accepted = secure_json_request(
                self.base_url,
                "/api/local-control/delete-okx-demo-credential-vault",
                {"confirmation": "DELETE_OKX_DEMO_CREDENTIAL"},
            )
            with urlopen(accepted, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(raised.exception.code, 409)
        delete.assert_called_once_with()
        self.assertEqual(payload["status"], "deleted")
        self.assertFalse(payload["metadata"]["stored"])
        deleted_events = [payload for event, payload in audit_events if event == "demo_vault_deleted"]
        self.assertEqual(len(deleted_events), 1)
        self.assertNotIn("credential", json.dumps(deleted_events[0]).lower())

    def test_demo_vault_delete_rejects_non_loopback_client(self) -> None:
        request = Request(
            self.base_url + "/api/local-control/delete-okx-demo-credential-vault",
            data=json.dumps({"confirmation": "DELETE_OKX_DEMO_CREDENTIAL"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with patch(
            "alphapilot_control_console.http_app._request_is_loopback",
            return_value=False,
        ), self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=2)

        self.assertEqual(raised.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
