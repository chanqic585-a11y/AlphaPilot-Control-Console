from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.experimental_live_canary_release import (
    build_experimental_live_canary_bundle,
    build_live_experiment_profile,
    validate_exact_live_canary_approval,
    write_experimental_live_canary_bundle,
)
from alphapilot_control_console.live_canary_service import (
    build_exact_live_canary_arm_readiness,
)
from alphapilot_control_console.live_auto_execution_service import (
    build_experimental_live_auto_execution_preflight,
)
from alphapilot_control_console.live_safety_plane import (
    evaluate_experimental_live_floors,
)


PROFILE_INPUT = {
    "allocatedCapitalUSDT": 1000.0,
    "maximumAcceptedLossUSDT": 1000.0,
    "riskPerTradePercent": 0.25,
    "riskPerTradeUSDT": 2.5,
    "maximumPortfolioOpenRiskPercent": 1.0,
    "maximumPortfolioOpenRiskUSDT": 10.0,
    "maximumConcurrentPositions": 1,
    "maximumInstrumentRisk": 0.5,
    "maximumLeverage": 1,
    "marginMode": "isolated",
    "dailyLossLimit": 10.0,
    "programLossLimit": 25.0,
    "hardKillLossLimit": 25.0,
    "scanTopN": 200,
}

SOURCE_DEMO_RELEASE = {
    "demoReleaseId": "provisional_research_demo_top200_policy_bound_test",
    "demoReleaseHash": "provisional_demo_release_" + "a" * 64,
    "riskOverlayHash": "risk_overlay_" + "b" * 64,
    "observerSidecarHash": "observer_sidecar_" + "c" * 64,
    "componentCandidateIds": ["s01", "s02", "s03"],
    "componentDefinitionHashes": ["candidate_" + "d" * 64],
}

SMOKE_RESULT = {
    "schemaVersion": "alphapilot_live_engineering_smoke_result_v1",
    "contractHash": "live_engineering_smoke_" + "e" * 64,
    "environment": "okx_live",
    "status": "completed_canceled_and_reconciled",
    "orderAttemptCount": 1,
    "cancelConfirmed": True,
    "finalOpenPositionCount": 0,
    "finalOpenOrderCount": 0,
    "finalReconciliationMatched": True,
    "rawCredentialsPersisted": False,
    "privateAccountValuesPersisted": False,
    "withdrawAllowed": False,
}

OBSERVER_BINDING = {
    "sidecarBindingHash": "observer_sidecar_" + "f" * 64,
    "modelHash": "model_" + "1" * 64,
    "modelPolicyHash": "model_policy_" + "2" * 64,
    "releaseHash": SOURCE_DEMO_RELEASE["demoReleaseHash"],
    "releaseId": SOURCE_DEMO_RELEASE["demoReleaseId"],
}

ADAPTIVE_READY = {
    "schemaVersion": "adaptive_learning_live_readiness_v1",
    "passed": True,
    "status": "passed",
    "modelMode": "rank_only",
    "blockers": [],
}

ADAPTIVE_BLOCKED_OBSERVER = {
    "schemaVersion": "adaptive_learning_technical_readiness_v1",
    "passed": False,
    "status": "blocked_not_ready",
    "modelMode": "observer",
    "blockers": ["live_model_mode_not_decision_participating"],
}

ARM_RUNTIME_READY = {
    "credentialsConfigured": True,
    "privateReadReady": True,
    "reconciliationMatched": True,
    "zeroOpenPositions": True,
    "zeroOpenOrders": True,
    "liveEnabled": False,
    "withdrawAllowed": False,
}


