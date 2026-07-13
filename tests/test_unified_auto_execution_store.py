from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from alphapilot_control_console.unified_auto_execution_store import (
    UnifiedAutoExecutionStore,
)


class UnifiedAutoExecutionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "auto-runtime.sqlite"
        self.store = UnifiedAutoExecutionStore(self.path)

    def tearDown(self) -> None:
        self.store.close()
        self.directory.cleanup()

    def test_runtime_state_never_persists_credentials(self) -> None:
        self.store.set_desired_enabled("okx_demo", True)
        self.store.record_arm("okx_demo", process_id="pid-1")

        state = self.store.runtime("okx_demo")

        self.assertTrue(state["desiredEnabled"])
        self.assertEqual(state["armedProcessId"], "pid-1")
        serialized = json.dumps(state, sort_keys=True).lower()
        for forbidden in ("apikey", "secretkey", "passphrase", "credential"):
            self.assertNotIn(forbidden, serialized)

    def test_checkpoint_is_scoped_by_environment_release_and_timeframe(self) -> None:
        self.store.save_checkpoint(
            "okx_demo",
            "release-1",
            "1h",
            "2026-07-12T10:00:00+00:00",
        )

        self.assertEqual(
            self.store.checkpoint("okx_demo", "release-1", "1h"),
            "2026-07-12T10:00:00+00:00",
        )
        self.assertIsNone(self.store.checkpoint("okx_live", "release-1", "1h"))
        self.assertIsNone(self.store.checkpoint("okx_demo", "release-1", "4h"))

    def test_retire_checkpoints_deletes_only_selected_release_ids(self) -> None:
        for release_id in ("release-1", "release-2", "release-keep"):
            self.store.save_checkpoint("okx_demo", release_id, "1h", "closed")
        self.store.save_checkpoint("okx_live", "release-1", "1h", "live-closed")

        retired = self.store.retire_checkpoints(
            "okx_demo",
            ["release-1", "release-2"],
        )

        self.assertEqual(retired, 2)
        self.assertIsNone(self.store.checkpoint("okx_demo", "release-1", "1h"))
        self.assertIsNone(self.store.checkpoint("okx_demo", "release-2", "1h"))
        self.assertEqual(self.store.checkpoint("okx_demo", "release-keep", "1h"), "closed")
        self.assertEqual(self.store.checkpoint("okx_live", "release-1", "1h"), "live-closed")

    def test_runtime_and_events_survive_reopen_without_restoring_arm_to_new_process(self) -> None:
        self.store.set_desired_enabled("okx_live", True)
        self.store.record_arm("okx_live", process_id="old-process")
        self.store.append_event("okx_live", "armed", {"actor": "user_manual"})
        self.store.close()

        self.store = UnifiedAutoExecutionStore(self.path)
        state = self.store.runtime("okx_live", current_process_id="new-process")

        self.assertTrue(state["desiredEnabled"])
        self.assertFalse(state["armedForCurrentProcess"])
        self.assertEqual(self.store.list_events("okx_live", 5)[0]["eventType"], "armed")

    def test_only_known_environments_are_accepted(self) -> None:
        with self.assertRaises(ValueError):
            self.store.runtime("production")
        with self.assertRaises(ValueError):
            self.store.set_desired_enabled("paper", True)

    def test_store_is_safe_across_runner_and_http_threads(self) -> None:
        failures: list[BaseException] = []
        results: list[dict[str, object]] = []

        def read_runtime() -> None:
            try:
                results.append(self.store.runtime("okx_demo"))
            except BaseException as error:  # pragma: no cover - asserted below
                failures.append(error)

        thread = threading.Thread(target=read_runtime)
        thread.start()
        thread.join(timeout=2.0)

        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(results[0]["status"], "disabled")


if __name__ == "__main__":
    unittest.main()
