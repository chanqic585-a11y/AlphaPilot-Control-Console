from __future__ import annotations

import unittest

from alphapilot_control_console.okx_demo_private_reconciliation import (
    OkxDemoPrivateState,
    reconcile_okx_demo_private_state,
)


class FakeClient:
    def __init__(self, *, orphan: bool = False) -> None:
        self.orphan = orphan

    def get_open_orders(self):
        return {"code": "0", "data": [{"clOrdId": "open1", "state": "live"}]}

    def get_fills(self, limit=100):
        return {"code": "0", "data": [{"clOrdId": "filled1", "fillSz": "1"}]}

    def get_positions(self, instrumentType="SWAP"):
        rows = [{"instId": "BTC-USDT-SWAP", "pos": "1"}]
        if self.orphan:
            rows.append({"instId": "ETH-USDT-SWAP", "pos": "2"})
        return {"code": "0", "data": rows}

    def get_balance(self, currency="USDT"):
        return {"code": "0", "data": [{"details": [{"ccy": "USDT", "availEq": "1000"}]}]}


class OkxDemoPrivateReconciliationTests(unittest.TestCase):
    def test_ws_partial_fill_and_rest_state_reconcile_without_invented_records(self) -> None:
        state = OkxDemoPrivateState()
        state.apply({
            "arg": {"channel": "orders"},
            "data": [{
                "clOrdId": "open1",
                "instId": "BTC-USDT-SWAP",
                "state": "partially_filled",
                "accFillSz": "0.5",
                "sz": "1",
            }],
        })
        state.apply({
            "arg": {"channel": "positions"},
            "data": [{"instId": "BTC-USDT-SWAP", "pos": "1"}],
        })

        result = reconcile_okx_demo_private_state(
            FakeClient(),
            ws_state=state,
            expected_client_order_ids={"open1", "filled1"},
            expected_position_instruments={"BTC-USDT-SWAP"},
        )

        self.assertTrue(result["matched"])
        self.assertTrue(result["partialFillObserved"])
        self.assertEqual(result["unknownOrderCount"], 0)
        self.assertEqual(result["orphanPositionCount"], 0)
        self.assertEqual(result["blockers"], [])

    def test_orphan_position_fails_closed(self) -> None:
        result = reconcile_okx_demo_private_state(
            FakeClient(orphan=True),
            ws_state=OkxDemoPrivateState(),
            expected_client_order_ids={"open1", "filled1"},
            expected_position_instruments={"BTC-USDT-SWAP"},
        )

        self.assertFalse(result["matched"])
        self.assertEqual(result["orphanPositionCount"], 1)
        self.assertIn("orphan_demo_position", result["blockers"])

    def test_private_rest_error_fails_closed(self) -> None:
        client = FakeClient()
        client.get_balance = lambda currency="USDT": {"code": "50110", "data": []}

        result = reconcile_okx_demo_private_state(
            client,
            ws_state=OkxDemoPrivateState(),
        )

        self.assertFalse(result["matched"])
        self.assertIn("demo_private_rest_error", result["blockers"])


if __name__ == "__main__":
    unittest.main()
