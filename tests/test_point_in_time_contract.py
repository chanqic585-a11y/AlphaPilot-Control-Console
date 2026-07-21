from __future__ import annotations

import unittest

from alphapilot_control_console.point_in_time_contract import validate_point_in_time


class PointInTimeContractTests(unittest.TestCase):
    def test_accepts_monotonic_market_to_order_timestamps(self) -> None:
        result = validate_point_in_time(
            source_timestamp="2026-07-22T00:00:00Z",
            available_at="2026-07-22T00:00:01Z",
            decision_at="2026-07-22T00:00:02Z",
            order_send_at="2026-07-22T00:00:03Z",
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["ordering"], [
            "sourceTimestamp",
            "availableAt",
            "decisionAt",
            "orderSendAt",
        ])

    def test_rejects_future_data_and_missing_required_timestamps(self) -> None:
        with self.assertRaises(ValueError):
            validate_point_in_time(
                source_timestamp="2026-07-22T00:00:02Z",
                available_at="2026-07-22T00:00:01Z",
                decision_at="2026-07-22T00:00:03Z",
            )
        with self.assertRaises(ValueError):
            validate_point_in_time(
                source_timestamp="",
                available_at="2026-07-22T00:00:01Z",
                decision_at="2026-07-22T00:00:03Z",
            )


if __name__ == "__main__":
    unittest.main()
