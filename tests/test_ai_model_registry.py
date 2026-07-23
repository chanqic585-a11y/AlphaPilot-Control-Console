from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.ai_orchestration.errors import ModelRegistryError
from alphapilot_control_console.ai_orchestration.model_registry import AIModelRegistry


REGISTRY = {
    "schemaVersion": "alphapilot_ai_model_registry_v1",
    "aliases": {
        "deepseek_reasoning_primary": {
            "provider": "deepseek",
            "modelId": "configured-model",
            "capabilities": ["reasoning", "structured_output"],
            "supportsStructuredOutput": True,
            "supportsFunctionCalling": True,
            "supportsFiles": False,
            "supportsImages": False,
            "supportsBatch": False,
            "contextLimit": 100000,
            "latencyTier": "standard",
            "costTier": "high",
            "previewOrStable": "stable",
            "inputUsdPerMillionTokens": 0.435,
            "outputUsdPerMillionTokens": 0.87,
            "enabled": True,
        },
    },
}


class AIModelRegistryTests(unittest.TestCase):
    def test_resolves_model_identity_from_versioned_registry_config(self) -> None:
        registry = AIModelRegistry.from_mapping(REGISTRY)
        identity = registry.resolve("deepseek_reasoning_primary")

        self.assertEqual(identity.alias, "deepseek_reasoning_primary")
        self.assertEqual(identity.provider, "deepseek")
        self.assertEqual(identity.model_id, "configured-model")
        self.assertIn("structured_output", identity.capabilities)
        self.assertEqual(identity.input_cost_per_million_usd, 0.435)
        self.assertEqual(identity.output_cost_per_million_usd, 0.87)

    def test_model_environment_indirection_is_blocked(self) -> None:
        unsafe = {
            "schemaVersion": "alphapilot_ai_model_registry_v1",
            "aliases": {
                "deepseek_reasoning_primary": {
                    "provider": "deepseek",
                    "modelIdEnv": "EXTRA_MODEL_ENV",
                    "capabilities": ["reasoning"],
                }
            },
        }
        with self.assertRaisesRegex(ModelRegistryError, "modelId"):
            AIModelRegistry.from_mapping(unsafe)

    def test_openai_provider_is_no_longer_active(self) -> None:
        unsafe = {
            "schemaVersion": "alphapilot_ai_model_registry_v1",
            "aliases": {
                "legacy_openai": {
                    "provider": "openai",
                    "modelId": "legacy-model",
                    "capabilities": ["reasoning"],
                }
            },
        }

        with self.assertRaisesRegex(ModelRegistryError, "unsupported provider"):
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
            if entry["alias"] == "deepseek_reasoning_primary"
        )

        self.assertTrue(item["supportsStructuredOutput"])
        self.assertTrue(item["supportsFunctionCalling"])
        self.assertEqual(item["contextLimit"], 100000)
        self.assertEqual(item["latencyTier"], "standard")
        self.assertEqual(item["modelId"], "configured-model")
        self.assertEqual(item["inputUsdPerMillionTokens"], 0.435)
        self.assertTrue(item["configured"])
        self.assertTrue(item["enabled"])


if __name__ == "__main__":
    unittest.main()
