from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.live_engineering_smoke_contract import (
    build_live_engineering_smoke_approval_request,
    build_live_engineering_smoke_contract,
)
from alphapilot_control_console.live_engineering_smoke_service import run_live_engineering_smoke


class FakeLiveSmokeClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.order_state = "live"

    def get_account_config(self) -> dict:
        self.calls.append("account_config")
        return {"code": "0", "data": [{"posMode": "net_mode"}]}

    def get_balance(self, currency: str = "USDT") -> dict:
        self.calls.append("balance")
        return {
            "code": "0",
            "data": [{"details": [{"ccy": currency, "availBal": "100"}]}],
        }

    def get_leverage(self, *, instId: str, marginMode: str) -> dict:
        self.calls.append("leverage")
        return {
            "code": "0",
            "data": [{"instId": instId, "mgnMode": marginMode, "lever": "1"}],
        }

    def get_positions(self, instrumentId: str | None = None) -> dict:
        self.calls.append("positions")
        return {"code": "0", "data": []}

    def get_open_orders(self, instrumentId: str | None = None) -> dict:
        self.calls.append("open_orders")
        return {"code": "0", "data": []}

    def place_protected_order(self, payload: dict) -> dict:
        self.calls.append("place_order")
        return {"code": "0", "data": [{"ordId": "order-1", "clOrdId": payload["clOrdId"]}]}

    def get_order(self, *, instId: str, ordId: str | None = None, clOrdId: str | None = None) -> dict:
        self.calls.append("get_order")
        return {"code": "0", "data": [{"ordId": ordId, "state": self.order_state}]}

    def cancel_order(self, *, instId: str, ordId: str | None = None, clOrdId: str | None = None) -> dict:
        self.calls.append("cancel_order")
        self.order_state = "canceled"
        return {"code": "0", "data": [{"ordId": ordId, "sCode": "0"}]}


