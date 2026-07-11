from __future__ import annotations

import unittest

from alphapilot_control_console.exchange_connectors.public_exchange_registry import fetch_okx_public_payload
from alphapilot_control_console.okx_market_universe import build_okx_usdt_swap_universe


class OkxMarketUniverseTests(unittest.TestCase):
    def test_filters_live_usdt_linear_swaps_and_ranks_liquid_contracts(self) -> None:
        instruments = [
            {"instId": "BTC-USDT-SWAP", "instType": "SWAP", "ctType": "linear", "settleCcy": "USDT", "state": "live"},
            {"instId": "ETH-USDT-SWAP", "instType": "SWAP", "ctType": "linear", "settleCcy": "USDT", "state": "live"},
            {"instId": "SOL-USDT-SWAP", "instType": "SWAP", "ctType": "linear", "settleCcy": "USDT", "state": "live"},
            {"instId": "OLD-USDT-SWAP", "instType": "SWAP", "ctType": "linear", "settleCcy": "USDT", "state": "suspend"},
            {"instId": "BTC-USD-SWAP", "instType": "SWAP", "ctType": "inverse", "settleCcy": "BTC", "state": "live"},
        ]
        tickers = [
            {"instId": "BTC-USDT-SWAP", "last": "60000", "bidPx": "59999", "askPx": "60001", "volCcy24h": "1000"},
            {"instId": "ETH-USDT-SWAP", "last": "3000", "bidPx": "2999", "askPx": "3001", "volCcy24h": "10000"},
            {"instId": "SOL-USDT-SWAP", "last": "100", "bidPx": "90", "askPx": "110", "volCcy24h": "50000"},
            {"instId": "OLD-USDT-SWAP", "last": "1", "bidPx": "0.99", "askPx": "1.01", "volCcy24h": "100000"},
        ]

        result = build_okx_usdt_swap_universe(instruments, tickers, screening_limit=1)

        self.assertEqual(result["totalInstrumentCount"], 5)
        self.assertEqual(result["usdtLinearSwapCount"], 4)
        self.assertEqual(result["liveUsdtLinearSwapCount"], 3)
        self.assertEqual(result["liquidityEligibleCount"], 2)
        self.assertEqual([row["instId"] for row in result["rankedInstruments"]], [
            "BTC-USDT-SWAP",
            "ETH-USDT-SWAP",
        ])
        self.assertEqual([row["instId"] for row in result["screeningPool"]], ["BTC-USDT-SWAP"])
        self.assertEqual(result["progress"]["completed"], 5)
        self.assertEqual(result["progress"]["required"], 5)
        reasons = {row["instId"]: row["reason"] for row in result["rejections"]}
        self.assertEqual(reasons["SOL-USDT-SWAP"], "spread_too_wide")
        self.assertEqual(reasons["OLD-USDT-SWAP"], "instrument_not_live")
        self.assertEqual(reasons["BTC-USD-SWAP"], "not_usdt_linear_swap")
        self.assertTrue(result["publicMarketOnly"])
        self.assertFalse(result["createsOrder"])

    def test_missing_ticker_is_rejected_without_fabricated_values(self) -> None:
        result = build_okx_usdt_swap_universe(
            [{"instId": "XRP-USDT-SWAP", "instType": "SWAP", "ctType": "linear", "settleCcy": "USDT", "state": "live"}],
            [],
        )

        self.assertEqual(result["liquidityEligibleCount"], 0)
        self.assertEqual(result["rankedInstruments"], [])
        self.assertEqual(result["rejections"][0]["reason"], "ticker_missing")

    def test_public_fetch_helper_rejects_private_okx_paths_before_network_access(self) -> None:
        result = fetch_okx_public_payload("/api/v5/account/balance")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "okx_public_path_not_allowed")
        self.assertFalse(result["privateEndpointsUsed"])


if __name__ == "__main__":
    unittest.main()
