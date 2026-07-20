from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.v46_engineering_smoke import (
    build_v46_engineering_smoke_contract,
    run_v46_engineering_smoke_phase,
    validate_v46_engineering_smoke_contract,
)


RELEASE_ID = "provisional_research_demo_v46_a3669d95101ba65f68fa89b1"
RELEASE_HASH = "provisional_demo_release_c1e28ecf59fb7fcc2b4876eec5e6fd04c50002bef28c69c03bedf164af7cd225"
RISK_HASH = "risk_overlay_7221d23144dcd0a357136f6e9587a505d81c86439e223457d2d7393d287b8218"
INTERSECTION_HASH = "demo_execution_intersection_1bcd5f70a24d1d2527a29965d95d1c47473f0e85a442dfda744354d95e0bd514"
REQUEST_HASH = "engineering_smoke_evidence_3347652ed144d6b9be81f16b860c1a2fc190c0ab109a24d820c4f13969779eca"


def _release() -> dict:
    return {
        "releaseId": RELEASE_ID,
        "releaseHash": RELEASE_HASH,
        "riskOverlayHash": RISK_HASH,
        "executionIntersectionHash": INTERSECTION_HASH,
        "executionInstruments": [
            "BTC-USDT-SWAP",
            "DOGE-USDT-SWAP",
            "ETH-USDT-SWAP",
            "SOL-USDT-SWAP",
            "XRP-USDT-SWAP",
        ],
        "formalPass": False,
        "approved": False,
        "demoArm": False,
        "livePromotionEligible": False,
    }


def _risk() -> dict:
    return {
        "riskOverlayHash": RISK_HASH,
        "environment": "okx_demo_only",
        "maximumConcurrentPositions": 3,
        "maximumLeverage": 2,
        "noAdding": True,
        "noAveraging": True,
        "noMartingale": True,
        "withdrawAllowed": False,
        "liveExecutionAllowed": False,
    }


def _universe() -> dict:
    return {
        "executionIntersectionHash": INTERSECTION_HASH,
        "executionInstruments": _release()["executionInstruments"],
        "status": "usable",
    }


def _request() -> dict:
    return {
        "requestType": "engineering_smoke_only",
        "releaseId": RELEASE_ID,
        "releaseHash": RELEASE_HASH,
        "riskOverlayHash": RISK_HASH,
        "evidenceHash": REQUEST_HASH,
        "approvalGranted": False,
        "strategyReleaseApprovalAccepted": False,
        "demoArm": False,
    }


def _approval_text() -> str:
    return "\n".join(
        [
            "# AlphaPilot V46 OKX Demo Engineering Smoke Explicit Approval",
            RELEASE_ID,
            RELEASE_HASH,
            RISK_HASH,
            INTERSECTION_HASH,
            REQUEST_HASH,
            "engineering_smoke_only",
            "strategyQualification=false",
            "formalPass=false",
            "forwardEvidenceEligible=false",
            "livePromotionEligible=false",
            "blocked_waiting_exact_release_approval",
        ]
    )


class FakeWs:
    def __init__(self) -> None:
        self.started = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def status(self) -> dict:
        return {
            "connected": self.started,
            "authenticated": self.started,
            "subscribed": self.started,
            "channels": ["orders", "positions", "account"],
            "lastError": None,
            "credentialsStored": False,
            "demoOnly": True,
        }


