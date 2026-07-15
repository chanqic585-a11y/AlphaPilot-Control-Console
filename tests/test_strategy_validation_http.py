from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from alphapilot_control_console.http_app import ConsoleHandler


class StrategyValidationHttpTests(unittest.TestCase):
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

    def post(self, path: str, payload: dict):
        return urlopen(
            Request(
                self.base_url + path,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            ),
            timeout=2,
        )

    def test_read_only_backtest_projection_requires_campaign_id(self) -> None:
        expected = {"campaignId": "campaign-1", "formalPassCount": 0, "readOnly": True}
        with patch(
            "alphapilot_control_console.http_app.build_backtest_screening_projection",
            return_value=expected,
            create=True,
        ) as build:
            with urlopen(self.base_url + "/api/backtest-screening?campaignId=campaign-1", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(payload, expected)
        build.assert_called_once_with("campaign-1")

        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base_url + "/api/backtest-screening", timeout=2)
        self.assertEqual(raised.exception.code, 400)

    def test_approval_route_is_loopback_hash_bound_and_does_not_arm(self) -> None:
        expected = {"approved": True, "runtimeArmed": False}
        with patch(
            "alphapilot_control_console.http_app.run_strategy_validation_approval_action",
            return_value=expected,
            create=True,
        ) as approve:
            with self.post(
                "/api/strategy-validation-releases/approve",
                {
                    "releaseId": "release-1",
                    "releaseHash": "release-hash",
                    "riskConfigHash": "risk-hash",
                    "reason": "reviewed",
                },
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(payload, expected)
        self.assertFalse(payload["runtimeArmed"])
        approve.assert_called_once()

    def test_browser_credentials_are_rejected(self) -> None:
        with self.assertRaises(HTTPError) as raised:
            self.post(
                "/api/strategy-validation-releases/approve",
                {
                    "releaseId": "release-1",
                    "releaseHash": "release-hash",
                    "riskConfigHash": "risk-hash",
                    "reason": "reviewed",
                    "apiKey": "forbidden",
                },
            )
        self.assertEqual(raised.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
