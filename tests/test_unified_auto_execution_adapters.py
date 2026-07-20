from __future__ import annotations

import unittest
from unittest.mock import patch

from alphapilot_control_console.unified_auto_execution_adapters import (
    OkxDemoAutoExecutionAdapter,
    OkxLiveAutoExecutionAdapter,
)


class UnifiedAutoExecutionAdapterTests(unittest.TestCase):
    def test_demo_adapter_lists_only_frozen_release_schedules(self) -> None:
        runtime = {
            "approved": True,
            "schedules": [
                {
                    "releaseId": "release-1",
                    "strategyId": "portfolio:1h",
                    "timeframe": "1h",
                },
                {
                    "releaseId": "release-1",
                    "strategyId": "portfolio:invalid",
                    "timeframe": "invalid",
                },
            ],
        }
        with patch(
            "alphapilot_control_console.unified_auto_execution_adapters.load_approved_top200_demo_runtime",
            return_value=runtime,
        ):
            schedules = OkxDemoAutoExecutionAdapter().list_releases()

        self.assertEqual(len(schedules), 1)
        self.assertEqual(schedules[0].releaseId, "release-1")
        self.assertEqual(schedules[0].timeframe, "1h")

    def test_demo_preflight_requires_both_runtime_and_readonly_success(self) -> None:
        with patch(
            "alphapilot_control_console.unified_auto_execution_adapters.load_approved_top200_demo_runtime",
            return_value={"blockers": [], "componentContracts": []},
        ), patch(
            "alphapilot_control_console.unified_auto_execution_adapters.build_evolution_demo_status",
            return_value={"summary": {"ready": True}, "blockers": []},
        ), patch(
            "alphapilot_control_console.unified_auto_execution_adapters.build_exchange_demo_simulation",
            return_value={"readonlySummary": {"status": "not_run"}},
        ), patch(
            "alphapilot_control_console.unified_auto_execution_adapters.get_demo_market_runtime_status",
            return_value={"runtime": {"warm": True}},
        ):
            blocked = OkxDemoAutoExecutionAdapter().preflight()

        self.assertFalse(blocked["ok"])
        self.assertIn("okx_demo_readonly_preflight_required", blocked["blockers"])

        with patch(
            "alphapilot_control_console.unified_auto_execution_adapters.load_approved_top200_demo_runtime",
            return_value={"blockers": [], "componentContracts": []},
        ), patch(
            "alphapilot_control_console.unified_auto_execution_adapters.build_evolution_demo_status",
            return_value={"summary": {"ready": True}, "blockers": []},
        ), patch(
            "alphapilot_control_console.unified_auto_execution_adapters.build_exchange_demo_simulation",
            return_value={"readonlySummary": {"status": "passed"}},
        ), patch(
            "alphapilot_control_console.unified_auto_execution_adapters.get_demo_market_runtime_status",
            return_value={"runtime": {"warm": True}},
        ):
            ready = OkxDemoAutoExecutionAdapter().preflight()

        self.assertTrue(ready["ok"])

    def test_demo_preflight_fails_closed_when_public_market_runtime_is_not_warm(self) -> None:
        with patch(
            "alphapilot_control_console.unified_auto_execution_adapters.load_approved_top200_demo_runtime",
            return_value={"blockers": [], "componentContracts": []},
        ), patch(
            "alphapilot_control_console.unified_auto_execution_adapters.build_evolution_demo_status",
            return_value={"summary": {"ready": True}, "blockers": []},
        ), patch(
            "alphapilot_control_console.unified_auto_execution_adapters.build_exchange_demo_simulation",
            return_value={"readonlySummary": {"status": "passed"}},
        ), patch(
            "alphapilot_control_console.unified_auto_execution_adapters.get_demo_market_runtime_status",
            return_value={"runtime": {"warm": False, "blockers": ["websocket_disconnected"]}},
        ):
            blocked = OkxDemoAutoExecutionAdapter().preflight()

        self.assertFalse(blocked["ok"])
        self.assertIn("demo_market_runtime_not_warm", blocked["blockers"])

    def test_demo_adapter_routes_batch_reconciliation_pause_and_stop(self) -> None:
        adapter = OkxDemoAutoExecutionAdapter()
        releases = [
            type("Release", (), {"releaseId": "release-1"})(),
            type("Release", (), {"releaseId": "release-2"})(),
        ]
        with patch(
            "alphapilot_control_console.unified_auto_execution_adapters.load_approved_top200_demo_runtime",
            return_value={
                "executionEnabled": True,
                "blockers": [],
                "componentContracts": [
                    {
                        "strategyCandidateId": "strategy-1",
                        "strategy": {"marketDefinition": {"timeframe": "1h"}},
                    }
                ],
            },
        ), patch(
            "alphapilot_control_console.unified_auto_execution_adapters.run_evolution_demo_batch_cycle",
            return_value={"ok": True},
        ) as batch, patch(
            "alphapilot_control_console.unified_auto_execution_adapters.reconcile_evolution_demo_runtime",
            return_value={"ok": True},
        ) as reconcile, patch(
            "alphapilot_control_console.unified_auto_execution_adapters.pause_evolution_demo_runtime",
        ) as pause, patch(
            "alphapilot_control_console.unified_auto_execution_adapters.activate_evolution_demo_kill_switch",
            return_value={"ok": True},
        ) as stop:
            close_event = {"timeframe": "1h"}
            self.assertTrue(adapter.run_batch(releases, {}, close_event=close_event)["ok"])
            self.assertTrue(adapter.reconcile()["ok"])
            adapter.pause("unit_test")
            self.assertTrue(adapter.emergency_stop("emergency")["ok"])

        batch.assert_called_once_with(
            ["release-1", "release-2"],
            close_event={"timeframe": "1h"},
            contracts_override=[
                {
                    "strategyCandidateId": "strategy-1",
                    "strategy": {"marketDefinition": {"timeframe": "1h"}},
                }
            ],
        )
        reconcile.assert_called_once_with(
            contracts_override=[
                {
                    "strategyCandidateId": "strategy-1",
                    "strategy": {"marketDefinition": {"timeframe": "1h"}},
                }
            ]
        )
        pause.assert_called_once_with("unit_test")
        stop.assert_called_once_with("emergency")

    def test_live_adapter_requires_automation_ready_status(self) -> None:
        with patch(
            "alphapilot_control_console.unified_auto_execution_adapters.build_live_canary_status",
            return_value={"summary": {"canaryOrderReady": True}, "runtimeGates": {"automationEnabled": False}, "blockers": []},
        ):
            blocked = OkxLiveAutoExecutionAdapter().preflight()

        self.assertFalse(blocked["ok"])
        self.assertIn("live_automation_gate_disabled", blocked["blockers"])

    def test_live_adapter_routes_batch_reconciliation_pause_and_stop(self) -> None:
        adapter = OkxLiveAutoExecutionAdapter()
        releases = [type("Release", (), {"releaseId": "live-release-1"})()]
        with patch(
            "alphapilot_control_console.unified_auto_execution_adapters.run_live_auto_execution_batch",
            return_value={"ok": True},
        ) as batch, patch(
            "alphapilot_control_console.unified_auto_execution_adapters.reconcile_live_auto_execution_runtime",
            return_value={"ok": True},
        ) as reconcile, patch(
            "alphapilot_control_console.unified_auto_execution_adapters.pause_live_auto_execution_runtime",
        ) as pause, patch(
            "alphapilot_control_console.unified_auto_execution_adapters.activate_live_canary_kill_switch",
            return_value={"ok": True},
        ) as stop:
            self.assertTrue(adapter.run_batch(releases, {})["ok"])
            self.assertTrue(adapter.reconcile()["ok"])
            adapter.pause("unit_test")
            self.assertTrue(adapter.emergency_stop("emergency")["ok"])

        batch.assert_called_once_with(["live-release-1"])
        reconcile.assert_called_once_with()
        pause.assert_called_once_with("unit_test")
        stop.assert_called_once_with({"reason": "emergency"})


if __name__ == "__main__":
    unittest.main()
