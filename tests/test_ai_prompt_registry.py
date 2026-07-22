from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.ai_orchestration.errors import AIOrchestrationError
from alphapilot_control_console.ai_orchestration.prompt_registry import PromptRegistry


class PromptRegistryTests(unittest.TestCase):
    def test_resolves_versioned_prompt_with_content_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "strategy.txt").write_text("Return a falsifiable hypothesis.", encoding="utf-8")
            (root / "registry.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": "alphapilot_prompt_registry_v1",
                        "prompts": {
                            "strategy-hypothesis-v1": {
                                "taskTypes": ["strategy_hypothesis"],
                                "path": "strategy.txt",
                                "enabled": True,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            registry = PromptRegistry.from_path(root / "registry.json")
            prompt = registry.resolve("strategy-hypothesis-v1", "strategy_hypothesis")

        self.assertEqual(prompt.version, "strategy-hypothesis-v1")
        self.assertTrue(prompt.content_hash.startswith("sha256:"))
        self.assertIn("falsifiable", prompt.content)

    def test_prompt_version_cannot_be_reused_for_another_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "strategy.txt").write_text("Research only.", encoding="utf-8")
            (root / "registry.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": "alphapilot_prompt_registry_v1",
                        "prompts": {
                            "strategy-v1": {
                                "taskTypes": ["strategy_hypothesis"],
                                "path": "strategy.txt",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            registry = PromptRegistry.from_path(root / "registry.json")
            with self.assertRaises(AIOrchestrationError):
                registry.resolve("strategy-v1", "failure_attribution")


if __name__ == "__main__":
    unittest.main()
