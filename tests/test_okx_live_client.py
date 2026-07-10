from __future__ import annotations

import unittest

from alphapilot_control_console.credential_runtime import OkxLiveCredentials
from alphapilot_control_console.exchange_connectors.okx_live_client import (
    OkxLiveClient,
    OkxLiveRequest,
)


class FakeTransport:
    def __init__(self) -> None:
        self.requests: list[OkxLiveRequest] = []

    def send(self, request: OkxLiveRequest) -> dict:
        self.requests.append(request)
        return {"code": "0", "msg": "", "data": [{"ordId": "live-1", "sCode": "0"}]}


class OkxLiveClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = FakeTransport()
        self.client = OkxLiveClient(
            OkxLiveCredentials("key", "secret", "pass"),
            transport=self.transport,
            timestampFactory=lambda: "2026-07-11T00:00:00.000Z",
        )

    @staticmethod
    def protected_order() -> dict:
        return {
            "instId": "BTC-USDT-SWAP",
            "tdMode": "isolated",
            "side": "buy",
            "posSide": "long",
            "ordType": "market",
            "sz": "1",
            "clOrdId": "aplive123",
            "attachAlgoOrds": [{
                "tpTriggerPx": "102",
                "tpOrdPx": "-1",
                "slTriggerPx": "99",
                "slOrdPx": "-1",
            }],
        }

    def test_live_request_has_no_simulated_trading_header(self) -> None:
        self.client.place_protected_order(self.protected_order())
        request = self.transport.requests[0]

        self.assertNotIn("x-simulated-trading", request.headers)
        self.assertEqual(request.path, "/api/v5/trade/order")
        self.assertIn("OK-ACCESS-SIGN", request.headers)

    def test_withdraw_is_not_allowlisted(self) -> None:
        with self.assertRaises(PermissionError):
            self.client.request("POST", "/api/v5/asset/withdrawal", body={"amt": "1"})

    def test_both_attached_protection_prices_are_required(self) -> None:
        payload = self.protected_order()
        del payload["attachAlgoOrds"][0]["slTriggerPx"]
        with self.assertRaises(ValueError):
            self.client.place_protected_order(payload)


if __name__ == "__main__":
    unittest.main()
