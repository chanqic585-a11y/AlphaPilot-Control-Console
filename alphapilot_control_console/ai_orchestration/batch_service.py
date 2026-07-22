"""Durable dual-provider Batch orchestration for non-urgent historical research."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence

from .batch import AIBatchLedger
from .contracts import AIRequest, ModelIdentity
from .errors import BatchConflictError, ProviderUnavailableError
from .model_registry import AIModelRegistry
from .prompt_registry import PromptRegistry
from .redaction import LocalRedactor
from .task_router import AITaskRouter
from .validation import canonical_json, validate_output


@dataclass(frozen=True, slots=True)
class BatchSubmission:
    provider_job_id: str
    status: str


@dataclass(frozen=True, slots=True)
class BatchProviderStatus:
    provider_job_id: str
    status: str
    outputs: Mapping[str, Mapping[str, object]] = field(default_factory=dict)
    total_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    error_type: str = ""


class BatchProviderAdapter(Protocol):
    provider: str

    def submit(
        self,
        identity: ModelIdentity,
        requests: Sequence[AIRequest],
        *,
        payload_hash: str,
    ) -> BatchSubmission: ...

    def get_status(self, provider_job_id: str) -> BatchProviderStatus: ...


class AIBatchOrchestrationService:
    """Submit once, reconcile later, and trust outputs only after local validation."""

    def __init__(
        self,
        *,
        model_registry: AIModelRegistry,
        prompt_registry: PromptRegistry,
        adapters: Mapping[str, BatchProviderAdapter],
        ledger: AIBatchLedger,
        router: AITaskRouter | None = None,
        redactor: LocalRedactor | None = None,
    ) -> None:
        self._model_registry = model_registry
        self._prompt_registry = prompt_registry
        self._adapters = dict(adapters)
        self._ledger = ledger
        self._router = router or AITaskRouter()
        self._redactor = redactor or LocalRedactor()

    def submit(
        self,
        *,
        requests: Sequence[AIRequest],
        idempotency_key: str,
    ) -> list[dict[str, object]]:
        if not requests:
            raise ValueError("AI Batch requires at least one request")
        request_ids = [item.request_id for item in requests]
        if len(request_ids) != len(set(request_ids)):
            raise BatchConflictError("AI Batch request IDs must be unique")

        route = self._router.route(requests[0])
        if route.mode != "batch":
            raise BatchConflictError("only historical_batch requests may use AI Batch")
        prepared_requests: list[AIRequest] = []
        request_hashes: list[str] = []
        for request in requests:
            item_route = self._router.route(request)
            if item_route != route:
                raise BatchConflictError("AI Batch requests must share one deterministic route")
            prompt = self._prompt_registry.resolve(request.prompt_version, request.task_type)
            enveloped = request.with_payload(
                {
                    "platformPrompt": prompt.content,
                    "untrustedData": request.payload,
                }
            )
            prepared = self._redactor.prepare(enveloped)
            prepared_requests.append(prepared.as_request())
            request_hashes.append(prepared.input_hash)

        jobs: list[dict[str, object]] = []
        for alias in route.model_aliases:
            identity = self._model_registry.resolve(alias)
            adapter = self._adapters.get(identity.provider)
            if adapter is None:
                raise ProviderUnavailableError(
                    f"no Batch adapter is configured for {identity.provider}"
                )
            job = self._ledger.register(
                idempotency_key=f"{idempotency_key}:{identity.provider}",
                provider=identity.provider,
                model_alias=identity.alias,
                request_hashes=request_hashes,
            )
            if not job["providerJobId"]:
                submission = adapter.submit(
                    identity,
                    tuple(prepared_requests),
                    payload_hash=str(job["payloadHash"]),
                )
                job = self._ledger.mark_submitted(
                    str(job["batchJobId"]), submission.provider_job_id
                )
            jobs.append(job)
        return jobs

    def refresh(
        self,
        batch_job_id: str,
        *,
        requests: Sequence[AIRequest],
    ) -> dict[str, object]:
        job = self._ledger.get(batch_job_id)
        provider_job_id = str(job["providerJobId"])
        if not provider_job_id:
            raise BatchConflictError("AI Batch has not been submitted")
        adapter = self._adapters.get(str(job["provider"]))
        if adapter is None:
            raise ProviderUnavailableError(
                f"no Batch adapter is configured for {job['provider']}"
            )
        status = adapter.get_status(provider_job_id)
        if status.status != "completed":
            return {**job, "providerStatus": status.status}

        expected = {item.request_id: item for item in requests}
        if set(status.outputs) != set(expected):
            raise BatchConflictError("provider Batch result IDs do not match the frozen request set")
        validated_hashes: dict[str, str] = {}
        for request_id, output in status.outputs.items():
            request = expected[request_id]
            validated_hashes[request_id] = validate_output(
                task_type=request.task_type,
                output=output,
                schema=request.response_schema,
                artifact_hashes=request.artifact_hashes,
            )
        result_hash = "sha256:" + hashlib.sha256(
            canonical_json(validated_hashes).encode("utf-8")
        ).hexdigest()
        return self._ledger.mark_completed(batch_job_id, result_hash)


def batch_request_set_hash(requests: Sequence[AIRequest]) -> str:
    """Hash a caller-owned immutable request manifest without retaining its contents."""

    payload = [
        {
            "requestId": item.request_id,
            "taskType": item.task_type,
            "promptVersion": item.prompt_version,
            "artifactHashes": list(item.artifact_hashes),
            "schema": item.response_schema,
        }
        for item in requests
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