class LiveEngineeringSmokeServiceTests(unittest.TestCase):
    def test_smoke_submits_once_cancels_and_reconciles_in_isolated_evidence(self) -> None:
        contract = build_live_engineering_smoke_contract(
            created_at="2026-07-21T06:00:00Z",
            maximum_notional_usdt=10.0,
        )
        request = build_live_engineering_smoke_approval_request(contract)
        approval = {
            "actor": "user_explicit",
            "contractHash": contract["contractHash"],
            "confirmation": request["requiredConfirmation"],
        }
        instrument = {
            "instId": "BTC-USDT-SWAP",
            "state": "live",
            "tickSz": "0.1",
            "lotSz": "0.001",
            "minSz": "0.001",
            "ctVal": "0.01",
        }
        quote = {"bidPx": "100000", "askPx": "100001"}
        client = FakeLiveSmokeClient()

        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "live_smoke.json"
            attempt = Path(directory) / "live_smoke_attempt.json"
            result = run_live_engineering_smoke(
                client=client,
                contract=contract,
                approval=approval,
                instrument=instrument,
                quote=quote,
                output_path=evidence,
                attempt_path=attempt,
            )

            self.assertEqual(result["status"], "completed_canceled_and_reconciled")
            self.assertEqual(result["orderAttemptCount"], 1)
            self.assertTrue(result["cancelConfirmed"])
            self.assertTrue(result["finalReconciliationMatched"])
            self.assertFalse(result["strategyQualification"])
            self.assertFalse(result["promotionEligible"])
            self.assertEqual(
                client.calls,
                [
                    "account_config",
                    "balance",
                    "positions",
                    "open_orders",
                    "leverage",
                    "place_order",
                    "get_order",
                    "cancel_order",
                    "get_order",
                    "positions",
                    "open_orders",
                ],
            )
            stored = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertNotIn("approval", stored)
            self.assertNotIn("credentials", stored)
            attempt_state = json.loads(attempt.read_text(encoding="utf-8"))
            self.assertEqual(attempt_state["status"], "completed_canceled_and_reconciled")
            self.assertEqual(attempt_state["orderAttemptCount"], 1)

    def test_existing_attempt_marker_blocks_before_client_calls(self) -> None:
        contract = build_live_engineering_smoke_contract(
            created_at="2026-07-21T06:00:00Z",
            maximum_notional_usdt=10.0,
        )
        request = build_live_engineering_smoke_approval_request(contract)
        approval = {
            "actor": "user_explicit",
            "contractHash": contract["contractHash"],
            "confirmation": request["requiredConfirmation"],
        }
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory) / "live_smoke_attempt.json"
            attempt.write_text('{"status":"attempt_reserved"}\n', encoding="utf-8")
            client = FakeLiveSmokeClient()
            with self.assertRaises(PermissionError):
                run_live_engineering_smoke(
                    client=client,
                    contract=contract,
                    approval=approval,
                    instrument={
                        "instId": "BTC-USDT-SWAP",
                        "state": "live",
                        "tickSz": "0.1",
                        "lotSz": "0.001",
                        "minSz": "0.001",
                        "ctVal": "0.01",
                    },
                    quote={"bidPx": "100000", "askPx": "100001"},
                    attempt_path=attempt,
                )
            self.assertEqual(client.calls, [])

    def test_missing_approval_blocks_before_client_calls(self) -> None:
        contract = build_live_engineering_smoke_contract(
            created_at="2026-07-21T06:00:00Z",
            maximum_notional_usdt=10.0,
        )
        client = FakeLiveSmokeClient()
        with self.assertRaises(PermissionError):
            run_live_engineering_smoke(
                client=client,
                contract=contract,
                approval={},
                instrument={"instId": "BTC-USDT-SWAP"},
                quote={"bidPx": "100000", "askPx": "100001"},
            )
        self.assertEqual(client.calls, [])

    def test_non_1x_leverage_blocks_before_attempt_reservation_or_order(self) -> None:
        contract = build_live_engineering_smoke_contract(
            created_at="2026-07-21T06:00:00Z",
            maximum_notional_usdt=10.0,
        )
        request = build_live_engineering_smoke_approval_request(contract)
        approval = {
            "actor": "user_explicit",
            "contractHash": contract["contractHash"],
            "confirmation": request["requiredConfirmation"],
        }
        client = FakeLiveSmokeClient()
        client.get_leverage = lambda **_: {
            "code": "0",
            "data": [{"instId": "BTC-USDT-SWAP", "mgnMode": "isolated", "lever": "2"}],
        }
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory) / "live_smoke_attempt.json"
            with self.assertRaises(RuntimeError) as caught:
                run_live_engineering_smoke(
                    client=client,
                    contract=contract,
                    approval=approval,
                    instrument={
                        "instId": "BTC-USDT-SWAP",
                        "state": "live",
                        "tickSz": "0.1",
                        "lotSz": "0.001",
                        "minSz": "0.001",
                        "ctVal": "0.01",
                    },
                    quote={"bidPx": "100000", "askPx": "100001"},
                    attempt_path=attempt,
                )
            self.assertEqual(caught.exception.safe_code, "isolated_leverage_not_1x")
            self.assertEqual(caught.exception.safe_instrument_id, "BTC-USDT-SWAP")
            self.assertFalse(attempt.exists())
            self.assertNotIn("place_order", client.calls)

    def test_long_short_mode_uses_explicit_long_position_side(self) -> None:
        contract = build_live_engineering_smoke_contract(
            created_at="2026-07-21T06:00:00Z",
            maximum_notional_usdt=10.0,
        )
        request = build_live_engineering_smoke_approval_request(contract)
        approval = {
            "actor": "user_explicit",
            "contractHash": contract["contractHash"],
            "confirmation": request["requiredConfirmation"],
        }
        client = FakeLiveSmokeClient()
        client.get_account_config = lambda: {
            "code": "0",
            "data": [{"posMode": "long_short_mode"}],
        }
        client.get_leverage = lambda **_: {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "mgnMode": "isolated",
                    "posSide": "long",
                    "lever": "1",
                },
                {
                    "instId": "BTC-USDT-SWAP",
                    "mgnMode": "isolated",
                    "posSide": "short",
                    "lever": "3",
                },
            ],
        }
        submitted_payloads: list[dict] = []

        def place_protected_order(payload: dict) -> dict:
            client.calls.append("place_order")
            submitted_payloads.append(payload)
            return {
                "code": "0",
                "data": [{"ordId": "order-1", "clOrdId": payload["clOrdId"]}],
            }

        client.place_protected_order = place_protected_order

        result = run_live_engineering_smoke(
            client=client,
            contract=contract,
            approval=approval,
            instrument={
                "instId": "BTC-USDT-SWAP",
                "state": "live",
                "tickSz": "0.1",
                "lotSz": "0.001",
                "minSz": "0.001",
                "ctVal": "0.01",
            },
            quote={"bidPx": "100000", "askPx": "100001"},
        )

        self.assertEqual(result["status"], "completed_canceled_and_reconciled")
        self.assertEqual(submitted_payloads[0]["posSide"], "long")

    def test_unknown_position_mode_has_safe_preflight_code_and_no_attempt(self) -> None:
        contract = build_live_engineering_smoke_contract(
            created_at="2026-07-21T06:00:00Z",
            maximum_notional_usdt=10.0,
        )
        request = build_live_engineering_smoke_approval_request(contract)
        approval = {
            "actor": "user_explicit",
            "contractHash": contract["contractHash"],
            "confirmation": request["requiredConfirmation"],
        }
        client = FakeLiveSmokeClient()
        client.get_account_config = lambda: {
            "code": "0",
            "data": [{"posMode": "portfolio_mode"}],
        }
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory) / "live_smoke_attempt.json"
            with self.assertRaises(RuntimeError) as caught:
                run_live_engineering_smoke(
                    client=client,
                    contract=contract,
                    approval=approval,
                    instrument={
                        "instId": "BTC-USDT-SWAP",
                        "state": "live",
                        "tickSz": "0.1",
                        "lotSz": "0.001",
                        "minSz": "0.001",
                        "ctVal": "0.01",
                    },
                    quote={"bidPx": "100000", "askPx": "100001"},
                    attempt_path=attempt,
                )
            self.assertEqual(caught.exception.safe_code, "unsupported_position_mode")
            self.assertFalse(attempt.exists())
            self.assertNotIn("place_order", client.calls)


if __name__ == "__main__":
    unittest.main()