class ExperimentalLiveCanaryReleaseTests(unittest.TestCase):
    def test_profile_is_configurable_versioned_and_hashed(self) -> None:
        first = build_live_experiment_profile(PROFILE_INPUT, version=1)
        second = build_live_experiment_profile(PROFILE_INPUT, version=1)

        self.assertEqual(first, second)
        self.assertEqual(first["allocatedCapitalUSDT"], 1000.0)
        self.assertEqual(first["maximumAcceptedLossUSDT"], 1000.0)
        self.assertEqual(first["lossLimitUnit"], "USDT")
        self.assertEqual(first["version"], 1)
        self.assertEqual(first["maximumSignalAgeMs"], 3000)
        self.assertEqual(first["criticalLatencyFailureMs"], 20000)
        self.assertNotEqual(first["maximumSignalAgeMs"], first["criticalLatencyFailureMs"])
        self.assertNotIn("maximumSignalAgeSeconds", first)
        self.assertTrue(
            first["executionLatencyProfileHash"].startswith("execution_latency_profile_")
        )
        self.assertTrue(first["profileHash"].startswith("live_experiment_profile_"))

        changed = build_live_experiment_profile(
            {**PROFILE_INPUT, "riskPerTradeUSDT": 1.0},
            version=2,
        )
        self.assertNotEqual(changed["profileHash"], first["profileHash"])

    def test_profile_rejects_unsafe_loss_relationships(self) -> None:
        invalid_profiles = (
            {**PROFILE_INPUT, "maximumAcceptedLossUSDT": 1001.0},
            {**PROFILE_INPUT, "hardKillLossLimit": 1001.0},
            {**PROFILE_INPUT, "dailyLossLimit": 26.0},
            {**PROFILE_INPUT, "programLossLimit": 26.0, "hardKillLossLimit": 25.0},
            {key: value for key, value in PROFILE_INPUT.items() if key != "hardKillLossLimit"},
        )
        for profile in invalid_profiles:
            with self.subTest(profile=profile):
                with self.assertRaises(ValueError):
                    build_live_experiment_profile(profile, version=1)

    def test_bundle_is_immutable_unarmed_and_marks_unexecuted_ledgers_not_run(self) -> None:
        bundle = build_experimental_live_canary_bundle(
            profile_input=PROFILE_INPUT,
            source_demo_release=SOURCE_DEMO_RELEASE,
            smoke_result=SMOKE_RESULT,
            observer_binding=OBSERVER_BINDING,
            adaptive_learning_readiness=ADAPTIVE_READY,
            generated_at="2026-07-21T06:00:00+00:00",
        )

        self.assertEqual(bundle["status"], "blocked_waiting_exact_live_release_approval")
        self.assertEqual(bundle["liveRelease"]["releasePurpose"], "operator_approved_live_canary")
        self.assertFalse(bundle["liveRelease"]["formalPass"])
        self.assertFalse(bundle["liveRelease"]["productionQualified"])
        self.assertFalse(bundle["liveRelease"]["automaticPromotion"])
        self.assertTrue(bundle["liveRelease"]["releaseHash"].startswith("experimental_live_release_"))
        self.assertTrue(bundle["riskOverlay"]["riskOverlayHash"].startswith("live_risk_overlay_"))
        self.assertEqual(bundle["riskOverlay"]["status"], "draft")
        self.assertTrue(bundle["environment"]["environmentHash"].startswith("live_environment_"))
        self.assertTrue(bundle["universePolicy"]["universePolicyHash"].startswith("live_universe_policy_"))
        self.assertFalse(bundle["environment"]["withdrawAllowed"])
        self.assertEqual(bundle["universePolicy"]["scanTopN"], 200)
        self.assertEqual(bundle["privateReadEvidence"]["status"], "passed_via_v58_private_preflight")
        self.assertEqual(bundle["executionState"]["armStatus"], "not_run")
        for ledger in ("orderLedger", "fillLedger", "positionLedger"):
            self.assertEqual(bundle[ledger]["status"], "not_run")
            self.assertEqual(bundle[ledger]["records"], [])

    def test_observer_bundle_is_non_actionable_draft_and_cannot_be_approved(self) -> None:
        bundle = build_experimental_live_canary_bundle(
            profile_input=PROFILE_INPUT,
            source_demo_release=SOURCE_DEMO_RELEASE,
            smoke_result=SMOKE_RESULT,
            observer_binding=OBSERVER_BINDING,
            adaptive_learning_readiness=ADAPTIVE_BLOCKED_OBSERVER,
            generated_at="2026-07-21T06:00:00+00:00",
        )

        self.assertEqual(bundle["status"], "draft_blocked_adaptive_learning_not_ready")
        self.assertEqual(
            bundle["liveRelease"]["status"],
            "draft_blocked_adaptive_learning_not_ready",
        )
        self.assertEqual(
            bundle["approvalRequest"]["status"],
            "draft_blocked_adaptive_learning_not_ready",
        )
        self.assertFalse(bundle["approvalRequest"]["approvalRequestActionable"])
        self.assertIsNone(bundle["approvalRequest"]["requiredConfirmation"])
        self.assertFalse(
            bundle["liveRelease"]["executionBoundary"][
                "mechanicalExecutionAllowedAfterExactApproval"
            ]
        )
        with self.assertRaises(PermissionError):
            validate_exact_live_canary_approval(
                bundle,
                {
                    "actor": "user_manual",
                    "confirmation": "not-actionable",
                    "releaseHash": bundle["liveRelease"]["releaseHash"],
                    "riskOverlayHash": bundle["riskOverlay"]["riskOverlayHash"],
                    "maximumAcceptedLossUSDT": 1000.0,
                },
            )

    def test_exact_approval_requires_release_risk_and_maximum_loss(self) -> None:
        bundle = build_experimental_live_canary_bundle(
            profile_input=PROFILE_INPUT,
            source_demo_release=SOURCE_DEMO_RELEASE,
            smoke_result=SMOKE_RESULT,
            observer_binding=OBSERVER_BINDING,
            adaptive_learning_readiness=ADAPTIVE_READY,
            generated_at="2026-07-21T06:00:00+00:00",
        )
        exact = {
            "actor": "user_manual",
            "confirmation": bundle["approvalRequest"]["requiredConfirmation"],
            "releaseHash": bundle["liveRelease"]["releaseHash"],
            "riskOverlayHash": bundle["riskOverlay"]["riskOverlayHash"],
            "maximumAcceptedLossUSDT": 1000.0,
        }

        validated = validate_exact_live_canary_approval(bundle, exact)
        self.assertEqual(validated["status"], "approved_exact_live_canary_identity")

        for changed in (
            {**exact, "releaseHash": "wrong"},
            {**exact, "riskOverlayHash": "wrong"},
            {**exact, "maximumAcceptedLossUSDT": 999.0},
            {**exact, "actor": "automation"},
        ):
            with self.assertRaises(PermissionError):
                validate_exact_live_canary_approval(bundle, changed)

    def test_arm_readiness_remains_false_without_exact_approval(self) -> None:
        bundle = build_experimental_live_canary_bundle(
            profile_input=PROFILE_INPUT,
            source_demo_release=SOURCE_DEMO_RELEASE,
            smoke_result=SMOKE_RESULT,
            observer_binding=OBSERVER_BINDING,
            adaptive_learning_readiness=ADAPTIVE_READY,
            generated_at="2026-07-21T06:00:00+00:00",
        )

        blocked = build_exact_live_canary_arm_readiness(
            bundle=bundle,
            approval=None,
            runtime_state=ARM_RUNTIME_READY,
        )
        self.assertFalse(blocked["canArm"])
        self.assertIn("exact_live_release_approval_missing", blocked["blockers"])

        exact = {
            "actor": "user_manual",
            "confirmation": bundle["approvalRequest"]["requiredConfirmation"],
            "releaseHash": bundle["liveRelease"]["releaseHash"],
            "riskOverlayHash": bundle["riskOverlay"]["riskOverlayHash"],
            "maximumAcceptedLossUSDT": 1000.0,
        }
        ready = build_exact_live_canary_arm_readiness(
            bundle=bundle,
            approval=exact,
            runtime_state=ARM_RUNTIME_READY,
        )
        self.assertTrue(ready["canArm"])
        self.assertEqual(ready["blockers"], [])

        blocked_bundle = build_experimental_live_canary_bundle(
            profile_input=PROFILE_INPUT,
            source_demo_release=SOURCE_DEMO_RELEASE,
            smoke_result=SMOKE_RESULT,
            observer_binding=OBSERVER_BINDING,
            adaptive_learning_readiness={
                **ADAPTIVE_READY,
                "passed": False,
                "status": "blocked_not_ready",
                "modelMode": "observer",
                "blockers": ["adaptive_evidence_not_ready:qlibCampaignReady"],
            },
            generated_at="2026-07-21T06:00:00+00:00",
        )
        blocked_adaptive = build_exact_live_canary_arm_readiness(
            bundle=blocked_bundle,
            approval={
                **exact,
                "confirmation": blocked_bundle["approvalRequest"]["requiredConfirmation"],
                "releaseHash": blocked_bundle["liveRelease"]["releaseHash"],
                "riskOverlayHash": blocked_bundle["riskOverlay"]["riskOverlayHash"],
            },
            runtime_state=ARM_RUNTIME_READY,
        )
        self.assertFalse(blocked_adaptive["canArm"])
        self.assertIn(
            "adaptive_learning_technical_readiness_not_passed",
            blocked_adaptive["blockers"],
        )

    def test_hard_floors_fail_closed(self) -> None:
        profile = build_live_experiment_profile(PROFILE_INPUT, version=1)
        healthy = {
            "dailyLossUSDT": 0.0,
            "programLossUSDT": 0.0,
            "openPositionCount": 0,
            "requestedLeverage": 1,
            "signalAgeSeconds": 1.0,
            "killSwitchActive": False,
            "reconciliationMatched": True,
        }
        self.assertEqual(evaluate_experimental_live_floors(profile, healthy), [])

        blocked = evaluate_experimental_live_floors(
            profile,
            {
                **healthy,
                "dailyLossUSDT": 10.0,
                "programLossUSDT": 25.0,
                "openPositionCount": 1,
                "requestedLeverage": 2,
                "signalAgeSeconds": 21.0,
                "killSwitchActive": True,
                "reconciliationMatched": False,
            },
        )
        self.assertEqual(
            blocked,
            [
                "live_daily_loss_limit",
                "live_program_loss_limit",
                "live_hard_kill_loss_limit",
                "live_maximum_concurrent_positions",
                "live_maximum_leverage",
                "live_signal_stale",
                "live_kill_switch_active",
                "live_reconciliation_not_confirmed",
            ],
        )

    def test_live_auto_execution_preflight_never_runs_without_all_frozen_gates(self) -> None:
        bundle = build_experimental_live_canary_bundle(
            profile_input=PROFILE_INPUT,
            source_demo_release=SOURCE_DEMO_RELEASE,
            smoke_result=SMOKE_RESULT,
            observer_binding=OBSERVER_BINDING,
            adaptive_learning_readiness=ADAPTIVE_READY,
            generated_at="2026-07-21T06:00:00+00:00",
        )
        runtime = {
            **ARM_RUNTIME_READY,
            "dailyLossUSDT": 0.0,
            "programLossUSDT": 0.0,
            "openPositionCount": 0,
            "requestedLeverage": 1,
            "signalAgeSeconds": 1.0,
            "killSwitchActive": False,
            "reconciliationMatched": True,
        }

        blocked = build_experimental_live_auto_execution_preflight(
            bundle=bundle,
            approval=None,
            runtime_state=runtime,
        )
        self.assertFalse(blocked["canProceedToArm"])
        self.assertEqual(blocked["orderStatus"], "not_run")

        exact = {
            "actor": "user_manual",
            "confirmation": bundle["approvalRequest"]["requiredConfirmation"],
            "releaseHash": bundle["liveRelease"]["releaseHash"],
            "riskOverlayHash": bundle["riskOverlay"]["riskOverlayHash"],
            "maximumAcceptedLossUSDT": 1000.0,
        }
        ready = build_experimental_live_auto_execution_preflight(
            bundle=bundle,
            approval=exact,
            runtime_state=runtime,
        )
        self.assertTrue(ready["canProceedToArm"])
        self.assertEqual(ready["blockers"], [])
        self.assertEqual(ready["orderStatus"], "not_run")

    def test_writer_emits_manifest_and_no_credentials(self) -> None:
        bundle = build_experimental_live_canary_bundle(
            profile_input=PROFILE_INPUT,
            source_demo_release=SOURCE_DEMO_RELEASE,
            smoke_result=SMOKE_RESULT,
            observer_binding=OBSERVER_BINDING,
            adaptive_learning_readiness=ADAPTIVE_READY,
            generated_at="2026-07-21T06:00:00+00:00",
        )
        with tempfile.TemporaryDirectory() as directory:
            manifest = write_experimental_live_canary_bundle(Path(directory), bundle)
            self.assertGreaterEqual(manifest["artifactCount"], 10)
            text = "\n".join(path.read_text(encoding="utf-8") for path in Path(directory).glob("*.json"))
            self.assertNotIn("apiSecret", text)
            self.assertNotIn("passphrase", text.lower())
            self.assertNotIn("apiKey", text)


if __name__ == "__main__":
    unittest.main()
