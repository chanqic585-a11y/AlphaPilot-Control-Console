from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

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
        self.batch_close_events: list[object | None] = []
        self.pause_reasons: list[str] = []
        self.emergency_reasons: list[str] = []

    def preflight(self) -> dict:
        return dict(self.preflight_result)

    def reconcile(self) -> dict:
        return dict(self.reconciliation_result)

    def list_releases(self) -> list[ReleaseSchedule]:
        return list(self.releases)

    def run_batch(
        self,
        releases: list[ReleaseSchedule],
        candle_keys: dict[str, str],
        close_event: object | None = None,
    ) -> dict:
        self.batch_calls.append([release.releaseId for release in releases])
        self.batch_close_events.append(close_event)
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
        self._start_and_arm("okx_live")

        first = self.controller.heartbeat("okx_live", now=NOW)
        second = self.controller.heartbeat("okx_live", now=NOW)

        self.assertEqual(first["evaluatedReleaseCount"], 1)
        self.assertEqual(first["status"], "running")
        self.assertEqual(second["evaluatedReleaseCount"], 0)
        self.assertEqual(second["status"], "waiting")
        self.assertEqual(self.live.batch_calls, [["live-1"]])

    def test_demo_recovery_heartbeat_does_not_reconstruct_a_missed_close_event(self) -> None:
        self._start_and_arm("okx_demo")

        result = self.controller.heartbeat("okx_demo", now=NOW)

        self.assertEqual(result["status"], "waiting")
        self.assertEqual(result["evaluatedReleaseCount"], 0)
        self.assertEqual(self.demo.batch_calls, [])
        self.assertIsNone(self.store.checkpoint("okx_demo", "release-1", "1h"))

    def test_confirmed_close_uses_event_sequence_for_one_matching_timeframe_checkpoint(self) -> None:
        self.demo.releases.append(ReleaseSchedule("release-5m", "strategy-5m", "5m"))
        self.demo.batch_result.update(
            {
                "latencyMetrics": {"selected": [{"closeToReadyMs": 4000}]},
                "expiredSignals": [],
                "conditionalLateEntries": [{"candidateId": "late-1"}],
                "evaluationAudit": {
                    "state": "evaluated_zero_matches",
                    "evaluatedReleaseCount": 1,
                },
            }
        )
        self._start_and_arm("okx_demo")
        close_event = SimpleNamespace(
            sequenceId="1h:1783900800000",
            timeframe="1h",
            receivedAt="2026-07-13T00:00:00+00:00",
        )

        first = self.controller.heartbeat("okx_demo", now=NOW, close_event=close_event)
        second = self.controller.heartbeat("okx_demo", now=NOW, close_event=close_event)

        self.assertEqual(first["evaluatedReleaseCount"], 1)
        self.assertEqual(second["evaluatedReleaseCount"], 0)
        self.assertEqual(self.demo.batch_calls, [["release-1"]])
        self.assertEqual(self.demo.batch_close_events, [close_event])
        self.assertEqual(
            self.store.checkpoint("okx_demo", "release-1", "1h"),
            "1h:1783900800000",
        )
        self.assertIsNone(self.store.checkpoint("okx_demo", "release-5m", "5m"))
        heartbeat_event = next(
            row
            for row in self.store.list_events("okx_demo")
            if row["eventType"] == "heartbeat_completed"
        )
        self.assertEqual(heartbeat_event["payload"]["closeSequenceId"], close_event.sequenceId)
        self.assertEqual(heartbeat_event["payload"]["closeReceivedAt"], close_event.receivedAt)
        self.assertEqual(heartbeat_event["payload"]["conditionalLateEntryCount"], 1)
        self.assertEqual(
            heartbeat_event["payload"]["evaluationAudit"]["state"],
            "evaluated_zero_matches",
        )
        status = self.controller.status("okx_demo")
        self.assertEqual(status["lastEvaluation"]["state"], "evaluated_zero_matches")

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

    def test_transient_demo_network_failure_degrades_then_recovers_without_pause(self) -> None:
        self._start_and_arm("okx_demo")
        self.demo.reconciliation_result = {
            "ok": False,
            "transient": True,
            "blockers": ["OKX Demo network request failed: TimeoutError"],
        }

        degraded = self.controller.heartbeat("okx_demo", now=NOW)

        self.assertEqual(degraded["status"], "degraded")
        self.assertEqual(
            degraded["blockers"],
            ["OKX Demo network request failed: TimeoutError"],
        )
        self.assertEqual(self.demo.pause_reasons, [])
        self.assertEqual(self.demo.batch_calls, [])
        self.assertIsNone(self.store.checkpoint("okx_demo", "release-1", "1h"))
        runtime = self.store.runtime("okx_demo", current_process_id="process-1")
        self.assertTrue(runtime["desiredEnabled"])
        self.assertTrue(runtime["armedForCurrentProcess"])
        self.assertEqual(runtime["status"], "degraded")
        self.assertIsNone(runtime["pauseReason"])
        self.assertEqual(
            runtime["lastError"],
            "OKX Demo network request failed: TimeoutError",
        )
        self.assertIn(
            "heartbeat_degraded",
            [row["eventType"] for row in self.store.list_events("okx_demo")],
        )

        self.demo.reconciliation_result = {"ok": True, "blockers": []}
        recovered = self.controller.heartbeat("okx_demo", now=NOW)

        self.assertEqual(recovered["status"], "waiting")
        recovered_runtime = self.store.runtime(
            "okx_demo",
            current_process_id="process-1",
        )
        self.assertIsNone(recovered_runtime["pauseReason"])
        self.assertIsNone(recovered_runtime["lastError"])
        self.assertEqual(self.demo.pause_reasons, [])

    def test_batch_failure_does_not_advance_checkpoint(self) -> None:
        self._start_and_arm("okx_demo")
        self.demo.batch_result = {"ok": False, "blockers": ["order_state_unknown"]}
        close_event = SimpleNamespace(
            sequenceId="1h:1783900800000",
            timeframe="1h",
            receivedAt="2026-07-13T00:00:00+00:00",
        )

        first = self.controller.heartbeat("okx_demo", now=NOW, close_event=close_event)

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
