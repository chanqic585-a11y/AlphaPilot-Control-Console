from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.execution_control import (
    ExecutionControlActionFacade,
    build_execution_control_status,
)
from alphapilot_control_console.unified_auto_execution_store import (
    UnifiedAutoExecutionStore,
)


class ExecutionControlProjectionTests(unittest.TestCase):
    def test_projection_is_redacted_and_keeps_demo_live_runtime_identity_isolated(self) -> None:
        automatic = {
            "running": True,
            "environments": {
                "okx_demo": {
                    "status": "waiting",
                    "desiredEnabled": True,
                    "armedForCurrentProcess": True,
                    "releaseCount": 2,
                    "lastHeartbeatAt": "2026-07-19T01:00:00+00:00",
                    "nextEvaluationAt": "2026-07-19T02:00:00+00:00",
                    "lastError": None,
                    "apiKey": "must-not-leak",
                },
                "okx_live": {
                    "status": "disabled",
                    "desiredEnabled": False,
                    "armedForCurrentProcess": False,
                    "releaseCount": 1,
                    "lastError": None,
                    "passphrase": "must-not-leak",
                },
            },
        }
        demo = {
            "summary": {"openOrderCount": 1, "openPositionCount": 1},
            "runtime": {
                "credentialStatus": {"allConfigured": True, "secretKey": "hidden"},
                "reconciliation": {"matched": True, "unknownOrderCount": 0},
                "risk": {"ready": True},
                "killSwitch": {"active": False},
            },
            "releaseHashes": ["demo-release-hash"],
            "positions": [{"instrumentId": "BTC-USDT-SWAP", "status": "open"}],
        }
        live = {
            "summary": {"canaryOrderReady": False, "executionRecordCount": 0},
            "credentialStatus": {"allConfigured": False, "apiKey": "hidden"},
            "runtime": {
                "paused": False,
                "killSwitchActive": False,
                "lastReconciliationMatched": False,
            },
            "runtimeGates": {"masterEnabled": False, "orderEnabled": False},
            "blockers": ["live_master_gate_disabled", "live_reconciliation_not_confirmed"],
            "liveReleases": {"releases": [{"contentHash": "live-release-hash"}]},
        }

        projection = build_execution_control_status(
            automatic_execution=automatic,
            demo_workflow=demo,
            live_canary=live,
            generated_at="2026-07-19T03:00:00+00:00",
        )

        self.assertEqual(projection["schemaVersion"], "execution-control.v1")
        self.assertEqual(projection["environments"]["demo"]["runtimeIdentity"], "okx_demo")
        self.assertEqual(projection["environments"]["live"]["runtimeIdentity"], "okx_live")
        self.assertTrue(projection["environments"]["demo"]["credentialReady"])
        self.assertFalse(projection["environments"]["live"]["credentialReady"])
        self.assertFalse(projection["environments"]["live"]["desiredEnabled"])
        self.assertFalse(projection["environments"]["live"]["armedForCurrentProcess"])
        self.assertIn("live_default_off", projection["environments"]["live"]["blockerCodes"])
        self.assertEqual(projection["crossTrack"]["demoReleaseHashes"], ["demo-release-hash"])
        self.assertEqual(projection["crossTrack"]["liveReleaseHashes"], ["live-release-hash"])
        serialized = json.dumps(projection)
        for forbidden in ("must-not-leak", "hidden", "apiKey", "secretKey", "passphrase"):
            self.assertNotIn(forbidden, serialized)

    def test_projection_emits_stable_blockers_and_chinese_next_actions(self) -> None:
        projection = build_execution_control_status(
            automatic_execution={
                "running": True,
                "environments": {
                    "okx_demo": {
                        "status": "disarmed",
                        "desiredEnabled": True,
                        "armedForCurrentProcess": False,
                        "releaseCount": 0,
                        "pauseReason": "process_arm_required",
                    },
                    "okx_live": {
                        "status": "disabled",
                        "desiredEnabled": False,
                        "armedForCurrentProcess": False,
                        "releaseCount": 0,
                    },
                },
            },
            demo_workflow={"summary": {}, "runtime": {"credentialStatus": {"allConfigured": False}}},
            live_canary={"summary": {}, "credentialStatus": {"allConfigured": False}, "blockers": []},
        )

        demo = projection["environments"]["demo"]
        self.assertEqual(
            demo["blockerCodes"],
            ["demo_credentials_missing", "immutable_release_missing", "process_arm_required"],
        )
        self.assertEqual(
            [item["code"] for item in demo["nextActions"]],
            ["start_demo_with_process_credentials", "prepare_immutable_demo_release", "arm_current_demo_process"],
        )
        self.assertTrue(all(item["labelZh"] for item in demo["nextActions"]))

    def test_unknown_demo_position_fails_closed_and_live_release_hash_is_projected(self) -> None:
        projection = build_execution_control_status(
            automatic_execution={
                "running": True,
                "environments": {
                    "okx_demo": {
                        "status": "armed",
                        "desiredEnabled": True,
                        "armedForCurrentProcess": True,
                        "releaseCount": 1,
                    },
                    "okx_live": {
                        "status": "disabled",
                        "desiredEnabled": False,
                        "armedForCurrentProcess": False,
                        "releaseCount": 1,
                    },
                },
            },
            demo_workflow={
                "runtime": {
                    "credentialsConfigured": True,
                    "reconciliation": {
                        "matched": True,
                        "unknownOrderCount": 0,
                        "unknownPositionCount": 1,
                    },
                },
                "releaseHashes": ["demo-release-hash"],
            },
            live_canary={
                "credentialStatus": {"allConfigured": False},
                "runtime": {"lastReconciliationMatched": False},
                "liveReleases": {
                    "releases": [
                        {
                            "liveReleaseHash": "live-release-hash",
                            "release": {"riskProfileHash": "risk-hash"},
                        }
                    ]
                },
                "blockers": [],
            },
        )

        self.assertIn("reconciliation_unhealthy", projection["environments"]["demo"]["blockerCodes"])
        self.assertEqual(
            projection["environments"]["demo"]["reconciliation"]["unknownPositionCount"],
            1,
        )
        self.assertEqual(projection["crossTrack"]["liveReleaseHashes"], ["live-release-hash"])

    def test_projection_includes_redacted_market_feed_and_cross_track_mismatch_summary(self) -> None:
        projection = build_execution_control_status(
            automatic_execution={
                "running": True,
                "environments": {
                    "okx_demo": {"status": "waiting", "desiredEnabled": True},
                    "okx_live": {"status": "disabled", "desiredEnabled": False},
                },
            },
            demo_workflow={
                "marketFeed": {
                    "status": "ready",
                    "source": "okx_public",
                    "lastUpdatedAt": "2026-07-19T04:00:00+00:00",
                    "apiKey": "must-not-leak",
                },
                "runtime": {"credentialStatus": {"allConfigured": False}},
            },
            live_canary={
                "marketFeed": {"status": "disabled", "source": "isolated_live_adapter"},
                "credentialStatus": {"allConfigured": False},
                "blockers": ["live_release_risk_profile_mismatch"],
            },
        )

        self.assertEqual(
            projection["environments"]["demo"]["marketFeed"],
            {
                "status": "ready",
                "source": "okx_public",
                "lastUpdatedAt": "2026-07-19T04:00:00+00:00",
                "stale": False,
            },
        )
        self.assertEqual(projection["environments"]["live"]["marketFeed"]["status"], "disabled")
        self.assertEqual(
            projection["crossTrack"]["mismatchBlockers"],
            [{"environment": "live", "code": "live_release_risk_profile_mismatch"}],
        )
        self.assertNotIn("must-not-leak", json.dumps(projection))

    def test_projection_aggregates_positions_orders_and_reconciliation_from_demo_workflow_queues(self) -> None:
        projection = build_execution_control_status(
            automatic_execution={
                "running": True,
                "environments": {
                    "okx_demo": {
                        "status": "armed",
                        "desiredEnabled": True,
                        "armedForCurrentProcess": True,
                        "releaseCount": 2,
                    },
                    "okx_live": {"status": "disabled", "desiredEnabled": False},
                },
            },
            demo_workflow={
                "summary": {"validatingCount": 2},
                "runtime": {"credentialsConfigured": True},
                "queues": {
                    "validating": [
                        {
                            "strategyId": "demo-filled",
                            "position": {"status": "filled"},
                            "positions": [
                                {
                                    "instrumentId": "BTC-USDT-SWAP",
                                    "status": "filled",
                                    "quantity": 1,
                                }
                            ],
                            "reconciliation": {
                                "status": "reconciled",
                                "updatedAt": "2026-07-19T05:00:00+00:00",
                            },
                        },
                        {
                            "strategyId": "demo-submitted",
                            "position": {"status": "order_submitted"},
                            "positions": [],
                            "reconciliation": {"status": "not_started"},
                        },
                    ]
                },
            },
            live_canary={
                "credentialStatus": {"allConfigured": False},
                "runtime": {"lastReconciliationMatched": False},
                "blockers": [],
            },
        )

        demo = projection["environments"]["demo"]
        self.assertEqual(demo["orders"]["openCount"], 1)
        self.assertEqual(demo["positions"]["openCount"], 1)
        self.assertEqual(demo["positions"]["items"][0]["instrumentId"], "BTC-USDT-SWAP")
        self.assertTrue(demo["reconciliation"]["matched"])
        self.assertEqual(demo["reconciliation"]["lastCheckedAt"], "2026-07-19T05:00:00+00:00")

    def test_projection_uses_latest_live_reconciliation_event_counts(self) -> None:
        projection = build_execution_control_status(
            automatic_execution={
                "running": True,
                "environments": {
                    "okx_demo": {"status": "disabled", "desiredEnabled": False},
                    "okx_live": {"status": "paused", "desiredEnabled": False},
                },
            },
            demo_workflow={"runtime": {"credentialsConfigured": False}},
            live_canary={
                "summary": {"executionRecordCount": 4},
                "credentialStatus": {"allConfigured": True},
                "runtime": {
                    "lastReconciliationMatched": False,
                    "lastReconciledAt": "2026-07-19T06:00:00+00:00",
                },
                "recentEvents": [
                    {
                        "eventType": "live_readonly_reconciliation",
                        "createdAt": "2026-07-19T06:00:00+00:00",
                        "payload": {
                            "matched": False,
                            "openPositionCount": 3,
                            "openOrderCount": 2,
                            "untrackedPositionCount": 2,
                            "untrackedOrderCount": 1,
                        },
                    }
                ],
                "blockers": ["live_reconciliation_not_confirmed"],
            },
        )

        live = projection["environments"]["live"]
        self.assertEqual(live["orders"]["recordCount"], 4)
        self.assertEqual(live["orders"]["openCount"], 2)
        self.assertEqual(live["positions"]["openCount"], 3)
        self.assertFalse(live["reconciliation"]["matched"])
        self.assertEqual(live["reconciliation"]["unknownOrderCount"], 1)
        self.assertEqual(live["reconciliation"]["unknownPositionCount"], 2)


