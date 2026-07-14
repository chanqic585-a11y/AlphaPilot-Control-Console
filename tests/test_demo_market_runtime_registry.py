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


class RetryRuntime(FakeRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.refresh_calls = 0

    def refresh_subscriptions(self, _contracts: list[dict]) -> dict:
        self.refresh_calls += 1
        if self.refresh_calls == 1:
            return {"seeded": False, "failures": ["metadata:ETH-USDT-SWAP"]}
        return {"seeded": True, "failures": []}


class WarmingRuntime(FakeRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.stop_calls = 0

    def status(self) -> dict:
        self.status_calls += 1
        return {
            "running": True,
            "warm": False,
            "blockers": ["websocket_connecting"],
        }

    def stop(self) -> None:
        self.stop_calls += 1


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

    def test_start_retries_transient_public_seed_failures(self) -> None:
        fake = RetryRuntime()
        with patch.object(registry, "_RUNTIME", fake), patch.object(
            registry, "_LAST_STARTUP", {"started": False}
        ), patch(
            "alphapilot_control_console.evolution_demo_service.discover_demo_contracts",
            return_value=([{"demoReleaseId": "release-1"}], []),
        ), patch.dict(
            os.environ, {"ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED": "1"}, clear=False
        ):
            result = registry.start_demo_market_runtime(
                seed_attempts=2,
                seed_retry_delay_seconds=0,
                warm_timeout_seconds=0.2,
            )

        self.assertTrue(result["started"])
        self.assertEqual(result["seedAttemptCount"], 2)
        self.assertEqual(fake.refresh_calls, 2)

    def test_warm_timeout_keeps_public_runtime_alive_for_background_recovery(self) -> None:
        fake = WarmingRuntime()
        with patch.object(registry, "_RUNTIME", fake), patch.object(
            registry, "_LAST_STARTUP", {"started": False}
        ), patch(
            "alphapilot_control_console.evolution_demo_service.discover_demo_contracts",
            return_value=([{"demoReleaseId": "release-1"}], []),
        ), patch.dict(
            os.environ, {"ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED": "1"}, clear=False
        ):
            result = registry.start_demo_market_runtime(warm_timeout_seconds=0)

        self.assertFalse(result["started"])
        self.assertEqual(result["blockers"], ["demo_market_runtime_warming"])
        self.assertEqual(fake.stop_calls, 0)
        self.assertTrue(result["runtime"]["running"])


if __name__ == "__main__":
    unittest.main()
