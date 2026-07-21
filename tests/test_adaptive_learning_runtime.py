from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.adaptive_learning_contracts import (
    build_feature_schema,
    build_observer_model_registry,
    stable_hash,
)
from alphapilot_control_console.adaptive_learning_runtime import AdaptiveLearningRuntime


def _registry() -> dict:
    factor = {
        "factorId": "rsi_14",
        "name": "RSI 14",
        "theme": "momentum",
        "canonicalFormula": "rsi(close,14)",
        "requiredFields": ["close"],
        "availableAtRule": "confirmed_bar_close",
        "pointInTimeReady": True,
        "normalizationPolicy": "bounded_0_100",
        "missingValuePolicy": "record_missing_flag",
        "sourceArtifactId": "test",
        "definitionHash": "factor-definition-hash",
        "implementationHash": "factor-implementation-hash",
        "sourceClass": "crypto_native",
    }
    core = {
        "schemaVersion": "production_factor_registry_v1",
        "boundedMaximum": 36,
        "factors": [factor],
        "pointInTimeOnly": True,
        "predictiveValueClaimed": False,
        "alpha191Compatibility": {
            "catalogCount": 191,
            "formulaReviewedCount": 0,
            "numericCrossvalidatedCount": 0,
            "productionValidatedCount": 0,
            "validationScope": "not_run",
            "allFactorsProductionValidated": False,
        },
    }
    return {**core, "factorRegistryHash": stable_hash(core, prefix="production_factor_registry")}


def _write_contracts(root: Path) -> tuple[dict, dict, dict]:
    registry = _registry()
    schema = build_feature_schema(registry)
    models = build_observer_model_registry(schema)
    root.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("production_factor_registry.json", registry),
        ("production_feature_schema.json", schema),
        ("model_registry.json", models),
    ):
        (root / name).write_text(json.dumps(payload), encoding="utf-8")
    return registry, schema, models


class AdaptiveLearningRuntimeTests(unittest.TestCase):
    def test_runtime_validates_contracts_and_records_demo_observer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "contracts"
            _, schema, models = _write_contracts(root)
            runtime = AdaptiveLearningRuntime(
                artifact_root=root,
                store_path=Path(directory) / "adaptive.sqlite",
            )
            try:
                result = runtime.demo.observe_scan(
                    {
                        "demoReleaseId": "release-1",
                        "releaseContentHash": "release-hash",
                        "strategyCandidateId": "candidate-1",
                        "riskOverlayHash": "risk-hash",
                        "strategy": {"marketDefinition": {"timeframe": "1h"}},
                    },
                    {
                        "signals": [{
                            "candidateId": "candidate-1",
                            "instId": "BTC-USDT-SWAP",
                            "signalTime": "2026-07-21T00:00:00+00:00",
                            "factorContext": {"factors": {"rsi_14": 55.0}},
                        }],
                    },
                    observed_at="2026-07-21T00:00:01+00:00",
                    source_event_hash="source-hash",
                    universe_snapshot_hash="universe-hash",
                )
                status = runtime.status()
            finally:
                runtime.close()

        self.assertEqual(result["featureSnapshotCount"], 1)
        self.assertEqual(status["modelMode"], "observer")
        self.assertEqual(status["featureSchemaHash"], schema["featureSchemaHash"])
        self.assertEqual(status["modelHash"], models["activeDemoModelHash"])
        self.assertEqual(status["featureSnapshotCount"], 1)
        self.assertFalse(status["altersOrderSemantics"])

    def test_runtime_rejects_tampered_feature_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "contracts"
            _, schema, _ = _write_contracts(root)
            tampered = copy.deepcopy(schema)
            tampered["featureNames"] = []
            (root / "production_feature_schema.json").write_text(
                json.dumps(tampered), encoding="utf-8"
            )

            with self.assertRaisesRegex(RuntimeError, "feature_schema_contract_mismatch"):
                AdaptiveLearningRuntime(
                    artifact_root=root,
                    store_path=Path(directory) / "adaptive.sqlite",
                )


if __name__ == "__main__":
    unittest.main()
