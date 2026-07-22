"""HTTP transport and provider adapter protocols."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Mapping, Protocol

from ..contracts import AIRequest, AIResponse, ModelIdentity
from ..errors import ProviderResponseError, ProviderUnavailableError


class HTTPTransport(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        json_body: Mapping[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]: ...


class ProviderAdapter(Protocol):
    provider: str

    def generate(self, identity: ModelIdentity, request: AIRequest) -> AIResponse: ...


class UrllibJSONTransport:
    """Small dependency-free transport; credentials remain in process memory."""

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        json_body: Mapping[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        body = json.dumps(json_body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={**headers, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            # Provider bodies can echo user content. Do not attach them to the exception.
            raise ProviderResponseError(f"provider returned HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderUnavailableError("provider transport is unavailable") from exc
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderResponseError("provider returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ProviderResponseError("provider returned a non-object response")
        return payload


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        output = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderResponseError("provider output is not valid JSON") from exc
    if not isinstance(output, dict):
        raise ProviderResponseError("provider output must be a JSON object")
    return output


def usage_from_payload(payload: Mapping[str, Any]) -> tuple[int, int, int]:
    usage = payload.get("usage")
    if not isinstance(usage, Mapping):
        return 0, 0, 0
    input_tokens = int(usage.get("input_tokens") or usage.get("inputTokens") or 0)
    output_tokens = int(usage.get("output_tokens") or usage.get("outputTokens") or 0)
    total_tokens = int(usage.get("total_tokens") or usage.get("totalTokens") or 0)
    if not total_tokens:
        total_tokens = input_tokens + output_tokens
    return input_tokens, output_tokens, total_tokens


def estimate_cost_usd(
    identity: ModelIdentity,
    *,
    input_tokens: int,
    output_tokens: int,
) -> float:
    input_cost = input_tokens * identity.input_cost_per_million_usd / 1_000_000
    output_cost = output_tokens * identity.output_cost_per_million_usd / 1_000_000
    return round(input_cost + output_cost, 12)
