from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alphapilot_control_console.live_approval_store import (
    LIVE_APPROVAL_CONFIRMATION,
    LiveApprovalStore,
)
from alphapilot_control_console.live_safety_plane import (
    LiveSafetyStore,
    attempt_live_execution,
    build_live_safety_status,
    evaluate_live_safety_request,
)


def stable_hash(value: object) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def package_export() -> dict:
    risk = {
        "capitalLimitUsdt": 1000.0,
        "riskPerTradePercent": 0.25,
        "maxOpenRiskPercent": 1.0,
        "maxOrderNotionalUsdt": 250.0,
        "maxConcurrentPositions": 3,
        "maxLeverage": 2,
        "dailyLossStopPercent": 2.0,
        "maxDrawdownStopPercent": 5.0,
    }
    package = {
        "demoReleaseId": "release-1",
        "demoReleaseHash": "release-hash-1",
        "manualApprovalRequired": True,
        "automaticApprovalAllowed": False,
        "liveExecutionAdapterPresent": False,
        "liveExecutionEnabled": False,
        "withdrawAllowed": False,
        "proposedRiskBudget": risk,
    }
    return {
        "schemaVersion": "alphapilot_live_candidate_review_v1",
        "liveCandidatePackageId": "package-1",
        "demoReleaseId": "release-1",
        "status": "awaiting_manual_approval",
        "packageHash": stable_hash(package),
        "package": package,
    }


def request_for(export: dict, now: datetime, **overrides: object) -> dict:
    package = export["package"]
    values = {
        "idempotencyKey": "idem-1",
        "liveCandidatePackageId": export["liveCandidatePackageId"],
        "packageHash": export["packageHash"],
        "demoReleaseId": export["demoReleaseId"],
        "demoReleaseHash": package["demoReleaseHash"],
        "riskBudgetHash": stable_hash(package["proposedRiskBudget"]),
        "instrumentId": "BTC-USDT-SWAP",
        "side": "long",
        "referencePrice": 100.0,
        "observedPrice": 100.5,
        "instrumentState": "live",
        "requestedAt": now.isoformat(),
        "expiresAt": (now + timedelta(seconds=20)).isoformat(),
        "reconciliationMatched": True,
    }
    values.update(overrides)
    return values


class LiveSafetyPlaneTests(unittest.TestCase):
    def test_approval_clears_review_check_but_execution_stays_disabled(self) -> None:
        export = package_export()
        now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as directory:
            approval_path = Path(directory) / "approval.sqlite"
            safety = LiveSafetyStore(Path(directory) / "safety.sqlite")
            safety.update_runtime(reconciliation_matched=True, reason="test_reconciliation")
            approvals = LiveApprovalStore(approval_path)
            approvals.approve(
                packageId=export["liveCandidatePackageId"],
                packageHash=export["packageHash"],
                riskBudget=export["package"]["proposedRiskBudget"],
                confirmation=LIVE_APPROVAL_CONFIRMATION,
                actor="user_manual",
            )
            approvals.close()

            decision = evaluate_live_safety_request(
                request=request_for(export, now),
                package_export=export,
                approval_store_path=approval_path,
                safety_store=safety,
                now=now,
            )
            repeated = evaluate_live_safety_request(
                request=request_for(export, now),
                package_export=export,
                approval_store_path=approval_path,
                safety_store=safety,
                now=now,
            )

            self.assertEqual(decision.status, "validated_execution_disabled")
            self.assertTrue(decision.passedSafetyChecks)
            self.assertFalse(decision.executionEnabled)
            self.assertIn("live_adapter_absent", decision.reasons)
            self.assertEqual(repeated.requestId, decision.requestId)
            self.assertEqual(len(safety.list_decisions()), 1)
            with self.assertRaises(ValueError):
                evaluate_live_safety_request(
                    request=request_for(export, now, observedPrice=100.6),
                    package_export=export,
                    approval_store_path=approval_path,
                    safety_store=safety,
                    now=now,
                )
            safety.close()
            with self.assertRaises(PermissionError):
                attempt_live_execution(decision)

    def test_expiry_hash_price_and_instrument_fail_closed(self) -> None:
        export = package_export()
        now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as directory:
            approval_path = Path(directory) / "approval.sqlite"
            safety = LiveSafetyStore(Path(directory) / "safety.sqlite")
            safety.update_runtime(reconciliation_matched=True, reason="test_reconciliation")
            decision = evaluate_live_safety_request(
                request=request_for(
                    export,
                    now - timedelta(minutes=2),
                    idempotencyKey="idem-expired",
                    riskBudgetHash="wrong",
                    observedPrice=103.0,
                    instrumentState="suspended",
                ),
                package_export=export,
                approval_store_path=approval_path,
                safety_store=safety,
                now=now,
            )
            safety.close()

        self.assertEqual(decision.status, "rejected")
        self.assertIn("request_expired_or_not_yet_valid", decision.reasons)
        self.assertIn("risk_budget_hash_mismatch", decision.reasons)
        self.assertIn("price_deviation_exceeded", decision.reasons)
        self.assertIn("instrument_not_live", decision.reasons)
        self.assertIn("manual_checksum_bound_approval_missing", decision.reasons)

    def test_kill_switch_and_status_are_persistent_and_non_executing(self) -> None:
        export = package_export()
        now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as directory:
            approval_path = Path(directory) / "approval.sqlite"
            safety_path = Path(directory) / "safety.sqlite"
            safety = LiveSafetyStore(safety_path)
            safety.update_runtime(
                kill_switch=True,
                reconciliation_matched=True,
                reason="operator_test",
            )
            decision = evaluate_live_safety_request(
                request=request_for(export, now, idempotencyKey="idem-kill"),
                package_export=export,
                approval_store_path=approval_path,
                safety_store=safety,
                now=now,
            )
            safety.close()
            status = build_live_safety_status(
                packages=[export],
                approval_store_path=approval_path,
                store_path=safety_path,
            )

        self.assertEqual(decision.status, "rejected")
        self.assertIn("kill_switch_active", decision.reasons)
        self.assertTrue(status["runtime"]["killSwitchActive"])
        self.assertEqual(status["summary"]["liveExecutionEnabledCount"], 0)
        self.assertFalse(status["safetyBoundary"]["approvalEnablesExecution"])


if __name__ == "__main__":
    unittest.main()
