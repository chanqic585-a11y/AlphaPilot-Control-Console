from __future__ import annotations

import copy
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from alphapilot_control_console.adaptive_learning_contracts import (
    build_model_policy,
    build_observer_sidecar_binding,
    build_successor_release_identity,
)
from alphapilot_control_console.adaptive_learning_core import (
    AdaptiveLearningCore,
    DemoAdaptiveRuntimeAdapter,
    LiveAdaptiveRuntimeAdapter,
)
from alphapilot_control_console.adaptive_learning_store import AdaptiveLearningStore


FACTOR_REGISTRY = {
    "schemaVersion": "production_factor_registry_v1",
    "factors": [
        {
            "factorId": "rsi14",
            "name": "RSI 14",
            "theme": "momentum",
            "canonicalFormula": "rsi(close,14)",
            "requiredFields": ["close"],
            "availableAtRule": "confirmed_bar_close",
            "pointInTimeReady": True,
            "normalizationPolicy": "bounded_0_100",
            "missingValuePolicy": "reject_signal",
            "sourceArtifactId": "internal_indicator_engine",
            "definitionHash": "factor-definition-hash",
            "implementationHash": "factor-implementation-hash",
        }
    ],
    "factorRegistryHash": "factor-registry-hash",
}

FEATURE_SCHEMA = {
    "schemaVersion": "production_feature_schema_v1",
    "featureNames": ["rsi14"],
    "factorRegistryHash": "factor-registry-hash",
    "featureSchemaHash": "feature-schema-hash",
}


def _observer_policy() -> dict:
    return build_model_policy(
        model_hash="observer-model-hash",
        feature_schema_hash="feature-schema-hash",
        factor_registry_hash="factor-registry-hash",
        model_mode="observer",
        thresholds={"observationThreshold": 0.5},
        lifecycle_status="shadow_approved",
    )


