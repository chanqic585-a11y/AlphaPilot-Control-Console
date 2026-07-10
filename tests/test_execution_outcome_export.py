from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.execution_outcome_export import build_execution_outcome_export
from alphapilot_control_console.execution_outcome_store import ExecutionOutcomeStore
from alphapilot_control_console.demo_execution_store import DemoExecutionStore


def draft(**overrides: object) -> dict:
    values = {
        "environment": "okx_demo",
        "sourceRecordId": "demo-record-1",
        "releaseId": "demo-release-1",
        "releaseHash": "release-hash",
        "riskProfileId": "risk-1",
        "riskProfileHash": "risk-hash",
        "strategyCandidateId": "candidate-1",
        "dataSnapshotId": "snapshot-1",
        "instrumentId": "BTC-USDT-SWAP",
        "timeframe": "1h",
        "direction": "long",
        "decisionAt": "2026-07-11T00:00:00+00:00",
        "entryAt": "2026-07-11T00:01:00+00:00",
        "exitAt": "2026-07-11T01:00:00+00:00",
        "entryPrice": 100.0,
        "exitPrice": 102.0,
        "quantity": 1.0,
        "grossPnl": 2.0,
        "feePaid": 0.1,
        "slippagePaid": 0.1,
        "netPnl": 1.8,
        "riskAmount": 1.0,
        "exitReason": "target",
        "sourcePayloadHash": "fill-payload-hash",
    }
    values.update(overrides)
    return values


class ExecutionOutcomeExportTests(unittest.TestCase):
    def test_closed_outcome_is_immutable_and_exported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outcome_path = Path(directory) / "outcomes.sqlite"
            store = ExecutionOutcomeStore(outcome_path)
            try:
                first = store.record_closed(draft())
                repeated = store.record_closed(draft())
            finally:
                store.close()
            payload = build_execution_outcome_export(
                outcome_store_path=outcome_path,
                demo_store_path=Path(directory) / "missing-demo.sqlite",
                live_store_path=Path(directory) / "missing-live.sqlite",
            )

        self.assertEqual(first, repeated)
        self.assertEqual(payload["summary"]["formalClosedOutcomeCount"], 1)
        self.assertEqual(payload["records"][0]["trade"]["netR"], 1.8)
        self.assertFalse(payload["safetyBoundary"]["createsOrders"])

    def test_inconsistent_net_pnl_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ExecutionOutcomeStore(Path(directory) / "outcomes.sqlite")
            try:
                with self.assertRaises(ValueError):
                    store.record_closed(draft(netPnl=2.0))
            finally:
                store.close()

    def test_opening_fill_is_quarantined_until_close_evidence_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            demo_path = Path(directory) / "demo.sqlite"
            demo_store = DemoExecutionStore(demo_path)
            try:
                record = demo_store.create_intent(
                    idempotencyKey="entry-fill-only",
                    demoReleaseId="demo-release-1",
                    signal={"instrumentId": "BTC-USDT-SWAP"},
                    orderPayload={"side": "buy", "sz": "1"},
                )
                demo_store.update_record(record.recordId, status="filled")
            finally:
                demo_store.close()

            payload = build_execution_outcome_export(
                outcome_store_path=Path(directory) / "outcomes.sqlite",
                demo_store_path=demo_path,
                live_store_path=Path(directory) / "missing-live.sqlite",
            )

        self.assertEqual(payload["summary"]["formalClosedOutcomeCount"], 0)
        self.assertEqual(payload["summary"]["quarantinedExecutionCount"], 1)
        self.assertEqual(
            payload["quarantinedExecutionRecords"][0]["reason"],
            "position_close_evidence_missing",
        )

    def test_live_outcome_requires_risk_profile_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ExecutionOutcomeStore(Path(directory) / "outcomes.sqlite")
            try:
                with self.assertRaises(ValueError):
                    store.record_closed(draft(
                        environment="live",
                        riskProfileId="",
                        riskProfileHash="",
                    ))
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
