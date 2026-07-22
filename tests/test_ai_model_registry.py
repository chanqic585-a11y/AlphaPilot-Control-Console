from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alphapilot_control_console.ai_orchestration.errors import ModelRegistryError
from alphapilot_control_console.ai_orchestration.model_registry import AIModelRegistry


REGISTRY = {
    "schemaVersion": "alphapilot_ai_model_registry_v1",
    "aliases": {
        "openai_reasoning_primary": {
            "provider": "openai",
            "modelIdEnv": "TEST_OPENAI_REASONING_MODEL",
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
            "enabled": True,
        },
        "openai_batch": {
            "provider": "openai",
            "modelIdEnv": "TEST_OPENAI_BATCH_MODEL",
            "capabilities": ["batch", "structured_output"],
        },
    },
}


class AIModelRegistryTests(unittest.TestCase):
    def test_resolves_model_identity_from_environment_without_code_default(self) -> None:
        with patch.dict(os.environ, {"TEST_OPENAI_REASONING_MODEL": "configured-model"}, clear=False):
            registry = AIModelRegistry.from_mapping(REGISTRY)
            identity = registry.resolve("openai_reasoning_primary")

        self.assertEqual(identity.alias, "openai_reasoning_primary")
        self.assertEqual(identity.provider, "openai")
        self.assertEqual(identity.model_id, "configured-model")
        self.assertIn("structured_output", identity.capabilities)

    def test_missing_model_environment_is_blocked(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            registry = AIModelRegistry.from_mapping(REGISTRY)
            with self.assertRaisesRegex(ModelRegistryError, "TEST_OPENAI_REASONING_MODEL"):
                registry.resolve("openai_reasoning_primary")

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
        self.assertTrue(item["enabled"])


if __name__ == "__main__":
    unittest.main()
