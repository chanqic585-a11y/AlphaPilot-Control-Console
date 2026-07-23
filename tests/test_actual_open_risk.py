from __future__ import annotations

import unittest

from alphapilot_control_console.actual_open_risk import build_actual_open_risk


class ActualOpenRiskTest(unittest.TestCase):
    def test_zero_positions_are_complete_and_zero(self) -> None:
        result = build_actual_open_risk(positions=[], records=[], open_orders=[])

        self.assertEqual(result["expectedOpenRisk"], 0.0)
        self.assertEqual(result["exchangePositionRisk"], 0.0)
        self.assertEqual(result["protectedOpenRisk"], 0.0)
        self.assertEqual(result["unprotectedPositionRisk"], 0.0)
        self.assertEqual(result["unknownProtectionCount"], 0)
        self.assertTrue(result["complete"])

    def test_verified_stop_protection_is_reconciled(self) -> None:
        result = build_actual_open_risk(
            positions=[{
                "instrumentId": "BTC-USDT-SWAP",
                "quantity": 2.0,
                "entryPrice": 100.0,
                "side": "long",
            }],
            records=[{
                "instrumentId": "BTC-USDT-SWAP",
                "status": "filled",
                "signal": {
                    "entryPrice": 100.0,
                    "stopLossPrice": 98.0,
                    "riskUsdt": 4.0,
                },
            }],
            open_orders=[{
                "instId": "BTC-USDT-SWAP",
                "reduceOnly": "true",
                "slTriggerPx": "98",
            }],
        )

        self.assertEqual(result["expectedOpenRisk"], 4.0)
        self.assertEqual(result["exchangePositionRisk"], 4.0)
        self.assertEqual(result["protectedOpenRisk"], 4.0)
        self.assertEqual(result["unprotectedPositionRisk"], 0.0)
        self.assertEqual(result["unknownProtectionCount"], 0)
        self.assertTrue(result["complete"])

    def test_missing_exchange_protection_is_fail_closed(self) -> None:
        result = build_actual_open_risk(
            positions=[{
                "instrumentId": "ETH-USDT-SWAP",
                "quantity": 1.0,
                "entryPrice": 100.0,
                "side": "long",
            }],
            records=[{
                "instrumentId": "ETH-USDT-SWAP",
                "status": "filled",
                "signal": {"entryPrice": 100.0, "stopLossPrice": 99.0},
            }],
            open_orders=[],
        )

        self.assertEqual(result["exchangePositionRisk"], 1.0)
        self.assertEqual(result["unprotectedPositionRisk"], 1.0)
        self.assertEqual(result["unknownProtectionCount"], 1)
        self.assertFalse(result["complete"])
        self.assertFalse(result["newEntriesAllowed"])
        self.assertEqual(result["route"], "actual_open_risk_unverified")

    def test_missing_stop_does_not_invent_risk(self) -> None:
        result = build_actual_open_risk(
            positions=[{
                "instrumentId": "SOL-USDT-SWAP",
                "quantity": 3.0,
                "entryPrice": 50.0,
                "side": "long",
            }],
            records=[],
            open_orders=[],
        )

        self.assertIsNone(result["exchangePositionRisk"])
        self.assertIsNone(result["unprotectedPositionRisk"])
        self.assertEqual(result["unknownProtectionCount"], 1)
        self.assertFalse(result["complete"])


if __name__ == "__main__":
    unittest.main()
