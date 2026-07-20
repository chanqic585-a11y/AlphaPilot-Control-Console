from __future__ import annotations

import unittest

from alphapilot_control_console.provisional_demo_admission import (
    classify_legacy_contract,
    count_forward_evidence,
    validate_exact_provisional_approval,
)


def release() -> dict:
    return {
        "schemaVersion": "provisional_research_demo_v1",
        "releaseId": "provisional-release-1",
        "releaseHash": "release-hash-1",
        "riskOverlayHash": "risk-hash-1",
        "formalPass": False,
        "cleanHistoricalOosPass": False,
        "livePromotionEligible": False,
        "automaticLivePromotionAllowed": False,
        "approved": False,
        "demoArm": False,
        "route": "blocked_waiting_exact_release_approval",
    }


class ProvisionalDemoAdmissionTests(unittest.TestCase):
    def test_approval_requires_exact_release_and_risk_hashes_without_arming(self) -> None:
        with self.assertRaisesRegex(PermissionError, "exact release hash"):
            validate_exact_provisional_approval(
                release(),
                {"releaseHash": "wrong", "riskOverlayHash": "risk-hash-1"},
            )

        result = validate_exact_provisional_approval(
            release(),
            {"releaseHash": "release-hash-1", "riskOverlayHash": "risk-hash-1"},
        )
        self.assertEqual(result["status"], "approved_not_armed")
        self.assertFalse(result["demoArm"])
        self.assertFalse(result["livePromotionEligible"])

    def test_only_post_approval_closed_strategy_demo_trades_count_forward(self) -> None:
        records = [
            {
                "environment": "okx_demo",
                "status": "closed",
                "releaseId": "provisional-release-1",
                "releaseHash": "release-hash-1",
                "entryAt": "2026-07-21T00:00:01Z",
                "evidenceClass": "okx_demo",
                "executionPurpose": "strategy_execution",
            },
            {
                "environment": "okx_demo",
                "status": "closed",
                "releaseId": "provisional-release-1",
                "releaseHash": "release-hash-1",
                "entryAt": "2026-07-19T23:59:59Z",
                "evidenceClass": "okx_demo",
                "executionPurpose": "strategy_execution",
            },
            {
                "environment": "okx_demo",
                "status": "closed",
                "releaseId": "provisional-release-1",
                "releaseHash": "release-hash-1",
                "entryAt": "2026-07-21T00:00:01Z",
                "evidenceClass": "demo_engineering_smoke",
                "executionPurpose": "connectivity_smoke_only",
            },
            {
                "environment": "okx_demo",
                "status": "closed",
                "releaseId": "legacy-release",
                "releaseHash": "legacy-hash",
                "entryAt": "2026-07-21T00:00:01Z",
                "evidenceClass": "okx_demo",
                "executionPurpose": "strategy_execution",
            },
            {
                "environment": "shadow",
                "status": "closed",
                "releaseId": "provisional-release-1",
                "releaseHash": "release-hash-1",
                "entryAt": "2026-07-21T00:00:01Z",
                "evidenceClass": "shadow",
                "executionPurpose": "strategy_execution",
            },
        ]

        result = count_forward_evidence(
            records,
            release_id="provisional-release-1",
            release_hash="release-hash-1",
            approved_at="2026-07-20T00:00:00Z",
        )

        self.assertEqual(result["eligibleClosedTradeCount"], 1)
        self.assertEqual(result["excludedRecordCount"], 4)
        self.assertEqual(result["preApprovalExcludedCount"], 1)
        self.assertEqual(result["engineeringSmokeExcludedCount"], 1)

    def test_legacy_override_is_classified_but_never_executable_or_eligible(self) -> None:
        result = classify_legacy_contract({"releaseMode": "experimental_override"})
        self.assertEqual(result["classification"], "legacy_experimental_override")
        self.assertFalse(result["executionEnabled"])
        self.assertFalse(result["forwardEvidenceEligible"])
        self.assertFalse(result["livePromotionEligible"])


if __name__ == "__main__":
    unittest.main()
