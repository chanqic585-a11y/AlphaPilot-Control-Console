from __future__ import annotations

import unittest

from alphapilot_control_console.demo_runtime_guard import evaluate_demo_runtime_guard


class DemoRuntimeGuardTests(unittest.TestCase):
    def test_unknown_order_state_and_drawdown_require_pause(self) -> None:
        result = evaluate_demo_runtime_guard(
            {
                "availableEquityUsdt": 800.0,
                "dailyLossPercent": 1.0,
                "drawdownPercent": 5.1,
                "reconciliationMatched": True,
            },
            recovered_statuses=["unknown"],
            checksums_match=True,
        )

        self.assertTrue(result.pauseRequired)
        self.assertIn("unresolved_demo_order_state", result.reasonCodes)
        self.assertIn("demo_drawdown_stop", result.reasonCodes)

    def test_clean_reconciled_demo_state_passes(self) -> None:
        result = evaluate_demo_runtime_guard(
            {
                "availableEquityUsdt": 1000.0,
                "dailyLossPercent": 0.0,
                "drawdownPercent": 0.0,
                "reconciliationMatched": True,
            },
            recovered_statuses=[],
            checksums_match=True,
        )

        self.assertTrue(result.passed)
        self.assertFalse(result.pauseRequired)

    def test_cost_and_loss_drift_pause_new_entries(self) -> None:
        result = evaluate_demo_runtime_guard(
            {
                "availableEquityUsdt": 900.0,
                "dailyLossPercent": 0.0,
                "drawdownPercent": 1.0,
                "reconciliationMatched": True,
                "closedOutcomeCount": 20,
                "rollingProfitFactor": 0.9,
                "consecutiveLosses": 5,
                "observedSlippageBps": 7.0,
                "assumedSlippageBps": 2.0,
            },
            recovered_statuses=[],
            checksums_match=True,
        )

        self.assertIn("demo_rolling_profit_factor_drift", result.reasonCodes)
        self.assertIn("demo_consecutive_loss_stop", result.reasonCodes)
        self.assertIn("demo_slippage_drift", result.reasonCodes)

    def test_data_auth_orphan_and_approval_drift_fail_closed(self) -> None:
        result = evaluate_demo_runtime_guard(
            {
                "availableEquityUsdt": 1000.0,
                "dailyLossPercent": 0.0,
                "drawdownPercent": 0.0,
                "reconciliationMatched": True,
                "marketDataFresh": False,
                "accountDataFresh": False,
                "authenticationHealthy": False,
                "orphanPositionCount": 1,
            },
            recovered_statuses=[],
            checksums_match=True,
            approval_checksums_match=False,
        )

        self.assertEqual(
            set(result.reasonCodes),
            {
                "demo_market_data_stale",
                "demo_account_data_stale",
                "demo_authentication_failure",
                "orphan_demo_position",
                "approval_checksum_mismatch",
            },
        )


if __name__ == "__main__":
    unittest.main()
