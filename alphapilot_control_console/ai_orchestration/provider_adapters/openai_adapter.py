"""OpenAI Responses adapter with stateless structured output."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from ..contracts import AIRequest, AIResponse, AIUsage, ModelIdentity
from ..errors import ProviderResponseError, ProviderUnavailableError
from .base import HTTPTransport, UrllibJSONTransport, parse_json_object, usage_from_payload


class OpenAIAdapter:
    provider = "openai"

    def __init__(
        self,
        *,
        transport: HTTPTransport | None = None,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com",
        timeout_seconds: float = 90.0,
    ) -> None:
        self._transport = transport or UrllibJSONTransport()
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def _credential(self) -> str:
        credential = str(self._api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
        if not credential:
            raise ProviderUnavailableError("OPENAI_API_KEY is not configured in process memory")
        return credential

    def generate(self, identity: ModelIdentity, request: AIRequest) -> AIResponse:
        if identity.provider != self.provider:
            raise ProviderResponseError("OpenAI adapter received a non-OpenAI identity")
        body = build_openai_response_body(identity, request)
        started = time.perf_counter()
        payload = self._transport.request(
            method="POST",
            url=f"{self._base_url}/v1/responses",
            headers={"Authorization": f"Bearer {self._credential()}"},
            json_body=body,
            timeout_seconds=self._timeout_seconds,
        )
        latency_ms = max(0, int((time.perf_counter() - started) * 1000))
        output_text = payload.get("output_text")
        if not isinstance(output_text, str):
            output_text = _extract_output_text(payload)
        output = parse_json_object(output_text)
        input_tokens, output_tokens, total_tokens = usage_from_payload(payload)
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
            ),
            latency_ms=latency_ms,
            provider_request_id=str(payload.get("id") or ""),
        )


def build_openai_response_body(identity: ModelIdentity, request: AIRequest) -> dict[str, Any]:
    prompt_envelope = {
        "taskType": request.task_type,
        "promptVersion": request.prompt_version,
        "artifactHashes": list(request.artifact_hashes),
        "payload": request.payload,
        "instruction": "Return only a JSON object matching the supplied schema.",
    }
    return {
        "model": identity.model_id,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(
                            prompt_envelope,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    }
                ],
            }
        ],
        "store": False,
        "max_output_tokens": request.token_ceiling,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "alphapilot_output",
                "strict": True,
                "schema": request.response_schema,
            }
        },
    }


def _extract_output_text(payload: dict[str, Any]) -> str:
    for item in payload.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    return text
    raise ProviderResponseError("OpenAI response has no structured output text")
