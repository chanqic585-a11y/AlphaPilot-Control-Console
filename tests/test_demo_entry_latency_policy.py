from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from alphapilot_control_console.demo_entry_latency_policy import (
    evaluate_demo_entry_latency,
)


CLOSE_RECEIVED_AT = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)


def long_signal(*, take_profit: float = 104.5) -> dict:
    return {
        "side": "buy",
        "entryPrice": 100.0,
        "stopLossPrice": 98.0,
        "takeProfitPrice": take_profit,
    }


def short_signal() -> dict:
    return {
        "side": "sell",
        "entryPrice": 100.0,
        "stopLossPrice": 102.0,
        "takeProfitPrice": 95.5,
    }


def quote(
    *,
    bid: float = 100.01,
    ask: float = 100.02,
    received_after_seconds: float = 11.5,
    spread_pct: float = 0.0001,
    liquidity_passed: bool = True,
) -> dict:
    return {
        "bidPrice": bid,
        "askPrice": ask,
        "receivedAt": (
            CLOSE_RECEIVED_AT + timedelta(seconds=received_after_seconds)
        ).isoformat(),
        "spreadPct": spread_pct,
        "liquidityPassed": liquidity_passed,
    }


class DemoEntryLatencyPolicyTests(unittest.TestCase):
    def evaluate(
        self,
        *,
        signal: dict | None = None,
        current_quote: dict | None = None,
        ready_after_seconds: float,
    ):
        return evaluate_demo_entry_latency(
            signal or long_signal(),
            current_quote or quote(),
            close_received_at=CLOSE_RECEIVED_AT,
            order_ready_at=CLOSE_RECEIVED_AT + timedelta(seconds=ready_after_seconds),
            fee_rate=0.0005,
            slippage_rate=0.0002,
        )

    def test_under_five_seconds_is_on_target(self) -> None:
        decision = self.evaluate(ready_after_seconds=4.999)

        self.assertTrue(decision.passed)
        self.assertEqual(decision.latencyClass, "on_target")
        self.assertEqual(decision.closeToReadyMs, 4999)

    def test_between_five_and_ten_seconds_is_delayed_but_eligible(self) -> None:
        decision = self.evaluate(ready_after_seconds=7.0)

        self.assertTrue(decision.passed)
        self.assertEqual(decision.latencyClass, "delayed")
        self.assertIsNone(decision.reasonCode)

    def test_twelve_second_entry_passes_with_small_drift_and_net_two_r(self) -> None:
        decision = self.evaluate(ready_after_seconds=12.0)

        self.assertTrue(decision.passed)
        self.assertEqual(decision.latencyClass, "conditional")
        self.assertAlmostEqual(decision.adverseDriftPercent or 0.0, 0.02, places=6)
        self.assertAlmostEqual(decision.allowedAdverseDriftPercent or 0.0, 0.2, places=6)
        self.assertGreaterEqual(decision.recalculatedNetRewardRisk or 0.0, 2.0)

    def test_more_than_thirty_seconds_expires_even_when_price_did_not_move(self) -> None:
        decision = self.evaluate(ready_after_seconds=30.001)

        self.assertFalse(decision.passed)
        self.assertEqual(decision.latencyClass, "expired")
        self.assertEqual(decision.reasonCode, "signal_expired")

    def test_long_higher_and_short_lower_entries_are_adverse(self) -> None:
        long_decision = self.evaluate(ready_after_seconds=12.0)
        short_decision = self.evaluate(
            signal=short_signal(),
            current_quote=quote(bid=99.98, ask=99.99),
            ready_after_seconds=12.0,
        )

        self.assertAlmostEqual(long_decision.adverseDriftPercent or 0.0, 0.02, places=6)
        self.assertAlmostEqual(short_decision.adverseDriftPercent or 0.0, 0.02, places=6)

    def test_conditional_entry_rejects_stale_quote(self) -> None:
        decision = self.evaluate(
            current_quote=quote(received_after_seconds=9.0),
            ready_after_seconds=12.0,
        )

        self.assertFalse(decision.passed)
        self.assertEqual(decision.reasonCode, "conditional_quote_stale")

    def test_conditional_entry_rejects_liquidity_or_spread_failure(self) -> None:
        illiquid = self.evaluate(
            current_quote=quote(liquidity_passed=False),
            ready_after_seconds=12.0,
        )
        wide_spread = self.evaluate(
            current_quote=quote(spread_pct=0.0021),
            ready_after_seconds=12.0,
        )

        self.assertEqual(illiquid.reasonCode, "conditional_liquidity_failed")
        self.assertEqual(wide_spread.reasonCode, "conditional_spread_exceeded")

    def test_conditional_entry_rejects_excessive_adverse_drift(self) -> None:
        decision = self.evaluate(
            current_quote=quote(bid=100.29, ask=100.30),
            ready_after_seconds=12.0,
        )

        self.assertFalse(decision.passed)
        self.assertEqual(decision.reasonCode, "conditional_price_drift_exceeded")

    def test_conditional_entry_requires_stop_distance(self) -> None:
        signal = long_signal()
        signal["stopLossPrice"] = None

        decision = self.evaluate(signal=signal, ready_after_seconds=12.0)

        self.assertFalse(decision.passed)
        self.assertEqual(decision.reasonCode, "conditional_stop_distance_missing")

    def test_conditional_entry_recalculates_net_reward_risk(self) -> None:
        decision = self.evaluate(
            signal=long_signal(take_profit=104.0),
            ready_after_seconds=12.0,
        )

        self.assertFalse(decision.passed)
        self.assertEqual(decision.reasonCode, "conditional_reward_risk_below_2r")
        self.assertLess(decision.recalculatedNetRewardRisk or 99.0, 2.0)


if __name__ == "__main__":
    unittest.main()
