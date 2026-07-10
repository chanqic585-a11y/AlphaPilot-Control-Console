from __future__ import annotations

import unittest

from alphapilot_control_console.demo_arbitrator import arbitrate_demo_signals


class DemoArbitratorTests(unittest.TestCase):
    def test_conflicting_and_duplicate_family_signals_are_rejected(self) -> None:
        signals = [
            {"candidateId": "a", "strategyFamilyId": "trend", "instId": "BTC-USDT-SWAP", "side": "buy", "score": 0.9},
            {"candidateId": "b", "strategyFamilyId": "reversion", "instId": "BTC-USDT-SWAP", "side": "sell", "score": 0.8},
            {"candidateId": "c", "strategyFamilyId": "trend", "instId": "ETH-USDT-SWAP", "side": "buy", "score": 0.7},
        ]
        result = arbitrate_demo_signals(signals, maxPositions=3)

        self.assertEqual([item["candidateId"] for item in result.selected], ["a"])
        reasons = {item["candidateId"]: item["reason"] for item in result.rejected}
        self.assertEqual(reasons["b"], "symbol_direction_conflict")
        self.assertEqual(reasons["c"], "duplicate_strategy_family")


if __name__ == "__main__":
    unittest.main()
