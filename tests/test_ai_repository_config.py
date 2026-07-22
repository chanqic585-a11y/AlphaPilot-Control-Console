from __future__ import annotations

import json
import unittest
from pathlib import Path

from alphapilot_control_console.ai_orchestration.model_registry import AIModelRegistry
from alphapilot_control_console.ai_orchestration.prompt_registry import PromptRegistry


class AIRepositoryConfigTests(unittest.TestCase):
    def test_repository_model_registry_has_all_routing_aliases_with_versioned_model_ids(self) -> None:
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
        self.assertNotIn('"modelIdEnv"', raw)
        registry = AIModelRegistry.from_path(path)
        for alias in expected:
            identity = registry.resolve(alias)
            self.assertTrue(identity.model_id)
            self.assertGreater(identity.input_cost_per_million_usd, 0.0)
            self.assertGreater(identity.output_cost_per_million_usd, 0.0)

    def test_repository_prompt_registry_resolves_strategy_and_failure_prompts(self) -> None:
        root = Path(__file__).parents[1]
        registry = PromptRegistry.from_path(root / "config" / "ai_prompt_registry.json")
        strategy = registry.resolve("strategy-hypothesis-v1", "strategy_hypothesis")
        failure = registry.resolve("failure-attribution-v1", "failure_attribution")

        self.assertNotEqual(strategy.content_hash, failure.content_hash)
        self.assertIn("untrusted", strategy.content.lower())
        self.assertIn("one variable", failure.content.lower())

    def test_repository_budget_policy_has_bounded_provider_smoke_limits(self) -> None:
        root = Path(__file__).parents[1]
        payload = json.loads(
            (root / "config" / "ai_budget_policy.json").read_text(encoding="utf-8")
        )

        self.assertEqual(payload["providerSmokeLimits"]["maximumTokens"], 512)
        self.assertEqual(payload["providerSmokeLimits"]["maximumCostUsd"], 0.05)


if __name__ == "__main__":
    unittest.main()
