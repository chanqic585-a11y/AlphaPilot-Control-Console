from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.ai_orchestration.batch import AIBatchLedger
from alphapilot_control_console.ai_orchestration.errors import BatchConflictError


class AIBatchLedgerTests(unittest.TestCase):
    def test_batch_submission_is_idempotent_for_same_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = AIBatchLedger(Path(directory) / "batch.sqlite")
            try:
                first = ledger.register(
                    idempotency_key="campaign-1:failure-attribution",
                    provider="gemini",
                    model_alias="gemini_batch",
                    request_hashes=["sha256:a", "sha256:b"],
                )
                second = ledger.register(
                    idempotency_key="campaign-1:failure-attribution",
                    provider="gemini",
                    model_alias="gemini_batch",
                    request_hashes=["sha256:a", "sha256:b"],
                )
                projection = ledger.projection()
            finally:
                ledger.close()

        self.assertEqual(first["batchJobId"], second["batchJobId"])
        self.assertEqual(projection["jobCount"], 1)
        self.assertEqual(projection["statusCounts"], {"registered": 1})

    def test_reusing_idempotency_key_with_different_payload_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = AIBatchLedger(Path(directory) / "batch.sqlite")
            try:
                ledger.register(
                    idempotency_key="campaign-1",
                    provider="gemini",
                    model_alias="gemini_batch",
                    request_hashes=["sha256:a"],
                )
                with self.assertRaises(BatchConflictError):
                    ledger.register(
                        idempotency_key="campaign-1",
                        provider="gemini",
                        model_alias="gemini_batch",
                        request_hashes=["sha256:different"],
                    )
            finally:
                ledger.close()

    def test_status_transition_preserves_provider_job_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = AIBatchLedger(Path(directory) / "batch.sqlite")
            try:
                job = ledger.register(
                    idempotency_key="campaign-2",
                    provider="gemini",
                    model_alias="gemini_batch",
                    request_hashes=["sha256:a"],
                )
                submitted = ledger.mark_submitted(job["batchJobId"], "provider-job-1")
                completed = ledger.mark_completed(job["batchJobId"], "sha256:result")
            finally:
                ledger.close()

        self.assertEqual(submitted["providerJobId"], "provider-job-1")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["resultArtifactHash"], "sha256:result")


if __name__ == "__main__":
    unittest.main()
