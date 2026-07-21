"""Validated runtime facade for the shared Demo and Live learning core."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Mapping

from .adaptive_learning_contracts import (
    build_feature_schema,
    build_observer_model_registry,
    stable_hash,
)
from .adaptive_learning_core import (
    AdaptiveLearningCore,
    DemoAdaptiveRuntimeAdapter,
    LiveAdaptiveRuntimeAdapter,
)
from .adaptive_learning_store import (
    DEFAULT_ADAPTIVE_LEARNING_STORE_PATH,
    AdaptiveLearningStore,
)
from .config import PROJECT_ROOT


DEFAULT_ADAPTIVE_ARTIFACT_ROOT = PROJECT_ROOT / "reports" / "v55_1_adaptive_learning"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"adaptive_learning_contract_missing:{path.name}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"adaptive_learning_contract_invalid:{path.name}")
    return payload


def _validate_registry(registry: Mapping[str, Any]) -> None:
    core = {key: value for key, value in registry.items() if key != "factorRegistryHash"}
    expected = stable_hash(core, prefix="production_factor_registry")
    if registry.get("factorRegistryHash") != expected:
        raise RuntimeError("factor_registry_contract_mismatch")
    if registry.get("pointInTimeOnly") is not True:
        raise RuntimeError("factor_registry_not_point_in_time")


class AdaptiveLearningRuntime:
    """Owns one core and exposes environment-specific adapters."""

    def __init__(
        self,
        *,
        artifact_root: Path | str = DEFAULT_ADAPTIVE_ARTIFACT_ROOT,
        store_path: Path | str = DEFAULT_ADAPTIVE_LEARNING_STORE_PATH,
    ) -> None:
        self.artifact_root = Path(artifact_root).expanduser().resolve()
        registry = _load_json(self.artifact_root / "production_factor_registry.json")
        _validate_registry(registry)
        feature_schema = _load_json(self.artifact_root / "production_feature_schema.json")
        expected_schema = build_feature_schema(registry)
        if feature_schema != expected_schema:
            raise RuntimeError("feature_schema_contract_mismatch")
        model_registry = _load_json(self.artifact_root / "model_registry.json")
        expected_registry = build_observer_model_registry(feature_schema)
        if model_registry != expected_registry:
            raise RuntimeError("model_registry_contract_mismatch")
        model_policy = model_registry.get("activeDemoModelPolicy")
        if not isinstance(model_policy, dict):
            raise RuntimeError("active_demo_model_policy_missing")

        self.factor_registry = registry
        self.feature_schema = feature_schema
        self.model_registry = model_registry
        self.store = AdaptiveLearningStore(store_path)
        self.core = AdaptiveLearningCore(
            factor_registry=registry,
            feature_schema=feature_schema,
            model_policy=model_policy,
            store=self.store,
        )
        self.demo = DemoAdaptiveRuntimeAdapter(self.core)
        self.live = LiveAdaptiveRuntimeAdapter(self.core)

    def close(self) -> None:
        self.store.close()

    def status(self) -> dict[str, Any]:
        projection = self.store.projection()
        policy = self.core.model_policy
        factors = self.factor_registry.get("factors")
        features = self.feature_schema.get("features")
        return {
            "schemaVersion": "adaptive_learning_runtime_status_v1",
            "status": "observer_ready",
            "factorRegistryHash": self.factor_registry["factorRegistryHash"],
            "featureSchemaHash": self.feature_schema["featureSchemaHash"],
            "modelRegistryHash": self.model_registry["modelRegistryHash"],
            "modelHash": policy["modelHash"],
            "modelPolicyHash": policy["modelPolicyHash"],
            "modelMode": policy["modelMode"],
            "factorCount": len(factors) if isinstance(factors, list) else 0,
            "featureCount": len(features) if isinstance(features, list) else 0,
            "altersOrderSemantics": False,
            "createsOrders": False,
            "changesRisk": False,
            "liveDecisionReady": False,
            **projection,
        }


_RUNTIME_LOCK = threading.Lock()
_RUNTIME: AdaptiveLearningRuntime | None = None


def get_adaptive_learning_runtime() -> AdaptiveLearningRuntime:
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            _RUNTIME = AdaptiveLearningRuntime()
        return _RUNTIME


def reset_adaptive_learning_runtime() -> None:
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is not None:
            _RUNTIME.close()
        _RUNTIME = None


def record_production_adaptive_scan(
    contract: Mapping[str, Any],
    scan: Mapping[str, Any],
    *,
    observed_at: str,
    source_event_hash: str,
    universe_instrument_ids: tuple[str, ...] | list[str] | set[str],
) -> dict[str, Any]:
    universe_snapshot_hash = stable_hash(
        {"instrumentIds": sorted({str(value) for value in universe_instrument_ids if str(value)})},
        prefix="adaptive_universe_snapshot",
    )
    return get_adaptive_learning_runtime().demo.observe_scan(
        contract,
        scan,
        observed_at=observed_at,
        source_event_hash=source_event_hash,
        universe_snapshot_hash=universe_snapshot_hash,
    )


def build_adaptive_learning_status() -> dict[str, Any]:
    try:
        return get_adaptive_learning_runtime().status()
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        return {
            "schemaVersion": "adaptive_learning_runtime_status_v1",
            "status": "blocked",
            "blockers": [str(error)],
            "modelMode": "observer",
            "factorCount": 0,
            "featureCount": 0,
            "altersOrderSemantics": False,
            "createsOrders": False,
            "changesRisk": False,
            "liveDecisionReady": False,
            "featureSnapshotCount": 0,
            "modelDecisionCount": 0,
            "learningSampleCount": 0,
        }
