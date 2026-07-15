from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.demo_engineering_smoke_store import DemoEngineeringSmokeStore


class DemoEngineeringSmokeStoreTests(unittest.TestCase):
    def test_initialization_is_idempotent_and_restart_recovers_active_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "engineering.sqlite"
            first = DemoEngineeringSmokeStore(path)
            created = first.create_or_get_run(
                idempotencyKey="key-1",
                releaseId="release-1",
                releaseHash="hash-1",
                instrumentId="BTC-USDT-SWAP",
                orderPayload={"instId": "BTC-USDT-SWAP", "sz": "0.01"},
            )
            first.append_event(created.record.runId, "run_created", {"safe": True})
            first.close()

            second = DemoEngineeringSmokeStore(path)
            recovered = second.list_recoverable_runs()
            events = second.list_events(created.record.runId)
            second.close()

        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0].runId, created.record.runId)
        self.assertEqual(events[0]["eventType"], "run_created")

    def test_unique_idempotency_key_prevents_second_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = DemoEngineeringSmokeStore(Path(temporary) / "engineering.sqlite")
            first = store.create_or_get_run(
                idempotencyKey="same-key",
                releaseId="release-1",
                releaseHash="hash-1",
                instrumentId="BTC-USDT-SWAP",
                orderPayload={"instId": "BTC-USDT-SWAP", "sz": "0.01"},
            )
            duplicate = store.create_or_get_run(
                idempotencyKey="same-key",
                releaseId="release-1",
                releaseHash="hash-1",
                instrumentId="BTC-USDT-SWAP",
                orderPayload={"instId": "BTC-USDT-SWAP", "sz": "0.01"},
            )
            summary = store.build_summary()
            store.close()

        self.assertTrue(first.created)
        self.assertFalse(duplicate.created)
        self.assertEqual(first.record.runId, duplicate.record.runId)
        self.assertEqual(summary["runCount"], 1)
        self.assertEqual(summary["duplicateAttemptCount"], 1)

    def test_attempts_are_bounded_and_sensitive_payloads_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = DemoEngineeringSmokeStore(Path(temporary) / "engineering.sqlite")
            created = store.create_or_get_run(
                idempotencyKey="key-1",
                releaseId="release-1",
                releaseHash="hash-1",
                instrumentId="BTC-USDT-SWAP",
                orderPayload={"instId": "BTC-USDT-SWAP", "sz": "0.01"},
            )
            for _ in range(3):
                store.increment_attempt(created.record.runId, maximumAttempts=3)
            with self.assertRaises(RuntimeError):
                store.increment_attempt(created.record.runId, maximumAttempts=3)
            with self.assertRaises(ValueError):
                store.update_run(created.record.runId, exchangeProjection={"passphrase": "forbidden"})
            store.close()


if __name__ == "__main__":
    unittest.main()
