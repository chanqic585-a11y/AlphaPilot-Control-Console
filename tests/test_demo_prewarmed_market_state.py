from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from alphapilot_control_console.demo_prewarmed_market_state import (
    DemoPrewarmedMarketState,
)


NOW = datetime(2026, 7, 13, 0, 0, 1, tzinfo=UTC)
INSTRUMENTS = ("BTC-USDT-SWAP", "ETH-USDT-SWAP")


def candle(timestamp: int, close: float, *, confirmed: bool = True) -> dict:
    return {
        "timestamp": timestamp,
        "open": close - 0.5,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": 1000.0,
        "confirmed": confirmed,
    }


def snapshot(instrument: str, price: float) -> dict:
    return {
        "ok": True,
        "instId": instrument,
        "timeframe": "1h",
        "price": price,
        "bidPrice": price - 0.01,
        "askPrice": price + 0.01,
        "spreadPct": 0.0002,
        "generatedAt": NOW.isoformat(),
        "latestCandleAt": 2_000,
        "_confirmedCandles": [candle(1_000, price - 1), candle(2_000, price)],
    }


class DemoPrewarmedMarketStateTests(unittest.TestCase):
    def build_state(self) -> DemoPrewarmedMarketState:
        state = DemoPrewarmedMarketState(
            screening_limit=2,
            minimum_history=2,
            max_quote_age_seconds=5,
            clock=lambda: NOW,
        )
        state.seed_universe(
            {
                "marketScope": "okx_usdt_linear_perpetual_full_market",
                "totalInstrumentCount": 405,
                "liquidityEligibleCount": 375,
                "screeningPool": [
                    {"instId": instrument, "spreadPct": 0.0002}
                    for instrument in INSTRUMENTS
                ],
            },
            timeframes=("1h",),
        )
        for instrument in INSTRUMENTS:
            state.seed_metadata(
                instrument,
                {
                    "ok": True,
                    "instId": instrument,
                    "state": "live",
                    "ctVal": 0.01,
                    "lotSz": 1.0,
                    "minSz": 1.0,
                },
            )
            state.seed_snapshot(
                instrument,
                "1h",
                snapshot(instrument, 100.0 if instrument.startswith("ETH") else 60_000.0),
            )
        return state

    def test_unconfirmed_updates_do_not_emit_and_confirmed_close_emits_once(self) -> None:
        state = self.build_state()
        provisional = candle(3_000, 101.0, confirmed=False)
        confirmed = candle(3_000, 101.0, confirmed=True)

        self.assertIsNone(
            state.apply_candle("ETH-USDT-SWAP", "1h", provisional, received_at=NOW)
        )
        first = state.apply_candle(
            "ETH-USDT-SWAP", "1h", confirmed, received_at=NOW
        )
        duplicate = state.apply_candle(
            "ETH-USDT-SWAP", "1h", confirmed, received_at=NOW
        )

        self.assertIsNotNone(first)
        self.assertEqual(first.timeframe, "1h")
        self.assertEqual(first.candleStartMs, 3_000)
        self.assertIsNone(duplicate)

    def test_frozen_snapshot_does_not_change_after_live_ticker_update(self) -> None:
        state = self.build_state()
        frozen = state.freeze_for_timeframe("1h", received_at=NOW)

        state.apply_ticker(
            "ETH-USDT-SWAP",
            {
                "bidPrice": 109.99,
                "askPrice": 110.01,
                "price": 110.0,
                "spreadPct": 0.0002,
            },
            received_at=NOW + timedelta(milliseconds=100),
        )

        self.assertEqual(frozen.load_snapshot("ETH-USDT-SWAP", "1h", 260)["price"], 100.0)
        self.assertEqual(frozen.quote("ETH-USDT-SWAP")["askPrice"], 100.01)

    def test_factors_are_precomputed_once_when_confirmed_market_state_changes(self) -> None:
        state = self.build_state()
        seeded = state.freeze_for_timeframe("1h", received_at=NOW).load_snapshot(
            "ETH-USDT-SWAP", "1h", 260
        )

        state.apply_candle(
            "ETH-USDT-SWAP",
            "1h",
            candle(3_000, 101.0, confirmed=True),
            received_at=NOW,
        )
        updated = state.freeze_for_timeframe("1h", received_at=NOW).load_snapshot(
            "ETH-USDT-SWAP", "1h", 260
        )

        self.assertEqual(seeded["_precomputedFactors"]["close"], 100.0)
        self.assertEqual(updated["_precomputedFactors"]["close"], 101.0)

    def test_state_is_warm_only_when_every_required_public_input_exists(self) -> None:
        state = self.build_state()

        self.assertTrue(state.status()["warm"])
        self.assertTrue(state.status()["synchronized"])
        self.assertEqual(state.status()["readyInstrumentCount"], 2)

        incomplete = DemoPrewarmedMarketState(
            screening_limit=2,
            minimum_history=2,
            clock=lambda: NOW,
        )
        incomplete.seed_universe(
            {"screeningPool": [{"instId": value} for value in INSTRUMENTS]},
            timeframes=("1h",),
        )
        incomplete.seed_metadata("BTC-USDT-SWAP", {"ok": True, "instId": "BTC-USDT-SWAP"})
        incomplete.seed_snapshot("BTC-USDT-SWAP", "1h", snapshot("BTC-USDT-SWAP", 60_000.0))

        self.assertFalse(incomplete.status()["warm"])
        self.assertIn("ETH-USDT-SWAP", incomplete.status()["missingMetadata"])

    def test_stale_quote_makes_state_not_ready(self) -> None:
        state = self.build_state()
        state.set_clock(lambda: NOW + timedelta(seconds=6))

        status = state.status()

        self.assertFalse(status["warm"])
        self.assertIn("BTC-USDT-SWAP", status["staleQuotes"])

    def test_short_history_is_individually_ineligible_without_blocking_runtime(self) -> None:
        state = self.build_state()
        short = snapshot("ETH-USDT-SWAP", 100.0)
        short["_confirmedCandles"] = short["_confirmedCandles"][:1]
        state.seed_snapshot("ETH-USDT-SWAP", "1h", short)

        status = state.status()
        frozen = state.freeze_for_timeframe("1h", received_at=NOW)
        eth = frozen.load_snapshot("ETH-USDT-SWAP", "1h", 260)

        self.assertTrue(status["warm"])
        self.assertTrue(status["synchronized"])
        self.assertEqual(status["readyInstrumentCount"], 1)
        self.assertIn("ETH-USDT-SWAP:1h", status["insufficientHistory"])
        self.assertFalse(eth["historyReady"])
        self.assertEqual(eth["requiredHistoryCount"], 2)

    def test_credential_like_fields_are_rejected(self) -> None:
        state = DemoPrewarmedMarketState(screening_limit=1, minimum_history=1)

        with self.assertRaisesRegex(ValueError, "credential"):
            state.seed_universe(
                {
                    "screeningPool": [{"instId": "BTC-USDT-SWAP"}],
                    "apiKey": "must-not-enter-public-state",
                },
                timeframes=("1h",),
            )


if __name__ == "__main__":
    unittest.main()