class FakeClient:
    site = "global"
    base_url = "https://openapi.okx.com"

    def __init__(
        self,
        *,
        unknown_order: bool = False,
        rate_limit_first_disarm: bool = False,
    ) -> None:
        self.unknown_order = unknown_order
        self.rate_limit_first_disarm = rate_limit_first_disarm
        self.disarm_rate_limit_returned = False
        self.position = 0.0
        self.orders: dict[str, dict] = {}
        self.place_payloads: list[dict] = []
        self.cancel_all_after_calls: list[int] = []

    def synchronize_server_time(self) -> dict:
        return {"roundTripMilliseconds": 2, "offsetMilliseconds": 1}

    def get_account_config(self) -> dict:
        return {"code": "0", "data": [{"acctLv": "2", "posMode": "net_mode"}]}

    def get_account_instruments(self, instrumentType="SWAP") -> dict:
        return {
            "code": "0",
            "data": [{
                "instId": "BTC-USDT-SWAP",
                "instType": "SWAP",
                "settleCcy": "USDT",
                "state": "live",
                "tickSz": "0.1",
                "lotSz": "0.01",
                "minSz": "0.01",
                "ctVal": "0.01",
                "ctType": "linear",
            }],
        }

    def get_balance(self, currency="USDT") -> dict:
        return {"code": "0", "data": [{"details": [{"ccy": "USDT", "availEq": "1000"}]}]}

    def get_positions(self, instrumentId=None, instrumentType=None) -> dict:
        rows = [] if self.position == 0 else [{
            "instId": "BTC-USDT-SWAP",
            "pos": format(self.position, ".15g"),
            "posSide": "net",
        }]
        return {"code": "0", "data": rows}

    def get_open_orders(self, instrumentId=None) -> dict:
        if self.unknown_order:
            return {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "clOrdId": "unknown1"}]}
        rows = [row for row in self.orders.values() if row["state"] == "live"]
        return {"code": "0", "data": rows}

    def get_fills(self, instrumentId=None, limit=100) -> dict:
        rows = [row for row in self.orders.values() if float(row.get("accFillSz") or 0) > 0]
        return {"code": "0", "data": rows}

    def get_ticker(self, instrumentId: str) -> dict:
        return {"code": "0", "data": [{"instId": instrumentId, "bidPx": "60000", "askPx": "60000.1"}]}

    def place_order(self, payload: dict) -> dict:
        self.place_payloads.append(dict(payload))
        client_id = payload["clOrdId"]
        if payload["ordType"] == "post_only":
            row = {"ordId": "1", "clOrdId": client_id, "state": "live", "accFillSz": "0"}
        elif payload.get("reduceOnly"):
            quantity = float(payload["sz"])
            self.position = max(0.0, self.position - quantity)
            row = {"ordId": "3", "clOrdId": client_id, "state": "filled", "accFillSz": payload["sz"]}
        else:
            self.position += float(payload["sz"])
            row = {"ordId": "2", "clOrdId": client_id, "state": "filled", "accFillSz": payload["sz"]}
        self.orders[client_id] = row
        return {"code": "0", "data": [{"ordId": row["ordId"], "clOrdId": client_id, "sCode": "0", "sMsg": ""}]}

    def get_order(self, *, instId: str, ordId=None, clOrdId=None) -> dict:
        row = self.orders[str(clOrdId)]
        return {"code": "0", "data": [dict(row)]}

    def cancel_order(self, *, instId: str, ordId=None, clOrdId=None) -> dict:
        row = self.orders[str(clOrdId)]
        row["state"] = "canceled"
        return {"code": "0", "data": [{"ordId": row["ordId"], "clOrdId": clOrdId, "sCode": "0"}]}

    def cancel_all_after(self, timeoutSeconds: int) -> dict:
        self.cancel_all_after_calls.append(timeoutSeconds)
        if (
            timeoutSeconds == 0
            and self.rate_limit_first_disarm
            and not self.disarm_rate_limit_returned
        ):
            self.disarm_rate_limit_returned = True
            return {"code": "50011", "data": [], "msg": "Rate limit reached"}
        return {"code": "0", "data": [{"triggerTime": "0", "ts": "0"}]}


