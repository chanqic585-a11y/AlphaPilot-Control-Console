from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import patch

from alphapilot_control_console.http_app import ConsoleHandler


class DemoInstrumentUniverseHttpTests(unittest.TestCase):
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

    def test_returns_compact_usable_projection(self) -> None:
        projection = {
            "status": "usable",
            "environment": "demo",
            "publicUniverseCount": 100,
            "demoAccountInstrumentCount": 405,
            "intersectionCount": 95,
            "liquidityEligibleCount": 95,
            "cacheAgeSeconds": 2,
            "stale": False,
            "includedSample": ["BTC-USDT-SWAP"],
            "excludedSample": [],
            "blockers": [],
        }
        with patch(
            "alphapilot_control_console.http_app._build_demo_instrument_universe_status",
            return_value=projection,
            create=True,
        ) as build:
            with urlopen(self.base_url + "/api/demo-instrument-universe?fresh=1", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload, projection)
        self.assertEqual(response.status, 200)
        build.assert_called_once_with(fresh=True)
        serialized = json.dumps(payload).lower()
        self.assertNotIn("apikey", serialized)
        self.assertNotIn("passphrase", serialized)

    def test_returns_503_for_blocked_authenticated_universe(self) -> None:
        with patch(
            "alphapilot_control_console.http_app._build_demo_instrument_universe_status",
            return_value={
                "status": "blocked",
                "environment": "demo",
                "eligibleInstrumentIds": [],
                "blockers": ["demo_account_instruments_unavailable"],
            },
            create=True,
        ):
            with self.assertRaises(HTTPError) as raised:
                urlopen(self.base_url + "/api/demo-instrument-universe?fresh=1", timeout=2)

        self.assertEqual(raised.exception.code, 503)
        payload = json.loads(raised.exception.read().decode("utf-8"))
        self.assertEqual(payload["status"], "blocked")

    def test_rejects_non_loopback_clients(self) -> None:
        with patch(
            "alphapilot_control_console.http_app._request_is_loopback",
            return_value=False,
        ):
            with self.assertRaises(HTTPError) as raised:
                urlopen(self.base_url + "/api/demo-instrument-universe", timeout=2)

        self.assertEqual(raised.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
