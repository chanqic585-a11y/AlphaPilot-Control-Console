from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.ai_control_projection import build_ai_control_projection


class AIControlProjectionTests(unittest.TestCase):
    def test_projects_registry_queue_budget_and_provider_health_without_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config" / "ai_model_registry.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": "alphapilot_ai_model_registry_v1",
                        "models": {
                            "deepseek_fast": {
                                "provider": "deepseek",
                                "modelId": "deepseek-v4-flash",
                                "enabled": True,
                                "capabilities": ["fast"],
                            },
                            "gemini_fast": {
                                "provider": "gemini",
                                "modelId": "gemini-test",
                                "enabled": True,
                                "capabilities": ["fast"],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "config" / "ai_prompt_registry.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": "alphapilot_prompt_registry_v1",
                        "prompts": {"strategy-hypothesis-v1": {"enabled": True}},
                    }
                ),
                encoding="utf-8",
            )
            (root / "config" / "ai_budget_policy.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": "alphapilot_ai_budget_policy_v1",
                        "defaultCampaignLimitUsd": 2.5,
                        "dailyProviderLimitsUsd": {"deepseek": 5, "gemini": 5},
                    }
                ),
                encoding="utf-8",
            )

            projection = build_ai_control_projection(
                repository_root=root,
                data_root=root / "data",
                environment={},
            )

        self.assertEqual(projection["status"], "provider_credentials_required")
        self.assertEqual(projection["providerHealth"]["deepseek"], "credentials_missing")
        self.assertEqual(projection["providerHealth"]["gemini"], "credentials_missing")
        self.assertEqual(projection["modelCount"], 2)
        self.assertEqual(projection["queue"]["status"], "empty")
        self.assertNotIn("apiKey", json.dumps(projection))
        self.assertFalse(projection["executionAuthorized"])


if __name__ == "__main__":
    unittest.main()
