from __future__ import annotations

import unittest
from unittest.mock import patch

from alphapilot_control_console.unified_auto_execution_adapters import (
    OkxDemoAutoExecutionAdapter,
)


class UnifiedAutoExecutionAdapterTests(unittest.TestCase):
    def test_demo_adapter_lists_only_frozen_release_schedules(self) -> None:
        contracts = [
            {
                "demoReleaseId": "release-1",
                "strategyCandidateId": "strategy-1",
                "strategy": {"marketDefinition": {"timeframe": "1h"}},
            },
            {
                "demoReleaseId": "release-2",
                "strategyCandidateId": "strategy-2",
                "strategy": {"marketDefinition": {}},
            },
        ]
        with patch(
            "alphapilot_control_console.unified_auto_execution_adapters.discover_demo_contracts",
            return_value=(contracts, []),
        ):
            schedules = OkxDemoAutoExecutionAdapter().list_releases()

        self.assertEqual(len(schedules), 1)
        self.assertEqual(schedules[0].releaseId, "release-1")
        self.assertEqual(schedules[0].timeframe, "1h")

    def test_demo_preflight_requires_both_runtime_and_readonly_success(self) -> None:
        with patch(
            "alphapilot_control_console.unified_auto_execution_adapters.build_evolution_demo_status",
            return_value={"summary": {"ready": True}, "blockers": []},
        ), patch(
            "alphapilot_control_console.unified_auto_execution_adapters.build_exchange_demo_simulation",
            return_value={"readonlySummary": {"status": "not_run"}},
        ):
            blocked = OkxDemoAutoExecutionAdapter().preflight()

        self.assertFalse(blocked["ok"])
        self.assertIn("okx_demo_readonly_preflight_required", blocked["blockers"])

        with patch(
            "alphapilot_control_console.unified_auto_execution_adapters.build_evolution_demo_status",
            return_value={"summary": {"ready": True}, "blockers": []},
        ), patch(
            "alphapilot_control_console.unified_auto_execution_adapters.build_exchange_demo_simulation",
            return_value={"readonlySummary": {"status": "passed"}},
        ):
            ready = OkxDemoAutoExecutionAdapter().preflight()

        self.assertTrue(ready["ok"])

    def test_demo_adapter_routes_batch_reconciliation_pause_and_stop(self) -> None:
        adapter = OkxDemoAutoExecutionAdapter()
        releases = [
            type("Release", (), {"releaseId": "release-1"})(),
            type("Release", (), {"releaseId": "release-2"})(),
        ]
        with patch(
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
            self.assertTrue(adapter.run_batch(releases, {})["ok"])
            self.assertTrue(adapter.reconcile()["ok"])
            adapter.pause("unit_test")
            self.assertTrue(adapter.emergency_stop("emergency")["ok"])

        batch.assert_called_once_with(["release-1", "release-2"])
        reconcile.assert_called_once_with()
        pause.assert_called_once_with("unit_test")
        stop.assert_called_once_with("emergency")


if __name__ == "__main__":
    unittest.main()
