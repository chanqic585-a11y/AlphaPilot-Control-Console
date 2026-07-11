from __future__ import annotations

import unittest
from unittest.mock import patch

import alphapilot_control_console.demo_workflow_service as service


def lifecycle(stage: str, *, closed_samples: int = 0) -> dict:
    return {
        "items": [
            {
                "strategyId": "strategy-1",
                "displayName": "Strategy 1",
                "currentStage": stage,
                "metrics": {"closedSamples": closed_samples, "tradeCount": 50},
                "blockers": [],
            }
        ]
    }


def exchange_demo(*, candidate_status: str = "strategy_loaded", contract: bool = False, ready: bool = False) -> dict:
    contracts = []
    if contract:
        contracts.append(
            {
                "demoReleaseId": "release-1",
                "strategyCandidateId": "strategy-1",
                "status": "demo_eligible",
            }
        )
    return {
        "summary": {
            "credentialsConfigured": ready,
            "demoPrivateEnabled": ready,
            "demoOrderEnabled": ready,
        },
        "automationPipeline": {
            "summary": {},
            "candidates": [
                {
                    "strategyId": "strategy-1",
                    "instId": "BTC-USDT-SWAP",
                    "screeningStatus": candidate_status,
                }
            ],
        },
        "evolutionDemo": {
            "summary": {"ready": ready},
            "contracts": contracts,
            "recentRecords": [],
            "recentOutcomes": [],
            "blockers": [] if ready else ["okx_demo_credentials_missing"],
        },
    }


class DemoWorkflowActionTests(unittest.TestCase):
    def test_public_scan_action_uses_full_okx_public_universe(self) -> None:
        with patch.object(service, "build_strategy_lifecycle_projection", return_value=lifecycle("demo_trial")), patch.object(
            service,
            "scan_demo_strategy_public_universe",
            return_value={
                "ok": True,
                "scan": {
                    "marketScope": "okx_usdt_linear_perpetual_full_market",
                    "totalInstrumentCount": 120,
                    "currentTopCandidate": "BTC-USDT-SWAP",
                },
                "createsOrder": False,
            },
            create=True,
        ) as scan, patch.object(service, "build_exchange_demo_simulation", return_value=exchange_demo()):
            result = service.run_demo_workflow_action(
                {"action": "scan_public_market", "strategyId": "strategy-1"}
            )

        self.assertTrue(result["ok"])
        scan.assert_called_once_with("strategy-1")
        self.assertEqual(result["scan"]["totalInstrumentCount"], 120)
        self.assertFalse(result["safetyBoundary"]["createsOrder"])

    def test_release_preflight_explains_why_trial_cannot_trade(self) -> None:
        with patch.object(service, "build_strategy_lifecycle_projection", return_value=lifecycle("demo_trial", closed_samples=1)), patch.object(
            service,
            "build_exchange_demo_simulation",
            return_value=exchange_demo(candidate_status="market_ready"),
        ):
            result = service.run_demo_workflow_action(
                {"action": "prepare_demo_release", "strategyId": "strategy-1"}
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "blocked")
        self.assertIn("immutable_demo_release_missing", result["blockers"])
        self.assertIn("local_forward_evidence_incomplete", result["blockers"])
        self.assertIn("target_r_below_2r", result["blockers"])
        self.assertIn("strategy_definition_incomplete", result["blockers"])
        self.assertEqual(result["readiness"]["closedSamples"], 1)
        self.assertEqual(result["readiness"]["reviewStartSamples"], 30)
        self.assertFalse(result["safetyBoundary"]["createsOrder"])

    def test_running_release_calls_existing_demo_cycle_only_when_release_matches(self) -> None:
        ready_exchange = exchange_demo(candidate_status="market_ready", contract=True, ready=True)
        cycle_result = {"ok": True, "created": [], "status": ready_exchange["evolutionDemo"]}
        with patch.object(
            service,
            "build_strategy_lifecycle_projection",
            return_value=lifecycle("demo_validation_running", closed_samples=30),
        ), patch.object(service, "build_exchange_demo_simulation", return_value=ready_exchange), patch.object(
            service,
            "run_evolution_demo_cycle",
            return_value=cycle_result,
        ) as run_cycle:
            result = service.run_demo_workflow_action(
                {"action": "run_demo_cycle", "strategyId": "strategy-1"}
            )

        self.assertTrue(result["ok"])
        run_cycle.assert_called_once_with({"demoReleaseId": "release-1"})
        self.assertTrue(result["safetyBoundary"]["okxDemoOnly"])
        self.assertFalse(result["safetyBoundary"]["liveExecutionAllowed"])

    def test_controlled_override_action_creates_demo_release_without_order(self) -> None:
        override_result = {
            "ok": True,
            "status": "ready",
            "created": True,
            "contract": {
                "demoReleaseId": "release-override",
                "strategyCandidateId": "strategy-1",
                "releaseMode": "experimental_override",
                "livePromotionAllowed": False,
            },
            "createsOrder": False,
            "liveExecutionAllowed": False,
        }
        with patch.object(service, "build_strategy_lifecycle_projection", return_value=lifecycle("demo_trial")), patch.object(
            service,
            "build_exchange_demo_simulation",
            return_value=exchange_demo(candidate_status="market_ready"),
        ), patch.object(
            service,
            "authorize_demo_override",
            return_value=override_result,
            create=True,
        ) as authorize:
            result = service.run_demo_workflow_action(
                {
                    "action": "authorize_demo_override",
                    "strategyId": "strategy-1",
                    "reason": "开始 OKX Demo 全市场验证",
                    "confirmation": "仅放行到OKX DEMO",
                }
            )

        self.assertTrue(result["ok"])
        self.assertFalse(result["safetyBoundary"]["createsOrder"])
        self.assertFalse(result["safetyBoundary"]["liveExecutionAllowed"])
        authorize.assert_called_once()
        _, kwargs = authorize.call_args
        self.assertEqual(kwargs["reason"], "开始 OKX Demo 全市场验证")
        self.assertEqual(kwargs["confirmation"], "仅放行到OKX DEMO")

    def test_update_symbol_limit_is_a_local_demo_setting_only(self) -> None:
        with patch.object(service, "build_strategy_lifecycle_projection", return_value=lifecycle("demo_trial")), patch.object(
            service,
            "build_exchange_demo_simulation",
            return_value=exchange_demo(candidate_status="market_ready"),
        ), patch.object(
            service,
            "update_demo_strategy_runtime_settings",
            return_value={
                "strategyId": "strategy-1",
                "maxConcurrentSymbols": 3,
                "okxDemoOnly": True,
                "liveExecutionAllowed": False,
            },
            create=True,
        ) as update:
            result = service.run_demo_workflow_action(
                {
                    "action": "update_demo_strategy_settings",
                    "strategyId": "strategy-1",
                    "maxConcurrentSymbols": 3,
                }
            )

        self.assertTrue(result["ok"])
        update.assert_called_once_with("strategy-1", 3)
        self.assertFalse(result["safetyBoundary"]["createsOrder"])
        self.assertFalse(result["settings"]["liveExecutionAllowed"])


if __name__ == "__main__":
    unittest.main()
