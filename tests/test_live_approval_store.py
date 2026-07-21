from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from alphapilot_control_console.live_approval_store import (
    LIVE_APPROVAL_CONFIRMATION,
    LiveApprovalStore,
)


class LiveApprovalStoreTests(unittest.TestCase):
    def test_manual_approval_is_checksum_bound_and_does_not_enable_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LiveApprovalStore(Path(directory) / "approval.sqlite")
            approved = store.approve(
                packageId="package-1",
                packageHash="hash-1",
                riskBudget={"capitalLimitUsdt": 1000.0, "riskPerTradePercent": 0.25},
                confirmation=LIVE_APPROVAL_CONFIRMATION,
                actor="user_manual",
            )
            current = store.get_state("package-1", "hash-1")
            changed = store.get_state("package-1", "hash-2")

            self.assertEqual(approved.action, "approved")
            self.assertEqual(current["status"], "approved_for_future_release_review")
            self.assertEqual(current["environment"], "okx_live")
            self.assertFalse(current["executionEnabled"])
            self.assertEqual(changed["status"], "checksum_changed_approval_invalid")
            self.assertEqual(changed["environment"], "okx_live")
            self.assertFalse(changed["executionEnabled"])
            store.close()

    def test_ai_bandit_and_ml_cannot_write_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LiveApprovalStore(Path(directory) / "approval.sqlite")
            for actor in ("ai", "bandit", "ml", "automation"):
                with self.assertRaises(PermissionError):
                    store.approve(
                        packageId="package-1",
                        packageHash="hash-1",
                        riskBudget={"capitalLimitUsdt": 1000.0},
                        confirmation=LIVE_APPROVAL_CONFIRMATION,
                        actor=actor,
                    )
            self.assertEqual(store.list_actions(), [])
            store.close()

    def test_revocation_is_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LiveApprovalStore(Path(directory) / "approval.sqlite")
            with patch(
                "alphapilot_control_console.live_approval_store._now",
                return_value="2099-01-01T00:00:00+00:00",
            ), patch(
                "alphapilot_control_console.live_approval_store.uuid.uuid4",
                side_effect=[SimpleNamespace(hex="z" * 32), SimpleNamespace(hex="a" * 32)],
            ):
                store.approve(
                    packageId="package-1",
                    packageHash="hash-1",
                    riskBudget={"capitalLimitUsdt": 1000.0},
                    confirmation=LIVE_APPROVAL_CONFIRMATION,
                    actor="user_manual",
                )
                store.revoke(packageId="package-1", packageHash="hash-1", actor="user_manual")

            self.assertEqual(store.get_state("package-1", "hash-1")["status"], "revoked")
            self.assertEqual(len(store.list_actions()), 2)
            store.close()


if __name__ == "__main__":
    unittest.main()