class V46EngineeringSmokeTests(unittest.TestCase):
    def _contract(self) -> dict:
        return build_v46_engineering_smoke_contract(
            release=_release(),
            risk_overlay=_risk(),
            universe=_universe(),
            smoke_request=_request(),
            approval_document_text=_approval_text(),
            generated_at="2026-07-20T16:00:00Z",
            instrument={
                "instId": "BTC-USDT-SWAP",
                "instType": "SWAP",
                "settleCcy": "USDT",
                "state": "live",
                "tickSz": "0.1",
                "lotSz": "0.01",
                "minSz": "0.01",
                "ctVal": "0.01",
                "ctType": "linear",
            },
            account_mode="2",
            position_mode="net_mode",
        )

    def test_contract_binds_exact_v46_identity_and_rejects_tampering(self) -> None:
        contract = self._contract()
        validate_v46_engineering_smoke_contract(contract)
        self.assertEqual(contract["releaseId"], RELEASE_ID)
        self.assertEqual(contract["approvedRequestEvidenceHash"], REQUEST_HASH)
        self.assertFalse(contract["strategyQualification"])
        self.assertFalse(contract["formalPass"])
        self.assertFalse(contract["forwardEvidenceEligible"])
        self.assertFalse(contract["livePromotionEligible"])
        self.assertEqual(contract["maximumOrderSize"], "0.01")
        self.assertNotIn("secret", json.dumps(contract).lower())
        with self.assertRaises((PermissionError, ValueError)):
            validate_v46_engineering_smoke_contract({**contract, "releaseHash": "wrong"})

    def test_contract_accepts_frozen_demo_only_overlay_without_redundant_negative_flags(self) -> None:
        risk = _risk()
        risk.pop("withdrawAllowed")
        risk.pop("liveExecutionAllowed")

        contract = build_v46_engineering_smoke_contract(
            release=_release(),
            risk_overlay=risk,
            universe=_universe(),
            smoke_request=_request(),
            approval_document_text=_approval_text(),
            generated_at="2026-07-20T16:00:00Z",
            instrument={
                "instId": "BTC-USDT-SWAP",
                "instType": "SWAP",
                "settleCcy": "USDT",
                "state": "live",
                "tickSz": "0.1",
                "lotSz": "0.01",
                "minSz": "0.01",
                "ctVal": "0.01",
                "ctType": "linear",
            },
            account_mode="2",
            position_mode="net_mode",
        )

        self.assertEqual(contract["environment"], "okx_demo_only")
        self.assertFalse(contract["liveExecutionAllowed"])
        self.assertFalse(contract["withdrawAllowed"])

    def test_contract_accepts_actual_universe_field_and_spaced_approval_assignments(self) -> None:
        universe = _universe()
        universe["executionIntersection"] = universe.pop("executionInstruments")
        approval = _approval_text().replace("=false", " = false")

        contract = build_v46_engineering_smoke_contract(
            release=_release(),
            risk_overlay=_risk(),
            universe=universe,
            smoke_request=_request(),
            approval_document_text=approval,
            generated_at="2026-07-20T16:00:00Z",
            instrument={
                "instId": "BTC-USDT-SWAP",
                "instType": "SWAP",
                "settleCcy": "USDT",
                "state": "live",
                "tickSz": "0.1",
                "lotSz": "0.01",
                "minSz": "0.01",
                "ctVal": "0.01",
                "ctType": "linear",
            },
            account_mode="2",
            position_mode="net_mode",
        )

        self.assertEqual(contract["executionIntersectionHash"], INTERSECTION_HASH)

    def test_contract_rejects_any_explicit_live_or_withdraw_enablement(self) -> None:
        for field in ("liveExecutionAllowed", "withdrawAllowed"):
            with self.subTest(field=field):
                risk = _risk()
                risk[field] = True
                with self.assertRaises(PermissionError):
                    build_v46_engineering_smoke_contract(
                        release=_release(),
                        risk_overlay=risk,
                        universe=_universe(),
                        smoke_request=_request(),
                        approval_document_text=_approval_text(),
                        generated_at="2026-07-20T16:00:00Z",
                        instrument={
                            "instId": "BTC-USDT-SWAP",
                            "instType": "SWAP",
                            "settleCcy": "USDT",
                            "state": "live",
                            "tickSz": "0.1",
                            "lotSz": "0.01",
                            "minSz": "0.01",
                            "ctVal": "0.01",
                            "ctType": "linear",
                        },
                        account_mode="2",
                        position_mode="net_mode",
                    )

    def test_two_process_phases_complete_once_and_write_required_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            client = FakeClient()
            counts = lambda: {"strategyOrderCount": 0, "strategyClosedTradeCount": 0}
            first = run_v46_engineering_smoke_phase(
                client=client,
                private_ws=FakeWs(),
                contract=self._contract(),
                output_dir=output,
                phase="path_a",
                strategy_evidence_snapshot=counts,
            )
            self.assertEqual(first["status"], "path_a_completed")
            self.assertEqual(len(client.place_payloads), 1)
            self.assertEqual(client.place_payloads[0]["ordType"], "post_only")
            self.assertEqual(client.orders[client.place_payloads[0]["clOrdId"]]["state"], "canceled")

            second = run_v46_engineering_smoke_phase(
                client=client,
                private_ws=FakeWs(),
                contract=self._contract(),
                output_dir=output,
                phase="resume_path_b",
                strategy_evidence_snapshot=counts,
                cancel_all_after_delay_seconds=0,
            )
            self.assertEqual(second["status"], "completed")
            self.assertEqual(len(client.place_payloads), 3)
            self.assertEqual(client.position, 0)
            self.assertEqual(client.cancel_all_after_calls, [10, 0])

            required = {
                "engineering_smoke_contract.json",
                "engineering_smoke_contract_hash_audit.json",
                "engineering_smoke_approval_overlay.json",
                "engineering_smoke_private_preflight.json",
                "engineering_smoke_cancel_audit.json",
                "engineering_smoke_fill_close_audit.json",
                "engineering_smoke_order_ledger.jsonl",
                "engineering_smoke_fill_ledger.jsonl",
                "engineering_smoke_position_ledger.jsonl",
                "engineering_smoke_restart_recovery_audit.json",
                "engineering_smoke_rest_reconciliation_audit.json",
                "engineering_smoke_private_websocket_audit.json",
                "engineering_smoke_kill_switch_audit.json",
                "engineering_smoke_strategy_evidence_isolation_audit.json",
                "engineering_smoke_final_self_check.json",
                "engineering_smoke_artifact_manifest.json",
            }
            self.assertTrue(required.issubset({path.name for path in output.iterdir()}))
            isolation = json.loads((output / "engineering_smoke_strategy_evidence_isolation_audit.json").read_text(encoding="utf-8"))
            self.assertFalse(isolation["strategyEvidenceChanged"])
            self.assertEqual(isolation["strategyOrderCountDelta"], 0)
            self.assertEqual(isolation["strategyClosedTradeCountDelta"], 0)

            repeated = run_v46_engineering_smoke_phase(
                client=client,
                private_ws=FakeWs(),
                contract=self._contract(),
                output_dir=output,
                phase="resume_path_b",
                strategy_evidence_snapshot=counts,
            )
            self.assertEqual(repeated["status"], "completed")
            self.assertEqual(len(client.place_payloads), 3)

    def test_cancel_all_after_retries_okx_rate_limit_without_duplicate_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            client = FakeClient(rate_limit_first_disarm=True)
            counts = lambda: {"strategyOrderCount": 0, "strategyClosedTradeCount": 0}
            run_v46_engineering_smoke_phase(
                client=client,
                private_ws=FakeWs(),
                contract=self._contract(),
                output_dir=output,
                phase="path_a",
                strategy_evidence_snapshot=counts,
            )
            result = run_v46_engineering_smoke_phase(
                client=client,
                private_ws=FakeWs(),
                contract=self._contract(),
                output_dir=output,
                phase="resume_path_b",
                strategy_evidence_snapshot=counts,
                cancel_all_after_delay_seconds=0,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(client.cancel_all_after_calls, [10, 0, 0])
            self.assertEqual(len(client.place_payloads), 3)
            self.assertEqual(client.position, 0)

    def test_unknown_order_fails_closed_before_order_submission(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            client = FakeClient(unknown_order=True)
            result = run_v46_engineering_smoke_phase(
                client=client,
                private_ws=FakeWs(),
                contract=self._contract(),
                output_dir=Path(temporary),
                phase="path_a",
                strategy_evidence_snapshot=lambda: {
                    "strategyOrderCount": 0,
                    "strategyClosedTradeCount": 0,
                },
            )
            self.assertEqual(result["status"], "blocked")
            self.assertIn("unknown_pending_order", result["blockers"])
            self.assertEqual(client.place_payloads, [])


if __name__ == "__main__":
    unittest.main()
