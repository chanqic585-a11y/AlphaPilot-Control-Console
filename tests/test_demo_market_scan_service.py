from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import alphapilot_control_console.state_store as state_store
from alphapilot_control_console.demo_market_scan_service import (
    get_demo_strategy_market_scan,
    scan_demo_strategy_public_universe,
)


class DemoMarketScanServiceTests(unittest.TestCase):
    def test_public_full_market_scan_is_persisted_without_fake_strategy_match(self) -> None:
        universe = {
            "marketScope": "okx_usdt_linear_perpetual_full_market",
            "totalInstrumentCount": 120,
            "liveUsdtLinearSwapCount": 98,
            "liquidityEligibleCount": 40,
            "screeningLimit": 20,
            "screeningPool": [
                {"instId": "BTC-USDT-SWAP", "quoteVolumeProxy": 100, "spreadPct": 0.0001},
                {"instId": "ETH-USDT-SWAP", "quoteVolumeProxy": 80, "spreadPct": 0.0002},
            ],
            "progress": {"status": "completed", "completed": 120, "required": 120, "percent": 100},
            "errors": [],
        }
        with tempfile.TemporaryDirectory() as directory, patch.object(
            state_store, "STATE_PATH", Path(directory) / "console_state.json"
        ), patch.object(state_store, "AUDIT_PATH", Path(directory) / "audit.jsonl"):
            result = scan_demo_strategy_public_universe(
                "strategy-1",
                universe_loader=lambda _limit: universe,
            )
            loaded = get_demo_strategy_market_scan("strategy-1")

        self.assertTrue(result["ok"])
        self.assertEqual(result["scan"]["marketScope"], "okx_usdt_linear_perpetual_full_market")
        self.assertEqual(result["scan"]["totalInstrumentCount"], 120)
        self.assertEqual(result["scan"]["currentTopCandidate"], "BTC-USDT-SWAP")
        self.assertIsNone(result["scan"]["strategyMatchedCount"])
        self.assertEqual(loaded["currentTopCandidate"], "BTC-USDT-SWAP")
        self.assertFalse(result["createsOrder"])


if __name__ == "__main__":
    unittest.main()
