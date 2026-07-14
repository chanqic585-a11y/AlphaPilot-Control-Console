from __future__ import annotations

import unittest

from alphapilot_control_console.credential_runtime import OkxDemoCredentials
from alphapilot_control_console.exchange_connectors.okx_demo_client import (
    OkxDemoClient,
    OkxDemoRequest,
    resolve_okx_rest_url,
)


class FakeTransport:
    def __init__(self) -> None:
        self.requests: list[OkxDemoRequest] = []

    def send(self, request: OkxDemoRequest) -> dict:
        self.requests.append(request)
        return {"code": "0", "msg": "", "data": [{"ordId": "123", "sCode": "0"}]}


class OkxDemoClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = FakeTransport()
        self.client = OkxDemoClient(
            OkxDemoCredentials("key", "secret", "pass"),
            transport=self.transport,
            timestampFactory=lambda: "2026-07-10T00:00:00.000Z",
        )

    def test_place_order_uses_demo_header_and_client_order_id(self) -> None:
        response = self.client.place_order(
            {
                "instId": "BTC-USDT-SWAP",
                "tdMode": "isolated",
                "side": "buy",
                "posSide": "long",
                "ordType": "market",
                "sz": "1",
                "clOrdId": "apdemo123",
            }
        )

        request = self.transport.requests[0]
        self.assertEqual(response["code"], "0")
        self.assertEqual(request.path, "/api/v5/trade/order")
        self.assertEqual(request.headers["x-simulated-trading"], "1")
        self.assertEqual(request.headers["Accept"], "application/json")
        self.assertEqual(request.headers["User-Agent"], "AlphaPilot-Control-Console/13.15.2")
        self.assertEqual(request.body["clOrdId"], "apdemo123")
        self.assertIn("OK-ACCESS-SIGN", request.headers)

    def test_account_instruments_uses_read_only_demo_endpoint(self) -> None:
        response = self.client.get_account_instruments("SWAP")

        request = self.transport.requests[0]
        self.assertEqual(response["code"], "0")
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.path, "/api/v5/account/instruments")
        self.assertEqual(request.query, {"instType": "SWAP"})
        self.assertEqual(request.headers["x-simulated-trading"], "1")

    def test_set_leverage_uses_demo_trade_endpoint(self) -> None:
        response = self.client.set_leverage(
            instrumentId="BTC-USDT-SWAP",
            leverage=5,
            marginMode="isolated",
            positionSide="long",
        )

        request = self.transport.requests[0]
        self.assertEqual(response["code"], "0")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.path, "/api/v5/account/set-leverage")
        self.assertEqual(
            request.body,
            {"instId": "BTC-USDT-SWAP", "lever": "5", "mgnMode": "isolated", "posSide": "long"},
        )
        self.assertEqual(request.headers["x-simulated-trading"], "1")

    def test_set_leverage_rejects_values_outside_one_to_five(self) -> None:
        for value in (0, 6, 2.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.client.set_leverage(
                    instrumentId="BTC-USDT-SWAP",
                    leverage=value,
                    marginMode="isolated",
                )

    def test_withdraw_endpoint_is_not_in_allowlist(self) -> None:
        with self.assertRaises(PermissionError):
            self.client.request("POST", "/api/v5/asset/withdrawal", body={"amt": "1"})

    def test_invalid_client_order_id_is_rejected_locally(self) -> None:
        with self.assertRaises(ValueError):
            self.client.place_order(
                {
                    "instId": "BTC-USDT-SWAP",
                    "tdMode": "isolated",
                    "side": "buy",
                    "ordType": "market",
                    "sz": "1",
                    "clOrdId": "contains spaces",
                }
            )

    def test_global_site_resolves_to_official_rest_domain(self) -> None:
        self.assertEqual(resolve_okx_rest_url("global"), "https://openapi.okx.com")

    def test_unknown_site_is_rejected_locally(self) -> None:
        with self.assertRaises(ValueError):
            resolve_okx_rest_url("unknown")

    def test_mismatched_custom_base_url_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            OkxDemoClient(
                OkxDemoCredentials("key", "secret", "pass"),
                site="global",
                baseUrl="https://us.okx.com",
            )


if __name__ == "__main__":
    unittest.main()
