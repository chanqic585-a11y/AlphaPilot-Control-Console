from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from alphapilot_control_console.http_app import ConsoleHandler
from alphapilot_control_console.local_simulation_retirement import (
    RETIRED_LOCAL_SIMULATION_POST_ROUTES,
)


class LocalSimulationRetirementHttpTests(unittest.TestCase):
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

    def post(self, path: str) -> dict:
        request = Request(
            self.base_url + path,
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=2)
        self.assertEqual(raised.exception.code, 410)
        return json.loads(raised.exception.read().decode("utf-8"))

    def test_every_legacy_write_route_returns_exact_retired_response(self) -> None:
        expected = {
            "status": "retired",
            "code": "local_simulation_retired",
            "historicalDataPreserved": True,
            "nextAction": "Use formal backtest and OKX Demo validation.",
        }
        self.assertGreaterEqual(len(RETIRED_LOCAL_SIMULATION_POST_ROUTES), 7)

        for path in sorted(RETIRED_LOCAL_SIMULATION_POST_ROUTES):
            with self.subTest(path=path):
                self.assertEqual(self.post(path), expected)

    def test_historical_reads_are_explicitly_read_only(self) -> None:
        with urlopen(self.base_url + "/api/local-sandbox/runs?limit=1", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["deprecated"])
        self.assertTrue(payload["readOnly"])
        self.assertEqual(payload["evidenceSource"], "legacy_local_observation")
        self.assertIn("runs", payload)


if __name__ == "__main__":
    unittest.main()
