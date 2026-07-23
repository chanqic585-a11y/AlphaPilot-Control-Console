"""Gemini Interactions adapter with stateless structured output."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from ..contracts import AIRequest, AIResponse, AIUsage, ModelIdentity
from ..errors import ProviderResponseError, ProviderUnavailableError
from .base import (
    HTTPTransport,
    UrllibJSONTransport,
    estimate_cost_usd,
    parse_json_object,
    usage_from_payload,
)


class GeminiAdapter:
    provider = "gemini"

    def __init__(
        self,
        *,
        transport: HTTPTransport | None = None,
        api_key: str | None = None,
        base_url: str = "https://generativelanguage.googleapis.com",
        timeout_seconds: float = 90.0,
    ) -> None:
        self._transport = transport or UrllibJSONTransport()
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def _credential(self) -> str:
        credential = str(self._api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
        if not credential:
            raise ProviderUnavailableError("GEMINI_API_KEY is not configured in process memory")
        return credential

    def generate(self, identity: ModelIdentity, request: AIRequest) -> AIResponse:
        if identity.provider != self.provider:
            raise ProviderResponseError("Gemini adapter received a non-Gemini identity")
        body = build_gemini_interaction_body(identity, request)
        started = time.perf_counter()
        payload = self._transport.request(
            method="POST",
            url=f"{self._base_url}/v1beta/interactions",
            headers={
                "x-goog-api-key": self._credential(),
                "Api-Revision": "2026-05-20",
            },
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
                estimated_cost_usd=estimate_cost_usd(
                    identity,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                ),
            ),
            latency_ms=latency_ms,
            provider_request_id=str(payload.get("id") or ""),
        )


def build_gemini_interaction_body(identity: ModelIdentity, request: AIRequest) -> dict[str, Any]:
    prompt_envelope = {
        "taskType": request.task_type,
        "promptVersion": request.prompt_version,
        "artifactHashes": list(request.artifact_hashes),
        "payload": request.payload,
        "instruction": "Return only a JSON object matching the supplied schema.",
    }
    return {
        "model": identity.model_id,
        "input": json.dumps(
            prompt_envelope,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        "store": False,
        "background": False,
        "generation_config": {"max_output_tokens": request.token_ceiling},
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": request.response_schema,
        },
    }


def _extract_output_text(payload: dict[str, Any]) -> str:
    for step in payload.get("steps") or []:
        if not isinstance(step, dict) or step.get("type") != "model_output":
            continue
        for content in step.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "text":
                text = content.get("text")
                if isinstance(text, str):
                    return text
    raise ProviderResponseError("Gemini interaction has no structured output text")
