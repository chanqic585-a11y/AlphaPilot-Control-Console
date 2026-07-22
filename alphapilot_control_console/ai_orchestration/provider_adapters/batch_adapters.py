"""Provider Batch adapters; no provider SDK is imported by AlphaPilot business code."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any, Mapping, Protocol, Sequence

from ..batch_service import BatchProviderStatus, BatchSubmission
from ..contracts import AIRequest, ModelIdentity
from ..errors import ProviderResponseError, ProviderUnavailableError
from .base import parse_json_object
from .openai_adapter import build_openai_response_body


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

    def upload_jsonl(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        content: str,
        filename: str,
        timeout_seconds: float,
    ) -> dict[str, Any]: ...

    def download_text(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> str: ...


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

    def upload_jsonl(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        content: str,
        filename: str,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        boundary = "alphapilot-" + uuid.uuid4().hex
        chunks = [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"purpose\"\r\n\r\nbatch\r\n",
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                f"filename=\"{filename}\"\r\nContent-Type: application/jsonl\r\n\r\n"
            ),
            content,
            f"\r\n--{boundary}--\r\n",
        ]
        request = urllib.request.Request(
            url,
            data="".join(chunks).encode("utf-8"),
            method="POST",
            headers={**headers, "Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        raw = self._open(request, timeout_seconds).decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderResponseError("provider file upload returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ProviderResponseError("provider file upload returned a non-object response")
        return payload

    def download_text(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> str:
        request = urllib.request.Request(url, method="GET", headers=dict(headers))
        return self._open(request, timeout_seconds).decode("utf-8")


class OpenAIBatchAdapter:
    provider = "openai"

    def __init__(
        self,
        *,
        transport: BatchHTTPTransport | None = None,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com",
        timeout_seconds: float = 90.0,
    ) -> None:
        self._transport = transport or UrllibBatchTransport()
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        credential = str(self._api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
        if not credential:
            raise ProviderUnavailableError("OPENAI_API_KEY is not configured in process memory")
        return {"Authorization": f"Bearer {credential}"}

    def submit(
        self,
        identity: ModelIdentity,
        requests: Sequence[AIRequest],
        *,
        payload_hash: str,
    ) -> BatchSubmission:
        if identity.provider != self.provider:
            raise ProviderResponseError("OpenAI Batch adapter received another provider")
        lines = [
            json.dumps(
                {
                    "custom_id": request.request_id,
                    "method": "POST",
                    "url": "/v1/responses",
                    "body": build_openai_response_body(identity, request),
                },
                separators=(",", ":"),
            )
            for request in requests
        ]
        uploaded = self._transport.upload_jsonl(
            url=f"{self._base_url}/v1/files",
            headers=self._headers(),
            content="\n".join(lines) + "\n",
            filename="alphapilot-batch.jsonl",
            timeout_seconds=self._timeout_seconds,
        )
        file_id = str(uploaded.get("id") or "")
        if not file_id:
            raise ProviderResponseError("OpenAI Batch upload returned no file identity")
        created = self._transport.request_json(
            method="POST",
            url=f"{self._base_url}/v1/batches",
            headers=self._headers(),
            json_body={
                "input_file_id": file_id,
                "endpoint": "/v1/responses",
                "completion_window": "24h",
                "metadata": {"alphapilot_payload_hash": payload_hash},
            },
            timeout_seconds=self._timeout_seconds,
        )
        provider_job_id = str(created.get("id") or "")
        if not provider_job_id:
            raise ProviderResponseError("OpenAI Batch returned no job identity")
        return BatchSubmission(provider_job_id, str(created.get("status") or "submitted"))

    def get_status(self, provider_job_id: str) -> BatchProviderStatus:
        payload = self._transport.request_json(
            method="GET",
            url=f"{self._base_url}/v1/batches/{provider_job_id}",
            headers=self._headers(),
            json_body=None,
            timeout_seconds=self._timeout_seconds,
        )
        state = str(payload.get("status") or "unknown")
        counts = payload.get("request_counts") or {}
        outputs: dict[str, Mapping[str, object]] = {}
        if state == "completed":
            output_file_id = str(payload.get("output_file_id") or "")
            if not output_file_id:
                raise ProviderResponseError("completed OpenAI Batch has no output file")
            raw = self._transport.download_text(
                url=f"{self._base_url}/v1/files/{output_file_id}/content",
                headers=self._headers(),
                timeout_seconds=self._timeout_seconds,
            )
            outputs = _parse_openai_jsonl(raw)
        normalized = "failed" if state in {"failed", "cancelled", "expired"} else state
        return BatchProviderStatus(
            provider_job_id=provider_job_id,
            status=normalized,
            outputs=outputs,
            total_count=int(counts.get("total") or 0),
            completed_count=int(counts.get("completed") or 0),
            failed_count=int(counts.get("failed") or 0),
        )


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


def _parse_openai_jsonl(raw: str) -> dict[str, Mapping[str, object]]:
    outputs: dict[str, Mapping[str, object]] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProviderResponseError("OpenAI Batch output file contains invalid JSONL") from exc
        custom_id = str(item.get("custom_id") or "")
        response = item.get("response") or {}
        body = response.get("body") or {}
        if not custom_id or int(response.get("status_code") or 0) != 200:
            raise ProviderResponseError("OpenAI Batch contains a failed request")
        output_text = body.get("output_text")
        if not isinstance(output_text, str):
            raise ProviderResponseError("OpenAI Batch response has no output_text")
        outputs[custom_id] = parse_json_object(output_text)
    return outputs


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
