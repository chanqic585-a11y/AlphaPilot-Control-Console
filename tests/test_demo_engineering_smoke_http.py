from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import MagicMock, patch

from alphapilot_control_console.http_app import ConsoleHandler


class DemoEngineeringSmokeHttpTests(unittest.TestCase):
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

    def post(self, path: str, payload: dict | None = None):
        request = Request(
            self.base_url + path,
            data=json.dumps(payload or {}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return urlopen(request, timeout=2)

    def test_status_is_compact_and_non_qualifying(self) -> None:
        projection = {
            "status": "usable",
            "evidenceClass": "demo_engineering_smoke",
            "strategyQualification": False,
            "promotionEligible": False,
            "summary": {"runCount": 1, "orphanCount": 0},
            "runs": [],
        }
        with patch(
            "alphapilot_control_console.http_app.build_demo_engineering_smoke_status",
            return_value=projection,
            create=True,
        ):
            with urlopen(self.base_url + "/api/demo-engineering-smoke", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(payload, projection)
        serialized = json.dumps(payload).lower()
        self.assertNotIn("apikey", serialized)
        self.assertNotIn("passphrase", serialized)

    def test_explicit_run_uses_process_credentials_contract_and_usable_universe(self) -> None:
        credentials = MagicMock()
        client = MagicMock()
        contract = {"releaseId": "demo-engineering-smoke-contract"}
        universe = {
            "status": "usable",
            "environment": "demo",
            "eligibleInstrumentIds": ["BTC-USDT-SWAP"],
        }
        result = {"status": "completed", "orderAttemptCount": 1, "positionStatus": "flat"}
        with (
            patch("alphapilot_control_console.http_app.load_okx_demo_credentials", return_value=credentials),
            patch("alphapilot_control_console.http_app.OkxDemoClient", return_value=client),
            patch("alphapilot_control_console.http_app._load_demo_engineering_smoke_contract", return_value=contract, create=True),
            patch("alphapilot_control_console.http_app._build_demo_instrument_universe_status", return_value=universe),
            patch("alphapilot_control_console.http_app.run_demo_engineering_smoke", return_value=result, create=True) as run,
        ):
            with self.post(
                "/api/demo-engineering-smoke/run",
                {"confirmation": "RUN_DEMO_ENGINEERING_SMOKE"},
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["engineeringSmoke"], result)
        run.assert_called_once_with(
            client=client,
            contract=contract,
            universe=universe,
            deterministicTrigger=True,
        )

    def test_run_rejects_concurrent_request(self) -> None:
        lock = MagicMock()
        lock.acquire.return_value = False
        with patch("alphapilot_control_console.http_app._DEMO_ENGINEERING_SMOKE_LOCK", lock, create=True):
            with self.assertRaises(HTTPError) as raised:
                self.post(
                    "/api/demo-engineering-smoke/run",
                    {"confirmation": "RUN_DEMO_ENGINEERING_SMOKE"},
                )
        self.assertEqual(raised.exception.code, 409)
        self.assertEqual(json.loads(raised.exception.read().decode("utf-8"))["error"], "engineering_smoke_already_running")

    def test_reconcile_is_explicit_and_uses_demo_client(self) -> None:
        credentials = MagicMock()
        client = MagicMock()
        universe = {"status": "usable", "environment": "demo", "eligibleInstrumentIds": ["BTC-USDT-SWAP"]}
        result = {"status": "usable", "summary": {"orphanCount": 0}}
        with (
            patch("alphapilot_control_console.http_app.load_okx_demo_credentials", return_value=credentials),
            patch("alphapilot_control_console.http_app.OkxDemoClient", return_value=client),
            patch("alphapilot_control_console.http_app._build_demo_instrument_universe_status", return_value=universe),
            patch("alphapilot_control_console.http_app.reconcile_demo_engineering_smoke", return_value=result, create=True) as reconcile,
        ):
            with self.post(
                "/api/demo-engineering-smoke/reconcile",
                {"confirmation": "RECONCILE_DEMO_ENGINEERING_SMOKE"},
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])
        reconcile.assert_called_once_with(client=client)

    def test_post_fails_closed_for_blocked_universe(self) -> None:
        with (
            patch("alphapilot_control_console.http_app.load_okx_demo_credentials", return_value=MagicMock()),
            patch("alphapilot_control_console.http_app._build_demo_instrument_universe_status", return_value={
                "status": "blocked",
                "environment": "demo",
                "eligibleInstrumentIds": [],
                "blockers": ["demo_account_instruments_unavailable"],
            }),
        ):
            with self.assertRaises(HTTPError) as raised:
                self.post(
                    "/api/demo-engineering-smoke/run",
                    {"confirmation": "RUN_DEMO_ENGINEERING_SMOKE"},
                )
        self.assertEqual(raised.exception.code, 409)
        self.assertEqual(json.loads(raised.exception.read().decode("utf-8"))["error"], "demo_instrument_universe_blocked")

    def test_post_fails_closed_for_missing_process_credentials(self) -> None:
        with patch(
            "alphapilot_control_console.http_app.load_okx_demo_credentials",
            side_effect=RuntimeError("missing"),
        ):
            with self.assertRaises(HTTPError) as raised:
                self.post(
                    "/api/demo-engineering-smoke/run",
                    {"confirmation": "RUN_DEMO_ENGINEERING_SMOKE"},
                )
        self.assertEqual(raised.exception.code, 409)
        self.assertEqual(json.loads(raised.exception.read().decode("utf-8"))["error"], "okx_demo_credentials_missing")

    def test_post_rejects_non_loopback_clients(self) -> None:
        with patch("alphapilot_control_console.http_app._request_is_loopback", return_value=False):
            with self.assertRaises(HTTPError) as raised:
                self.post(
                    "/api/demo-engineering-smoke/reconcile",
                    {"confirmation": "RECONCILE_DEMO_ENGINEERING_SMOKE"},
                )
        self.assertEqual(raised.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
