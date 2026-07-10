from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.demo_execution_store import DemoExecutionStore


class DemoExecutionStoreTests(unittest.TestCase):
    def test_intent_is_idempotent_and_survives_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.sqlite"
            store = DemoExecutionStore(path)
            first = store.create_intent(
                idempotencyKey="idem-1",
                demoReleaseId="release-1",
                signal={"candidateId": "signal-1"},
                orderPayload={"clOrdId": "apdemo1"},
            )
            second = store.create_intent(
                idempotencyKey="idem-1",
                demoReleaseId="release-1",
                signal={"candidateId": "signal-1"},
                orderPayload={"clOrdId": "apdemo1"},
            )
            store.close()

            reopened = DemoExecutionStore(path)
            recovered = reopened.get_record(first.recordId)
            self.assertEqual(first.recordId, second.recordId)
            self.assertEqual(recovered.idempotencyKey, "idem-1")
            self.assertEqual(len(reopened.list_records()), 1)
            reopened.close()


if __name__ == "__main__":
    unittest.main()
