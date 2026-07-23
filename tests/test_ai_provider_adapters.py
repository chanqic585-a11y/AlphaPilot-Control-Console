from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from alphapilot_control_console.ai_orchestration.contracts import AIRequest, ModelIdentity
from alphapilot_control_console.ai_orchestration.errors import (
    ProviderResponseError,
    ProviderUnavailableError,
)
from alphapilot_control_console.ai_orchestration.provider_adapters.deepseek_adapter import (
    DeepSeekAdapter,
)
from alphapilot_control_console.ai_orchestration.provider_adapters.gemini_adapter import GeminiAdapter


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


class DisconnectingTransport:
    def __init__(self) -> None:
        self.calls = 0

    def request(self, **kwargs: object) -> dict:
        self.calls += 1
        raise ProviderUnavailableError("provider transport is unavailable")


def _request(*, tool_names: tuple[str, ...] = ()) -> AIRequest:
    return AIRequest(
        request_id="request-1",
        task_type="research_summary",
        payload={"evidence": ["artifact-1"]},
        response_schema=SCHEMA,
        sensitivity="internal",
        prompt_version="summary-v1",
        token_ceiling=900,
        tool_names=tool_names,
    )


class ProviderAdapterTests(unittest.TestCase):
    def test_deepseek_uses_chat_completions_json_mode(self) -> None:
        transport = RecordingTransport(
            {
                "id": "chatcmpl-1",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"summary": "ok"}),
                            "reasoning_content": "must not be persisted or parsed",
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "read_market_summary",
                                        "arguments": json.dumps({"symbol": "BTC-USDT"}),
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
            }
        )
        adapter = DeepSeekAdapter(transport=transport, api_key="process-only")
        response = adapter.generate(
            ModelIdentity(
                "deepseek_reasoning_primary",
                "deepseek",
                "deepseek-v4-pro",
                frozenset(),
                input_cost_per_million_usd=0.435,
                output_cost_per_million_usd=0.87,
            ),
            _request(tool_names=("read_market_summary",)),
        )

        call = transport.calls[0]
        self.assertEqual(call["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(call["headers"]["Authorization"], "Bearer process-only")
        self.assertEqual(call["json_body"]["model"], "deepseek-v4-pro")
        self.assertEqual(call["json_body"]["max_tokens"], 900)
        self.assertEqual(call["json_body"]["response_format"], {"type": "json_object"})
        prompt = call["json_body"]["messages"][0]["content"]
        self.assertIn("JSON", prompt)
        self.assertIn(json.dumps(SCHEMA, sort_keys=True, separators=(",", ":")), prompt)
        self.assertEqual(response.output, {"summary": "ok"})
        self.assertEqual(response.provider, "deepseek")
        self.assertEqual(response.usage.total_tokens, 16)
        self.assertEqual(response.usage.estimated_cost_usd, 0.0000087)
        self.assertEqual(response.provider_request_id, "chatcmpl-1")
        self.assertEqual(response.reasoning_content, "must not be persisted or parsed")
        self.assertEqual(len(response.tool_calls), 1)
        self.assertEqual(response.tool_calls[0].name, "read_market_summary")
        self.assertEqual(response.tool_calls[0].arguments, {"symbol": "BTC-USDT"})

    def test_deepseek_requires_process_only_credential_before_transport(self) -> None:
        transport = RecordingTransport({})
        adapter = DeepSeekAdapter(transport=transport)
        identity = ModelIdentity(
            "deepseek_fast",
            "deepseek",
            "deepseek-v4-flash",
            frozenset(),
        )

        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ProviderUnavailableError, "DEEPSEEK_API_KEY"):
                adapter.generate(identity, _request())

        self.assertEqual(transport.calls, [])

    def test_deepseek_rejects_another_provider_identity(self) -> None:
        adapter = DeepSeekAdapter(transport=RecordingTransport({}), api_key="process-only")

        with self.assertRaisesRegex(ProviderResponseError, "another provider"):
            adapter.generate(
                ModelIdentity("gemini_fast", "gemini", "gemini-configured", frozenset()),
                _request(),
            )

    def test_deepseek_fails_closed_without_final_message_content(self) -> None:
        adapter = DeepSeekAdapter(
            transport=RecordingTransport(
                {
                    "id": "chatcmpl-empty",
                    "choices": [{"message": {"reasoning_content": "internal only"}}],
                    "usage": {},
                }
            ),
            api_key="process-only",
        )

        with self.assertRaisesRegex(ProviderResponseError, "final JSON content"):
            adapter.generate(
                ModelIdentity(
                    "deepseek_reasoning_primary",
                    "deepseek",
                    "deepseek-v4-pro",
                    frozenset(),
                ),
                _request(),
            )

    def test_deepseek_rejects_unrequested_or_forbidden_tool_call(self) -> None:
        adapter = DeepSeekAdapter(
            transport=RecordingTransport(
                {
                    "id": "chatcmpl-forbidden-tool",
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps({"summary": "ok"}),
                                "reasoning_content": "",
                                "tool_calls": [
                                    {
                                        "id": "call-order",
                                        "type": "function",
                                        "function": {
                                            "name": "place_order",
                                            "arguments": "{}",
                                        },
                                    }
                                ],
                            }
                        }
                    ],
                    "usage": {},
                }
            ),
            api_key="process-only",
        )

        with self.assertRaisesRegex(ProviderResponseError, "tool call is not allowed"):
            adapter.generate(
                ModelIdentity(
                    "deepseek_reasoning_primary",
                    "deepseek",
                    "deepseek-v4-pro",
                    frozenset(),
                ),
                _request(tool_names=("place_order",)),
            )

    def test_deepseek_disconnect_fails_without_partial_response(self) -> None:
        transport = DisconnectingTransport()
        adapter = DeepSeekAdapter(transport=transport, api_key="process-only")

        with self.assertRaisesRegex(ProviderUnavailableError, "transport is unavailable"):
            adapter.generate(
                ModelIdentity(
                    "deepseek_reasoning_primary",
                    "deepseek",
                    "deepseek-v4-pro",
                    frozenset(),
                ),
                _request(),
            )

        self.assertEqual(transport.calls, 1)

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
                "usage": {
                    "total_input_tokens": 10,
                    "total_output_tokens": 3,
                    "total_tokens": 13,
                },
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
        self.assertTrue(str(call["url"]).endswith("/v1beta/interactions"))
        self.assertEqual(call["headers"]["x-goog-api-key"], "process-only")
        self.assertEqual(call["headers"]["Api-Revision"], "2026-05-20")
        self.assertFalse(call["json_body"]["store"])
        self.assertFalse(call["json_body"]["background"])
        self.assertEqual(call["json_body"]["model"], "configured-gemini")
        self.assertEqual(call["json_body"]["response_format"]["mime_type"], "application/json")
        self.assertEqual(response.output, {"summary": "ok"})
        self.assertEqual(response.usage.input_tokens, 10)
        self.assertEqual(response.usage.output_tokens, 3)
        self.assertEqual(response.usage.total_tokens, 13)
        self.assertEqual(response.usage.estimated_cost_usd, 0.0000375)


if __name__ == "__main__":
    unittest.main()
