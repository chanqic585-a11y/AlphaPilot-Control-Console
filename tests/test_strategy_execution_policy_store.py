from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.risk_profile_store import RiskProfileStore
from alphapilot_control_console.strategy_execution_policy_store import (
    STRATEGY_POLICY_ACTIVATION_CONFIRMATION,
    StrategyExecutionPolicyStore,
)


class StrategyExecutionPolicyStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.risk_store = RiskProfileStore(self.root / "risk.sqlite")
        self.store = StrategyExecutionPolicyStore(
            self.root / "strategy-policies.sqlite",
            risk_profile_store=self.risk_store,
        )

    def tearDown(self) -> None:
        self.store.close()
        self.risk_store.close()
        self.temp_dir.cleanup()

    @staticmethod
    def _policy(**overrides: object) -> dict:
        policy = {
            "schemaVersion": "strategy_execution_policy_v1",
            "policyKey": "okx_demo:portfolio-v62",
            "environment": "okx_demo",
            "strategyId": "portfolio-v62",
            "releaseId": "release-v62",
            "releaseHash": "release-hash-v62",
            "name": "Portfolio V62 Demo",
            "allocationUsdt": 300.0,
            "maxOrderNotionalUsdt": 75.0,
            "riskPerTradePercent": 0.20,
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
            "stopPolicy": {
                "type": "atr",
                "atrMultiple": 1.2,
                "maximumLossR": 1.0,
            },
            "exitPolicy": {
                "type": "hybrid_trailing",
                "initialTargetR": 2.0,
                "trailingAtrMultiple": 1.5,
                "partialTakeProfitR": 1.0,
                "partialTakeProfitPercent": 50.0,
            },
        }
        policy.update(overrides)
        return policy

    def test_creates_immutable_version_and_deterministic_identity(self) -> None:
        created = self.store.create_policy(self._policy())
        repeated = self.store.create_policy(self._policy(version=1))

        self.assertEqual(created["policyId"], repeated["policyId"])
        self.assertEqual(created["version"], 1)
        self.assertEqual(len(created["contentHash"]), 64)
        self.assertEqual(created["classification"], "initial")
        self.assertEqual(created["status"], "draft")

        with self.assertRaisesRegex(ValueError, "already exists"):
            self.store.create_policy(self._policy(version=1, maxLeverage=2))

    def test_lower_risk_revision_can_activate_without_execution_side_effect(self) -> None:
        first = self.store.create_policy(self._policy())
        self.store.activate(
            first["policyId"],
            actor="user_manual",
            confirmation=STRATEGY_POLICY_ACTIVATION_CONFIRMATION,
            reason="initial_exact_activation",
        )

        revision = self.store.create_revision(
            first["policyId"],
            {"maxOrderNotionalUsdt": 50.0, "riskPerTradeUsdt": 1.5},
        )
        result = self.store.activate(
            revision["policyId"],
            actor="user_manual",
            confirmation="",
            reason="reduce_demo_risk",
        )

        self.assertEqual(revision["version"], 2)
        self.assertEqual(revision["parentPolicyId"], first["policyId"])
        self.assertEqual(revision["classification"], "lower_risk")
        self.assertEqual(result["activePolicy"]["policyId"], revision["policyId"])
        self.assertFalse(result["executionEnabled"])

    def test_risk_increase_and_exit_semantics_require_exact_approval(self) -> None:
        first = self.store.create_policy(self._policy())
        self.store.activate(
            first["policyId"],
            actor="user_manual",
            confirmation=STRATEGY_POLICY_ACTIVATION_CONFIRMATION,
            reason="initial_exact_activation",
        )
        higher = self.store.create_revision(first["policyId"], {"maxLeverage": 2})
        changed_exit = self.store.create_revision(
            first["policyId"],
            {"exitPolicy": {"type": "fixed_r", "targetR": 1.5}},
        )

        self.assertEqual(higher["classification"], "higher_risk")
        self.assertEqual(changed_exit["classification"], "execution_semantics_change")
        for policy in (higher, changed_exit):
            with self.assertRaisesRegex(PermissionError, "Exact"):
                self.store.activate(
                    policy["policyId"],
                    actor="user_manual",
                    confirmation="",
                    reason="missing_confirmation",
                )

    def test_rejects_sensitive_or_account_limit_breaching_policy(self) -> None:
        with self.assertRaisesRegex(ValueError, "Credential-like"):
            self.store.create_policy(self._policy(apiKey="must-not-be-stored"))
        with self.assertRaisesRegex(ValueError, "account RiskProfile"):
            self.store.create_policy(self._policy(maxLeverage=5))
        with self.assertRaisesRegex(ValueError, "latency"):
            self.store.create_policy(
                self._policy(
                    targetSignalToOrderSeconds=12.0,
                    maximumSignalAgeSeconds=10.0,
                )
            )


if __name__ == "__main__":
    unittest.main()
