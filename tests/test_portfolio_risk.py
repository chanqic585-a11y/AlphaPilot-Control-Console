from __future__ import annotations

import unittest

from alphapilot_control_console.portfolio_risk import evaluate_portfolio_risk
from alphapilot_control_console.risk_profile_store import default_profile


class PortfolioRiskTests(unittest.TestCase):
    def test_multi_strategy_profile_accepts_diversified_slot(self) -> None:
        profile = default_profile("okx_demo")
        decision = evaluate_portfolio_risk(
            profile=profile,
            intent={
                "strategyId": "strategy-b",
                "instId": "ETH-USDT-SWAP",
                "side": "buy",
                "correlationGroup": "eth",
                "notionalUsdt": 100,
                "leverage": 1,
                "riskPercent": 0.25,
            },
            portfolio={
                "availableEquityUsdt": 900,
                "activeStrategyIds": ["strategy-a"],
                "openPositionCount": 1,
                "positionsByStrategy": {"strategy-a": 1},
                "positionsBySymbol": {"BTC-USDT-SWAP": 1},
                "openRiskPercent": 0.25,
                "openRiskByStrategy": {"strategy-a": 0.25},
                "openRiskBySymbol": {"BTC-USDT-SWAP": 0.25},
                "openRiskByDirection": {"short": 0.25},
                "openRiskByCorrelationGroup": {"btc": 0.25},
                "dailyLossPercent": 0,
                "drawdownPercent": 0,
                "canaryLossUsdt": 0,
                "cooldownActive": False,
                "dataFresh": True,
                "liquidityPassed": True,
            },
        )

        self.assertTrue(decision.passed)
        self.assertEqual(decision.projectedActiveStrategyCount, 2)

    def test_concentrated_symbol_and_strategy_limits_fail_closed(self) -> None:
        profile = default_profile("okx_demo")
        decision = evaluate_portfolio_risk(
            profile=profile,
            intent={
                "strategyId": "strategy-a",
                "instId": "BTC-USDT-SWAP",
                "side": "sell",
                "notionalUsdt": 100,
                "leverage": 1,
                "riskPercent": 0.25,
            },
            portfolio={
                "availableEquityUsdt": 900,
                "activeStrategyIds": ["strategy-a"],
                "openPositionCount": 3,
                "positionsByStrategy": {"strategy-a": 2},
                "positionsBySymbol": {"BTC-USDT-SWAP": 1},
                "openRiskPercent": 0.5,
                "openRiskByStrategy": {"strategy-a": 0.5},
                "openRiskBySymbol": {"BTC-USDT-SWAP": 0.25},
                "openRiskByDirection": {"short": 0.5},
                "dailyLossPercent": 0,
                "drawdownPercent": 0,
                "canaryLossUsdt": 0,
                "cooldownActive": False,
                "dataFresh": True,
                "liquidityPassed": True,
            },
        )

        self.assertFalse(decision.passed)
        self.assertIn("max_concurrent_positions", decision.reasonCodes)
        self.assertIn("max_positions_per_strategy", decision.reasonCodes)
        self.assertIn("max_positions_per_symbol", decision.reasonCodes)


if __name__ == "__main__":
    unittest.main()
