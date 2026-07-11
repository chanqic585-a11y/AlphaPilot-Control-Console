from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.live_canary_service import (
    activate_live_canary_kill_switch,
    build_live_canary_status,
    run_live_readonly_reconciliation,
)
from alphapilot_control_console.live_execution_store import LiveExecutionStore


class FakeReadClient:
    def get_account_config(self) -> dict:
        return {"code": "0", "data": [{}]}

    def get_balance(self, _: str) -> dict:
        return {"code": "0", "data": [{"totalEq": "1000"}]}

    def get_positions(self) -> dict:
        return {"code": "0", "data": []}

    def get_open_orders(self) -> dict:
        return {"code": "0", "data": []}

    def cancel_all_after(self, _: int) -> dict:
        return {"code": "0", "data": []}


class LiveCanaryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store_path = Path(self.directory.name) / "live.sqlite"
        self.environment = {
            "ALPHAPILOT_OKX_LIVE_ENABLED": "1",
            "ALPHAPILOT_OKX_LIVE_READ_ENABLED": "1",
            "ALPHAPILOT_OKX_LIVE_API_KEY": "key",
            "ALPHAPILOT_OKX_LIVE_SECRET_KEY": "secret",
            "ALPHAPILOT_OKX_LIVE_PASSPHRASE": "pass",
        }

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_status_is_fail_closed_by_default(self) -> None:
        status = build_live_canary_status(environment={}, store_path=self.store_path)
        self.assertTrue(status["runtime"]["killSwitchActive"])
        self.assertFalse(status["summary"]["canaryOrderReady"])
        self.assertTrue(status["safetyBoundary"]["liveAdapterPresent"])
        self.assertFalse(status["safetyBoundary"]["liveExecutionEnabledByDefault"])
        self.assertTrue(status["safetyBoundary"]["automaticSignalRunnerPresent"])
        self.assertFalse(status["safetyBoundary"]["automaticExecutionEnabledByDefault"])

    def test_readonly_reconciliation_persists_counts_not_account_values(self) -> None:
        result = run_live_readonly_reconciliation(
            environment=self.environment,
            store_path=self.store_path,
            client=FakeReadClient(),
        )
        self.assertTrue(result["reconciliationMatched"])
        self.assertFalse(result["accountValuesPersisted"])

    def test_kill_switch_is_local_first_and_can_send_cancel_all_after(self) -> None:
        result = activate_live_canary_kill_switch(
            {"reason": "unit_test"},
            environment=self.environment,
            store_path=self.store_path,
            client=FakeReadClient(),
        )
        store = LiveExecutionStore(self.store_path)
        try:
            self.assertTrue(store.runtime_state()["killSwitchActive"])
        finally:
            store.close()
        self.assertTrue(result["exchangeCancelSent"])


if __name__ == "__main__":
    unittest.main()
