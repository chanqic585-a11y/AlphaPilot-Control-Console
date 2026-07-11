from __future__ import annotations

import unittest

from alphapilot_control_console.demo_workflow_projection import build_demo_workflow_projection


def lifecycle_item(strategy_id: str, stage: str, **overrides: object) -> dict:
    return {
        "strategyId": strategy_id,
        "displayName": f"Strategy {strategy_id}",
        "currentStage": stage,
        "stageLabel": stage,
        "metrics": {},
        "blockers": [],
        "nextGate": "next gate",
        **overrides,
    }


class DemoWorkflowProjectionTests(unittest.TestCase):
    def test_readonly_passed_without_order_gates_requires_automation_restart(self) -> None:
        lifecycle = {
            "items": [lifecycle_item("running-1", "demo_validation_running")]
        }
        exchange_demo = {
            "summary": {
                "credentialsConfigured": True,
                "demoPrivateEnabled": True,
                "demoOrderEnabled": False,
            },
            "readonlySummary": {"status": "passed"},
            "automationPipeline": {"summary": {}, "candidates": []},
            "evolutionDemo": {
                "summary": {"ready": False},
                "runtimeGates": {
                    "privateEnabled": True,
                    "orderEnabled": False,
                    "automationEnabled": False,
                },
                "contracts": [
                    {"demoReleaseId": "release-running", "strategyCandidateId": "running-1"}
                ],
                "recentRecords": [],
                "recentOutcomes": [],
                "blockers": ["okx_demo_order_gate_disabled", "demo_automation_disabled"],
            },
        }

        result = build_demo_workflow_projection(
            lifecycle=lifecycle,
            exchange_demo=exchange_demo,
        )

        action = result["queues"]["validating"][0]["nextAction"]
        self.assertEqual(action["actionId"], "restart_with_demo_automation")
        self.assertFalse(action["enabled"])
        self.assertIn("-EnableOrder", action["command"])
        self.assertIn("-EnableAutomation", action["command"])

    def test_four_queues_are_exclusive_and_preserve_unknown_trade_values(self) -> None:
        lifecycle = {
            "items": [
                lifecycle_item("trial-1", "demo_trial"),
                lifecycle_item("running-1", "demo_validation_running"),
                lifecycle_item("passed-1", "demo_validated"),
                lifecycle_item("live-1", "live_candidate"),
            ]
        }
        exchange_demo = {
            "summary": {
                "credentialsConfigured": True,
                "demoPrivateEnabled": True,
                "demoOrderEnabled": True,
                "strategyAutomationReady": True,
            },
            "automationPipeline": {
                "summary": {"publicProbeCount": 0},
                "candidates": [
                    {
                        "strategyId": "trial-1",
                        "instId": "BTC-USDT-SWAP",
                        "screeningStatus": "strategy_loaded",
                    }
                ],
            },
            "evolutionDemo": {
                "summary": {"ready": True},
                "contracts": [
                    {"demoReleaseId": "release-running", "strategyCandidateId": "running-1"},
                    {"demoReleaseId": "release-passed", "strategyCandidateId": "passed-1"},
                ],
                "recentRecords": [
                    {
                        "recordId": "record-1",
                        "demoReleaseId": "release-running",
                        "status": "filled",
                        "signal": {
                            "instId": "ETH-USDT-SWAP",
                            "side": "buy",
                            "entryPrice": 2500.0,
                            "stopLossPrice": 2475.0,
                            "takeProfitPrice": 2550.0,
                        },
                        "orderPayload": {"sz": "0.1"},
                        "createdAt": "2026-07-11T00:00:00+00:00",
                    }
                ],
                "recentOutcomes": [
                    {
                        "strategyCandidateId": "running-1",
                        "outcome": {
                            "trade": {
                                "netPnl": 3.5,
                                "feePaid": 0.3,
                                "slippagePaid": 0.2,
                            }
                        },
                    }
                ],
                "blockers": [],
            },
        }

        result = build_demo_workflow_projection(
            lifecycle=lifecycle,
            exchange_demo=exchange_demo,
        )

        self.assertEqual(
            result["summary"],
            {
                "waitingCount": 1,
                "validatingCount": 1,
                "passedCount": 1,
                "liveCandidateCount": 1,
            },
        )
        all_ids = [
            item["strategyId"]
            for queue in result["queues"].values()
            for item in queue
        ]
        self.assertEqual(sorted(all_ids), ["live-1", "passed-1", "running-1", "trial-1"])
        self.assertEqual(len(all_ids), len(set(all_ids)))

        waiting = result["queues"]["waiting"][0]
        self.assertEqual(waiting["market"]["instrumentId"], "BTC-USDT-SWAP")
        self.assertIsNone(waiting["position"]["entryPrice"])
        self.assertIsNone(waiting["performance"]["unrealizedPnl"])
        self.assertEqual(waiting["nextAction"]["actionId"], "scan_public_market")

        running = result["queues"]["validating"][0]
        self.assertEqual(running["market"]["instrumentId"], "ETH-USDT-SWAP")
        self.assertEqual(running["position"]["status"], "filled")
        self.assertEqual(running["position"]["entryPrice"], 2500.0)
        self.assertEqual(running["position"]["takeProfitPrice"], 2550.0)
        self.assertEqual(running["performance"]["realizedPnl"], 3.5)
        self.assertEqual(running["performance"]["closedTradeCount"], 1)

    def test_demo_trials_without_release_are_waiting_not_validating(self) -> None:
        lifecycle = {
            "items": [
                lifecycle_item(
                    f"trial-{index}",
                    "demo_trial",
                    metrics={"closedSamples": index},
                )
                for index in range(10)
            ]
        }
        exchange_demo = {
            "summary": {
                "credentialsConfigured": False,
                "demoPrivateEnabled": False,
                "demoOrderEnabled": False,
                "strategyAutomationReady": False,
            },
            "automationPipeline": {"summary": {}, "candidates": []},
            "evolutionDemo": {
                "summary": {"ready": False},
                "contracts": [],
                "recentRecords": [],
                "recentOutcomes": [],
                "blockers": ["no_eligible_demo_release", "okx_demo_credentials_missing"],
            },
        }

        result = build_demo_workflow_projection(
            lifecycle=lifecycle,
            exchange_demo=exchange_demo,
        )

        self.assertEqual(result["summary"]["waitingCount"], 10)
        self.assertEqual(result["summary"]["validatingCount"], 0)
        self.assertTrue(all(item["progress"]["percent"] < 50 for item in result["queues"]["waiting"]))
        self.assertTrue(
            all("尚未生成不可变 Demo Release" in item["failure"]["analysis"] for item in result["queues"]["waiting"])
        )


if __name__ == "__main__":
    unittest.main()
