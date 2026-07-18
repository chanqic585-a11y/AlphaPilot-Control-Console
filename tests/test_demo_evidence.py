from __future__ import annotations

import unittest

from alphapilot_control_console.demo_evidence import build_demo_evidence_checklist
from alphapilot_control_console.strategy_validation_hashing import stable_hash


def lifecycle_item(*, closed_samples: int = 5, trade_count: int = 42, target_r: float = 2.0) -> dict:
    return {
        "strategyId": "strategy-1",
        "metrics": {
            "closedSamples": closed_samples,
            "tradeCount": trade_count,
        },
        "optimizationContext": {
            "definition": {
                "schemaVersion": "strategy_workflow_definition_v1",
                "family": "squeeze_breakout",
                "direction": "long_research",
                "timeframe": "1d",
                "targetR": target_r,
            },
            "parameters": {
                "atrMultiplier": 2.0,
                "targetRewardRiskRatio": target_r,
                "maxHoldBars": 16,
            },
        },
    }


def advisory_lifecycle_item(*, policy: dict | None = None) -> dict:
    exit_policy = policy or {
        "version": "advisory_r_exit_policy_v1",
        "mode": "fixed_r",
        "maximumHoldBars": 48,
        "initialStopMayWiden": False,
        "parameters": {"targetR": 1.25},
    }
    return {
        "strategyId": "advisory-strategy-1",
        "metrics": {"closedSamples": 30, "tradeCount": 42},
        "optimizationContext": {
            "definition": {
                "schemaVersion": "strategy_workflow_definition_v2",
                "family": "event_continuation",
                "direction": "long_research",
                "timeframe": "1h",
                "exitPolicy": exit_policy,
                "exitPolicyHash": stable_hash(exit_policy, "exit_policy"),
            },
            "parameters": {"atrMultiplier": 1.2},
        },
    }


class DemoEvidenceTests(unittest.TestCase):
    def test_checklist_is_permanent_and_explains_automatic_and_manual_evidence(self) -> None:
        result = build_demo_evidence_checklist(
            lifecycle_item(),
            contract=None,
            runtime={
                "credentialsConfigured": False,
                "privateEnabled": False,
                "orderEnabled": False,
                "automationReady": False,
                "closedTradeCount": 0,
            },
        )

        items = {item["evidenceId"]: item for item in result["items"]}
        self.assertEqual(
            set(items),
            {
                "formal_backtest",
                "target_reward_risk",
                "strategy_definition",
                "local_forward_samples",
                "formal_strategy_candidate",
                "immutable_demo_release",
                "demo_runtime",
                "demo_closed_trades",
            },
        )
        self.assertEqual(items["formal_backtest"]["status"], "passed")
        self.assertEqual(items["formal_backtest"]["current"], 42)
        self.assertEqual(items["formal_backtest"]["sourceType"], "automatic")
        self.assertEqual(items["local_forward_samples"]["status"], "missing")
        self.assertEqual(items["local_forward_samples"]["current"], 5)
        self.assertEqual(items["local_forward_samples"]["target"], 30)
        self.assertTrue(items["local_forward_samples"]["blocking"])
        self.assertEqual(items["demo_runtime"]["sourceType"], "manual_runtime")
        self.assertIn("启动", items["demo_runtime"]["nextAction"])
        self.assertGreater(result["summary"]["blockingCount"], 0)

    def test_experimental_override_marks_only_forward_samples_bypassed(self) -> None:
        contract = {
            "demoReleaseId": "release-1",
            "strategyCandidateId": "strategy-1",
            "releaseMode": "experimental_override",
            "livePromotionAllowed": False,
        }

        result = build_demo_evidence_checklist(
            lifecycle_item(closed_samples=0),
            contract=contract,
            runtime={"automationReady": False, "closedTradeCount": 0},
        )

        items = {item["evidenceId"]: item for item in result["items"]}
        self.assertEqual(items["local_forward_samples"]["status"], "bypassed")
        self.assertEqual(items["local_forward_samples"]["sourceType"], "controlled_override")
        self.assertFalse(items["local_forward_samples"]["blocking"])
        self.assertEqual(items["formal_backtest"]["status"], "passed")
        self.assertEqual(items["target_reward_risk"]["status"], "passed")
        self.assertEqual(items["formal_strategy_candidate"]["status"], "passed")
        self.assertEqual(items["immutable_demo_release"]["status"], "passed")
        self.assertFalse(contract["livePromotionAllowed"])

    def test_engineering_smoke_cannot_count_as_strategy_demo_evidence(self) -> None:
        result = build_demo_evidence_checklist(
            lifecycle_item(),
            contract=None,
            runtime={
                "evidenceClass": "demo_engineering_smoke",
                "closedTradeCount": 99,
                "credentialsConfigured": True,
                "privateEnabled": True,
                "orderEnabled": True,
                "automationReady": True,
            },
        )

        items = {item["evidenceId"]: item for item in result["items"]}
        self.assertEqual(items["demo_closed_trades"]["current"], 0)
        self.assertEqual(items["demo_closed_trades"]["status"], "pending")
        self.assertFalse(items["demo_closed_trades"]["blocking"])

    def test_advisory_policy_replaces_fixed_two_r_demo_gate(self) -> None:
        result = build_demo_evidence_checklist(
            advisory_lifecycle_item(),
            contract=None,
            runtime={"automationReady": False, "closedTradeCount": 0},
        )

        item = {row["evidenceId"]: row for row in result["items"]}["target_reward_risk"]
        self.assertEqual(item["status"], "passed")
        self.assertFalse(item["blocking"])
        self.assertEqual(item["current"], "fixed_r")
        self.assertEqual(item["target"], "完整且不可变的 Exit Policy")

    def test_incomplete_advisory_policy_remains_blocking(self) -> None:
        incomplete = {
            "version": "advisory_r_exit_policy_v1",
            "mode": "structure_or_time",
            "maximumHoldBars": 48,
            "initialStopMayWiden": False,
        }
        result = build_demo_evidence_checklist(
            advisory_lifecycle_item(policy=incomplete),
            contract=None,
            runtime={"automationReady": False},
        )

        item = {row["evidenceId"]: row for row in result["items"]}["target_reward_risk"]
        self.assertEqual(item["status"], "missing")
        self.assertTrue(item["blocking"])


if __name__ == "__main__":
    unittest.main()
