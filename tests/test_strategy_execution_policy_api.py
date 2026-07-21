from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.risk_profile_store import RiskProfileStore
from alphapilot_control_console.strategy_execution_policy_api import (
    StrategyExecutionPolicyApi,
)
from alphapilot_control_console.strategy_execution_policy_store import (
    STRATEGY_POLICY_ACTIVATION_CONFIRMATION,
    StrategyExecutionPolicyStore,
)


class StrategyExecutionPolicyApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.risk_store = RiskProfileStore(root / "risk.sqlite")
        self.store = StrategyExecutionPolicyStore(
            root / "policies.sqlite",
            risk_profile_store=self.risk_store,
        )
        self.api = StrategyExecutionPolicyApi(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.risk_store.close()
        self.temp_dir.cleanup()

    @staticmethod
    def _policy() -> dict:
        return {
            "schemaVersion": "strategy_execution_policy_v1",
            "policyKey": "okx_demo:strategy-a",
            "environment": "okx_demo",
            "strategyId": "strategy-a",
            "releaseId": "release-a",
            "releaseHash": "release-hash-a",
            "name": "Strategy A Demo",
            "allocationUsdt": 250.0,
            "maxOrderNotionalUsdt": 50.0,
            "riskPerTradePercent": 0.2,
            "riskPerTradeUsdt": 2.0,
            "maxLeverage": 1,
            "marginMode": "isolated",
            "maxConcurrentPositions": 2,
            "maxPositionsPerSymbol": 1,
            "scanTopN": 100,
            "minimumQuoteTurnoverUsdt": 1_000_000.0,
            "minimumDepthNotionalUsdt": 25_000.0,
            "targetSignalToOrderSeconds": 5.0,
            "maximumSignalAgeSeconds": 10.0,
            "criticalLatencyFailureSeconds": 20.0,
            "orderAckTimeoutSeconds": 5.0,
            "cooldownAfterLossMinutes": 60,
            "feeRate": 0.0005,
            "slippageRate": 0.0002,
            "stopPolicy": {"type": "atr", "atrMultiple": 1.2, "maximumLossR": 1.0},
            "exitPolicy": {
                "type": "hybrid_trailing",
                "initialTargetR": 2.0,
                "trailingAtrMultiple": 1.5,
            },
        }

    def test_create_list_revise_and_exact_activate_without_enabling_execution(self) -> None:
        created = self.api.post(
            "/api/strategy-execution-policies",
            {"policy": self._policy()},
        )
        policy_id = created["policy"]["policyId"]

        listed = self.api.get(
            "/api/strategy-execution-policies",
            {"environment": ["okx_demo"]},
        )
        self.assertEqual(len(listed["policies"]), 1)

        revised = self.api.post(
            f"/api/strategy-execution-policies/{policy_id}/revisions",
            {"changes": {"maxOrderNotionalUsdt": 40.0}},
        )
        self.assertEqual(revised["policy"]["classification"], "lower_risk")

        activated = self.api.post(
            f"/api/strategy-execution-policies/{policy_id}/activate",
            {
                "confirmation": STRATEGY_POLICY_ACTIVATION_CONFIRMATION,
                "reason": "operator_exact_activation",
            },
        )
        self.assertTrue(activated["ok"])
        self.assertFalse(activated["executionEnabled"])
        self.assertEqual(
            self.api.get(
                f"/api/strategy-execution-policies/{policy_id}",
                {},
            )["policy"]["status"],
            "active",
        )

    def test_bootstrap_creates_one_safe_initial_draft_without_execution(self) -> None:
        identity = {
            "environment": "okx_demo",
            "strategyId": "strategy-a",
            "releaseId": "release-a",
            "releaseHash": "release-hash-a",
            "name": "Strategy A Demo",
        }

        created = self.api.post(
            "/api/strategy-execution-policies/bootstrap",
            {"identity": identity},
        )
        repeated = self.api.post(
            "/api/strategy-execution-policies/bootstrap",
            {"identity": identity},
        )

        self.assertTrue(created["ok"])
        self.assertFalse(created["executionEnabled"])
        self.assertEqual(created["policy"]["policyId"], repeated["policy"]["policyId"])
        self.assertEqual(created["policy"]["classification"], "initial")
        self.assertEqual(created["policy"]["status"], "draft")
        self.assertEqual(created["policy"]["policy"]["scanTopN"], 200)
        self.assertEqual(created["policy"]["policy"]["marginMode"], "isolated")
        self.assertEqual(len(self.store.list_policies(strategy_id="strategy-a")), 1)

    def test_bootstrap_rejects_sensitive_identity_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "Credential-like"):
            self.api.post(
                "/api/strategy-execution-policies/bootstrap",
                {
                    "identity": {
                        "environment": "okx_demo",
                        "strategyId": "strategy-a",
                        "releaseId": "release-a",
                        "releaseHash": "release-hash-a",
                        "name": "Strategy A Demo",
                        "apiKey": "forbidden",
                    }
                },
            )

    def test_rejects_sensitive_fields_and_unknown_routes(self) -> None:
        with self.assertRaisesRegex(ValueError, "Credential-like"):
            self.api.post(
                "/api/strategy-execution-policies",
                {"policy": {**self._policy(), "apiKey": "forbidden"}},
            )
        with self.assertRaises(KeyError):
            self.api.get("/api/strategy-execution-policies/missing", {})
        with self.assertRaises(KeyError):
            self.api.post("/api/strategy-execution-policies/missing/action", {})


if __name__ == "__main__":
    unittest.main()
