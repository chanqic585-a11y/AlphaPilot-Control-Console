from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.top200_minimal_ui_projection import (
    Top200MinimalUiProjection,
    write_top200_minimal_ui_projection_artifacts,
)


def _write_json(root: Path, name: str, payload: dict) -> None:
    (root / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


class Top200MinimalUiProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        _write_json(
            self.root,
            "top200_demo_universe_policy.json",
            {
                "policyId": "okx_demo_top200_liquid_usdt_swap_forward_v1",
                "maximumInstrumentCount": 200,
                "refreshCadence": "daily_frozen_snapshot",
            },
        )
        _write_json(
            self.root,
            "initial_top200_demo_universe_snapshot.json",
            {
                "utcDate": "2026-07-20",
                "policyId": "okx_demo_top200_liquid_usdt_swap_forward_v1",
                "policyHash": "top200_universe_policy_fixture",
                "actualInstrumentCount": 2,
                "maximumInstrumentCount": 200,
                "instrumentIds": ["BTC-USDT-SWAP", "ETH-USDT-SWAP"],
                "rankedInstruments": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "medianDailyQuoteTurnover": 100.0,
                        "quoteTurnoverSource": "okx_completed_1Dutc_volCcyQuote",
                    },
                    {
                        "instId": "ETH-USDT-SWAP",
                        "medianDailyQuoteTurnover": 80.0,
                        "quoteTurnoverSource": "okx_completed_1Dutc_volCcyQuote",
                    },
                ],
                "status": "completed",
                "dailyFrozen": True,
                "snapshotHash": "demo_top200_universe_snapshot_fixture",
            },
        )
        _write_json(
            self.root,
            "top200_universe_readiness_audit.json",
            {
                "publicInstrumentCount": 426,
                "authenticatedDemoInstrumentCount": 116,
                "eligibleInstrumentCount": 2,
                "selectedInstrumentCount": 2,
                "collectionErrorCount": 0,
            },
        )
        _write_json(
            self.root,
            "superseding_provisional_release.json",
            {
                "releaseId": "provisional_research_demo_top200_fixture",
                "releaseHash": "provisional_demo_release_fixture",
                "releasePurpose": "provisional_forward_collection",
                "portfolioCandidateId": "portfolio_fixture",
                "componentIds": ["component_a", "component_b", "component_c"],
                "actualInstrumentCount": 2,
                "maximumInstrumentCount": 200,
                "dynamicUniversePolicyId": "okx_demo_top200_liquid_usdt_swap_forward_v1",
                "dynamicUniversePolicyHash": "top200_universe_policy_fixture",
                "dynamicUniverseSnapshotHash": "demo_top200_universe_snapshot_fixture",
                "riskOverlayHash": "risk_overlay_fixture",
                "formalPass": False,
                "approved": False,
                "demoArm": False,
                "livePromotionEligible": False,
                "route": "blocked_waiting_exact_release_approval",
                "generatedAt": "2026-07-20T17:00:00Z",
                "supersedesReleaseId": "old_release",
                "supersedesReleaseHash": "old_release_hash",
            },
        )
        _write_json(
            self.root,
            "superseding_demo_approval_request.json",
            {
                "releaseId": "provisional_research_demo_top200_fixture",
                "releaseHash": "provisional_demo_release_fixture",
                "requestHash": "approval_request_fixture",
                "approvalGranted": False,
                "approved": False,
                "demoArm": False,
                "strategyOrderCount": 0,
                "route": "blocked_waiting_exact_release_approval",
                "live": False,
                "withdraw": False,
            },
        )
        _write_json(
            self.root,
            "old_release_supersession_overlay.json",
            {
                "oldReleaseId": "old_release",
                "oldReleaseHash": "old_release_hash",
                "status": "superseded_unapproved",
                "oldApproved": False,
                "oldDemoArm": False,
            },
        )
        _write_json(
            self.root,
            "engineering_smoke_final_self_check.json",
            {
                "status": "passed",
                "engineeringSmokeReady": True,
                "duplicateOrderCount": 0,
                "orphanOrderCount": 0,
                "orphanPositionCount": 0,
                "unknownStateCount": 0,
                "finalPositionCount": 0,
                "strategyOrderCount": 0,
                "strategyClosedTradeCount": 0,
                "formalEvidenceDelta": 0,
                "forwardEvidenceDelta": 0,
                "nextRoute": "blocked_waiting_exact_release_approval",
                "generatedAt": "2026-07-20T16:16:28Z",
            },
        )
        _write_json(
            self.root,
            "engineering_smoke_rest_reconciliation_audit.json",
            {
                "status": "passed",
                "pendingOrderCount": 0,
                "nonzeroPositionCount": 0,
                "orphanPositionCount": 0,
                "unknownOrderCount": 0,
                "recentFillCount": 2,
            },
        )
        self.projection = Top200MinimalUiProjection(self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_strategy_projection_exposes_five_result_classes_and_exact_release(self) -> None:
        summary = self.projection.strategy_summary()

        self.assertEqual(summary["resultCounts"]["canEnterDemo"], 1)
        self.assertEqual(set(summary["resultCounts"]), {
            "canEnterDemo",
            "needsForwardValidation",
            "failed",
            "dataInsufficient",
            "systemIssue",
        })
        self.assertFalse(summary["approved"])
        self.assertFalse(summary["demoArm"])
        self.assertEqual(summary["strategyOrderCount"], 0)
        release = self.projection.strategy_release(
            "provisional_research_demo_top200_fixture"
        )
        self.assertEqual(release["releaseHash"], "provisional_demo_release_fixture")
        self.assertEqual(release["status"], "can_enter_demo")

    def test_demo_projection_is_truthful_and_keeps_smoke_isolated(self) -> None:
        summary = self.projection.demo_summary()

        self.assertEqual(summary["connectionStatus"], "engineering_smoke_passed")
        self.assertEqual(summary["approvedStrategyCount"], 0)
        self.assertEqual(summary["runningStrategyCount"], 0)
        self.assertEqual(summary["openPositionCount"], 0)
        self.assertIsNone(summary["equity"])
        self.assertIsNone(summary["todayPnl"])
        self.assertEqual(summary["strategyOrderCount"], 0)
        self.assertEqual(summary["engineeringSmoke"]["recentFillCount"], 2)
        self.assertEqual(self.projection.demo_positions()["positions"], [])
        self.assertEqual(self.projection.demo_orders()["orders"], [])

    def test_demo_projection_exposes_only_four_matchability_headlines(self) -> None:
        _write_json(
            self.root,
            "signal_matchability_30d.json",
            {"status": "ready_with_sparse_signal_warning", "signalCount": 4},
        )
        _write_json(
            self.root,
            "signal_matchability_90d.json",
            {"status": "ready_with_sparse_signal_warning", "signalCount": 10},
        )
        _write_json(
            self.root,
            "pre_arm_scan_funnel.json",
            {
                "status": "ready_with_sparse_signal_warning",
                "releaseInstrumentCount": 82,
                "compatibleComponentCount": 3,
                "warnings": ["component_without_signal_30d:long_1d"],
            },
        )

        matchability = self.projection.demo_matchability()

        self.assertEqual(
            matchability,
            {
                "status": "ready_with_sparse_signal_warning",
                "releaseInstrumentCount": 82,
                "compatibleComponentCount": 3,
                "signalCount30d": 4,
                "signalCount90d": 10,
                "warningCount": 1,
            },
        )
        self.assertEqual(self.projection.demo_summary()["matchability"], matchability)

    def test_all_read_projections_do_not_modify_evidence(self) -> None:
        before = {
            path.name: path.read_bytes()
            for path in self.root.glob("*.json")
        }

        self.projection.research_factory_summary()
        self.projection.research_factory_runs()
        self.projection.research_factory_run(self.projection.RESEARCH_RUN_ID)
        self.projection.strategy_summary()
        self.projection.strategy_releases()
        self.projection.strategy_release("provisional_research_demo_top200_fixture")
        self.projection.forward_validation("provisional_research_demo_top200_fixture")
        self.projection.demo_summary()
        self.projection.demo_strategies()
        self.projection.demo_positions()
        self.projection.demo_orders()
        self.projection.demo_universe()
        self.projection.demo_reconciliation()
        self.projection.demo_matchability()

        after = {
            path.name: path.read_bytes()
            for path in self.root.glob("*.json")
        }
        self.assertEqual(before, after)

    def test_writes_the_four_required_projection_artifacts_explicitly(self) -> None:
        output_dir = self.root / "projections"

        manifest = write_top200_minimal_ui_projection_artifacts(
            self.projection,
            output_dir,
        )

        self.assertEqual(manifest["artifactCount"], 4)
        self.assertEqual(
            {item["path"] for item in manifest["artifacts"]},
            {
                "research_factory_progress_projection.json",
                "strategy_summary_projection.json",
                "demo_summary_projection.json",
                "demo_scan_funnel_projection.json",
            },
        )
        for item in manifest["artifacts"]:
            self.assertTrue((output_dir / item["path"]).is_file())
            self.assertEqual(len(item["sha256"]), 64)

    def test_policy_bound_successor_and_control_overlays_replace_pre_final_identity(
        self,
    ) -> None:
        release_root = self.root / "release"
        control_root = self.root / "control"
        release_root.mkdir()
        control_root.mkdir()
        _write_json(
            release_root,
            "final_superseding_provisional_release.json",
            {
                "releaseId": "policy-bound-release",
                "releaseHash": "policy-bound-release-hash",
                "componentIds": ["component_a", "component_b", "component_c"],
                "actualInstrumentCount": 2,
                "maximumInstrumentCount": 200,
                "dynamicUniversePolicyId": "okx_demo_top200_liquid_usdt_swap_forward_v1",
                "dynamicUniversePolicyHash": "top200_universe_policy_fixture",
                "dynamicUniverseSnapshotHash": "demo_top200_universe_snapshot_fixture",
                "snapshotBindingMode": "policy_bound_daily_snapshot",
                "riskOverlayHash": "risk_overlay_fixture",
                "formalPass": False,
                "approved": False,
                "demoArm": False,
                "route": "blocked_waiting_exact_release_approval",
                "generatedAt": "2026-07-21T00:00:00Z",
                "supersedesReleaseId": "provisional_research_demo_top200_fixture",
                "supersedesReleaseHash": "provisional_demo_release_fixture",
            },
        )
        _write_json(
            release_root,
            "final_demo_approval_request.json",
            {
                "releaseId": "policy-bound-release",
                "releaseHash": "policy-bound-release-hash",
                "requestHash": "policy-bound-approval-request",
                "approved": False,
                "demoArm": False,
                "strategyOrderCount": 0,
                "route": "blocked_waiting_exact_release_approval",
            },
        )
        _write_json(
            control_root,
            "demo_approval_overlay.json",
            {
                "releaseId": "policy-bound-release",
                "releaseHash": "policy-bound-release-hash",
                "approved": True,
                "demoArm": False,
                "status": "approved_not_armed",
            },
        )
        _write_json(
            control_root,
            "demo_arm_audit.json",
            {
                "releaseId": "policy-bound-release",
                "releaseHash": "policy-bound-release-hash",
                "action": "arm",
                "status": "armed",
            },
        )

        projection = Top200MinimalUiProjection(
            self.root,
            release_root=release_root,
            control_audit_root=control_root,
        )

        release = projection.strategy_release("policy-bound-release")
        summary = projection.strategy_summary()
        self.assertEqual(release["snapshotBindingMode"], "policy_bound_daily_snapshot")
        self.assertTrue(summary["approved"])
        self.assertTrue(summary["demoArm"])
        self.assertEqual(summary["route"], "armed")


if __name__ == "__main__":
    unittest.main()
