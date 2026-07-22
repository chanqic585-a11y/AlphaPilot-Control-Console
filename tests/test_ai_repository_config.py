from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from alphapilot_control_console.ai_orchestration.model_registry import AIModelRegistry
from alphapilot_control_console.ai_orchestration.prompt_registry import PromptRegistry


class AIRepositoryConfigTests(unittest.TestCase):
    def test_repository_model_registry_has_all_routing_aliases_without_literal_models(self) -> None:
        root = Path(__file__).parents[1]
        path = root / "config" / "ai_model_registry.json"
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        expected = {
            "openai_reasoning_primary",
            "openai_coding_primary",
            "openai_fast",
            "openai_batch",
            "gemini_reasoning_primary",
            "gemini_multimodal_primary",
            "gemini_fast",
            "gemini_batch",
        }
        self.assertEqual(set(payload["aliases"]), expected)
        self.assertNotIn('"modelId"', raw)
        env = {
            item["modelIdEnv"]: f"configured-{alias}"
            for alias, item in payload["aliases"].items()
        }
        with patch.dict(os.environ, env, clear=False):
            registry = AIModelRegistry.from_path(path)
            for alias in expected:
                self.assertTrue(registry.resolve(alias).model_id.startswith("configured-"))

    def test_repository_prompt_registry_resolves_strategy_and_failure_prompts(self) -> None:
        root = Path(__file__).parents[1]
        registry = PromptRegistry.from_path(root / "config" / "ai_prompt_registry.json")
        strategy = registry.resolve("strategy-hypothesis-v1", "strategy_hypothesis")
        failure = registry.resolve("failure-attribution-v1", "failure_attribution")

        self.assertNotEqual(strategy.content_hash, failure.content_hash)
        self.assertIn("untrusted", strategy.content.lower())
        self.assertIn("one variable", failure.content.lower())


if __name__ == "__main__":
    unittest.main()
