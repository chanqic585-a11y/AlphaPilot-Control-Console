from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from alphapilot_control_console import risk_profile_store
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
            with patch(
                "alphapilot_control_console.risk_profile_store._now",
                return_value="2099-01-01T00:00:00+00:00",
            ), patch(
                "alphapilot_control_console.risk_profile_store.uuid.uuid4",
                side_effect=[SimpleNamespace(hex="z" * 32), SimpleNamespace(hex="a" * 32)],
            ):
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

    def test_reward_risk_is_versioned_and_may_be_below_two_r(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RiskProfileStore(Path(directory) / "risk.sqlite")
            try:
                base = store.get_active_profile("live_canary")
                created = store.create_profile({
                    **base["profile"],
                    "version": None,
                    "profileKey": "live_canary_rr_125",
                    "name": "Live Canary RR 1.25",
                    "rewardRiskRatio": 1.25,
                })
            finally:
                store.close()

        self.assertEqual(created["profile"]["rewardRiskRatio"], 1.25)

    def test_revised_default_preset_creates_new_version_without_replacing_active_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "risk.sqlite"
            first_store = RiskProfileStore(path)
            original_active = first_store.get_active_profile("okx_demo")
            first_store.close()

            original_default_profile = risk_profile_store.default_profile

            def revised_default_profile(environment: str) -> dict[str, object]:
                profile = original_default_profile(environment)
                return {**profile, "name": f"{profile['name']} Revised"}

            with patch.object(
                risk_profile_store,
                "default_profile",
                side_effect=revised_default_profile,
            ):
                revised_store = RiskProfileStore(path)
                revised_profiles = revised_store.list_profiles("okx_demo")
                active_after_reopen = revised_store.get_active_profile("okx_demo")
                revised_store.close()

        self.assertEqual([profile["version"] for profile in revised_profiles], [1, 2])
        self.assertEqual(
            active_after_reopen["riskProfileId"],
            original_active["riskProfileId"],
        )


if __name__ == "__main__":
    unittest.main()
