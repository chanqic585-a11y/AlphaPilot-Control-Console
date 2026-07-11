from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from alphapilot_control_console.unified_auto_execution_controller import (
    ReleaseSchedule,
    UnifiedAutoExecutionController,
)
from alphapilot_control_console.unified_auto_execution_store import (
    UnifiedAutoExecutionStore,
)


NOW = datetime(2026, 7, 12, 10, 37, tzinfo=UTC)


class FakeAdapter:
    def __init__(self, environment: str, releases: list[ReleaseSchedule]):
        self.environment = environment
        self.releases = releases
        self.preflight_result = {"ok": True, "blockers": []}
        self.reconciliation_result = {"ok": True, "blockers": []}
        self.batch_result = {"ok": True, "createdOrderCount": 0, "matchedSignalCount": 0}
        self.batch_calls: list[list[str]] = []
        self.pause_reasons: list[str] = []
        self.emergency_reasons: list[str] = []

    def preflight(self) -> dict:
        return dict(self.preflight_result)

    def reconcile(self) -> dict:
        return dict(self.reconciliation_result)

    def list_releases(self) -> list[ReleaseSchedule]:
        return list(self.releases)

    def run_batch(self, releases: list[ReleaseSchedule], candle_keys: dict[str, str]) -> dict:
        self.batch_calls.append([release.releaseId for release in releases])
        return {**self.batch_result, "candleKeys": dict(candle_keys)}

    def pause(self, reason: str) -> None:
        self.pause_reasons.append(reason)

    def emergency_stop(self, reason: str) -> dict:
        self.emergency_reasons.append(reason)
        return {"ok": True, "reason": reason}


class UnifiedAutoExecutionControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store = UnifiedAutoExecutionStore(Path(self.directory.name) / "runtime.sqlite")
        self.demo = FakeAdapter(
            "okx_demo",
            [ReleaseSchedule("release-1", "strategy-1", "1h")],
        )
        self.live = FakeAdapter(
            "okx_live",
            [ReleaseSchedule("live-1", "strategy-live", "1h")],
        )
        self.controller = UnifiedAutoExecutionController(
            store=self.store,
            adapters={"okx_demo": self.demo, "okx_live": self.live},
            process_id="process-1",
        )

    def tearDown(self) -> None:
        self.store.close()
        self.directory.cleanup()

    def _start_and_arm(self, environment: str) -> None:
        self.controller.start(environment)
        self.controller.arm(environment)

    def test_heartbeat_runs_each_release_only_once_per_closed_candle(self) -> None:
        self._start_and_arm("okx_demo")

        first = self.controller.heartbeat("okx_demo", now=NOW)
        second = self.controller.heartbeat("okx_demo", now=NOW)

        self.assertEqual(first["evaluatedReleaseCount"], 1)
        self.assertEqual(first["status"], "running")
        self.assertEqual(second["evaluatedReleaseCount"], 0)
        self.assertEqual(second["status"], "waiting")
        self.assertEqual(self.demo.batch_calls, [["release-1"]])

    def test_live_cannot_run_without_current_process_arm(self) -> None:
        self.controller.start("okx_live")

        result = self.controller.heartbeat("okx_live", now=NOW)

        self.assertEqual(result["status"], "disarmed")
        self.assertEqual(self.live.batch_calls, [])
        self.assertEqual(self.live.pause_reasons, [])

    def test_old_process_arm_is_not_restored_after_restart(self) -> None:
        self.store.set_desired_enabled("okx_live", True)
        self.store.record_arm("okx_live", process_id="old-process")

        result = self.controller.heartbeat("okx_live", now=NOW)

        self.assertEqual(result["status"], "disarmed")
        self.assertEqual(self.live.batch_calls, [])

    def test_preflight_failure_pauses_before_reconciliation_or_batch(self) -> None:
        self._start_and_arm("okx_demo")
        self.demo.preflight_result = {"ok": False, "blockers": ["auth_failed"]}

        result = self.controller.heartbeat("okx_demo", now=NOW)

        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["blockers"], ["auth_failed"])
        self.assertEqual(self.demo.batch_calls, [])
        self.assertEqual(self.demo.pause_reasons, ["auth_failed"])

    def test_reconciliation_failure_pauses_before_batch(self) -> None:
        self._start_and_arm("okx_live")
        self.live.reconciliation_result = {
            "ok": False,
            "blockers": ["private_state_mismatch"],
        }

        result = self.controller.heartbeat("okx_live", now=NOW)

        self.assertEqual(result["status"], "paused")
        self.assertEqual(self.live.batch_calls, [])
        self.assertEqual(self.live.pause_reasons, ["private_state_mismatch"])

    def test_batch_failure_does_not_advance_checkpoint(self) -> None:
        self._start_and_arm("okx_demo")
        self.demo.batch_result = {"ok": False, "blockers": ["order_state_unknown"]}

        first = self.controller.heartbeat("okx_demo", now=NOW)

        self.assertEqual(first["status"], "paused")
        self.assertIsNone(self.store.checkpoint("okx_demo", "release-1", "1h"))
        self.assertEqual(self.demo.pause_reasons, ["order_state_unknown"])

    def test_emergency_stop_disables_runtime_and_routes_to_selected_adapter(self) -> None:
        self._start_and_arm("okx_live")

        result = self.controller.emergency_stop("okx_live", "operator_stop")

        self.assertTrue(result["ok"])
        self.assertEqual(self.live.emergency_reasons, ["operator_stop"])
        runtime = self.store.runtime("okx_live", current_process_id="process-1")
        self.assertFalse(runtime["desiredEnabled"])
        self.assertFalse(runtime["armedForCurrentProcess"])


if __name__ == "__main__":
    unittest.main()
