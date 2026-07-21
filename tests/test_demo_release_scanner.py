from __future__ import annotations

import time
import unittest
from unittest.mock import patch

from alphapilot_control_console.demo_release_scanner import scan_immutable_demo_release
from alphapilot_control_console.strategy_validation_hashing import stable_hash


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
                "parameters": {"targetRewardRiskRatio": 1.25},
            },
        },
    }


def advisory_contract(mode: str) -> dict:
    release = contract()
    if mode == "fixed_r":
        parameters = {"targetR": 1.25}
    else:
        parameters = {
            "structureRule": {
                "kind": "event_reversal",
                "confirmationBars": 2,
            }
        }
    policy = {
        "version": "advisory_r_exit_policy_v1",
        "mode": mode,
        "maximumHoldBars": 24,
        "initialStopMayWiden": False,
        "parameters": parameters,
    }
    release["strategy"].update(
        {
            "schemaVersion": "strategy_workflow_definition_v2",
            "exitPolicy": policy,
            "exitPolicyHash": stable_hash(policy, "exit_policy"),
        }
    )
    return release


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
    def test_scanner_uses_prewarmed_precomputed_factors(self) -> None:
        prewarmed = snapshot("BTC-USDT-SWAP", "1h", 100)
        prewarmed["_precomputedFactors"] = {"rsi_14": 55.0}

        with patch(
            "alphapilot_control_console.demo_release_scanner._rsi",
            side_effect=AssertionError("indicators must not be recomputed"),
        ):
            result = scan_immutable_demo_release(
                contract(),
                snapshot_loader=lambda *_args: prewarmed,
                metadata_loader=metadata,
            )

        self.assertEqual(result["blockers"], [])
        self.assertEqual(len(result["signals"]), 1)

    def test_missing_prewarmed_snapshot_fails_closed_without_rest_fallback(self) -> None:
        result = scan_immutable_demo_release(
            contract(),
            snapshot_loader=lambda *_args: {
                "ok": False,
                "prewarmedMarketMissing": True,
                "errors": ["prewarmed_market_snapshot_missing"],
            },
            metadata_loader=metadata,
        )

        self.assertEqual(result["signals"], [])
        self.assertIn("prewarmed_market_snapshot_missing", result["blockers"])

    def test_instrument_with_short_history_is_rejected_without_blocking_batch(self) -> None:
        short = snapshot("BTC-USDT-SWAP", "1h", 100)
        short["historyReady"] = False
        short["requiredHistoryCount"] = 260

        result = scan_immutable_demo_release(
            contract(),
            snapshot_loader=lambda *_args: short,
            metadata_loader=metadata,
        )

        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["signals"], [])
        self.assertEqual(result["rejections"][0]["reason"], "insufficient_confirmed_history")

    def test_stale_quote_is_rejected_without_blocking_other_instruments(self) -> None:
        stale = snapshot("BTC-USDT-SWAP", "1h", 100)
        stale["quoteFresh"] = False

        result = scan_immutable_demo_release(
            contract(),
            snapshot_loader=lambda *_args: stale,
            metadata_loader=metadata,
        )

        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["signals"], [])
        self.assertEqual(result["rejections"][0]["reason"], "public_market_or_liquidity_gate_failed")
        self.assertFalse(result["rejections"][0]["quoteFresh"])

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
        self.assertEqual(signal["takeProfitPrice"] - signal["entryPrice"], 2.5)
        self.assertEqual(signal["entryPrice"] - signal["stopLossPrice"], 2.0)
        self.assertLessEqual(signal["notionalUsdt"], 250.0)
        self.assertFalse(result["createsOrder"])

    def test_advisory_fixed_r_below_two_is_not_clamped_by_demo_scanner(self) -> None:
        result = scan_immutable_demo_release(
            advisory_contract("fixed_r"),
            snapshot_loader=snapshot,
            metadata_loader=metadata,
        )

        self.assertEqual(result["blockers"], [])
        signal = result["signals"][0]
        self.assertEqual(signal["exitPolicyMode"], "fixed_r")
        self.assertEqual(signal["takeProfitPrice"] - signal["entryPrice"], 2.5)
        self.assertEqual(signal["exitPolicy"]["parameters"]["targetR"], 1.25)

    def test_advisory_structure_or_time_has_no_synthetic_two_r_target(self) -> None:
        result = scan_immutable_demo_release(
            advisory_contract("structure_or_time"),
            snapshot_loader=snapshot,
            metadata_loader=metadata,
        )

        self.assertEqual(result["blockers"], [])
        signal = result["signals"][0]
        self.assertEqual(signal["exitPolicyMode"], "structure_or_time")
        self.assertIsNone(signal["takeProfitPrice"])
        self.assertIsNone(signal["advisoryTargetR"])

    def test_advisory_scanner_rejects_incomplete_policy_before_market_call(self) -> None:
        release = advisory_contract("fixed_r")
        release["strategy"]["exitPolicyHash"] = "exit_policy_changed"
        calls = 0

        def forbidden_loader(_symbol: str, _timeframe: str, _limit: int) -> dict:
            nonlocal calls
            calls += 1
            return {}

        result = scan_immutable_demo_release(
            release,
            snapshot_loader=forbidden_loader,
            metadata_loader=metadata,
        )

        self.assertEqual(calls, 0)
        self.assertIn("exit_policy_incomplete", result["blockers"])

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

    def test_approved_portfolio_binding_expands_scanner_beyond_legacy_top100(self) -> None:
        release = contract()
        release["strategy"]["marketDefinition"] = {
            "timeframe": "1h",
            "universePolicy": {
                "mode": "okx_usdt_linear_perpetual_full_market",
                "screeningLimit": 100,
            },
        }
        release["portfolioRuntimeBinding"] = {
            "snapshotBindingMode": "policy_bound_daily_snapshot",
            "universePolicy": {
                "mode": "daily_frozen_top200",
                "policyId": "okx_demo_top200_liquid_usdt_swap_forward_v1",
                "policyHash": "top200-policy-hash",
                "maximumInstrumentCount": 200,
            },
        }
        instruments = [f"C{index:03d}-USDT-SWAP" for index in range(101)]
        calls: list[int] = []

        def universe_loader(limit: int) -> dict:
            calls.append(limit)
            return {
                "marketScope": "daily_frozen_top200",
                "totalInstrumentCount": 405,
                "liveUsdtLinearSwapCount": 375,
                "liquidityEligibleCount": 200,
                "screeningPool": [
                    {"instId": instrument, "quoteVolumeProxy": 200 - index}
                    for index, instrument in enumerate(instruments)
                ],
                "errors": [],
            }

        result = scan_immutable_demo_release(
            release,
            snapshot_loader=snapshot,
            metadata_loader=dynamic_metadata,
            universe_loader=universe_loader,
        )

        self.assertEqual(calls, [200])
        self.assertEqual(result["progress"]["required"], 101)
        self.assertEqual(result["universe"]["screeningLimit"], 200)

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
                "targetRewardRiskRatio": 1.25,
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
