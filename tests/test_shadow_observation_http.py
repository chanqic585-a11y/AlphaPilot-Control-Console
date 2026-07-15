from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen
from unittest.mock import patch

from alphapilot_control_console.http_app import ConsoleHandler
from alphapilot_control_console.shadow_observation_store import ShadowObservationStore


def _observation(index: int, release_id: str = "release-1") -> dict:
    return {
        "releaseId": release_id,
        "strategyId": "strategy-1",
        "strategyFamilyId": "family-1",
        "timestamp": f"2026-07-15T00:00:{index:02d}+00:00",
        "symbol": f"COIN{index}-USDT-SWAP",
        "direction": "long",
        "timeframe": "1h",
        "signalMatched": index % 2 == 0,
        "passOrReject": "pass" if index % 2 == 0 else "reject",
        "reasonZh": "冻结规则匹配" if index % 2 == 0 else "冻结规则未匹配",
        "featureSnapshot": {"rsi14": 50 + index},
        "marketRegime": "neutral",
        "publicUniverseIncluded": True,
        "demoUniverseIncluded": index % 2 == 0,
        "liquidityPassed": True,
        "dataQualityPassed": True,
        "riskGatePassed": None,
        "wouldAttemptDemoOrder": index % 2 == 0,
        "sourceDataHashes": {
            "definitionHash": "definition-hash",
            "sourceEventHash": f"event-{index}",
        },
    }


class ShadowObservationHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "shadow.sqlite"
        self.patch = patch(
            "alphapilot_control_console.http_app.DEFAULT_SHADOW_PATH",
            self.path,
            create=True,
        )
        self.patch.start()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ConsoleHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.patch.stop()
        self.temp.cleanup()

    def get(self, suffix: str = "") -> dict:
        with urlopen(self.base_url + "/api/shadow-observation" + suffix, timeout=2) as response:
            self.assertEqual(response.status, 200)
            return json.loads(response.read().decode("utf-8"))

    def test_empty_state_and_forbidden_performance_fields(self) -> None:
        payload = self.get()

        self.assertEqual(payload["summary"]["observationCount"], 0)
        self.assertEqual(payload["rows"], [])
        serialized = json.dumps(payload, ensure_ascii=False).lower()
        for fragment in ("pnl", "profit", "loss", "mfe", "mae", "equity", "position"):
            self.assertNotIn(fragment, serialized)

    def test_filters_release_and_bounds_limit(self) -> None:
        store = ShadowObservationStore(self.path)
        try:
            for index in range(4):
                store.append(_observation(index, "release-1" if index < 3 else "release-2"))
        finally:
            store.close()

        payload = self.get("?releaseId=release-1&limit=2")

        self.assertEqual(payload["summary"]["observationCount"], 3)
        self.assertEqual(len(payload["rows"]), 2)
        self.assertTrue(all(row["releaseId"] == "release-1" for row in payload["rows"]))


if __name__ == "__main__":
    unittest.main()
