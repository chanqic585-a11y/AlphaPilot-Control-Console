from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import alphapilot_control_console.live_candidate_service as service
from alphapilot_control_console.live_approval_store import LIVE_APPROVAL_CONFIRMATION


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def package_export() -> dict:
    package = {
        "manualApprovalRequired": True,
        "automaticApprovalAllowed": False,
        "liveExecutionAdapterPresent": False,
        "liveExecutionEnabled": False,
        "withdrawAllowed": False,
        "proposedRiskBudget": {"capitalLimitUsdt": 1000.0, "riskPerTradePercent": 0.25},
        "demoEvidence": {"demoClosedTrades": 80, "netProfitFactor": 1.22},
        "rollbackPolicy": {"killSwitchRequired": True},
    }
    package_hash = hashlib.sha256(canonical(package).encode("utf-8")).hexdigest()
    return {
        "schemaVersion": "alphapilot_live_candidate_review_v1",
        "liveCandidatePackageId": "package-1",
        "demoReleaseId": "release-1",
        "status": "awaiting_manual_approval",
        "packageHash": package_hash,
        "package": package,
        "approvalBoundary": {
            "manualApprovalRequired": True,
            "automaticApprovalAllowed": False,
            "approvalEnablesExecution": False,
            "liveExecutionAdapterPresent": False,
            "withdrawAllowed": False,
        },
    }


class LiveCandidateServiceTests(unittest.TestCase):
    def test_manual_approval_and_checksum_invalidation(self) -> None:
        export = package_export()
        with tempfile.TemporaryDirectory() as directory, patch.object(
            service, "APPROVAL_STORE_PATH", Path(directory) / "approval.sqlite"
        ), patch.object(service, "discover_live_candidate_packages", return_value=([export], [])):
            result = service.approve_live_candidate(
                {
                    "liveCandidatePackageId": "package-1",
                    "packageHash": export["packageHash"],
                    "confirmation": LIVE_APPROVAL_CONFIRMATION,
                    "actor": "user_manual",
                }
            )
            status = service.build_live_candidate_status()

        self.assertTrue(result["ok"])
        self.assertEqual(status["packages"][0]["approval"]["status"], "approved_for_future_release_review")
        self.assertFalse(status["safetyBoundary"]["approvalEnablesExecution"])

    def test_invalid_package_hash_is_rejected(self) -> None:
        export = package_export()
        export["packageHash"] = "tampered"
        with self.assertRaises(ValueError):
            service.validate_live_candidate_export(export)


if __name__ == "__main__":
    unittest.main()
