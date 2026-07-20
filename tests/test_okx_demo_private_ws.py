from __future__ import annotations

import base64
import hashlib
import hmac
import json
import unittest

from alphapilot_control_console.credential_runtime import OkxDemoCredentials
from alphapilot_control_console.exchange_connectors.okx_demo_private_ws import (
    OKX_DEMO_PRIVATE_WS_URLS,
    OkxDemoPrivateWsRuntime,
    OkxPrivateWsUnavailable,
    build_okx_private_ws_login,
    start_okx_demo_private_order_runtime,
)


class FakeWebSocketApp:
    def __init__(self, url, *, on_open, on_message, on_error, on_close):
        self.url = url
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.sent: list[dict] = []
        self.closed = False
        self.order_response: dict | None = None

    def send(self, payload: str) -> None:
        decoded = json.loads(payload)
        self.sent.append(decoded)
        if decoded.get("op") == "order" and self.order_response is not None:
            self.on_message(
                self,
                json.dumps({**self.order_response, "id": decoded["id"], "op": "order"}),
            )

    def close(self) -> None:
        self.closed = True


class OkxDemoPrivateWsTests(unittest.TestCase):
    def test_process_runtime_start_fails_closed_without_demo_credentials(self) -> None:
        result = start_okx_demo_private_order_runtime(environment={})

        self.assertFalse(result["started"])
        self.assertEqual(result["blockers"], ["okx_demo_runtime_credentials_incomplete"])
        self.assertFalse(result["credentialsStored"])

    def test_login_signature_uses_official_private_ws_prehash(self) -> None:
        credentials = OkxDemoCredentials("key", "secret", "pass")
        payload = build_okx_private_ws_login(credentials, timestamp="1783987200")
        expected = base64.b64encode(
            hmac.new(
                b"secret",
                b"1783987200GET/users/self/verify",
                hashlib.sha256,
            ).digest()
        ).decode("ascii")

        self.assertEqual(payload["op"], "login")
        self.assertEqual(payload["args"][0]["sign"], expected)
        self.assertEqual(payload["args"][0]["apiKey"], "key")

    def test_login_success_subscribes_orders_positions_and_account(self) -> None:
        created: list[FakeWebSocketApp] = []

        def factory(url, **callbacks):
            app = FakeWebSocketApp(url, **callbacks)
            created.append(app)
            return app

        events: list[dict] = []
        runtime = OkxDemoPrivateWsRuntime(
            OkxDemoCredentials("key", "secret", "pass"),
            websocket_factory=factory,
            timestamp_factory=lambda: "1783987200",
            event_listener=events.append,
        )
        app = runtime.create_app()
        app.on_open(app)
        self.assertEqual(app.url, OKX_DEMO_PRIVATE_WS_URLS["global"])
        self.assertEqual(app.sent[0]["op"], "login")

        app.on_message(app, json.dumps({"event": "login", "code": "0"}))
        self.assertEqual(app.sent[1]["op"], "subscribe")
        self.assertEqual(
            app.sent[1]["args"],
            [
                {"channel": "orders", "instType": "SWAP"},
                {"channel": "positions", "instType": "SWAP"},
                {"channel": "account", "ccy": "USDT"},
            ],
        )

        update = {
            "arg": {"channel": "orders", "instType": "SWAP"},
            "data": [{"instId": "BTC-USDT-SWAP", "state": "filled"}],
        }
        app.on_message(app, json.dumps(update))
        self.assertEqual(events, [update])
        status = runtime.status()
        self.assertTrue(status["authenticated"])
        self.assertTrue(status["subscribed"])
        rendered = json.dumps(status).lower()
        self.assertNotIn("secret", rendered)
        self.assertNotIn("pass", rendered)
        self.assertNotIn("key", rendered)

    def test_authentication_failure_is_reported_without_credentials(self) -> None:
        runtime = OkxDemoPrivateWsRuntime(
            OkxDemoCredentials("key", "secret", "pass"),
            websocket_factory=lambda url, **callbacks: FakeWebSocketApp(url, **callbacks),
            timestamp_factory=lambda: "1783987200",
        )
        app = runtime.create_app()
        app.on_message(app, json.dumps({"event": "login", "code": "60009", "msg": "Login failed"}))

        status = runtime.status()
        self.assertFalse(status["authenticated"])
        self.assertEqual(status["lastError"], "private_ws_authentication_failed:60009")

    def test_authenticated_runtime_submits_order_and_correlates_ack(self) -> None:
        runtime = OkxDemoPrivateWsRuntime(
            OkxDemoCredentials("key", "secret", "pass"),
            websocket_factory=lambda url, **callbacks: FakeWebSocketApp(url, **callbacks),
            timestamp_factory=lambda: "1783987200",
        )
        app = runtime.create_app()
        app.on_open(app)
        app.on_message(app, json.dumps({"event": "login", "code": "0"}))
        app.order_response = {"code": "0", "data": [{"ordId": "ws-order-1", "sCode": "0"}]}

        response = runtime.place_order(
            {
                "instId": "BTC-USDT-SWAP",
                "tdMode": "isolated",
                "side": "buy",
                "ordType": "market",
                "sz": "1",
                "clOrdId": "apws123",
            },
            timeoutSeconds=0.2,
        )

        self.assertEqual(response["data"][0]["ordId"], "ws-order-1")
        self.assertEqual(app.sent[-1]["op"], "order")
        self.assertEqual(app.sent[-1]["args"][0]["clOrdId"], "apws123")
        self.assertTrue(runtime.status()["orderTransportReady"])

    def test_order_is_rejected_before_send_when_private_ws_is_not_ready(self) -> None:
        runtime = OkxDemoPrivateWsRuntime(
            OkxDemoCredentials("key", "secret", "pass"),
            websocket_factory=lambda url, **callbacks: FakeWebSocketApp(url, **callbacks),
        )
        runtime.create_app()

        with self.assertRaises(OkxPrivateWsUnavailable):
            runtime.place_order({"clOrdId": "apws123"}, timeoutSeconds=0.1)


if __name__ == "__main__":
    unittest.main()
