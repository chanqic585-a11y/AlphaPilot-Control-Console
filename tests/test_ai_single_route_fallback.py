from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alphapilot_control_console.ai_orchestration.audit import AIAuditLedger
from alphapilot_control_console.ai_orchestration.contracts import AIRequest, AIResponse, AIUsage
from alphapilot_control_console.ai_orchestration.errors import ProviderUnavailableError
from alphapilot_control_console.ai_orchestration.model_registry import AIModelRegistry
from alphapilot_control_console.ai_orchestration.prompt_registry import PromptRegistry
from alphapilot_control_console.ai_orchestration.service import AIOrchestrationService


class _Adapter:
    def __init__(self, provider: str, *, fail: bool = False) -> None:
        self.provider = provider
        self.fail = fail
        self.calls = 0

    def generate(self, identity, request):
        self.calls += 1
        if self.fail:
            raise ProviderUnavailableError(f"{self.provider} unavailable")
        return AIResponse(
            request_id=request.request_id,
            provider=self.provider,
            model_alias=identity.alias,
            model_id=identity.model_id,
            output={"summary": "validated research summary"},
            usage=AIUsage(input_tokens=3, output_tokens=2, total_tokens=5),
            latency_ms=1,
        )


class SingleRouteFallbackTests(unittest.TestCase):
    def test_noncritical_single_route_falls_back_to_gemini(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "TEST_OPENAI_FAST_MODEL": "openai-fast-configured",
                "TEST_GEMINI_FAST_MODEL": "gemini-fast-configured",
            },
        ):
            root = Path(directory)
            prompt = root / "research-summary-v1.txt"
            prompt.write_text("Summarize research evidence only.", encoding="utf-8")
            prompt_registry_path = root / "prompt-registry.json"
            prompt_registry_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": "alphapilot_prompt_registry_v1",
                        "prompts": {
                            "research-summary-v1": {
                                "taskTypes": ["research_summary"],
                                "path": prompt.name,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            model_registry = AIModelRegistry.from_mapping(
                {
                    "schemaVersion": "alphapilot_ai_model_registry_v1",
                    "aliases": {
                        "openai_fast": {
                            "provider": "openai",
                            "modelId": "openai-fast-configured",
                            "capabilities": ["fast", "structured_output"],
                        },
                        "gemini_fast": {
                            "provider": "gemini",
                            "modelId": "gemini-fast-configured",
                            "capabilities": ["fast", "structured_output"],
                        },
                    },
                }
            )
            openai = _Adapter("openai", fail=True)
            gemini = _Adapter("gemini")
            ledger = AIAuditLedger(root / "audit.sqlite")
            service = AIOrchestrationService(
                model_registry=model_registry,
                prompt_registry=PromptRegistry.from_path(prompt_registry_path),
                adapters={"openai": openai, "gemini": gemini},
                audit_ledger=ledger,
            )
            try:
                result = service.execute(
                    AIRequest(
                        request_id="summary-1",
                        task_type="research_summary",
                        payload={"facts": ["measured"]},
                        response_schema={
                            "type": "object",
                            "properties": {"summary": {"type": "string"}},
                            "required": ["summary"],
                            "additionalProperties": False,
                        },
                        sensitivity="internal",
                        prompt_version="research-summary-v1",
                    )
                )
                projection = ledger.projection()
            finally:
                ledger.close()

        self.assertEqual(result.status, "accepted")
        self.assertEqual(openai.calls, 1)
        self.assertEqual(gemini.calls, 1)
        self.assertEqual(projection["statusCounts"], {"accepted": 1})
        self.assertEqual(projection["events"][0]["routeMode"], "single_fallback")
        self.assertEqual(projection["events"][0]["modelAliases"], ["gemini_fast"])


if __name__ == "__main__":
    unittest.main()
