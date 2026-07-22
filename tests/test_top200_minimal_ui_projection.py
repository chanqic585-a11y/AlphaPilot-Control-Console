from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from alphapilot_control_console.top200_minimal_ui_projection import (
    Top200MinimalUiProjection,
    write_top200_minimal_ui_projection_artifacts,
)
from alphapilot_control_console.strategy_factory_orchestrator import (
    StrategyFactoryOrchestrator,
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

    def test_research_factory_projection_prefers_active_persisted_run(self) -> None:
        quant_root = self.root / "quant"
        registry_path = quant_root / "research/source_registry/strategy_research_source_registry.json"
        registry_path.parent.mkdir(parents=True)
        registry_path.write_text(
            json.dumps(
                {
                    "families": [
                        {
                            "familyId": "family-a",
                            "variants": [{"candidateId": "candidate-a"}],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        state_path = self.root / "factory.sqlite"
        artifact_root = self.root / "factory-runs"
        factory = StrategyFactoryOrchestrator(
            state_path=state_path,
            artifact_root=artifact_root,
            quant_root=quant_root,
            source_registry_path=registry_path,
            launcher=lambda **_kwargs: {"pid": 1, "started": True},
        )
        created = factory.create_run(
            {
                "operation": "generate",
                "timeframe": "15m",
                "mode": "quick",
                "maxCandidateCount": 1,
                "maxTrialBudget": 4,
            }
        )
        factory.close()

        projection = Top200MinimalUiProjection(
            self.root,
            strategy_factory_state_path=state_path,
            strategy_factory_artifact_root=artifact_root,
            strategy_factory_quant_root=quant_root,
        )

        summary = projection.research_factory_summary()
        self.assertEqual(summary["researchRunId"], created["runId"])
        self.assertEqual(summary["status"], "queued")

    def test_research_factory_run_projects_truthful_development_evidence(self) -> None:
        quant_root = self.root / "quant-evidence"
        registry_path = quant_root / "research/source_registry/strategy_research_source_registry.json"
        registry_path.parent.mkdir(parents=True)
        registry_path.write_text(
            json.dumps(
                {
                    "families": [
                        {
                            "familyId": "family-a",
                            "variants": [{"candidateId": "candidate-a"}],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        state_path = self.root / "factory-evidence.sqlite"
        artifact_root = self.root / "factory-evidence-runs"
        factory = StrategyFactoryOrchestrator(
            state_path=state_path,
            artifact_root=artifact_root,
            quant_root=quant_root,
            source_registry_path=registry_path,
            launcher=lambda **_kwargs: {"pid": 1, "started": True},
        )
        created = factory.create_run(
            {
                "operation": "generate",
                "timeframe": "1h",
                "mode": "quick",
                "maxCandidateCount": 1,
                "maxTrialBudget": 3,
            }
        )
        campaign_root = Path(created["artifactPath"]) / created["campaignId"]
        campaign_root.mkdir(parents=True)
        _write_json(
            campaign_root,
            "campaign_summary.json",
            {
                "campaignId": created["campaignId"],
                "status": "awaiting_formal_validation",
                "candidateCount": 1,
                "trialCount": 3,
                "developmentReplayStatus": "completed",
                "formalRunCount": 0,
                "resultReadCount": 0,
                "lockedOosReadCount": 0,
                "releaseCount": 0,
            },
        )
        _write_json(
            campaign_root,
            "preregistration.json",
            {
                "campaignId": created["campaignId"],
                "selectionSplit": "development",
                "comparisonPanel": {
                    "developmentStart": "2021-02-01T00:00:00Z",
                    "developmentEnd": "2025-01-01T00:00:00Z",
                    "dataSnapshotId": "snapshot-fixture",
                    "costPolicyHash": "cost-policy-fixture",
                },
            },
        )
        _write_json(
            campaign_root,
            "development_replay_audit.json",
            {
                "campaignId": created["campaignId"],
                "status": "completed",
                "formalRunCount": 0,
                "resultReadCount": 0,
                "lockedOosReadCount": 0,
                "snapshotAudit": {
                    "snapshotId": "snapshot-fixture",
                    "verifiedPartitionCount": 2,
                    "partitions": [
                        {
                            "instrumentId": "BTC-USDT-SWAP",
                            "timeframe": "1h",
                            "rowCount": 100,
                        },
                        {
                            "instrumentId": "ETH-USDT-SWAP",
                            "timeframe": "1h",
                            "rowCount": 120,
                        },
                    ],
                },
                "trialAudit": [
                    {"candidateId": "candidate-a", "trialId": "trial-a", "eventCount": 12}
                ],
            },
        )
        _write_json(
            campaign_root,
            "development_projection.json",
            {
                "campaignId": created["campaignId"],
                "projectionCount": 1,
                "projections": [
                    {
                        "candidateId": "candidate-a",
                        "trialId": "trial-a",
                        "split": "development",
                        "profitFactor": 1.25,
                        "selectionNetR": 0.18,
                        "maxDrawdownR": 2.5,
                        "typeSpecificMetrics": {
                            "eventCount": 12,
                            "totalNetR": 2.16,
                            "totalCostR": 0.42,
                            "averageNetR": 0.18,
                        },
                    }
                ],
            },
        )
        _write_json(
            campaign_root,
            "artifact_manifest.json",
            {
                "campaignId": created["campaignId"],
                "artifacts": [
                    {"path": "campaign_summary.json", "sha256": "summary-sha"},
                    {"path": "development_projection.json", "sha256": "projection-sha"},
                ],
            },
        )
        factory.close()

        projection = Top200MinimalUiProjection(
            self.root,
            strategy_factory_state_path=state_path,
            strategy_factory_artifact_root=artifact_root,
            strategy_factory_quant_root=quant_root,
        )

        run = projection.research_factory_run(created["runId"])
        evidence = run["executionEvidence"]
        self.assertEqual(evidence["evaluationMode"], "real_development_backtest")
        self.assertEqual(evidence["validationLevel"], "development_only")
        self.assertEqual(evidence["development"]["status"], "completed")
        self.assertEqual(evidence["development"]["selectionSplit"], "development")
        self.assertEqual(evidence["development"]["verifiedPartitionCount"], 2)
        self.assertEqual(evidence["development"]["instrumentCount"], 2)
        self.assertEqual(evidence["development"]["totalRowCount"], 220)
        self.assertEqual(evidence["development"]["candidateCount"], 1)
        self.assertEqual(evidence["development"]["trialCount"], 3)
        self.assertEqual(evidence["development"]["eventCount"], 12)
        self.assertEqual(evidence["development"]["bestTrial"]["profitFactor"], 1.25)
        self.assertEqual(evidence["development"]["bestTrial"]["totalCostR"], 0.42)
        self.assertEqual(evidence["formal"]["status"], "not_run")
        self.assertEqual(evidence["formal"]["formalRunCount"], 0)
        self.assertEqual(evidence["formal"]["lockedOosReadCount"], 0)
        self.assertEqual(
            [item["name"] for item in evidence["artifacts"]],
            ["campaign_summary.json", "development_projection.json"],
        )

    def test_research_factory_run_refreshes_finished_worker_receipt(self) -> None:
        quant_root = self.root / "quant-refresh"
        registry_path = quant_root / "research/source_registry/strategy_research_source_registry.json"
        registry_path.parent.mkdir(parents=True)
        registry_path.write_text(
            json.dumps(
                {
                    "families": [
                        {
                            "familyId": "family-a",
                            "variants": [{"candidateId": "candidate-a"}],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        state_path = self.root / "factory-refresh.sqlite"
        artifact_root = self.root / "factory-refresh-runs"
        factory = StrategyFactoryOrchestrator(
            state_path=state_path,
            artifact_root=artifact_root,
            quant_root=quant_root,
            source_registry_path=registry_path,
            launcher=lambda **_kwargs: {"pid": 1, "started": True},
        )
        created = factory.create_run(
            {
                "operation": "generate",
                "timeframe": "15m",
                "mode": "quick",
                "maxCandidateCount": 1,
                "maxTrialBudget": 4,
            }
        )
        factory.start_run(created["runId"])
        receipt_path = Path(created["jobJsonPath"]).parent / "state/research_cycle_receipts.jsonl"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(
                {
                    "status": "research_blocked_data",
                    "campaignId": created["campaignId"],
                    "candidateCount": 1,
                    "eligibleCandidateCount": 0,
                    "releaseCount": 0,
                    "approvalCount": 0,
                    "demoArm": False,
                    "orderCount": 0,
                    "receiptHash": "projection-refresh-receipt",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        factory.close()

        projection = Top200MinimalUiProjection(
            self.root,
            strategy_factory_state_path=state_path,
            strategy_factory_artifact_root=artifact_root,
            strategy_factory_quant_root=quant_root,
        )

        refreshed = projection.research_factory_run(created["runId"])

        self.assertEqual(refreshed["status"], "completed")
        self.assertEqual(refreshed["progressPercent"], 100)
        self.assertEqual(refreshed["resultClass"], "data_insufficient")

    def test_strategy_projection_includes_factory_reviews_and_archived_failures(self) -> None:
        quant_root = self.root / "quant-outcomes"
        registry_path = quant_root / "research/source_registry/strategy_research_source_registry.json"
        registry_path.parent.mkdir(parents=True)
        registry_path.write_text(
            json.dumps(
                {
                    "families": [
                        {
                            "familyId": "family-a",
                            "variants": [
                                {"candidateId": "candidate-a"},
                                {"candidateId": "candidate-b"},
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        state_path = self.root / "factory-outcomes.sqlite"
        artifact_root = self.root / "factory-outcomes"
        factory = StrategyFactoryOrchestrator(
            state_path=state_path,
            artifact_root=artifact_root,
            quant_root=quant_root,
            source_registry_path=registry_path,
            launcher=lambda **_kwargs: {"pid": 1, "started": True},
        )
        created = factory.create_run(
            {
                "operation": "generate",
                "timeframe": "15m",
                "mode": "quick",
                "maxCandidateCount": 2,
                "maxTrialBudget": 8,
            }
        )
        campaign_root = Path(created["artifactPath"]) / created["campaignId"]
        campaign_root.mkdir(parents=True)
        summary_path = campaign_root / "campaign_summary.json"
        summary_path.write_text("{}\n", encoding="utf-8")
        _write_json(
            campaign_root,
            "immutable_releases.json",
            {
                "campaignId": created["campaignId"],
                "releaseCount": 1,
                "approved": False,
                "demoArm": False,
                "orders": 0,
                "releases": [
                    {
                        "candidateId": "candidate-a",
                        "trialId": "trial-a",
                        "outcome": "formal_pass",
                        "immutableReleaseHash": "immutable-release-a",
                        "approved": False,
                        "demoArm": False,
                        "orders": 0,
                    }
                ],
            },
        )
        factory.record_receipt(
            created["runId"],
            {
                "status": "immutable_release_ready",
                "campaignId": created["campaignId"],
                "releaseCount": 1,
                "eligibleCandidateCount": 1,
                "artifactPath": str(summary_path),
                "receiptHash": "receipt-a",
                "approvalCount": 0,
                "demoArm": False,
                "orderCount": 0,
            },
        )
        factory.close()

        projection = Top200MinimalUiProjection(
            self.root,
            strategy_factory_state_path=state_path,
            strategy_factory_artifact_root=artifact_root,
            strategy_factory_quant_root=quant_root,
        )

        summary = projection.strategy_summary()
        self.assertEqual(summary["resultCounts"]["canEnterDemo"], 2)
        self.assertEqual(summary["resultCounts"]["failed"], 1)
        self.assertEqual(summary["pendingCandidateReviewCount"], 1)
        self.assertEqual(summary["archivedFailureCount"], 1)
        reviews = projection.strategy_releases()["candidateReviews"]
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["candidateId"], "candidate-a")
        self.assertEqual(reviews[0]["status"], "pending_human_review")
        self.assertFalse(reviews[0]["automaticApprovalAllowed"])
        self.assertFalse(reviews[0]["demoArm"])
        self.assertEqual(reviews[0]["orderCount"], 0)
        runs = projection.research_factory_runs()["runs"]
        self.assertEqual(runs[0]["runId"], created["runId"])
        self.assertEqual(
            projection.research_factory_run(created["runId"])["campaignId"],
            created["campaignId"],
        )

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

    def test_runtime_terminal_projection_replaces_static_demo_and_live_state(self) -> None:
        terminal = Mock()
        terminal.summary.side_effect = lambda environment: {
            "environment": environment,
            "runtimeStatus": "waiting" if environment == "okx_demo" else "disabled",
            "desiredEnabled": environment == "okx_demo",
            "armed": environment == "okx_demo",
            "equity": 1000.0 if environment == "okx_demo" else None,
            "availableBalance": 975.0 if environment == "okx_demo" else None,
            "todayPnl": 8.0 if environment == "okx_demo" else None,
            "floatingPnl": -1.5 if environment == "okx_demo" else None,
            "openPositionCount": 1 if environment == "okx_demo" else None,
            "runningStrategyCount": 3 if environment == "okx_demo" else 0,
            "strategyOrderCount": 2 if environment == "okx_demo" else 0,
            "scanFunnel": {"marketInstrumentCount": 200},
            "issues": [],
            "updatedAt": "2026-07-22T01:00:00Z",
            "source": "runtime_and_execution_ledgers",
            "readOnly": True,
        }
        terminal.strategies.side_effect = lambda environment: {
            "environment": environment,
            "strategies": [{"strategyId": "strategy-a", "status": "running"}],
            "readOnly": True,
        }
        terminal.positions.side_effect = lambda environment: {
            "environment": environment,
            "positions": [{"instrumentId": "BTC-USDT-SWAP"}],
            "openPositionCount": 1,
            "readOnly": True,
        }
        terminal.orders.side_effect = lambda environment: {
            "environment": environment,
            "orders": [{"recordId": "order-a"}],
            "strategyOrderCount": 1,
            "readOnly": True,
        }
        projection = Top200MinimalUiProjection(
            self.root,
            terminal_projection=terminal,
        )

        demo = projection.demo_summary()
        live = projection.live_summary()

        self.assertEqual(demo["connectionStatus"], "connected_armed")
        self.assertEqual(demo["equity"], 1000.0)
        self.assertEqual(demo["availableBalance"], 975.0)
        self.assertEqual(demo["scanFunnel"]["marketInstrumentCount"], 200)
        self.assertTrue(
            any(
                issue["code"] == "exact_release_approval_required"
                for issue in demo["issues"]
            )
        )
        self.assertEqual(projection.demo_strategies()["strategies"][0]["strategyId"], "strategy-a")
        self.assertEqual(projection.demo_positions()["positions"][0]["instrumentId"], "BTC-USDT-SWAP")
        self.assertEqual(projection.demo_orders()["orders"][0]["recordId"], "order-a")
        self.assertEqual(live["connectionStatus"], "disabled")
        self.assertEqual(projection.live_positions()["positions"][0]["instrumentId"], "BTC-USDT-SWAP")
        terminal.summary.assert_any_call("okx_demo")
        terminal.summary.assert_any_call("okx_live")

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

    def test_exact_approval_without_arm_projects_approved_not_armed(self) -> None:
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

        projection = Top200MinimalUiProjection(
            self.root,
            release_root=release_root,
            control_audit_root=control_root,
        )

        summary = projection.strategy_summary()
        demo_strategy = projection.demo_strategies()["strategies"][0]
        self.assertTrue(summary["approved"])
        self.assertFalse(summary["demoArm"])
        self.assertEqual(summary["route"], "approved_not_armed")
        self.assertEqual(summary["strategyOrderCount"], 0)
        self.assertEqual(demo_strategy["status"], "approved_not_armed")

    def test_strategy_summary_uses_current_runtime_over_historical_arm_audit(self) -> None:
        terminal = Mock()
        terminal.summary.return_value = {
            "environment": "okx_demo",
            "runtimeStatus": "disarmed",
            "desiredEnabled": True,
            "armed": False,
            "strategyOrderCount": 0,
            "updatedAt": "2026-07-22T02:00:00Z",
        }
        projection = Top200MinimalUiProjection(
            self.root,
            terminal_projection=terminal,
        )
        projection._approval = Mock(return_value={
            "approved": True,
            "demoArm": True,
            "route": "armed",
            "strategyOrderCount": 0,
        })

        summary = projection.strategy_summary()
        release = projection.strategy_releases()["releases"][0]

        self.assertTrue(summary["approved"])
        self.assertFalse(summary["demoArm"])
        self.assertEqual(summary["armedReleaseCount"], 0)
        self.assertEqual(summary["route"], "approved_not_armed")
        self.assertFalse(release["demoArm"])
        self.assertEqual(release["route"], "approved_not_armed")
        self.assertGreaterEqual(terminal.summary.call_count, 2)
        terminal.summary.assert_called_with("okx_demo")


if __name__ == "__main__":
    unittest.main()
