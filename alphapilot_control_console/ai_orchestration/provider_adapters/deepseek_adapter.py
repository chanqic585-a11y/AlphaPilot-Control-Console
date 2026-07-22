"""DeepSeek Chat Completions adapter with stateless JSON output."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from typing import Any

from ..contracts import AIProviderToolCall, AIRequest, AIResponse, AIUsage, ModelIdentity
from ..errors import ProviderResponseError, ProviderUnavailableError
from ..task_router import RESEARCH_TOOL_ALLOWLIST
from .base import HTTPTransport, UrllibJSONTransport, estimate_cost_usd, parse_json_object


class DeepSeekAdapter:
    provider = "deepseek"

    def __init__(
        self,
        *,
        transport: HTTPTransport | None = None,
        api_key: str | None = None,
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 90.0,
    ) -> None:
        self._transport = transport or UrllibJSONTransport()
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def _credential(self) -> str:
        credential = str(self._api_key or os.environ.get("DEEPSEEK_API_KEY") or "").strip()
        if not credential:
            raise ProviderUnavailableError("DEEPSEEK_API_KEY is not configured in process memory")
        return credential

    def generate(self, identity: ModelIdentity, request: AIRequest) -> AIResponse:
        if identity.provider != self.provider:
            raise ProviderResponseError("DeepSeek adapter received another provider identity")
        credential = self._credential()
        started = time.perf_counter()
        payload = self._transport.request(
            method="POST",
            url=f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {credential}"},
            json_body=build_deepseek_chat_body(identity, request),
            timeout_seconds=self._timeout_seconds,
        )
        latency_ms = max(0, int((time.perf_counter() - started) * 1000))
        message = _extract_message(payload)
        output = parse_json_object(_extract_final_content(message))
        input_tokens, output_tokens, total_tokens = _usage_from_deepseek(payload)
        return AIResponse(
            request_id=request.request_id,
            provider=self.provider,
            model_alias=identity.alias,
            model_id=identity.model_id,
            output=output,
            usage=AIUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimate_cost_usd(
                    identity,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                ),
            ),
            latency_ms=latency_ms,
            provider_request_id=str(payload.get("id") or ""),
            reasoning_content=_extract_reasoning_content(message),
            tool_calls=_extract_tool_calls(message, request),
        )


def build_deepseek_chat_body(identity: ModelIdentity, request: AIRequest) -> dict[str, Any]:
    prompt_envelope = {
        "taskType": request.task_type,
        "promptVersion": request.prompt_version,
        "artifactHashes": list(request.artifact_hashes),
        "payload": request.payload,
        "responseSchema": request.response_schema,
        "instruction": "Return only a valid JSON object matching responseSchema.",
    }
    body: dict[str, Any] = {
        "model": identity.model_id,
        "messages": [
            {
                "role": "user",
                "content": json.dumps(
                    prompt_envelope,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": request.token_ceiling,
        "stream": False,
    }
    if request.tool_names:
        body["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": "Read-only AlphaPilot research tool.",
                    "parameters": {"type": "object", "additionalProperties": True},
                },
            }
            for name in request.tool_names
            if name in RESEARCH_TOOL_ALLOWLIST
        ]
    return body


def _extract_message(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0]
        if isinstance(choice, Mapping):
            message = choice.get("message")
            if isinstance(message, Mapping):
                return message
    raise ProviderResponseError("DeepSeek response has no final JSON content")


def _extract_final_content(message: Mapping[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    raise ProviderResponseError("DeepSeek response has no final JSON content")


def _extract_reasoning_content(message: Mapping[str, Any]) -> str:
    reasoning = message.get("reasoning_content")
    if reasoning is None:
        return ""
    if not isinstance(reasoning, str):
        raise ProviderResponseError("DeepSeek reasoning_content must be text")
    return reasoning


def _extract_tool_calls(
    message: Mapping[str, Any], request: AIRequest
) -> tuple[AIProviderToolCall, ...]:
    raw_calls = message.get("tool_calls")
    if raw_calls is None:
        return ()
    if not isinstance(raw_calls, list):
        raise ProviderResponseError("DeepSeek tool_calls must be a list")
    requested = frozenset(request.tool_names)
    parsed: list[AIProviderToolCall] = []
    for raw_call in raw_calls:
        if not isinstance(raw_call, Mapping) or raw_call.get("type") != "function":
            raise ProviderResponseError("DeepSeek tool call is malformed")
        function = raw_call.get("function")
        if not isinstance(function, Mapping):
            raise ProviderResponseError("DeepSeek tool call is malformed")
        call_id = str(raw_call.get("id") or "").strip()
        name = str(function.get("name") or "").strip()
        if not call_id or name not in RESEARCH_TOOL_ALLOWLIST or name not in requested:
            raise ProviderResponseError("DeepSeek tool call is not allowed")
        raw_arguments = function.get("arguments")
        if not isinstance(raw_arguments, str):
            raise ProviderResponseError("DeepSeek tool arguments must be JSON text")
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            raise ProviderResponseError("DeepSeek tool arguments are invalid JSON") from exc
        if not isinstance(arguments, dict):
            raise ProviderResponseError("DeepSeek tool arguments must be a JSON object")
        parsed.append(AIProviderToolCall(call_id=call_id, name=name, arguments=arguments))
    return tuple(parsed)


def _usage_from_deepseek(payload: Mapping[str, Any]) -> tuple[int, int, int]:
    usage = payload.get("usage")
    if not isinstance(usage, Mapping):
        return 0, 0, 0
    input_tokens = int(usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
    return input_tokens, output_tokens, total_tokens
