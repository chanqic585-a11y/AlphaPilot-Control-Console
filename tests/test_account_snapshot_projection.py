from __future__ import annotations

import json
import unittest

from alphapilot_control_console.account_snapshot_projection import (
    build_sanitized_account_snapshot,
)


class AccountSnapshotProjectionTests(unittest.TestCase):
    def test_builds_sanitized_account_and_position_snapshot(self) -> None:
        snapshot = build_sanitized_account_snapshot(
            balance_response={
                "code": "0",
                "apiKey": "must-not-survive",
                "data": [
                    {
                        "totalEq": "1200.50",
                        "details": [
                            {
                                "ccy": "USDT",
                                "eq": "1198.25",
                                "availEq": "950.75",
                                "upl": "7.50",
                                "secretKey": "must-not-survive",
                            }
                        ],
                    }
                ],
            },
            positions_response={
                "code": "0",
                "data": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "pos": "2",
                        "posSide": "long",
                        "avgPx": "61000",
                        "markPx": "61500",
                        "upl": "10.5",
                        "lever": "2",
                        "mgnMode": "isolated",
                        "liqPx": "42000",
                        "uTime": "1784692800000",
                        "rawPrivateField": "must-not-survive",
                    },
                    {"instId": "ETH-USDT-SWAP", "pos": "0", "upl": "0"},
                ],
            },
            strategy_ids_by_instrument={"BTC-USDT-SWAP": ["strategy-a"]},
            updated_at="2026-07-22T04:00:00+00:00",
        )

        self.assertEqual(snapshot["status"], "available")
        self.assertEqual(snapshot["accountEquityUsdt"], 1198.25)
        self.assertEqual(snapshot["availableEquityUsdt"], 950.75)
        self.assertEqual(snapshot["availableBalanceUsdt"], 950.75)
        self.assertEqual(snapshot["floatingPnlUsdt"], 10.5)
        self.assertIsNone(snapshot["todayRealizedPnlUsdt"])
        self.assertEqual(snapshot["openPositionCount"], 1)
        self.assertEqual(snapshot["positions"][0]["strategyId"], "strategy-a")
        self.assertEqual(snapshot["positions"][0]["side"], "long")
        self.assertEqual(snapshot["positions"][0]["quantity"], 2.0)
        self.assertEqual(snapshot["positions"][0]["unrealizedPnlUsdt"], 10.5)

        serialized = json.dumps(snapshot, sort_keys=True)
        self.assertNotIn("must-not-survive", serialized)
        self.assertNotIn("apiKey", serialized)
        self.assertNotIn("secretKey", serialized)
        self.assertNotIn("rawPrivateField", serialized)

    def test_attributes_ambiguous_position_to_all_candidate_strategies(self) -> None:
        snapshot = build_sanitized_account_snapshot(
            balance_response={"code": "0", "data": [{"details": [{"ccy": "USDT", "availEq": "100"}]}]},
            positions_response={
                "code": "0",
                "data": [{"instId": "SOL-USDT-SWAP", "pos": "-3", "avgPx": "150", "upl": "-2"}],
            },
            strategy_ids_by_instrument={"SOL-USDT-SWAP": ["strategy-b", "strategy-a"]},
            updated_at="2026-07-22T04:00:00+00:00",
        )

        position = snapshot["positions"][0]
        self.assertEqual(position["side"], "short")
        self.assertIsNone(position["strategyId"])
        self.assertEqual(position["strategyIds"], ["strategy-a", "strategy-b"])


if __name__ == "__main__":
    unittest.main()
