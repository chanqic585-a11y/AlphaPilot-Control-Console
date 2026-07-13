from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from alphapilot_control_console.demo_execution_engine import DemoExecutionEngine
from alphapilot_control_console.demo_execution_store import DemoExecutionStore
from alphapilot_control_console.execution_outcome_store import ExecutionOutcomeStore


class FakeDemoClient:
    def __init__(self) -> None:
        self.placeCalls = 0
        self.queryCalls = 0
        self.killCalls = 0

    def place_order(self, payload: dict) -> dict:
        self.placeCalls += 1
        return {"code": "0", "data": [{"ordId": "okx-1", "clOrdId": payload["clOrdId"], "sCode": "0"}]}

    def get_order(self, *, instId: str, ordId: str | None = None, clOrdId: str | None = None) -> dict:
        self.queryCalls += 1
        state = "partially_filled" if self.queryCalls == 1 else "filled"
        return {"code": "0", "data": [{"ordId": "okx-1", "state": state, "accFillSz": str(self.queryCalls)}]}

    def cancel_all_after(self, timeoutSeconds: int) -> dict:
        self.killCalls += 1
        return {"code": "0", "data": [{"triggerTime": "1"}]}


def contract() -> dict:
    return {
        "schemaVersion": "alphapilot_control_console_demo_v1",
        "demoReleaseId": "release-1",
        "status": "demo_eligible",
        "releaseContentHash": "release-hash",
        "riskEnvelope": {"initialEquityUsdt": 1000.0},
        "executionBoundary": {
            "environment": "okx_demo_only",
            "automaticDemoExecutionAllowed": True,
            "liveExecutionAllowed": False,
            "withdrawAllowed": False,
        },
    }


def signal() -> dict:
    return {
        "candidateId": "signal-1",
        "signalTime": "2026-07-10T00:00:00Z",
        "strategyFamilyId": "trend",
        "instId": "BTC-USDT-SWAP",
        "side": "buy",
        "posSide": "long",
        "tdMode": "isolated",
        "ordType": "market",
        "sz": "1",
        "entryPrice": 100.0,
        "stopLossPrice": 99.0,
        "takeProfitPrice": 102.0,
        "notionalUsdt": 200.0,
        "leverage": 2,
        "riskPercent": 0.25,
        "score": 0.9,
    }


