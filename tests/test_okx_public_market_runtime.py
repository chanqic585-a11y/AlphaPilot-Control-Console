from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime

from alphapilot_control_console.demo_prewarmed_market_state import (
    DemoPrewarmedMarketState,
)
from alphapilot_control_console.okx_public_market_runtime import (
    OKX_BUSINESS_WS_URL,
    OKX_PUBLIC_WS_URL,
    OkxPublicMarketRuntime,
)


NOW = datetime(2026, 7, 13, 0, 0, 1, tzinfo=UTC)
INSTRUMENTS = ("BTC-USDT-SWAP", "ETH-USDT-SWAP")


def universe_loader(limit: int) -> dict:
    return {
        "marketScope": "okx_usdt_linear_perpetual_full_market",
        "totalInstrumentCount": 405,
        "liquidityEligibleCount": 375,
        "screeningPool": [
            {"instId": value, "spreadPct": 0.0002}
            for value in INSTRUMENTS[:limit]
        ],
    }


def metadata_loader(instrument: str) -> dict:
    return {
        "ok": True,
        "instId": instrument,
        "state": "live",
        "ctVal": 0.01,
        "lotSz": 1.0,
        "minSz": 1.0,
    }


def snapshot_loader(instrument: str, timeframe: str, _limit: int) -> dict:
    price = 60_000.0 if instrument.startswith("BTC") else 100.0
    return {
        "ok": True,
        "instId": instrument,
        "timeframe": timeframe,
        "price": price,
        "bidPrice": price - 0.01,
        "askPrice": price + 0.01,
        "spreadPct": 0.0002,
        "generatedAt": NOW.isoformat(),
        "latestCandleAt": 2_000,
        "_confirmedCandles": [
            {
                "timestamp": timestamp,
                "open": price - 0.5,
                "high": price + 1.0,
                "low": price - 1.0,
                "close": price,
                "volume": 1000.0,
                "confirmed": True,
            }
            for timestamp in (1_000, 2_000)
        ],
    }


