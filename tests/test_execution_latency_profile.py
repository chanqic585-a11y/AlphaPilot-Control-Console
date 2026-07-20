from __future__ import annotations

import unittest

from alphapilot_control_console.execution_latency_profile import (
    build_execution_latency_profile,
)


class ExecutionLatencyProfileTests(unittest.TestCase):
    def test_default_profile_is_versioned_hashed_and_matches_v55_targets(self) -> None:
        profile = build_execution_latency_profile()

        self.assertEqual(profile["executionLatencyProfileVersion"], "v55-default-1")
        self.assertEqual(profile["signalToOrderSendTargetMs"], 750)
        self.assertEqual(profile["signalToOrderSendSoftWarnMs"], 1500)
        self.assertEqual(profile["maximumSignalAgeMs"], 3000)
        self.assertEqual(profile["exchangeAckTimeoutMs"], 2000)
        self.assertEqual(profile["orderRequestExpiryMs"], 3000)
        self.assertEqual(profile["orderTransportMode"], "auto")
        self.assertEqual(profile["criticalLatencyFailureMs"], 20000)
        self.assertTrue(
            profile["executionLatencyProfileHash"].startswith("execution_latency_profile_")
        )

    def test_profile_hash_changes_with_a_valid_override(self) -> None:
        default = build_execution_latency_profile()
        adjusted = build_execution_latency_profile({"signalToOrderSendSoftWarnMs": 1200})

        self.assertNotEqual(
            default["executionLatencyProfileHash"],
            adjusted["executionLatencyProfileHash"],
        )

    def test_invalid_expiry_mode_and_critical_boundary_fail_closed(self) -> None:
        invalid_profiles = (
            {"orderRequestExpiryMs": 3001},
            {"maximumSignalAgeMs": 20001},
            {"orderTransportMode": "fastest_magic"},
            {"criticalLatencyFailureMs": 21000},
        )
        for overrides in invalid_profiles:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                build_execution_latency_profile(overrides)


if __name__ == "__main__":
    unittest.main()
