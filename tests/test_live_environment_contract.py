from __future__ import annotations

import tempfile
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from alphapilot_control_console.http_app import ConsoleHandler
from alphapilot_control_console.live_environment_contract import (
    build_live_environment_contract,
    run_live_private_read_audit,
)


class FakeReadOnlyLiveClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_account_config(self) -> dict:
        self.calls.append("account_config")
        return {"code": "0", "data": [{"acctLv": "2"}]}

    def get_balance(self, currency: str = "USDT") -> dict:
        self.calls.append(f"balance:{currency}")
        return {"code": "0", "data": [{"totalEq": "1000"}]}

    def get_positions(self, instrumentId: str | None = None) -> dict:
        self.calls.append("positions")
        return {"code": "0", "data": []}

    def get_open_orders(self, instrumentId: str | None = None) -> dict:
        self.calls.append("open_orders")
        return {"code": "0", "data": []}


class LiveEnvironmentContractTests(unittest.TestCase):
    def test_demo_credentials_never_satisfy_live_contract(self) -> None:
        environment = {
            "ALPHAPILOT_OKX_DEMO_API_KEY": "demo-key",
            "ALPHAPILOT_OKX_DEMO_SECRET_KEY": "demo-secret",
            "ALPHAPILOT_OKX_DEMO_PASSPHRASE": "demo-pass",
            "ALPHAPILOT_OKX_LIVE_ENABLED": "1",
            "ALPHAPILOT_OKX_LIVE_READ_ENABLED": "1",
        }
        contract = build_live_environment_contract(environment)
        result = run_live_private_read_audit(environment=environment)

        self.assertEqual(contract["status"], "not_run_live_credentials_absent")
        self.assertFalse(contract["demoCredentialFallbackAllowed"])
        self.assertEqual(result["status"], "not_run")
        self.assertEqual(result["reason"], "live_runtime_credentials_missing")

    def test_read_only_audit_records_only_codes_and_counts(self) -> None:
        environment = {
            "ALPHAPILOT_OKX_LIVE_API_KEY": "live-key",
            "ALPHAPILOT_OKX_LIVE_SECRET_KEY": "live-secret",
            "ALPHAPILOT_OKX_LIVE_PASSPHRASE": "live-pass",
            "ALPHAPILOT_OKX_LIVE_ENABLED": "1",
            "ALPHAPILOT_OKX_LIVE_READ_ENABLED": "1",
        }
        client = FakeReadOnlyLiveClient()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "live_private_read_audit.json"
            result = run_live_private_read_audit(
                environment=environment,
                client=client,
                output_path=output,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["endpointCodes"], {
                "accountConfig": "0",
                "balance": "0",
                "positions": "0",
                "openOrders": "0",
            })
            self.assertEqual(result["positionCount"], 0)
            self.assertEqual(result["openOrderCount"], 0)
            self.assertNotIn("responses", result)
            self.assertNotIn("totalEq", output.read_text(encoding="utf-8"))
            self.assertEqual(
                client.calls,
                ["account_config", "balance:USDT", "positions", "open_orders"],
            )

    def test_read_only_audit_fails_closed_when_order_gate_is_enabled(self) -> None:
        environment = {
            "ALPHAPILOT_OKX_LIVE_API_KEY": "live-key",
            "ALPHAPILOT_OKX_LIVE_SECRET_KEY": "live-secret",
            "ALPHAPILOT_OKX_LIVE_PASSPHRASE": "live-pass",
            "ALPHAPILOT_OKX_LIVE_ENABLED": "1",
            "ALPHAPILOT_OKX_LIVE_READ_ENABLED": "1",
            "ALPHAPILOT_OKX_LIVE_ORDER_ENABLED": "1",
        }
        client = FakeReadOnlyLiveClient()
        result = run_live_private_read_audit(environment=environment, client=client)

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "live_readonly_boundary_not_isolated")
        self.assertEqual(client.calls, [])


class LiveEnvironmentContractHttpTests(unittest.TestCase):
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

    def test_get_exposes_redacted_live_contract_and_audit_status(self) -> None:
        contract = {
            "schemaVersion": "alphapilot_live_environment_contract_v1",
            "status": "not_run_live_credentials_absent",
            "environment": "okx_live",
            "rawCredentialStorageAllowed": False,
            "withdrawAllowed": False,
        }
        audit = {
            "schemaVersion": "alphapilot_live_private_read_audit_v1",
            "status": "not_run",
            "reason": "private_read_audit_not_run",
            "liveOrdersCreated": 0,
        }
        with patch(
            "alphapilot_control_console.http_app.build_live_environment_contract",
            return_value=contract,
            create=True,
        ), patch(
            "alphapilot_control_console.http_app.build_live_private_read_audit_status",
            return_value=audit,
            create=True,
        ):
            with urlopen(self.base_url + "/api/live/environment-contract", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["contract"], contract)
        self.assertEqual(payload["privateReadAudit"], audit)
        serialized = json.dumps(payload).lower()
        self.assertNotIn("apikey", serialized)
        self.assertNotIn("passphrase", serialized)

    def test_private_read_audit_is_loopback_only(self) -> None:
        request = Request(
            self.base_url + "/api/live/private-read-audit",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with patch(
            "alphapilot_control_console.http_app._request_is_loopback",
            return_value=False,
        ):
            with self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=2)

        self.assertEqual(error.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
