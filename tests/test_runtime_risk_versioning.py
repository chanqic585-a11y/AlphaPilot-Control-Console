from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.demo_strategy_runtime_settings import (
    apply_runtime_risk_profile,
)
from alphapilot_control_console.risk_profile_store import RiskProfileStore


EXPECTED_RUNTIME_FIELDS = {
    "allocatedCapital",
    "riskPerTradePercent",
    "riskPerTradeUSDT",
    "maximumPortfolioOpenRiskPercent",
    "maximumPortfolioOpenRiskUSDT",
    "maximumConcurrentPositions",
    "maximumInstrumentRisk",
    "maximumSameDirectionRisk",
    "maximumCorrelationClusterRisk",
    "maximumPortfolioBeta",
    "maximumLeverage",
    "marginMode",
    "dailyLossLimit",
    "programLossLimit",
    "hardKillLossLimit",
    "scanTopN",
}


class RuntimeRiskVersioningTests(unittest.TestCase):
    def test_runtime_contract_projects_all_adjustable_fields_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RiskProfileStore(Path(directory) / "risk.sqlite")
            contract = store.get_runtime_risk_contract("okx_demo")
            store.close()

        self.assertEqual(set(contract["fields"]), EXPECTED_RUNTIME_FIELDS)
        for field in contract["fields"].values():
            self.assertIn("currentValue", field)
            self.assertIn("suggestedValue", field)
            self.assertIn("minimumAllowed", field)
            self.assertIn("maximumAllowed", field)
            self.assertEqual(field["effectiveAt"], "next_new_order")
            self.assertEqual(field["changeMode"], "runtime_overlay_hash")
        self.assertEqual(contract["fields"]["allocatedCapital"]["currentValue"], 1000.0)
        self.assertEqual(contract["fields"]["scanTopN"]["maximumAllowed"], 200)
        self.assertFalse(contract["executionEnabled"])

    def test_canonical_runtime_fields_apply_and_are_capped_by_frozen_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RiskProfileStore(Path(directory) / "risk.sqlite")
            created = store.create_runtime_overlay(
                "okx_demo",
                {
                    "allocatedCapital": 500.0,
                    "riskPerTradeUSDT": 1.0,
                    "maximumPortfolioOpenRiskUSDT": 5.0,
                    "maximumConcurrentPositions": 2,
                    "maximumPortfolioBeta": 0.8,
                    "scanTopN": 100,
                },
                actor="user_manual",
                reason="reduce_demo_runtime",
            )
            contract = store.get_runtime_risk_contract("okx_demo")
            with self.assertRaises(ValueError):
                store.create_runtime_overlay(
                    "okx_demo",
                    {"scanTopN": 201},
                    actor="user_manual",
                    reason="exceeds_frozen_scan_cap",
                )
            store.close()

        self.assertEqual(created["status"], "applied")
        self.assertEqual(created["effectiveProfile"]["capitalLimitUsdt"], 500.0)
        self.assertEqual(created["effectiveProfile"]["riskPerTradeUsdt"], 1.0)
        self.assertEqual(created["effectiveProfile"]["scanTopN"], 100)
        self.assertEqual(contract["fields"]["scanTopN"]["currentValue"], 100)

    def test_runtime_profile_is_applied_to_new_demo_contract_without_mutation(self) -> None:
        original = {
            "riskEnvelope": {
                "initialEquityUsdt": 1000.0,
                "riskPerTradePercent": 0.25,
                "maxConcurrentPositions": 3,
                "maxLeverage": 2,
            },
            "portfolioRuntimeBinding": {
                "universePolicy": {
                    "mode": "daily_frozen_top200",
                    "maximumInstrumentCount": 200,
                }
            },
        }
        updated = apply_runtime_risk_profile(
            original,
            {
                "capitalLimitUsdt": 500.0,
                "riskPerTradePercent": 0.1,
                "riskPerTradeUsdt": 0.5,
                "maxOpenRiskPercent": 0.5,
                "maxOpenRiskUsdt": 2.5,
                "maxConcurrentPositions": 2,
                "maxSymbolOpenRiskPercent": 0.25,
                "maxDirectionOpenRiskPercent": 0.5,
                "maxCorrelatedOpenRiskPercent": 0.5,
                "maxPortfolioBeta": 0.8,
                "maxLeverage": 1,
                "marginMode": "isolated",
                "dailyLossStopPercent": 1.0,
                "maxDrawdownStopPercent": 2.5,
                "canaryLossStopUsdt": 10.0,
                "scanTopN": 100,
            },
            runtime_overlay_hash="runtime_hash_1",
        )

        self.assertEqual(original["riskEnvelope"]["initialEquityUsdt"], 1000.0)
        self.assertEqual(updated["riskEnvelope"]["initialEquityUsdt"], 500.0)
        self.assertEqual(updated["riskEnvelope"]["riskPerTradeUsdt"], 0.5)
        self.assertEqual(updated["riskEnvelope"]["runtimeRiskOverlayHash"], "runtime_hash_1")
        self.assertEqual(
            updated["portfolioRuntimeBinding"]["universePolicy"]["maximumInstrumentCount"],
            100,
        )

    def test_lower_risk_applies_to_new_orders_without_enabling_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RiskProfileStore(Path(directory) / "risk.sqlite")
            active = store.get_active_profile("okx_demo")

            created = store.create_runtime_overlay(
                "okx_demo",
                {
                    "maxOrderNotionalUsdt": 100.0,
                    "riskPerTradePercent": 0.1,
                    "maxConcurrentPositions": 2,
                },
                actor="user_manual",
                reason="reduce_demo_risk",
            )
            current = store.get_active_runtime_overlay("okx_demo")
            history = store.list_runtime_overlay_events("okx_demo")
            store.close()

        self.assertEqual(created["classification"], "risk_decrease_or_equal")
        self.assertEqual(created["status"], "applied")
        self.assertEqual(created["appliesTo"], "new_orders_only")
        self.assertFalse(created["executionEnabled"])
        self.assertEqual(current["runtimeRiskOverlayId"], created["runtimeRiskOverlayId"])
        self.assertEqual(current["effectiveProfile"]["maxOrderNotionalUsdt"], 100.0)
        self.assertEqual(current["baseRiskProfileId"], active["riskProfileId"])
        self.assertEqual(history[-1]["action"], "applied_risk_decrease")

    def test_risk_increase_requires_new_hash_and_exact_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RiskProfileStore(Path(directory) / "risk.sqlite")
            lowered = store.create_runtime_overlay(
                "okx_demo",
                {"maxOrderNotionalUsdt": 100.0},
                actor="user_manual",
                reason="lower_first",
            )
            increase = store.create_runtime_overlay(
                "okx_demo",
                {"maxOrderNotionalUsdt": 150.0},
                actor="user_manual",
                reason="request_increase",
            )

            self.assertEqual(increase["classification"], "risk_increase")
            self.assertEqual(increase["status"], "pending_exact_approval")
            self.assertNotEqual(increase["contentHash"], lowered["contentHash"])
            self.assertEqual(
                store.get_active_runtime_overlay("okx_demo")["runtimeRiskOverlayId"],
                lowered["runtimeRiskOverlayId"],
            )

            with self.assertRaises(PermissionError):
                store.approve_runtime_overlay(
                    increase["runtimeRiskOverlayId"],
                    actor="user_manual",
                    confirmation="wrong",
                    reason="unit_test",
                )

            approved = store.approve_runtime_overlay(
                increase["runtimeRiskOverlayId"],
                actor="user_manual",
                confirmation=(
                    "APPROVE_RUNTIME_RISK_OVERLAY:" + increase["contentHash"]
                ),
                reason="unit_test",
            )
            current = store.get_active_runtime_overlay("okx_demo")
            store.close()

        self.assertEqual(approved["status"], "applied")
        self.assertEqual(current["runtimeRiskOverlayId"], increase["runtimeRiskOverlayId"])
        self.assertEqual(current["effectiveProfile"]["maxOrderNotionalUsdt"], 150.0)

    def test_runtime_overlay_cannot_exceed_frozen_base_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RiskProfileStore(Path(directory) / "risk.sqlite")
            with self.assertRaises(ValueError):
                store.create_runtime_overlay(
                    "okx_demo",
                    {"maxOrderNotionalUsdt": 251.0},
                    actor="user_manual",
                    reason="exceeds_frozen_cap",
                )
            store.close()


if __name__ == "__main__":
    unittest.main()
