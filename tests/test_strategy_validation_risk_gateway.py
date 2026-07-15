from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_validation_risk_gateway import StrategyValidationRiskGateway
from alphapilot_control_console.strategy_validation_risk_store import StrategyValidationRiskStore
from tests.strategy_validation_fixtures import make_risk_profile


class StrategyValidationRiskGatewayTests(unittest.TestCase):
    def test_limit_breach_persists_pause_and_manual_resume_does_not_change_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StrategyValidationRiskStore(Path(directory) / "risk.sqlite")
            gateway = StrategyValidationRiskGateway(store)
            profile = make_risk_profile()

            rejected = gateway.evaluate(
                releaseId="release-1",
                profile=profile,
                requestedRiskR=0.25,
                snapshot={
                    "openRiskR": 0.0,
                    "singleSymbolRiskR": 0.0,
                    "correlatedClusterRiskR": 0.0,
                    "openPositionCount": 0,
                    "dailyLossR": 1.1,
                    "weeklyLossR": 1.1,
                    "consecutiveLosses": 1,
                    "demoDrawdownPct": 1.0,
                    "marginUtilizationPct": 10.0,
                    "reconciliationHealthy": True,
                    "dataFresh": True,
                },
            )

            self.assertFalse(rejected["passed"])
            self.assertTrue(store.state()["paused"])
            resumed = store.manual_resume(reason="Issue reviewed locally", actor="human_local_operator")
            self.assertFalse(resumed["paused"])
            self.assertEqual(profile["riskPerTradeR"], 0.25)
            store.close()

    def test_data_staleness_and_open_risk_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StrategyValidationRiskStore(Path(directory) / "risk.sqlite")
            gateway = StrategyValidationRiskGateway(store)
            profile = make_risk_profile()
            result = gateway.evaluate(
                releaseId="release-1",
                profile=profile,
                requestedRiskR=0.25,
                snapshot={
                    "openRiskR": 0.4,
                    "singleSymbolRiskR": 0.2,
                    "correlatedClusterRiskR": 0.4,
                    "openPositionCount": 1,
                    "dailyLossR": 0.0,
                    "weeklyLossR": 0.0,
                    "consecutiveLosses": 0,
                    "demoDrawdownPct": 0.0,
                    "marginUtilizationPct": 10.0,
                    "reconciliationHealthy": True,
                    "dataFresh": False,
                },
            )
            self.assertFalse(result["passed"])
            self.assertIn("maximum_open_risk", result["blockers"])
            self.assertIn("data_stale", result["blockers"])
            store.close()


if __name__ == "__main__":
    unittest.main()
