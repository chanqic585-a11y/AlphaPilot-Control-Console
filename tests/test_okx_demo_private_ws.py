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
    build_okx_private_ws_login,
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

    def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    def close(self) -> None:
        self.closed = True


class OkxDemoPrivateWsTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
