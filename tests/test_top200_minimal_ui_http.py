from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import Mock, patch

from alphapilot_control_console.http_app import ConsoleHandler


class Top200MinimalUiHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ConsoleHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _get(self, path: str) -> dict:
        with urlopen(self.base_url + path, timeout=2) as response:
            self.assertEqual(response.status, 200)
            return json.loads(response.read().decode("utf-8"))

    def _post(self, path: str, payload: dict) -> dict:
        request = Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            self.assertEqual(response.status, 200)
            return json.loads(response.read().decode("utf-8"))

    def test_exposes_all_minimal_read_only_routes(self) -> None:
        service = Mock()
        service.RESEARCH_RUN_ID = "run-1"
        methods = {
            "research_factory_summary": {"kind": "research-summary"},
            "research_factory_runs": {"kind": "research-runs"},
            "research_factory_run": {"kind": "research-run"},
            "strategy_summary": {"kind": "strategy-summary"},
            "strategy_releases": {"kind": "strategy-releases"},
            "strategy_release": {"kind": "strategy-release"},
            "forward_validation": {"kind": "forward-validation"},
            "demo_summary": {"kind": "demo-summary"},
            "demo_strategies": {"kind": "demo-strategies"},
            "demo_positions": {"kind": "demo-positions"},
            "demo_orders": {"kind": "demo-orders"},
            "demo_universe": {"kind": "demo-universe"},
            "demo_reconciliation": {"kind": "demo-reconciliation"},
            "live_summary": {"kind": "live-summary"},
            "live_strategies": {"kind": "live-strategies"},
            "live_positions": {"kind": "live-positions"},
            "live_orders": {"kind": "live-orders"},
            "live_canary_readiness": {"kind": "live-canary-readiness"},
        }
        for name, payload in methods.items():
            getattr(service, name).return_value = payload

        routes = {
            "/api/research-factory/summary": "research-summary",
            "/api/research-factory/runs": "research-runs",
            "/api/research-factory/runs/run-1": "research-run",
            "/api/strategy/summary": "strategy-summary",
            "/api/strategy/releases": "strategy-releases",
            "/api/strategy/releases/release-1": "strategy-release",
            "/api/strategy/releases/release-1/forward-validation": "forward-validation",
            "/api/demo/summary": "demo-summary",
            "/api/demo/strategies": "demo-strategies",
            "/api/demo/positions": "demo-positions",
            "/api/demo/orders": "demo-orders",
            "/api/demo/universe": "demo-universe",
            "/api/demo/reconciliation": "demo-reconciliation",
            "/api/live/summary": "live-summary",
            "/api/live/strategies": "live-strategies",
            "/api/live/positions": "live-positions",
            "/api/live/orders": "live-orders",
            "/api/live/canary-readiness": "live-canary-readiness",
        }
        with patch(
            "alphapilot_control_console.http_app.build_top200_minimal_ui_projection",
            return_value=service,
        ):
            for path, expected_kind in routes.items():
                with self.subTest(path=path):
                    self.assertEqual(self._get(path)["kind"], expected_kind)

        service.research_factory_run.assert_called_once_with("run-1")
        service.strategy_release.assert_called_once_with("release-1")
        service.forward_validation.assert_called_once_with("release-1")

    def test_missing_projection_evidence_returns_503_without_sensitive_data(self) -> None:
        with patch(
            "alphapilot_control_console.http_app.build_top200_minimal_ui_projection",
            side_effect=RuntimeError("missing projection evidence"),
        ):
            with self.assertRaises(HTTPError) as raised:
                self._get("/api/demo/summary")

        self.assertEqual(raised.exception.code, 503)
        payload = json.loads(raised.exception.read().decode("utf-8"))
        self.assertEqual(payload["error"], "top200_projection_unavailable")
        serialized = json.dumps(payload).lower()
        self.assertNotIn("apikey", serialized)
        self.assertNotIn("passphrase", serialized)

    def test_strategy_execution_policy_routes_are_local_versioned_controls(self) -> None:
        with patch(
            "alphapilot_control_console.http_app.read_strategy_execution_policy_api",
            return_value={"policies": [{"policyId": "policy-a"}], "readOnly": True},
        ) as read_api:
            payload = self._get(
                "/api/strategy-execution-policies?environment=okx_demo"
            )
        self.assertEqual(payload["policies"][0]["policyId"], "policy-a")
        read_api.assert_called_once()

        with patch(
            "alphapilot_control_console.http_app.write_strategy_execution_policy_api",
            return_value={"ok": True, "executionEnabled": False},
        ) as write_api:
            payload = self._post(
                "/api/strategy-execution-policies/policy-a/activate",
                {
                    "confirmation": "ACTIVATE_STRATEGY_EXECUTION_POLICY",
                    "reason": "operator_activation",
                },
            )
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["executionEnabled"])
        write_api.assert_called_once()

    def test_exact_demo_release_approval_and_arm_are_separate_local_routes(self) -> None:
        approval = {"ok": True, "approved": True, "demoArm": False}
        armed = {"ok": True, "approved": True, "demoArm": True}
        disarmed = {"ok": True, "approved": True, "demoArm": False}
        exact = {
            "releaseId": "release-1",
            "releaseHash": "release-hash-1",
            "riskOverlayHash": "risk-hash-1",
            "executionIntersectionHash": "intersection-hash-1",
            "engineeringSmokeEvidenceHash": "smoke-evidence-hash-1",
            "engineeringSmokeContractHash": "smoke-contract-hash-1",
            "approvalRequestHash": "approval-request-hash-1",
            "operatorIdentity": "human_local_operator",
            "approvedAt": "2026-07-21T01:00:00Z",
        }
        with patch(
            "alphapilot_control_console.http_app.approve_final_demo_release",
            return_value=approval,
        ) as approve, patch(
            "alphapilot_control_console.http_app.arm_final_demo_release",
            return_value=armed,
        ) as arm, patch(
            "alphapilot_control_console.http_app.disarm_final_demo_release",
            return_value=disarmed,
        ) as disarm:
            self.assertEqual(
                self._post("/api/strategy/releases/release-1/approve", exact),
                approval,
            )
            self.assertEqual(
                self._post("/api/demo/releases/release-1/arm", exact),
                armed,
            )
            self.assertEqual(
                self._post("/api/demo/releases/release-1/disarm", exact),
                disarmed,
            )

        approve.assert_called_once_with("release-1", exact)
        arm.assert_called_once_with("release-1", exact)
        disarm.assert_called_once_with("release-1", exact)

    def test_exact_demo_release_write_routes_reject_non_loopback_clients(self) -> None:
        request = Request(
            self.base_url + "/api/strategy/releases/release-1/approve",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with patch(
            "alphapilot_control_console.http_app._request_is_loopback",
            return_value=False,
        ), self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=2)

        self.assertEqual(raised.exception.code, 403)

    def test_strategy_factory_create_pause_and_resume_are_local_bounded_routes(self) -> None:
        factory = Mock()
        factory.create_run.return_value = {"runId": "factory-run-1", "status": "queued"}
        factory.start_run.return_value = {"runId": "factory-run-1", "status": "running"}
        factory.pause_run.return_value = {"runId": "factory-run-1", "status": "paused"}
        factory.resume_run.return_value = {"runId": "factory-run-1", "status": "running"}
        payload = {
            "operation": "generate",
            "timeframe": "15m",
            "mode": "quick",
            "maxCandidateCount": 4,
            "maxTrialBudget": 24,
        }

        with patch(
            "alphapilot_control_console.http_app.build_strategy_factory_orchestrator",
            return_value=factory,
        ):
            created = self._post("/api/research-factory/runs", payload)
            paused = self._post(
                "/api/research-factory/runs/factory-run-1/pause",
                {},
            )
            resumed = self._post(
                "/api/research-factory/runs/factory-run-1/resume",
                {},
            )

        self.assertEqual(created["status"], "running")
        self.assertEqual(paused["status"], "paused")
        self.assertEqual(resumed["status"], "running")
        factory.create_run.assert_called_once_with(payload)
        factory.start_run.assert_called_once_with("factory-run-1")
        factory.pause_run.assert_called_once_with("factory-run-1")
        factory.resume_run.assert_called_once_with("factory-run-1")
        self.assertEqual(factory.close.call_count, 3)

    def test_strategy_factory_continuous_runner_has_local_enable_and_disable_routes(self) -> None:
        status = {
            "enabled": False,
            "phase": "disabled",
            "currentRunId": None,
        }
        enabled = {
            "enabled": True,
            "phase": "running",
            "currentRunId": "factory-run-1",
        }
        disabled = {
            "enabled": False,
            "phase": "disabled_after_current_run",
            "currentRunId": "factory-run-1",
        }

        with patch(
            "alphapilot_control_console.http_app.get_strategy_factory_continuous_status",
            return_value=status,
        ) as read_status, patch(
            "alphapilot_control_console.http_app.run_strategy_factory_continuous_action",
            side_effect=[enabled, disabled],
        ) as run_action:
            current = self._get("/api/research-factory/continuous")
            started = self._post(
                "/api/research-factory/continuous/enable",
                {},
            )
            stopped = self._post(
                "/api/research-factory/continuous/disable",
                {},
            )

        self.assertEqual(current, status)
        self.assertEqual(started, enabled)
        self.assertEqual(stopped, disabled)
        read_status.assert_called_once_with()
        self.assertEqual(
            [call.args[0] for call in run_action.call_args_list],
            ["enable", "disable"],
        )

    def test_strategy_factory_write_route_rejects_sensitive_fields(self) -> None:
        with self.assertRaises(HTTPError) as raised:
            self._post(
                "/api/research-factory/runs",
                {
                    "operation": "generate",
                    "timeframe": "15m",
                    "mode": "quick",
                    "maxCandidateCount": 4,
                    "maxTrialBudget": 24,
                    "apiKey": "must-not-be-accepted",
                },
            )

        self.assertEqual(raised.exception.code, 400)
        response = json.loads(raised.exception.read().decode("utf-8"))
        self.assertEqual(response["error"], "sensitive_field_forbidden")

    def test_manual_intervention_routes_are_read_only_plus_local_append_only(self) -> None:
        status = {
            "ok": True,
            "recentEvents": [],
            "executionEnabled": False,
        }
        recorded = {
            "ok": True,
            "event": {
                "interventionId": "manual-1",
                "action": "pause_strategy",
                "executionEnabled": False,
            },
        }
        payload = {
            "environment": "okx_demo",
            "action": "pause_strategy",
            "operator": "user_manual",
            "strategyId": "strategy-1",
            "reason": "operator review",
        }

        with patch(
            "alphapilot_control_console.http_app.build_manual_intervention_status",
            return_value=status,
        ) as build_status, patch(
            "alphapilot_control_console.http_app.record_manual_intervention",
            return_value=recorded,
        ) as record:
            self.assertEqual(self._get("/api/manual-interventions"), status)
            self.assertEqual(
                self._post("/api/manual-interventions/record", payload),
                recorded,
            )

        build_status.assert_called_once_with()
        record.assert_called_once_with(payload)

    def test_manual_intervention_write_rejects_sensitive_fields(self) -> None:
        with self.assertRaises(HTTPError) as raised:
            self._post(
                "/api/manual-interventions/record",
                {
                    "environment": "okx_demo",
                    "action": "pause_strategy",
                    "operator": "user_manual",
                    "strategyId": "strategy-1",
                    "reason": "operator review",
                    "apiSecret": "must-not-be-accepted",
                },
            )

        self.assertEqual(raised.exception.code, 400)
        response = json.loads(raised.exception.read().decode("utf-8"))
        self.assertEqual(response["error"], "sensitive_field_forbidden")

    def test_v56_runtime_control_write_routes_require_loopback(self) -> None:
        routes = (
            "/api/risk-profiles/runtime-overlays/create",
            "/api/strategy-version-switch/action",
            "/api/manual-interventions/record",
        )
        with patch(
            "alphapilot_control_console.http_app._request_is_loopback",
            return_value=False,
        ):
            for route in routes:
                with self.subTest(route=route), self.assertRaises(HTTPError) as raised:
                    self._post(route, {})
                self.assertEqual(raised.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
