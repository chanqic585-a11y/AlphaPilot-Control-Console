from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.v62_4_1_ui_evidence import (
    UiEvidenceError,
    build_current_pilot_projection,
    build_provider_smoke_summary,
)


def _write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


class V6241UiEvidenceTests(unittest.TestCase):
    def test_builds_current_pilot_from_matching_campaign_and_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary_path = root / "campaign_summary.json"
            handoff_path = root / "formal_handoff.json"
            _write(
                summary_path,
                {
                    "campaignId": "pilot-1",
                    "status": "awaiting_formal_validation",
                    "candidateCount": 4,
                    "trialCount": 12,
                    "stableSelectionCount": 2,
                    "formalReadyCandidateCount": 1,
                    "formalBlockedCandidateCount": 1,
                    "formalRunCount": 0,
                    "resultReadCount": 0,
                },
            )
            _write(
                handoff_path,
                {
                    "campaignId": "pilot-1",
                    "formalRunCount": 0,
                    "resultReadCount": 0,
                    "readyCandidates": [{"candidateId": "candidate-ready"}],
                    "blockedCandidates": [{"candidateId": "candidate-blocked"}],
                },
            )

            payload = build_current_pilot_projection(summary_path, handoff_path)

        self.assertEqual(payload["authority"], "current_v62_4_acceptance_pilot")
        self.assertEqual(payload["campaignId"], "pilot-1")
        self.assertEqual(payload["formalReadyCandidateIds"], ["candidate-ready"])
        self.assertEqual(payload["formalBlockedCandidateIds"], ["candidate-blocked"])
        self.assertEqual(payload["formalRunCount"], 0)
        self.assertEqual(payload["resultReadCount"], 0)
        self.assertRegex(payload["sourceHashes"]["campaignSummary"], r"^sha256:[0-9a-f]{64}$")

    def test_rejects_campaign_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary_path = root / "campaign_summary.json"
            handoff_path = root / "formal_handoff.json"
            _write(summary_path, {"campaignId": "pilot-1"})
            _write(handoff_path, {"campaignId": "pilot-2"})

            with self.assertRaises(UiEvidenceError):
                build_current_pilot_projection(summary_path, handoff_path)

    def test_projects_completed_formal_receipt_over_stale_pilot_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary_path = root / "campaign_summary.json"
            handoff_path = root / "formal_handoff.json"
            receipt_path = root / "formal_result_read_receipt.json"
            _write(
                summary_path,
                {
                    "campaignId": "pilot-1",
                    "status": "awaiting_formal_validation",
                    "candidateCount": 4,
                    "trialCount": 12,
                    "stableSelectionCount": 2,
                    "formalReadyCandidateCount": 1,
                    "formalBlockedCandidateCount": 1,
                    "formalRunCount": 0,
                    "resultReadCount": 0,
                },
            )
            _write(
                handoff_path,
                {
                    "campaignId": "pilot-1",
                    "formalRunCount": 0,
                    "resultReadCount": 0,
                    "readyCandidates": [{"candidateId": "candidate-ready"}],
                    "blockedCandidates": [{"candidateId": "candidate-blocked"}],
                },
            )
            _write(
                receipt_path,
                {
                    "campaignId": "formal-campaign-1",
                    "candidateId": "candidate-ready",
                    "formalRunCount": 1,
                    "resultReadCount": 1,
                    "formalResultCount": 1,
                    "route": "archive_s01_current_version",
                    "releaseCount": 0,
                    "demoArm": False,
                    "orderCount": 0,
                    "selectedResultFields": {"formalPass": [False, False]},
                },
            )

            payload = build_current_pilot_projection(
                summary_path,
                handoff_path,
                formal_result_receipt_path=receipt_path,
            )

        self.assertEqual(payload["status"], "formal_completed_not_passed")
        self.assertEqual(payload["formalRunCount"], 1)
        self.assertEqual(payload["resultReadCount"], 1)
        self.assertEqual(payload["formalCampaignId"], "formal-campaign-1")
        self.assertEqual(payload["formalCandidateId"], "candidate-ready")
        self.assertFalse(payload["formalPass"])
        self.assertEqual(payload["formalRoute"], "archive_s01_current_version")
        self.assertEqual(payload["releaseCount"], 0)
        self.assertFalse(payload["demoArm"])
        self.assertEqual(payload["strategyOrderCount"], 0)
        self.assertRegex(
            payload["sourceHashes"]["formalResultReadReceipt"],
            r"^sha256:[0-9a-f]{64}$",
        )

    def test_sanitizes_historical_provider_smoke_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "provider_smoke.json"
            _write(
                source,
                {
                    "status": "provider_smoke_passed",
                    "providerSmokeInputHash": "sha256:fixed",
                    "checks": [
                        {
                            "taskType": "provider_smoke_deepseek",
                            "routeMode": "single",
                            "status": "accepted",
                            "executionAuthorized": False,
                            "responseHashes": ["ai_output:one"],
                        },
                        {
                            "taskType": "provider_smoke_gemini",
                            "routeMode": "single",
                            "status": "accepted",
                            "executionAuthorized": False,
                            "responseHashes": ["ai_output:two"],
                        },
                    ],
                    "executionAuthorized": False,
                    "runtimeArmed": False,
                    "withdrawEnabled": False,
                    "aiWorkerIdentity": {
                        "exchangePrivateCredentialsPresent": False,
                        "executionAuthority": False,
                    },
                },
            )

            payload = build_provider_smoke_summary(source)

        rendered = json.dumps(payload, sort_keys=True)
        self.assertEqual(payload["status"], "provider_smoke_passed")
        self.assertEqual(len(payload["checks"]), 2)
        self.assertFalse(payload["executionAuthorized"])
        self.assertFalse(payload["credentialsPersisted"])
        self.assertNotIn("apiKey", rendered)
        self.assertNotIn("secret", rendered.lower())


if __name__ == "__main__":
    unittest.main()
