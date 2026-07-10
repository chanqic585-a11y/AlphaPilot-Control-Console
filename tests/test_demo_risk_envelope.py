from __future__ import annotations

import unittest

from alphapilot_control_console.demo_risk_envelope import evaluate_demo_order_risk


class DemoRiskEnvelopeTests(unittest.TestCase):
    def test_default_1000_usdt_envelope_accepts_small_order(self) -> None:
        result = evaluate_demo_order_risk(
            notionalUsdt=200,
            leverage=2,
            riskPercent=0.25,
            openRiskPercent=0.5,
            openPositionCount=1,
            dailyLossPercent=0.5,
            drawdownPercent=1.0,
            dataFresh=True,
            liquidityPassed=True,
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.equityUsdt, 1000.0)

    def test_notional_and_drawdown_breaches_are_blocked(self) -> None:
        result = evaluate_demo_order_risk(
            notionalUsdt=300,
            leverage=2,
            riskPercent=0.25,
            openRiskPercent=0.5,
            openPositionCount=1,
            dailyLossPercent=0.5,
            drawdownPercent=5.1,
            dataFresh=True,
            liquidityPassed=True,
        )
        self.assertFalse(result.passed)
        self.assertIn("max_order_notional", result.reasonCodes)
        self.assertIn("demo_drawdown_stop", result.reasonCodes)


if __name__ == "__main__":
    unittest.main()
