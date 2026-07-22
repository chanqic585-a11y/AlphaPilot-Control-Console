from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.ai_orchestration.errors import ModelRegistryError
from alphapilot_control_console.ai_orchestration.model_registry import AIModelRegistry


REGISTRY = {
    "schemaVersion": "alphapilot_ai_model_registry_v1",
    "aliases": {
        "openai_reasoning_primary": {
            "provider": "openai",
            "modelId": "configured-model",
            "capabilities": ["reasoning", "structured_output"],
            "batchAlias": "openai_batch",
            "supportsStructuredOutput": True,
            "supportsFunctionCalling": True,
            "supportsFiles": False,
            "supportsImages": False,
            "supportsBatch": False,
            "contextLimit": 100000,
            "latencyTier": "standard",
            "costTier": "high",
            "previewOrStable": "stable",
            "inputUsdPerMillionTokens": 2.5,
            "outputUsdPerMillionTokens": 15.0,
            "enabled": True,
        },
        "openai_batch": {
            "provider": "openai",
            "modelId": "configured-batch-model",
            "capabilities": ["batch", "structured_output"],
        },
    },
}


class AIModelRegistryTests(unittest.TestCase):
    def test_resolves_model_identity_from_versioned_registry_config(self) -> None:
        registry = AIModelRegistry.from_mapping(REGISTRY)
        identity = registry.resolve("openai_reasoning_primary")

        self.assertEqual(identity.alias, "openai_reasoning_primary")
        self.assertEqual(identity.provider, "openai")
        self.assertEqual(identity.model_id, "configured-model")
        self.assertIn("structured_output", identity.capabilities)
        self.assertEqual(identity.input_cost_per_million_usd, 2.5)
        self.assertEqual(identity.output_cost_per_million_usd, 15.0)

    def test_model_environment_indirection_is_blocked(self) -> None:
        unsafe = {
            "schemaVersion": "alphapilot_ai_model_registry_v1",
            "aliases": {
                "openai_reasoning_primary": {
                    "provider": "openai",
                    "modelIdEnv": "EXTRA_MODEL_ENV",
                    "capabilities": ["reasoning"],
                }
            },
        }
        with self.assertRaisesRegex(ModelRegistryError, "modelId"):
            AIModelRegistry.from_mapping(unsafe)

    def test_unknown_alias_is_blocked(self) -> None:
        registry = AIModelRegistry.from_mapping(REGISTRY)
        with self.assertRaisesRegex(ModelRegistryError, "unknown model alias"):
            registry.resolve("not_registered")

    def test_registry_file_rejects_literal_api_credentials(self) -> None:
        unsafe = dict(REGISTRY)
        unsafe["apiKey"] = "must-not-be-here"
        with self.assertRaisesRegex(ModelRegistryError, "credential"):
            AIModelRegistry.from_mapping(unsafe)

    def test_registry_round_trip_uses_versioned_content_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(__import__("json").dumps(REGISTRY), encoding="utf-8")
            first = AIModelRegistry.from_path(path)
            second = AIModelRegistry.from_path(path)

        self.assertEqual(first.registry_hash, second.registry_hash)
        self.assertTrue(first.registry_hash.startswith("sha256:"))

    def test_registry_projection_preserves_routing_capability_metadata(self) -> None:
        registry = AIModelRegistry.from_mapping(REGISTRY)
        item = next(
            entry
            for entry in registry.describe()["aliases"]
            if entry["alias"] == "openai_reasoning_primary"
        )

        self.assertTrue(item["supportsStructuredOutput"])
        self.assertTrue(item["supportsFunctionCalling"])
        self.assertEqual(item["contextLimit"], 100000)
        self.assertEqual(item["latencyTier"], "standard")
        self.assertEqual(item["modelId"], "configured-model")
        self.assertEqual(item["inputUsdPerMillionTokens"], 2.5)
        self.assertTrue(item["configured"])
        self.assertTrue(item["enabled"])


if __name__ == "__main__":
    unittest.main()
