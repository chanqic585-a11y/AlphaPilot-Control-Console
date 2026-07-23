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
            smoke_path = root / "provider_smoke_summary.json"
            smoke_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": "alphapilot_v62_4_provider_smoke_summary_v1",
                        "status": "provider_smoke_passed",
                        "providerSmokeInputHash": "sha256:fixed-redacted-input",
                        "checks": [
                            {
                                "taskType": "provider_smoke_deepseek",
                                "routeMode": "single",
                                "status": "accepted",
                                "executionAuthorized": False,
                            },
                            {
                                "taskType": "provider_smoke_gemini",
                                "routeMode": "single",
                                "status": "accepted",
                                "executionAuthorized": False,
                            },
                            {
                                "taskType": "provider_smoke_dual",
                                "routeMode": "dual",
                                "status": "accepted",
                                "executionAuthorized": False,
                            },
                        ],
                        "credentialsPersisted": False,
                        "sourceHash": "sha256:smoke",
                    }
                ),
                encoding="utf-8",
            )

            projection = build_ai_control_projection(
                repository_root=root,
                data_root=root / "data",
                environment={},
                provider_smoke_status_path=smoke_path,
            )

        self.assertEqual(projection["status"], "provider_credentials_required")
        self.assertEqual(projection["providerHealth"]["deepseek"], "credentials_missing")
        self.assertEqual(projection["providerHealth"]["gemini"], "credentials_missing")
        self.assertEqual(projection["modelCount"], 2)
        self.assertEqual(projection["queue"]["status"], "empty")
        self.assertNotIn("apiKey", json.dumps(projection))
        self.assertFalse(projection["executionAuthorized"])
        self.assertEqual(
            projection["currentCredentialState"]["status"],
            "provider_credentials_required",
        )
        self.assertEqual(
            projection["historicalProviderSmoke"]["status"],
            "provider_smoke_passed",
        )
        self.assertEqual(
            projection["historicalProviderSmoke"]["acceptedTaskTypes"],
            [
                "provider_smoke_deepseek",
                "provider_smoke_gemini",
                "provider_smoke_dual",
            ],
        )
        self.assertFalse(projection["historicalProviderSmoke"]["executionAuthorized"])
        self.assertFalse(projection["historicalProviderSmoke"]["credentialsPersisted"])


if __name__ == "__main__":
    unittest.main()