class ExecutionControlActionFacadeTests(unittest.TestCase):
    def test_same_request_is_replayed_and_conflicting_request_is_rejected(self) -> None:
        calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmp:
            store = UnifiedAutoExecutionStore(Path(tmp) / "auto.sqlite")
            try:
                facade = ExecutionControlActionFacade(
                    store=store,
                    action_runner=lambda payload: calls.append(dict(payload)) or {
                        "ok": True,
                        "runtime": {"environments": {}},
                    },
                )
                request = {
                    "requestId": "req-demo-start-001",
                    "environment": "okx_demo",
                    "action": "start",
                    "actor": "console_operator",
                }

                first = facade.execute(request)
                replay = facade.execute(dict(request))
                conflict = facade.execute({**request, "action": "pause"})

                self.assertTrue(first["ok"])
                self.assertFalse(first["idempotentReplay"])
                self.assertTrue(replay["ok"])
                self.assertTrue(replay["idempotentReplay"])
                self.assertEqual(len(calls), 1)
                self.assertFalse(conflict["ok"])
                self.assertEqual(conflict["status"], "conflict")
                self.assertEqual(conflict["blockers"], ["idempotency_key_payload_mismatch"])
                self.assertEqual(store.action_request("req-demo-start-001")["status"], "completed")
            finally:
                store.close()

    def test_live_start_is_not_an_allowed_v37a_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = UnifiedAutoExecutionStore(Path(tmp) / "auto.sqlite")
            try:
                facade = ExecutionControlActionFacade(
                    store=store,
                    action_runner=lambda _payload: self.fail("Live start must fail before dispatch"),
                )
                result = facade.execute(
                    {
                        "requestId": "req-live-start-001",
                        "environment": "okx_live",
                        "action": "start",
                    }
                )
            finally:
                store.close()

        self.assertFalse(result["ok"])
        self.assertEqual(result["blockers"], ["live_start_not_available_in_v37a"])

    def test_live_arm_stays_on_the_existing_manual_approval_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = UnifiedAutoExecutionStore(Path(tmp) / "auto.sqlite")
            try:
                facade = ExecutionControlActionFacade(
                    store=store,
                    action_runner=lambda _payload: self.fail("V37A facade must not replace manual Live ARM"),
                )
                result = facade.execute(
                    {
                        "requestId": "req-live-arm-001",
                        "environment": "okx_live",
                        "action": "arm",
                    }
                )
            finally:
                store.close()

        self.assertFalse(result["ok"])
        self.assertEqual(result["blockers"], ["live_arm_requires_existing_manual_path"])

    def test_dispatch_timeout_is_persisted_and_replayed_without_duplicate_dispatch(self) -> None:
        calls = 0

        def timeout_runner(_payload: dict[str, object]) -> dict[str, object]:
            nonlocal calls
            calls += 1
            raise TimeoutError("exchange response was not observed")

        with tempfile.TemporaryDirectory() as tmp:
            store = UnifiedAutoExecutionStore(Path(tmp) / "auto.sqlite")
            try:
                facade = ExecutionControlActionFacade(store=store, action_runner=timeout_runner)
                request = {
                    "requestId": "req-demo-timeout-001",
                    "environment": "okx_demo",
                    "action": "start",
                }
                first = facade.execute(request)
                replay = facade.execute(request)
                persisted = store.action_request(request["requestId"])
            finally:
                store.close()

        self.assertFalse(first["ok"])
        self.assertEqual(first["blockers"], ["action_dispatch_timeout"])
        self.assertTrue(replay["idempotentReplay"])
        self.assertEqual(calls, 1)
        self.assertEqual(persisted["status"], "completed")


if __name__ == "__main__":
    unittest.main()