class OkxPublicMarketRuntimeTests(unittest.TestCase):
    def build_runtime(self) -> OkxPublicMarketRuntime:
        state = DemoPrewarmedMarketState(
            screening_limit=2,
            minimum_history=2,
            max_quote_age_seconds=5,
            clock=lambda: NOW,
        )
        return OkxPublicMarketRuntime(
            state=state,
            universe_loader=universe_loader,
            snapshot_loader=snapshot_loader,
            metadata_loader=metadata_loader,
            clock=lambda: NOW,
            subscription_batch_size=50,
        )

    def test_refresh_seeds_state_and_builds_separate_public_subscriptions(self) -> None:
        runtime = self.build_runtime()

        status = runtime.refresh_subscriptions([{"timeframe": "1h"}])
        batches = runtime.subscription_batches()

        self.assertTrue(status["seeded"])
        self.assertTrue(status["marketState"]["warm"])
        self.assertEqual({row["url"] for row in batches}, {OKX_PUBLIC_WS_URL, OKX_BUSINESS_WS_URL})
        ticker_args = [
            arg
            for row in batches
            if row["url"] == OKX_PUBLIC_WS_URL
            for arg in row["payload"]["args"]
        ]
        candle_args = [
            arg
            for row in batches
            if row["url"] == OKX_BUSINESS_WS_URL
            for arg in row["payload"]["args"]
        ]
        self.assertEqual({arg["channel"] for arg in ticker_args}, {"tickers"})
        self.assertEqual({arg["channel"] for arg in candle_args}, {"candle1H"})
        self.assertNotIn("login", json.dumps(batches).lower())
        self.assertNotIn("apikey", json.dumps(batches).lower())

    def test_confirmed_close_notifies_once_after_every_top_instrument_arrives(self) -> None:
        runtime = self.build_runtime()
        runtime.refresh_subscriptions([{"timeframe": "1h"}])
        events = []
        runtime.add_close_listener(events.append)

        runtime.handle_message(
            "business",
            {
                "arg": {"channel": "candle1H", "instId": "BTC-USDT-SWAP"},
                "data": [["3000", "1", "2", "0.5", "1.5", "10", "", "", "0"]],
            },
        )
        self.assertEqual(events, [])

        for instrument in INSTRUMENTS:
            runtime.handle_message(
                "business",
                {
                    "arg": {"channel": "candle1H", "instId": instrument},
                    "data": [["3000", "1", "2", "0.5", "1.5", "10", "", "", "1"]],
                },
            )
        runtime.handle_message(
            "business",
            {
                "arg": {"channel": "candle1H", "instId": "ETH-USDT-SWAP"},
                "data": [["3000", "1", "2", "0.5", "1.5", "10", "", "", "1"]],
            },
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].timeframe, "1h")
        self.assertEqual(events[0].candleStartMs, 3_000)
        self.assertEqual(events[0].sequenceId, "1h:3000")
        self.assertEqual(runtime.status()["lastConfirmedClose"]["sequenceId"], "1h:3000")

    def test_ticker_message_updates_executable_quote(self) -> None:
        runtime = self.build_runtime()
        runtime.refresh_subscriptions([{"timeframe": "1h"}])

        runtime.handle_message(
            "public",
            {
                "arg": {"channel": "tickers", "instId": "ETH-USDT-SWAP"},
                "data": [{"last": "101", "bidPx": "100.99", "askPx": "101.01"}],
            },
        )
        frozen = runtime.state.freeze_for_timeframe("1h", received_at=NOW)

        self.assertEqual(frozen.quote("ETH-USDT-SWAP")["price"], 101.0)
        self.assertEqual(frozen.quote("ETH-USDT-SWAP")["askPrice"], 101.01)

    def test_disconnect_blocks_runtime_until_both_public_connections_recover(self) -> None:
        runtime = self.build_runtime()
        runtime.refresh_subscriptions([{"timeframe": "1h"}])
        runtime.mark_connected("public")
        runtime.mark_connected("business")
        self.assertTrue(runtime.status()["warm"])

        runtime.mark_disconnected("business", "connection_lost")

        self.assertFalse(runtime.status()["warm"])
        self.assertIn("okx_business_websocket_disconnected", runtime.status()["blockers"])

    def test_reconnect_reseeds_before_restoring_readiness(self) -> None:
        runtime = self.build_runtime()
        runtime.refresh_subscriptions([{"timeframe": "1h"}])
        runtime.mark_connected("public")
        runtime.mark_connected("business")
        runtime.mark_disconnected("business", "connection_lost")
        sent: list[dict] = []

        class FakeSocket:
            def send(self, payload: str) -> None:
                sent.append(json.loads(payload))

        self.assertFalse(runtime.status()["seeded"])
        runtime._on_open("business", FakeSocket())

        self.assertTrue(runtime.status()["seeded"])
        self.assertTrue(runtime.status()["warm"])
        self.assertTrue(sent)
        self.assertEqual({arg["channel"] for row in sent for arg in row["args"]}, {"candle1H"})

    def test_connection_loop_uses_ping_and_pong_timeouts(self) -> None:
        runtime = self.build_runtime()
        runtime.refresh_subscriptions([{"timeframe": "1h"}])
        calls: list[tuple[int, int]] = []

        class FakeApp:
            def __init__(self, _url: str, **_callbacks: object) -> None:
                pass

            def run_forever(self, *, ping_interval: int, ping_timeout: int) -> None:
                calls.append((ping_interval, ping_timeout))
                runtime._stop.set()

        runtime.websocket_factory = FakeApp
        runtime._run_connection("public", OKX_PUBLIC_WS_URL)

        self.assertEqual(calls, [(20, 10)])

    def test_credential_like_message_is_rejected(self) -> None:
        runtime = self.build_runtime()
        runtime.refresh_subscriptions([{"timeframe": "1h"}])

        with self.assertRaisesRegex(ValueError, "credential"):
            runtime.handle_message("public", {"apiKey": "must-not-enter-runtime"})


if __name__ == "__main__":
    unittest.main()
