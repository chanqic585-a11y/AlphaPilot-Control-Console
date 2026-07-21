from __future__ import annotations

import unittest

from alphapilot_control_console.advisory_r_exit_policy import (
    advisory_target_r,
    validate_canonical_exit_policy,
)


class AdvisoryRExitPolicyTests(unittest.TestCase):
    def test_trend_following_exit_is_versioned_without_a_fixed_r_target(self) -> None:
        policy = validate_canonical_exit_policy(
            {
                "version": "advisory_r_exit_policy_v1",
                "mode": "trend_following_exit",
                "maximumHoldBars": 240,
                "initialStopMayWiden": False,
                "parameters": {
                    "trailingAtrMultiple": 2.5,
                    "trendRule": {
                        "kind": "trend_invalidation",
                        "fastWindow": 20,
                        "slowWindow": 50,
                    },
                },
            }
        )

        self.assertEqual(policy["mode"], "trend_following_exit")
        self.assertIsNone(advisory_target_r(policy))

    def test_fixed_r_is_explicit_and_may_be_below_two_r(self) -> None:
        policy = validate_canonical_exit_policy(
            {
                "version": "advisory_r_exit_policy_v1",
                "mode": "fixed_r",
                "maximumHoldBars": 24,
                "initialStopMayWiden": False,
                "parameters": {"targetR": 1.25},
            }
        )

        self.assertEqual(advisory_target_r(policy), 1.25)
