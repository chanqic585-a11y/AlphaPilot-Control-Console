from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.risk_profile_store import (
    LIVE_ACTIVATION_CONFIRMATION,
    RiskProfileStore,
)


class RiskProfileStoreTests(unittest.TestCase):
    def test_profile_versions_activate_and_rollback_without_enabling_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RiskProfileStore(Path(directory) / "risk.sqlite")
            base = store.get_active_profile("live_canary")
            profile = {
                **base["profile"],
                "version": None,
                "profileKey": "live_canary_operator",
                "name": "Live Canary Operator",
                "maxActiveStrategies": 3,
                "maxConcurrentPositions": 5,
                "maxPositionsPerStrategy": 2,
                "maxOrderNotionalUsdt": 150.0,
                "maxLeverage": 2,
                "maxOpenRiskPercent": 2.0,
                "maxDirectionOpenRiskPercent": 1.5,
            }
            created = store.create_profile(profile)
            activated = store.activate(
                created["riskProfileId"],
                actor="user_manual",
                confirmation=LIVE_ACTIVATION_CONFIRMATION,
                reason="unit_test",
            )
            rolled_back = store.rollback(
                "live_canary",
                actor="user_manual",
                confirmation=LIVE_ACTIVATION_CONFIRMATION,
            )
            current = store.get_active_profile("live_canary")
            store.close()

        self.assertFalse(activated["executionEnabled"])
        self.assertEqual(current["riskProfileId"], base["riskProfileId"])
        self.assertEqual(rolled_back["activation"]["action"], "rolled_back")

    def test_live_activation_requires_exact_manual_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RiskProfileStore(Path(directory) / "risk.sqlite")
            profile = store.get_active_profile("live_standard")
            with self.assertRaises(PermissionError):
                store.activate(
                    profile["riskProfileId"],
                    actor="user_manual",
                    confirmation="wrong",
                    reason="unit_test",
                )
            store.close()


if __name__ == "__main__":
    unittest.main()
