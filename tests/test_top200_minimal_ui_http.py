from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import Mock, patch

from alphapilot_control_console.http_app import ConsoleHandler


class Top200MinimalUiHttpTests(unittest.TestCase):
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

    def _get(self, path: str) -> dict:
        with urlopen(self.base_url + path, timeout=2) as response:
            self.assertEqual(response.status, 200)
            return json.loads(response.read().decode("utf-8"))

    def test_exposes_all_minimal_read_only_routes(self) -> None:
        service = Mock()
        service.RESEARCH_RUN_ID = "run-1"
        methods = {
            "research_factory_summary": {"kind": "research-summary"},
            "research_factory_runs": {"kind": "research-runs"},
            "research_factory_run": {"kind": "research-run"},
            "strategy_summary": {"kind": "strategy-summary"},
            "strategy_releases": {"kind": "strategy-releases"},
            "strategy_release": {"kind": "strategy-release"},
            "forward_validation": {"kind": "forward-validation"},
            "demo_summary": {"kind": "demo-summary"},
            "demo_strategies": {"kind": "demo-strategies"},
            "demo_positions": {"kind": "demo-positions"},
            "demo_orders": {"kind": "demo-orders"},
            "demo_universe": {"kind": "demo-universe"},
            "demo_reconciliation": {"kind": "demo-reconciliation"},
        }
        for name, payload in methods.items():
            getattr(service, name).return_value = payload

        routes = {
            "/api/research-factory/summary": "research-summary",
            "/api/research-factory/runs": "research-runs",
            "/api/research-factory/runs/run-1": "research-run",
            "/api/strategy/summary": "strategy-summary",
            "/api/strategy/releases": "strategy-releases",
            "/api/strategy/releases/release-1": "strategy-release",
            "/api/strategy/releases/release-1/forward-validation": "forward-validation",
            "/api/demo/summary": "demo-summary",
            "/api/demo/strategies": "demo-strategies",
            "/api/demo/positions": "demo-positions",
            "/api/demo/orders": "demo-orders",
            "/api/demo/universe": "demo-universe",
            "/api/demo/reconciliation": "demo-reconciliation",
        }
        with patch(
            "alphapilot_control_console.http_app.build_top200_minimal_ui_projection",
            return_value=service,
        ):
            for path, expected_kind in routes.items():
                with self.subTest(path=path):
                    self.assertEqual(self._get(path)["kind"], expected_kind)

        service.research_factory_run.assert_called_once_with("run-1")
        service.strategy_release.assert_called_once_with("release-1")
        service.forward_validation.assert_called_once_with("release-1")

    def test_missing_projection_evidence_returns_503_without_sensitive_data(self) -> None:
        with patch(
            "alphapilot_control_console.http_app.build_top200_minimal_ui_projection",
            side_effect=RuntimeError("missing projection evidence"),
        ):
            with self.assertRaises(HTTPError) as raised:
                self._get("/api/demo/summary")

        self.assertEqual(raised.exception.code, 503)
        payload = json.loads(raised.exception.read().decode("utf-8"))
        self.assertEqual(payload["error"], "top200_projection_unavailable")
        serialized = json.dumps(payload).lower()
        self.assertNotIn("apikey", serialized)
        self.assertNotIn("passphrase", serialized)


if __name__ == "__main__":
    unittest.main()
