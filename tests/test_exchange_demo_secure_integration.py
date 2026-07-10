from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import alphapilot_control_console.exchange_demo_simulation as simulation


class FakeReadOnlyDemoClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def get_account_config(self) -> dict:
        self.calls.append(("config", None))
        return {"code": "0", "msg": "", "data": [{"acctLv": "2", "uid": "private-uid"}]}

    def get_balance(self, currency: str = "USDT") -> dict:
        self.calls.append(("balance", currency))
        return {"code": "0", "msg": "", "data": [{"availBal": "999.99", "ccy": currency}]}

    def get_positions(
        self,
        instrumentId: str | None = None,
        instrumentType: str | None = None,
    ) -> dict:
        self.calls.append(("positions", instrumentType))
        return {"code": "0", "msg": "", "data": [{"instId": "BTC-USDT-SWAP", "pos": "1"}]}


class ExchangeDemoSecureIntegrationTests(unittest.TestCase):
    def test_readonly_check_uses_single_client_and_persists_only_redacted_metadata(self) -> None:
        client = FakeReadOnlyDemoClient()
        saved_events: list[dict] = []

        def save_event(event: dict) -> dict:
            saved_events.append(dict(event))
            return {**event, "eventId": "event-1", "createdAt": "2026-07-10T00:00:00Z"}

        with patch.object(simulation, "_private_blockers", return_value=[]), patch.object(
            simulation, "_make_demo_client", return_value=client
        ), patch.object(simulation, "save_exchange_demo_event", side_effect=save_event), patch.object(
            simulation, "build_exchange_demo_simulation", return_value={"summary": {}}
        ):
            result = simulation.run_exchange_demo_readonly_check()

        self.assertTrue(result["ok"])
        self.assertEqual(client.calls, [("config", None), ("balance", "USDT"), ("positions", "SWAP")])
        self.assertEqual(saved_events[0]["accountConfigStatus"], 200)
        self.assertEqual(saved_events[0]["okxAccountConfigCode"], "0")
        self.assertEqual(saved_events[0]["okxBalanceCode"], "0")
        self.assertEqual(saved_events[0]["okxPositionCode"], "0")
        self.assertEqual(saved_events[0]["site"], "global")

        serialized_event = json.dumps(saved_events[0], ensure_ascii=False)
        serialized_result = json.dumps(result, ensure_ascii=False)
        for forbidden in ("private-uid", "999.99", '"pos": "1"', "OK-ACCESS-KEY", "OK-ACCESS-SIGN"):
            self.assertNotIn(forbidden, serialized_event)
            self.assertNotIn(forbidden, serialized_result)

    def test_manual_demo_order_is_connectivity_smoke_not_strategy_evidence(self) -> None:
        saved_events: list[dict] = []

        def save_event(event: dict) -> dict:
            saved_events.append(dict(event))
            return {**event, "eventId": "event-2", "createdAt": "2026-07-10T00:00:00Z"}

        with patch.object(simulation, "_private_blockers", return_value=[]), patch.object(
            simulation,
            "_okx_request",
            return_value={
                "ok": True,
                "status": 200,
                "payload": {"code": "0", "msg": "", "data": [{"ordId": "demo-order-1"}]},
                "demoHeaderUsed": True,
                "baseUrl": "https://openapi.okx.com",
            },
        ), patch.object(simulation, "save_exchange_demo_event", side_effect=save_event), patch.object(
            simulation, "build_exchange_demo_simulation", return_value={"summary": {}}
        ):
            result = simulation.submit_exchange_demo_order(
                {
                    "instId": "BTC-USDT-SWAP",
                    "side": "buy",
                    "tdMode": "isolated",
                    "ordType": "market",
                    "size": "1",
                    "notionalUsdt": 10,
                    "manualConfirm": "OKX_DEMO_ORDER_APPROVED",
                }
            )

        self.assertTrue(result["ok"])
        self.assertEqual(saved_events[0]["executionPurpose"], "connectivity_smoke_only")
        self.assertFalse(saved_events[0]["strategyEvidenceEligible"])
        self.assertFalse(saved_events[0]["createsDemoRelease"])
        self.assertFalse(saved_events[0]["createsLiveCandidate"])
        self.assertEqual(saved_events[0]["orderId"], "demo-order-1")
        self.assertEqual(result["executionPurpose"], "connectivity_smoke_only")
        self.assertFalse(result["strategyEvidenceEligible"])
        self.assertFalse(result["createsDemoRelease"])
        self.assertFalse(result["createsLiveCandidate"])

    def test_demo_order_status_query_is_scoped_to_connectivity_smoke(self) -> None:
        saved_events: list[dict] = []

        def save_event(event: dict) -> dict:
            saved_events.append(dict(event))
            return {**event, "eventId": "event-3", "createdAt": "2026-07-10T00:00:00Z"}

        with patch.object(simulation, "_private_blockers", return_value=[]), patch.object(
            simulation,
            "_okx_request",
            return_value={
                "ok": True,
                "status": 200,
                "payload": {
                    "code": "0",
                    "msg": "",
                    "data": [{"ordId": "demo-order-1", "clOrdId": "APD1", "state": "live"}],
                },
                "demoHeaderUsed": True,
                "baseUrl": "https://openapi.okx.com",
            },
        ), patch.object(simulation, "save_exchange_demo_event", side_effect=save_event), patch.object(
            simulation, "build_exchange_demo_simulation", return_value={"summary": {}}
        ):
            result = simulation.query_exchange_demo_order_status(
                {"instId": "BTC-USDT", "ordId": "demo-order-1"}
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["orderState"], "live")
        self.assertEqual(saved_events[0]["orderId"], "demo-order-1")
        self.assertEqual(saved_events[0]["executionPurpose"], "connectivity_smoke_only")
        self.assertFalse(saved_events[0]["strategyEvidenceEligible"])

    def test_demo_cancel_accepts_client_order_id_for_recovery(self) -> None:
        saved_events: list[dict] = []

        def save_event(event: dict) -> dict:
            saved_events.append(dict(event))
            return {**event, "eventId": "event-4", "createdAt": "2026-07-10T00:00:00Z"}

        with patch.object(simulation, "_private_blockers", return_value=[]), patch.object(
            simulation,
            "_env_enabled",
            side_effect=lambda name: name == "ALPHAPILOT_OKX_DEMO_CANCEL_ENABLED",
        ), patch.object(
            simulation,
            "_okx_request",
            return_value={
                "ok": True,
                "status": 200,
                "payload": {"code": "0", "msg": "", "data": [{"sCode": "0"}]},
                "demoHeaderUsed": True,
                "baseUrl": "https://openapi.okx.com",
            },
        ), patch.object(simulation, "save_exchange_demo_event", side_effect=save_event), patch.object(
            simulation, "build_exchange_demo_simulation", return_value={"summary": {}}
        ):
            result = simulation.run_exchange_demo_emergency_drill(
                {
                    "instId": "BTC-USDT",
                    "clOrdId": "APD1",
                    "manualConfirm": "OKX_DEMO_EMERGENCY_APPROVED",
                }
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["exchangeCancelSent"])
        self.assertEqual(saved_events[0]["clientOrderId"], "APD1")


if __name__ == "__main__":
    unittest.main()
