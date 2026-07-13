from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import alphapilot_control_console.demo_market_runtime_registry as registry


class FakeRuntime:
    def __init__(self) -> None:
        self.status_calls = 0
        self.listener = None

    def refresh_subscriptions(self, _contracts: list[dict]) -> dict:
        return {"seeded": True, "failures": []}

    def add_close_listener(self, listener: object) -> None:
        self.listener = listener

    def start(self) -> dict:
        return {"running": True}

    def status(self) -> dict:
        self.status_calls += 1
        return {
            "warm": self.status_calls >= 2,
            "blockers": [] if self.status_calls >= 2 else ["websocket_connecting"],
        }

    def stop(self) -> None:
        return None


class DemoMarketRuntimeRegistryTests(unittest.TestCase):
    def test_start_waits_for_warm_public_runtime_before_reporting_ready(self) -> None:
        fake = FakeRuntime()
        listener = lambda _event: None
        with patch.object(registry, "_RUNTIME", fake), patch.object(
            registry, "_LAST_STARTUP", {"started": False}
        ), patch(
            "alphapilot_control_console.evolution_demo_service.discover_demo_contracts",
            return_value=([{"demoReleaseId": "release-1"}], []),
        ), patch.dict(
            os.environ, {"ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED": "1"}, clear=False
        ):
            result = registry.start_demo_market_runtime(
                close_listener=listener,
                warm_timeout_seconds=0.2,
            )

        self.assertTrue(result["started"])
        self.assertTrue(result["runtime"]["warm"])
        self.assertIs(fake.listener, listener)


if __name__ == "__main__":
    unittest.main()
