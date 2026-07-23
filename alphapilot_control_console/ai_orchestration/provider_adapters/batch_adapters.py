"""Provider Batch adapters; no provider SDK is imported by AlphaPilot business code."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Mapping, Protocol, Sequence

from ..batch_service import BatchProviderStatus, BatchSubmission
from ..contracts import AIRequest, ModelIdentity
from ..errors import ProviderResponseError, ProviderUnavailableError
from .base import parse_json_object


class BatchHTTPTransport(Protocol):
    def request_json(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        json_body: Mapping[str, Any] | None,
        timeout_seconds: float,
    ) -> dict[str, Any]: ...

class UrllibBatchTransport:
    def _open(self, request: urllib.request.Request, timeout_seconds: float) -> bytes:
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise ProviderResponseError(f"provider Batch returned HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderUnavailableError("provider Batch transport is unavailable") from exc

    def request_json(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        json_body: Mapping[str, Any] | None,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        data = None
        request_headers = dict(headers)
        if json_body is not None:
            data = json.dumps(json_body, separators=(",", ":")).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, method=method, headers=request_headers)
        raw = self._open(request, timeout_seconds).decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderResponseError("provider Batch returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ProviderResponseError("provider Batch returned a non-object response")
        return payload

class GeminiBatchAdapter:
    provider = "gemini"

    def __init__(
        self,
        *,
        transport: BatchHTTPTransport | None = None,
        api_key: str | None = None,
        base_url: str = "https://generativelanguage.googleapis.com",
        timeout_seconds: float = 90.0,
    ) -> None:
        self._transport = transport or UrllibBatchTransport()
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        credential = str(self._api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
        if not credential:
            raise ProviderUnavailableError("GEMINI_API_KEY is not configured in process memory")
        return {"x-goog-api-key": credential}

    def submit(
        self,
        identity: ModelIdentity,
        requests: Sequence[AIRequest],
        *,
        payload_hash: str,
    ) -> BatchSubmission:
        if identity.provider != self.provider:
            raise ProviderResponseError("Gemini Batch adapter received another provider")
        inline_requests = [
            {
                "request": _gemini_generate_content_request(request),
                "metadata": {"key": request.request_id},
            }
            for request in requests
        ]
        created = self._transport.request_json(
            method="POST",
            url=f"{self._base_url}/v1beta/models/{identity.model_id}:batchGenerateContent",
            headers=self._headers(),
            json_body={
                "batch": {
                    "display_name": f"alphapilot-{payload_hash[-12:]}",
                    "input_config": {"requests": {"requests": inline_requests}},
                }
            },
            timeout_seconds=self._timeout_seconds,
        )
        provider_job_id = str(created.get("name") or "")
        if not provider_job_id:
            raise ProviderResponseError("Gemini Batch returned no job identity")
        return BatchSubmission(provider_job_id, _normalize_gemini_state(created.get("state")))

    def get_status(self, provider_job_id: str) -> BatchProviderStatus:
        payload = self._transport.request_json(
            method="GET",
            url=f"{self._base_url}/v1beta/{provider_job_id.lstrip('/')}",
            headers=self._headers(),
            json_body=None,
            timeout_seconds=self._timeout_seconds,
        )
        state = _normalize_gemini_state(payload.get("state"))
        outputs = _parse_gemini_inline_outputs(payload) if state == "completed" else {}
        stats = payload.get("batchStats") or payload.get("batch_stats") or {}
        return BatchProviderStatus(
            provider_job_id=provider_job_id,
            status=state,
            outputs=outputs,
            total_count=int(stats.get("requestCount") or stats.get("request_count") or 0),
            completed_count=int(
                stats.get("successfulRequestCount") or stats.get("successful_request_count") or 0
            ),
            failed_count=int(
                stats.get("failedRequestCount") or stats.get("failed_request_count") or 0
            ),
        )


def _gemini_generate_content_request(request: AIRequest) -> dict[str, Any]:
    text = json.dumps(
        {
            "taskType": request.task_type,
            "promptVersion": request.prompt_version,
            "artifactHashes": list(request.artifact_hashes),
            "payload": request.payload,
            "instruction": "Return only a JSON object matching the supplied schema.",
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generation_config": {
            "max_output_tokens": request.token_ceiling,
            "response_mime_type": "application/json",
            "response_json_schema": request.response_schema,
        },
    }


def _normalize_gemini_state(value: object) -> str:
    state = str(value or "unknown").upper()
    if state == "JOB_STATE_SUCCEEDED":
        return "completed"
    if state in {"JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}:
        return "failed"
    return state.lower()


def _parse_gemini_inline_outputs(payload: Mapping[str, Any]) -> dict[str, Mapping[str, object]]:
    dest = payload.get("dest") or {}
    responses = dest.get("inlinedResponses") or dest.get("inlined_responses") or []
    outputs: dict[str, Mapping[str, object]] = {}
    for item in responses:
        metadata = item.get("metadata") or {}
        key = str(metadata.get("key") or item.get("key") or "")
        response = item.get("response") or {}
        candidates = response.get("candidates") or []
        if not key or not candidates:
            raise ProviderResponseError("Gemini Batch contains an unkeyed or failed response")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = next((part.get("text") for part in parts if isinstance(part.get("text"), str)), None)
        if text is None:
            raise ProviderResponseError("Gemini Batch response has no text output")
        outputs[key] = parse_json_object(text)
    return outputs
