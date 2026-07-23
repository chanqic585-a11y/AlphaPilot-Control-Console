from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from unittest.mock import patch

from alphapilot_control_console.http_app import ConsoleHandler


class AIControlHttpTests(unittest.TestCase):
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

    def test_ai_control_route_is_read_only_and_redacted(self) -> None:
        projection = {
            "schemaVersion": "alphapilot_ai_control_projection_v1",
            "status": "provider_credentials_required",
            "providerHealth": {
                "deepseek": "credentials_missing",
                "gemini": "credentials_missing",
            },
            "models": [],
            "budget": {},
            "routing": {},
            "credentialsPersisted": False,
            "exchangeCredentialsAvailableToWorker": False,
            "executionAuthorized": False,
        }
        with patch(
            "alphapilot_control_console.http_app.build_ai_control_projection",
            return_value=projection,
        ) as build:
            with urlopen(self.base_url + "/api/ai/control?fresh=1", timeout=2) as response:
                self.assertEqual(response.status, 200)
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload, projection)
        self.assertFalse(payload["credentialsPersisted"])
        self.assertFalse(payload["exchangeCredentialsAvailableToWorker"])
        self.assertFalse(payload["executionAuthorized"])
        self.assertNotIn("apiKey", json.dumps(payload))
        build.assert_called_once()


if __name__ == "__main__":
    unittest.main()
