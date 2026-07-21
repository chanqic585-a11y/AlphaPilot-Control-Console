from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from unittest.mock import patch

from alphapilot_control_console.http_app import ConsoleHandler


class AdaptiveLearningHttpTests(unittest.TestCase):
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

    def test_status_exposes_only_read_only_adaptive_projection(self) -> None:
        projection = {
            "schemaVersion": "adaptive_learning_runtime_status_v1",
            "status": "observer_ready",
            "modelMode": "observer",
            "featureSnapshotCount": 3,
            "modelDecisionCount": 3,
            "learningSampleCount": 1,
            "altersOrderSemantics": False,
            "createsOrders": False,
            "changesRisk": False,
            "liveDecisionReady": False,
        }
        with patch(
            "alphapilot_control_console.http_app.build_adaptive_learning_status",
            return_value=projection,
            create=True,
        ):
            with urlopen(self.base_url + "/api/adaptive-learning?fresh=1", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(payload, projection)
        serialized = json.dumps(payload).lower()
        self.assertNotIn("apikey", serialized)
        self.assertNotIn("passphrase", serialized)
        self.assertFalse(payload["createsOrders"])
        self.assertFalse(payload["changesRisk"])


if __name__ == "__main__":
    unittest.main()
