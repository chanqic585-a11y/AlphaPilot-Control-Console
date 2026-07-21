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

    def test_read_only_surface_excludes_withdraw_transfer_and_post_methods(self) -> None:
        paths = self.client.read_only_endpoint_paths()

        self.assertIn("/api/v5/account/balance", paths)
        self.assertIn("/api/v5/account/instruments", paths)
        self.assertIn("/api/v5/account/leverage-info", paths)
        self.assertNotIn("/api/v5/asset/withdrawal", paths)
        self.assertNotIn("/api/v5/asset/transfer", paths)
        self.assertFalse(hasattr(self.client, "withdraw"))
        self.assertFalse(hasattr(self.client, "transfer"))

    def test_live_preflight_read_methods_are_allowlisted(self) -> None:
        self.client.get_account_instruments("SWAP")
        self.client.get_leverage(instId="ETH-USDT-SWAP", marginMode="isolated")

        instruments_request, leverage_request = self.transport.requests
        self.assertEqual(instruments_request.path, "/api/v5/account/instruments")
        self.assertEqual(instruments_request.query, {"instType": "SWAP"})
        self.assertEqual(leverage_request.path, "/api/v5/account/leverage-info")
        self.assertEqual(
            leverage_request.query,
            {"instId": "ETH-USDT-SWAP", "mgnMode": "isolated"},
        )

    def test_both_attached_protection_prices_are_required(self) -> None:
        payload = self.protected_order()
        del payload["attachAlgoOrds"][0]["slTriggerPx"]
        with self.assertRaises(ValueError):
            self.client.place_protected_order(payload)

    def test_emergency_close_position_is_allowlisted_and_reduce_only(self) -> None:
        self.client.close_position(
            instId="BTC-USDT-SWAP",
            marginMode="isolated",
            posSide="long",
        )

        request = self.transport.requests[-1]
        self.assertEqual(request.path, "/api/v5/trade/close-position")
        self.assertEqual(request.body["instId"], "BTC-USDT-SWAP")
        self.assertEqual(request.body["mgnMode"], "isolated")
        self.assertEqual(request.body["posSide"], "long")

    def test_emergency_close_position_rejects_cross_margin(self) -> None:
        with self.assertRaises(ValueError):
            self.client.close_position(
                instId="BTC-USDT-SWAP",
                marginMode="cross",
                posSide="long",
            )


if __name__ == "__main__":
    unittest.main()
