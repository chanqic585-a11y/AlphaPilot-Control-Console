from __future__ import annotations

import json
import unittest

from alphapilot_control_console.ai_orchestration.contracts import AIRequest, ModelIdentity
from alphapilot_control_console.ai_orchestration.provider_adapters.gemini_adapter import GeminiAdapter
from alphapilot_control_console.ai_orchestration.provider_adapters.openai_adapter import OpenAIAdapter


SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
    "additionalProperties": False,
}


class RecordingTransport:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[dict] = []

    def request(self, **kwargs: object) -> dict:
        self.calls.append(dict(kwargs))
        return self.response


def _request() -> AIRequest:
    return AIRequest(
        request_id="request-1",
        task_type="research_summary",
        payload={"evidence": ["artifact-1"]},
        response_schema=SCHEMA,
        sensitivity="internal",
        prompt_version="summary-v1",
        token_ceiling=900,
    )


class ProviderAdapterTests(unittest.TestCase):
    def test_openai_uses_responses_api_stateless_structured_output(self) -> None:
        transport = RecordingTransport(
            {
                "id": "resp-1",
                "output_text": json.dumps({"summary": "ok"}),
                "usage": {"input_tokens": 12, "output_tokens": 4, "total_tokens": 16},
            }
        )
        adapter = OpenAIAdapter(transport=transport, api_key="process-only")
        response = adapter.generate(
            ModelIdentity(
                "openai_reasoning_primary",
                "openai",
                "configured-openai",
                frozenset(),
                input_cost_per_million_usd=2.5,
                output_cost_per_million_usd=15.0,
            ),
            _request(),
        )

        call = transport.calls[0]
        self.assertTrue(str(call["url"]).endswith("/v1/responses"))
        self.assertEqual(call["headers"]["Authorization"], "Bearer process-only")
        self.assertFalse(call["json_body"]["store"])
        self.assertEqual(call["json_body"]["model"], "configured-openai")
        self.assertEqual(call["json_body"]["text"]["format"]["type"], "json_schema")
        self.assertEqual(response.output, {"summary": "ok"})
        self.assertEqual(response.usage.total_tokens, 16)
        self.assertEqual(response.usage.estimated_cost_usd, 0.00009)

    def test_gemini_uses_interactions_api_stateless_structured_output(self) -> None:
        transport = RecordingTransport(
            {
                "id": "int-1",
                "steps": [
                    {
                        "type": "model_output",
                        "status": "done",
                        "content": [{"type": "text", "text": json.dumps({"summary": "ok"})}],
                    }
                ],
                "usage": {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13},
            }
        )
        adapter = GeminiAdapter(transport=transport, api_key="process-only")
        response = adapter.generate(
            ModelIdentity(
                "gemini_reasoning_primary",
                "gemini",
                "configured-gemini",
                frozenset(),
                input_cost_per_million_usd=1.5,
                output_cost_per_million_usd=7.5,
            ),
            _request(),
        )

        call = transport.calls[0]
        self.assertTrue(str(call["url"]).endswith("/v1beta2/interactions"))
        self.assertEqual(call["headers"]["x-goog-api-key"], "process-only")
        self.assertFalse(call["json_body"]["store"])
        self.assertFalse(call["json_body"]["background"])
        self.assertEqual(call["json_body"]["model"], "configured-gemini")
        self.assertEqual(call["json_body"]["response_format"][0]["mime_type"], "application/json")
        self.assertEqual(response.output, {"summary": "ok"})
        self.assertEqual(response.usage.total_tokens, 13)
        self.assertEqual(response.usage.estimated_cost_usd, 0.0000375)


if __name__ == "__main__":
    unittest.main()
