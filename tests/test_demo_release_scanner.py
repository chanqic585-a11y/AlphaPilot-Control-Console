from __future__ import annotations

import time
import unittest

from alphapilot_control_console.demo_release_scanner import scan_immutable_demo_release


def contract() -> dict:
    return {
        "demoReleaseId": "release-1",
        "strategyCandidateId": "candidate-1",
        "riskEnvelope": {
            "initialEquityUsdt": 1000.0,
            "riskPerTradePercent": 0.25,
            "maxOrderNotionalUsdt": 250.0,
            "defaultMaxLeverage": 2,
        },
        "strategy": {
            "familyKey": "trend",
            "marketDefinition": {
                "timeframe": "1h",
                "eligibleInstruments": ["BTC-USDT-SWAP"],
            },
            "forwardSignalPolicy": {
                "direction": "long",
                "rules": [{"factorId": "rsi_14", "operator": "gte", "threshold": 0}],
            },
        },
    }


def snapshot(_symbol: str, _timeframe: str, _limit: int) -> dict:
    now = int(time.time() * 1000)
    candles = [
        {
            "timestamp": now - (59 - index) * 3_600_000,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000.0,
            "confirmed": True,
        }
        for index in range(60)
    ]
    return {
        "ok": True,
        "price": 100.0,
        "bidPrice": 99.99,
        "askPrice": 100.01,
        "spreadPct": 0.0002,
        "atr14": 2.0,
        "latestCandleAt": now,
        "_confirmedCandles": candles,
    }


def metadata(_symbol: str) -> dict:
    return {
        "ok": True,
        "instId": "BTC-USDT-SWAP",
        "state": "live",
        "ctVal": 0.01,
        "lotSz": 1.0,
        "minSz": 1.0,
        "tickSz": 0.1,
    }


def dynamic_metadata(symbol: str) -> dict:
    return {
        **metadata(symbol),
        "instId": symbol,
    }


def trending_snapshot(_symbol: str, _timeframe: str, _limit: int) -> dict:
    now = int(time.time() * 1000)
    candles = []
    for index in range(260):
        close = 100.0 + index * 0.1
        candles.append(
            {
                "timestamp": now - (259 - index) * 86_400_000,
                "open": close - 0.05,
                "high": close + 0.05,
                "low": close - 0.15,
                "close": close,
                "volume": 1000.0,
                "confirmed": True,
            }
        )
    return {
        "ok": True,
        "price": candles[-1]["close"],
        "bidPrice": candles[-1]["close"] - 0.01,
        "askPrice": candles[-1]["close"] + 0.01,
        "spreadPct": 0.0002,
        "atr14": 0.2,
        "latestCandleAt": now,
        "_confirmedCandles": candles,
    }


class DemoReleaseScannerTests(unittest.TestCase):
    def test_scanner_binds_signal_to_release_and_sizes_from_public_metadata(self) -> None:
        result = scan_immutable_demo_release(
            contract(), snapshot_loader=snapshot, metadata_loader=metadata
        )

        self.assertEqual(result["blockers"], [])
        self.assertEqual(len(result["signals"]), 1)
        signal = result["signals"][0]
        self.assertEqual(signal["demoReleaseId"], "release-1")
        self.assertEqual(signal["strategyCandidateId"], "candidate-1")
        self.assertEqual(signal["source"], "immutable_release_scanner_v13_20")
        self.assertEqual(signal["takeProfitPrice"] - signal["entryPrice"], 4.0)
        self.assertEqual(signal["entryPrice"] - signal["stopLossPrice"], 2.0)
        self.assertLessEqual(signal["notionalUsdt"], 250.0)
        self.assertFalse(result["createsOrder"])

    def test_incomplete_release_policy_fails_closed_before_market_call(self) -> None:
        calls = 0

        def forbidden_loader(_symbol: str, _timeframe: str, _limit: int) -> dict:
            nonlocal calls
            calls += 1
            return {}

        result = scan_immutable_demo_release(
            {"strategy": {}},
            snapshot_loader=forbidden_loader,
            metadata_loader=metadata,
        )

        self.assertEqual(calls, 0)
        self.assertIn("release_market_definition_incomplete", result["blockers"])

    def test_dynamic_full_market_policy_uses_ranked_public_universe_and_reports_progress(self) -> None:
        release = contract()
        release["strategy"]["marketDefinition"] = {
            "timeframe": "1h",
            "universePolicy": {
                "mode": "okx_usdt_linear_perpetual_full_market",
                "screeningLimit": 2,
            },
        }
        calls: list[int] = []

        def universe_loader(limit: int) -> dict:
            calls.append(limit)
            return {
                "marketScope": "okx_usdt_linear_perpetual_full_market",
                "totalInstrumentCount": 123,
                "liveUsdtLinearSwapCount": 98,
                "liquidityEligibleCount": 40,
                "screeningPool": [
                    {"instId": "BTC-USDT-SWAP", "quoteVolumeProxy": 20},
                    {"instId": "ETH-USDT-SWAP", "quoteVolumeProxy": 10},
                ],
                "errors": [],
            }

        result = scan_immutable_demo_release(
            release,
            snapshot_loader=snapshot,
            metadata_loader=dynamic_metadata,
            universe_loader=universe_loader,
        )

        self.assertEqual(calls, [2])
        self.assertEqual({row["instId"] for row in result["signals"]}, {"BTC-USDT-SWAP", "ETH-USDT-SWAP"})
        self.assertEqual(result["universe"]["totalInstrumentCount"], 123)
        self.assertEqual(result["universe"]["liquidityEligibleCount"], 40)
        self.assertEqual(result["progress"]["completed"], 2)
        self.assertEqual(result["progress"]["required"], 2)
        self.assertEqual(result["progress"]["percent"], 100)
        self.assertEqual(result["progress"]["status"], "completed")

    def test_strategy_family_policy_scans_without_generic_placeholder_rules(self) -> None:
        release = contract()
        release["strategy"]["marketDefinition"] = {
            "timeframe": "1d",
            "eligibleInstruments": ["BTC-USDT-SWAP"],
        }
        release["strategy"]["forwardSignalPolicy"] = {
            "policyType": "strategy_family_params_v1",
            "family": "breakout",
            "direction": "long",
            "parameters": {
                "btcRegimes": ["bull"],
                "minVolumeRatio": 0.5,
                "rsiMin": 0,
                "rsiMax": 100,
                "breakoutMultiplier": 0.998,
                "atrMultiplier": 2.0,
                "btcReturn24hMinPct": -100,
                "btcReturn3dMinPct": -100,
            },
        }

        result = scan_immutable_demo_release(
            release,
            snapshot_loader=trending_snapshot,
            metadata_loader=dynamic_metadata,
        )

        self.assertEqual(result["blockers"], [])
        self.assertEqual(len(result["signals"]), 1)
        self.assertEqual(result["signals"][0]["instId"], "BTC-USDT-SWAP")
        self.assertEqual(result["signals"][0]["factorContext"]["policyType"], "strategy_family_params_v1")


if __name__ == "__main__":
    unittest.main()