class DemoExecutionEngineTests(unittest.TestCase):
    def test_order_send_and_exchange_response_timestamps_are_persisted(self) -> None:
        timestamps = iter(
            (
                datetime(2026, 7, 13, 0, 0, 4, tzinfo=UTC),
                datetime(2026, 7, 13, 0, 0, 4, 120000, tzinfo=UTC),
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            store = DemoExecutionStore(Path(directory) / "demo.sqlite")
            try:
                engine = DemoExecutionEngine(
                    client=FakeDemoClient(),
                    store=store,
                    clock=lambda: next(timestamps),
                )

                record = engine.execute(contract=contract(), signal=signal(), portfolio={})

                timing = record.exchangeResponse["_alphaPilotTiming"]
                self.assertEqual(timing["orderSentAt"], "2026-07-13T00:00:04+00:00")
                self.assertEqual(timing["exchangeResponseReceivedAt"], "2026-07-13T00:00:04.120000+00:00")
                self.assertNotIn("apiKey", str(timing))
            finally:
                store.close()

    def test_duplicate_signal_places_one_order_and_reconciles_partial_fill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = DemoExecutionStore(Path(directory) / "demo.sqlite")
            client = FakeDemoClient()
            engine = DemoExecutionEngine(client=client, store=store)

            first = engine.execute(contract=contract(), signal=signal(), portfolio={})
            repeated = engine.execute(contract=contract(), signal=signal(), portfolio={})
            partial = engine.reconcile(first.recordId)
            filled = engine.reconcile(first.recordId)

            self.assertEqual(first.recordId, repeated.recordId)
            self.assertEqual(client.placeCalls, 1)
            self.assertEqual(first.orderPayload["attachAlgoOrds"][0]["tpTriggerPx"], "102.0")
            self.assertEqual(first.orderPayload["attachAlgoOrds"][0]["slTriggerPx"], "99.0")
            self.assertEqual(partial.status, "partially_filled")
            self.assertEqual(filled.status, "filled")
            store.close()

    def test_unknown_place_state_pauses_before_any_retry(self) -> None:
        class FailingClient(FakeDemoClient):
            def place_order(self, payload: dict) -> dict:
                self.placeCalls += 1
                raise TimeoutError("simulated timeout")

        with tempfile.TemporaryDirectory() as directory:
            store = DemoExecutionStore(Path(directory) / "demo.sqlite")
            client = FailingClient()
            engine = DemoExecutionEngine(client=client, store=store)
            with self.assertRaises(TimeoutError):
                engine.execute(contract=contract(), signal=signal(), portfolio={})

            records = store.list_records()
            self.assertEqual(records[0].status, "unknown")
            self.assertTrue(store.get_runtime_flag("paused"))
            self.assertEqual(client.placeCalls, 1)
            store.close()

    def test_kill_switch_pauses_new_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = DemoExecutionStore(Path(directory) / "demo.sqlite")
            client = FakeDemoClient()
            engine = DemoExecutionEngine(client=client, store=store)
            engine.activate_kill_switch("unit_test")

            with self.assertRaises(RuntimeError):
                engine.execute(contract=contract(), signal=signal(), portfolio={})
            self.assertEqual(client.killCalls, 1)
            store.close()

    def test_credential_like_signal_field_is_rejected_before_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = DemoExecutionStore(Path(directory) / "demo.sqlite")
            engine = DemoExecutionEngine(client=FakeDemoClient(), store=store)
            unsafe_signal = {**signal(), "apiKey": "must-never-be-stored"}

            with self.assertRaises(ValueError):
                engine.execute(contract=contract(), signal=unsafe_signal, portfolio={})
            self.assertEqual(store.list_records(), [])
            store.close()

    def test_closed_outcome_requires_filled_entry_and_explicit_exit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = DemoExecutionStore(Path(directory) / "demo.sqlite")
            outcome_store = ExecutionOutcomeStore(Path(directory) / "outcomes.sqlite")
            client = FakeDemoClient()
            engine = DemoExecutionEngine(client=client, store=store, outcomeStore=outcome_store)
            record = engine.execute(contract=contract(), signal=signal(), portfolio={})
            with self.assertRaises(RuntimeError):
                engine.record_closed_outcome(
                    recordId=record.recordId,
                    contract=contract(),
                    dataSnapshotId="snapshot-1",
                    closeEvidence={},
                )
            engine.reconcile(record.recordId)
            engine.reconcile(record.recordId)
            outcome = engine.record_closed_outcome(
                recordId=record.recordId,
                contract=contract(),
                dataSnapshotId="snapshot-1",
                closeEvidence={
                    "timeframe": "1h",
                    "direction": "long",
                    "entryAt": "2026-07-10T00:01:00+00:00",
                    "exitAt": "2026-07-10T01:00:00+00:00",
                    "entryPrice": 100.0,
                    "exitPrice": 102.0,
                    "quantity": 1.0,
                    "grossPnl": 2.0,
                    "feePaid": 0.1,
                    "slippagePaid": 0.1,
                    "netPnl": 1.8,
                    "riskAmount": 1.0,
                    "exitReason": "target",
                    "sourcePayloadHash": "demo-close-fill-hash",
                },
            )
            self.assertEqual(outcome.environment, "okx_demo")
            self.assertEqual(len(outcome_store.list_outcomes()), 1)
            outcome_store.close()
            store.close()


if __name__ == "__main__":
    unittest.main()
