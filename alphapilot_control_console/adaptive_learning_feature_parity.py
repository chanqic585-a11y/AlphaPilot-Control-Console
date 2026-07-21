"""Prove Demo/Live feature-vector parity through the shared adaptive core."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Mapping

from .adaptive_learning_contracts import stable_hash
from .adaptive_learning_core import AdaptiveLearningCore
from .adaptive_learning_store import AdaptiveLearningStore


def build_feature_pipeline_parity_evidence(
    *,
    factor_registry: Mapping[str, Any],
    feature_schema: Mapping[str, Any],
    model_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay one identical point-in-time vector in Demo and Live contexts."""

    factor_ids = [
        str(row["factorId"])
        for row in factor_registry.get("factors", [])
        if isinstance(row, dict)
        and row.get("pointInTimeReady") is True
        and row.get("factorId")
    ]
    if not factor_ids:
        raise ValueError("Factor Registry contains no point-in-time-ready factor")
    factors = {factor_ids[0]: 1.0}
    common = {
        "release_id": "feature-parity-fixture-release",
        "release_hash": "feature-parity-fixture-release-hash",
        "strategy_candidate_id": "feature-parity-fixture-candidate",
        "risk_overlay_hash": "feature-parity-fixture-risk-hash",
        "symbol": "BTC-USDT-SWAP",
        "timeframe": "1h",
        "signal_at": "2026-07-21T00:00:00+00:00",
        "observed_at": "2026-07-21T00:00:01+00:00",
        "available_at": "2026-07-21T00:00:00+00:00",
        "universe_snapshot_hash": "feature-parity-fixture-universe-hash",
        "factors": factors,
    }
    with tempfile.TemporaryDirectory() as directory:
        store = AdaptiveLearningStore(Path(directory) / "feature-parity.sqlite")
        try:
            core = AdaptiveLearningCore(
                factor_registry=factor_registry,
                feature_schema=feature_schema,
                model_policy=model_policy,
                store=store,
            )
            demo = core.observe_signal(
                environment="okx_demo",
                source_event_hash="feature-parity-demo-event",
                **common,
            )
            live = core.observe_signal(
                environment="live",
                source_event_hash="feature-parity-live-event",
                **common,
            )
        finally:
            store.close()

    hashes_equal = demo["featureVectorHash"] == live["featureVectorHash"]
    core_payload = {
        "schemaVersion": "adaptive_learning_feature_pipeline_parity_v1",
        "status": "completed" if hashes_equal else "blocked",
        "passed": hashes_equal,
        "featureVectorHashEqual": hashes_equal,
        "sharedCoreImplementation": True,
        "factorRegistryHash": factor_registry.get("factorRegistryHash"),
        "featureSchemaHash": feature_schema.get("featureSchemaHash"),
        "modelPolicyHash": model_policy.get("modelPolicyHash"),
        "factorIdsUsed": sorted(factors),
        "demoFeatureVectorHash": demo["featureVectorHash"],
        "liveFeatureVectorHash": live["featureVectorHash"],
        "fixtureOnly": True,
        "liveOrderPathExercised": False,
        "grantsLiveAuthority": False,
        "createsOrders": False,
    }
    return {
        **core_payload,
        "evidenceHash": stable_hash(
            core_payload,
            prefix="adaptive_feature_pipeline_parity",
        ),
    }