class AdaptiveLearningCoreTests(unittest.TestCase):
    def test_store_serializes_concurrent_idempotent_feature_writes(self) -> None:
        payload = {
            "environment": "okx_demo",
            "releaseId": "release-1",
            "releaseHash": "release-hash",
            "strategyCandidateId": "candidate-1",
            "symbol": "BTC-USDT-SWAP",
            "timeframe": "1h",
            "signalAt": "2026-07-21T00:00:00+00:00",
            "observedAt": "2026-07-21T00:00:01+00:00",
            "availableAt": "2026-07-21T00:00:00+00:00",
            "sourceEventHash": "source-event-hash",
            "universeSnapshotHash": "universe-hash",
            "factorRegistryHash": "factor-registry-hash",
            "featureSchemaHash": "feature-schema-hash",
            "features": {"rsi14": 57.0},
        }
        with tempfile.TemporaryDirectory() as directory:
            store = AdaptiveLearningStore(Path(directory) / "adaptive.sqlite")
            try:
                with ThreadPoolExecutor(max_workers=8) as pool:
                    rows = list(pool.map(store.append_feature_snapshot, [payload] * 32))
                projection = store.projection()
            finally:
                store.close()

        self.assertEqual({row["featureSnapshotId"] for row in rows}, {rows[0]["featureSnapshotId"]})
        self.assertEqual(projection["featureSnapshotCount"], 1)

    def test_demo_observer_records_point_in_time_snapshot_without_mutating_scan(self) -> None:
        contract = {
            "demoReleaseId": "release-1",
            "releaseContentHash": "release-hash",
            "strategyCandidateId": "candidate-1",
            "riskOverlayHash": "risk-hash",
            "strategy": {"marketDefinition": {"timeframe": "1h"}},
        }
        scan = {
            "signals": [
                {
                    "candidateId": "candidate-1",
                    "instId": "BTC-USDT-SWAP",
                    "signalTime": "2026-07-21T00:00:00+00:00",
                    "factorContext": {"factors": {"rsi14": 57.0}},
                }
            ],
            "rejections": [],
        }
        original = copy.deepcopy(scan)
        with tempfile.TemporaryDirectory() as directory:
            store = AdaptiveLearningStore(Path(directory) / "adaptive.sqlite")
            try:
                core = AdaptiveLearningCore(
                    factor_registry=FACTOR_REGISTRY,
                    feature_schema=FEATURE_SCHEMA,
                    model_policy=_observer_policy(),
                    store=store,
                )
                result = DemoAdaptiveRuntimeAdapter(core).observe_scan(
                    contract,
                    scan,
                    observed_at="2026-07-21T00:00:01+00:00",
                    source_event_hash="source-event-hash",
                    universe_snapshot_hash="universe-hash",
                )
                duplicate = DemoAdaptiveRuntimeAdapter(core).observe_scan(
                    contract,
                    scan,
                    observed_at="2026-07-21T00:00:01+00:00",
                    source_event_hash="source-event-hash",
                    universe_snapshot_hash="universe-hash",
                )
                projection = store.projection()
            finally:
                store.close()

        self.assertEqual(scan, original)
        self.assertEqual(result["featureSnapshotCount"], 1)
        self.assertEqual(duplicate["featureSnapshotCount"], 1)
        self.assertEqual(projection["featureSnapshotCount"], 1)
        self.assertEqual(projection["modelDecisionCount"], 1)
        self.assertEqual(result["modelMode"], "observer")
        self.assertTrue(result["executionUnaffected"])

    def test_only_real_closed_trade_becomes_learning_sample(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = AdaptiveLearningStore(Path(directory) / "adaptive.sqlite")
            try:
                core = AdaptiveLearningCore(
                    factor_registry=FACTOR_REGISTRY,
                    feature_schema=FEATURE_SCHEMA,
                    model_policy=_observer_policy(),
                    store=store,
                )
                observed = core.observe_signal(
                    environment="okx_demo",
                    release_id="release-1",
                    release_hash="release-hash",
                    strategy_candidate_id="candidate-1",
                    risk_overlay_hash="risk-hash",
                    symbol="BTC-USDT-SWAP",
                    timeframe="1h",
                    signal_at="2026-07-21T00:00:00+00:00",
                    observed_at="2026-07-21T00:00:01+00:00",
                    available_at="2026-07-21T00:00:00+00:00",
                    source_event_hash="event-hash",
                    universe_snapshot_hash="universe-hash",
                    factors={"rsi14": 57.0},
                )
                outcome = {
                    "schemaVersion": "alphapilot_execution_outcome_v1",
                    "environment": "okx_demo",
                    "status": "closed",
                    "sourceEntityId": "demo-record-1",
                    "releaseId": "release-1",
                    "releaseHash": "release-hash",
                    "strategyCandidateId": "candidate-1",
                    "instrumentId": "BTC-USDT-SWAP",
                    "timeframe": "1h",
                    "direction": "long",
                    "decisionAt": "2026-07-21T00:00:00+00:00",
                    "entryAt": "2026-07-21T00:01:00+00:00",
                    "exitAt": "2026-07-21T03:00:00+00:00",
                    "trade": {
                        "feePaid": 0.2,
                        "slippagePaid": 0.1,
                        "netR": 0.8,
                        "netPnl": 2.0,
                        "grossPnl": 2.3,
                        "exitReason": "take_profit",
                    },
                }
                sample = core.record_closed_trade(
                    outcome,
                    feature_snapshot_id=observed["featureSnapshotId"],
                    model_decision_id=observed["modelDecisionId"],
                    market_state="trend",
                    funding=0.0001,
                    mfe=1.1,
                    mae=-0.3,
                    manually_intervened=False,
                )
                with self.assertRaises(PermissionError):
                    core.record_closed_trade(
                        {**outcome, "sourceEntityId": "smoke-1", "engineeringOnly": True},
                        feature_snapshot_id=observed["featureSnapshotId"],
                        model_decision_id=observed["modelDecisionId"],
                        market_state="trend",
                        funding=0.0,
                        mfe=0.0,
                        mae=0.0,
                        manually_intervened=False,
                    )
                projection = store.projection()
            finally:
                store.close()

        self.assertEqual(sample["schemaVersion"], "strategy_evolution_sample_v2")
        self.assertEqual(projection["learningSampleCount"], 1)

    def test_demo_adapter_resolves_opening_observation_for_closed_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = AdaptiveLearningStore(Path(directory) / "adaptive.sqlite")
            try:
                core = AdaptiveLearningCore(
                    factor_registry=FACTOR_REGISTRY,
                    feature_schema=FEATURE_SCHEMA,
                    model_policy=_observer_policy(),
                    store=store,
                )
                adapter = DemoAdaptiveRuntimeAdapter(core)
                core.observe_signal(
                    environment="okx_demo",
                    release_id="release-1",
                    release_hash="release-hash",
                    strategy_candidate_id="candidate-1",
                    risk_overlay_hash="risk-hash",
                    symbol="BTC-USDT-SWAP",
                    timeframe="1h",
                    signal_at="2026-07-21T00:00:00+00:00",
                    observed_at="2026-07-21T00:00:01+00:00",
                    available_at="2026-07-21T00:00:00+00:00",
                    source_event_hash="event-hash",
                    universe_snapshot_hash="universe-hash",
                    factors={"rsi14": 57.0},
                )
                sample = adapter.record_closed_outcome(
                    {
                        "schemaVersion": "alphapilot_execution_outcome_v1",
                        "environment": "okx_demo",
                        "status": "closed",
                        "sourceEntityId": "demo-record-2",
                        "releaseId": "release-1",
                        "releaseHash": "release-hash",
                        "strategyCandidateId": "candidate-1",
                        "instrumentId": "BTC-USDT-SWAP",
                        "timeframe": "1h",
                        "direction": "long",
                        "decisionAt": "2026-07-21T00:00:00+00:00",
                        "entryAt": "2026-07-21T00:01:00+00:00",
                        "exitAt": "2026-07-21T03:00:00+00:00",
                        "trade": {
                            "feePaid": 0.2,
                            "slippagePaid": 0.1,
                            "netR": 0.8,
                            "netPnl": 2.0,
                            "exitReason": "take_profit",
                        },
                    },
                    signal={
                        "candidateId": "candidate-1",
                        "instId": "BTC-USDT-SWAP",
                        "signalTime": "2026-07-21T00:00:00+00:00",
                    },
                )
                projection = store.projection()
            finally:
                store.close()

        self.assertEqual(sample["schemaVersion"], "strategy_evolution_sample_v2")
        self.assertEqual(sample["funding"], None)
        self.assertEqual(sample["mfe"], None)
        self.assertEqual(sample["mae"], None)
        self.assertEqual(sample["metricAvailability"]["funding"], False)
        self.assertEqual(projection["learningSampleCount"], 1)

    def test_demo_and_live_adapters_share_core_and_live_rejects_observer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = AdaptiveLearningStore(Path(directory) / "adaptive.sqlite")
            try:
                core = AdaptiveLearningCore(
                    factor_registry=FACTOR_REGISTRY,
                    feature_schema=FEATURE_SCHEMA,
                    model_policy=_observer_policy(),
                    store=store,
                )
                demo = DemoAdaptiveRuntimeAdapter(core)
                live = LiveAdaptiveRuntimeAdapter(core)
                self.assertIs(demo.core, live.core)
                with self.assertRaises(PermissionError):
                    live.validate_model_mode()
            finally:
                store.close()

    def test_decision_mode_change_creates_unapproved_successor_release(self) -> None:
        observer = _observer_policy()
        rank_policy = build_model_policy(
            model_hash="rank-model-hash",
            feature_schema_hash="feature-schema-hash",
            factor_registry_hash="factor-registry-hash",
            model_mode="rank_only",
            thresholds={"minimumScore": 0.6},
            lifecycle_status="shadow_approved",
        )
        sidecar = build_observer_sidecar_binding(
            release_id="release-1",
            release_hash="release-hash",
            model_policy=observer,
        )
        successor = build_successor_release_identity(
            release_id="release-1",
            release_hash="release-hash",
            model_policy=rank_policy,
        )

        self.assertFalse(sidecar["altersOrderSemantics"])
        self.assertNotEqual(successor["releaseHash"], "release-hash")
        self.assertTrue(successor["requiresExactHumanApproval"])
        self.assertFalse(successor["approved"])


if __name__ == "__main__":
    unittest.main()
