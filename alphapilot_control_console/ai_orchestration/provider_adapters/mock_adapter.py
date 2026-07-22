"""Deterministic local adapter for credential-free orchestration tests."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from ..contracts import AIRequest, AIResponse, AIUsage, ModelIdentity
from ..errors import ProviderResponseError


class MockProviderAdapter:
    def __init__(
        self,
        *,
        provider: str,
        output: Mapping[str, Any],
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        normalized = provider.strip().lower()
        if normalized not in {"openai", "gemini"}:
            raise ValueError("mock provider must be openai or gemini")
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("mock token counts cannot be negative")
        self.provider = normalized
        self._output = copy.deepcopy(dict(output))
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self.requests: list[AIRequest] = []

    def generate(self, identity: ModelIdentity, request: AIRequest) -> AIResponse:
        if identity.provider != self.provider:
            raise ProviderResponseError(
                f"mock {self.provider} adapter received a {identity.provider} identity"
            )
        self.requests.append(request)
        return AIResponse(
            request_id=request.request_id,
            provider=self.provider,
            model_alias=identity.alias,
            model_id=identity.model_id,
            output=copy.deepcopy(self._output),
            usage=AIUsage(
                input_tokens=self._input_tokens,
                output_tokens=self._output_tokens,
                total_tokens=self._input_tokens + self._output_tokens,
                estimated_cost_usd=0.0,
            ),
            latency_ms=0,
            provider_request_id=f"mock:{request.request_id}",
        )
