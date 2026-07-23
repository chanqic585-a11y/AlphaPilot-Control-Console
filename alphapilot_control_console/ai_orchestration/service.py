"""The only supported synchronous entry point for AlphaPilot AI research."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping, Protocol

from .audit import AIAuditLedger
from .budget import AIBudgetPolicy
from .circuit_breaker import ProviderCircuitBreaker
from .contracts import AIRequest, AIResponse, OrchestrationResult, PreparedAIRequest, TaskRoute
from .errors import (
    BudgetExceededError,
    OutputValidationError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from .model_registry import AIModelRegistry
from .prompt_registry import PromptDefinition, PromptRegistry
from .redaction import LocalRedactor
from .task_router import AITaskRouter
from .validation import canonical_json, validate_output


class AIProviderAdapter(Protocol):
    provider: str

    def generate(self, identity, request: AIRequest) -> AIResponse: ...


@dataclass(frozen=True, slots=True)
class _ValidatedResponse:
    response: AIResponse
    output_hash: str


class AIOrchestrationService:
    """Route, redact, call, validate, compare and audit research-only AI work."""

    def __init__(
        self,
        *,
        model_registry: AIModelRegistry,
        prompt_registry: PromptRegistry,
        adapters: Mapping[str, AIProviderAdapter],
        audit_ledger: AIAuditLedger,
        router: AITaskRouter | None = None,
        redactor: LocalRedactor | None = None,
        budget_policy: AIBudgetPolicy | None = None,
        circuit_breaker: ProviderCircuitBreaker | None = None,
    ) -> None:
        self._model_registry = model_registry
        self._prompt_registry = prompt_registry
        self._adapters = dict(adapters)
        self._audit_ledger = audit_ledger
        self._router = router or AITaskRouter()
        self._redactor = redactor or LocalRedactor()
        self._budget_policy = budget_policy
        self._circuit_breaker = circuit_breaker

    def execute(self, request: AIRequest) -> OrchestrationResult:
        # Route first so execution-authority tasks cannot reach redaction or provider code.
        route = self._router.route(request)
        if route.mode == "batch":
            raise ProviderUnavailableError(
                "historical_batch must be submitted through the durable Batch service"
            )
        prompt = self._prompt_registry.resolve(request.prompt_version, request.task_type)
        enveloped_request = request.with_payload(
            {
                "platformPrompt": prompt.content,
                "untrustedData": request.payload,
            }
        )
        prepared = self._redactor.prepare(enveloped_request)
        responses: list[AIResponse] = []
        validated: list[_ValidatedResponse] = []
        campaign_id = str(request.metadata.get("researchCampaignId") or "unscoped")
        try:
            if route.mode == "single":
                selected = self._execute_single_route(
                    request=request,
                    prepared=prepared,
                    route=route,
                    campaign_id=campaign_id,
                )
                responses.append(selected.response)
                validated.append(selected)
            else:
                identities = [self._model_registry.resolve(alias) for alias in route.model_aliases]
                per_provider_ceiling = request.cost_ceiling_usd / max(1, len(identities))
                for identity in identities:
                    self._assert_provider_available(
                        identity=identity,
                        request=request,
                        campaign_id=campaign_id,
                        requested_cost_ceiling_usd=per_provider_ceiling,
                    )
                for identity in identities:
                    selected = self._execute_identity(
                        identity=identity,
                        request=request,
                        prepared=prepared,
                    )
                    responses.append(selected.response)
                    validated.append(selected)
            self._enforce_budget(request, responses)
            if self._budget_policy is not None:
                for response in responses:
                    self._budget_policy.record_usage(
                        provider=response.provider,
                        task_type=request.task_type,
                        campaign_id=campaign_id,
                        request_id=f"{request.request_id}:{response.provider}:{response.model_alias}",
                        cost_usd=response.usage.estimated_cost_usd,
                        total_tokens=response.usage.total_tokens,
                    )
        except BudgetExceededError as exc:
            self._record(
                prepared=prepared,
                route=route,
                responses=responses,
                validated=validated,
                status="paused_budget_exhausted",
                disagreements=(),
                error_type=type(exc).__name__,
                prompt=prompt,
            )
            raise
        except (ProviderUnavailableError, ProviderResponseError) as exc:
            self._record(
                prepared=prepared,
                route=route,
                responses=responses,
                validated=validated,
                status="provider_failed",
                disagreements=(),
                error_type=type(exc).__name__,
                prompt=prompt,
            )
            raise
        except OutputValidationError as exc:
            self._record(
                prepared=prepared,
                route=route,
                responses=responses,
                validated=validated,
                status="validation_failed",
                disagreements=(),
                error_type=type(exc).__name__,
                prompt=prompt,
            )
            raise

        disagreements = self._find_disagreements(validated, route)
        status = (
            "human_review_required"
            if disagreements and route.requires_human_on_disagreement
            else "accepted"
        )
        self._record(
            prepared=prepared,
            route=route,
            responses=responses,
            validated=validated,
            status=status,
            disagreements=disagreements,
            error_type="",
            prompt=prompt,
        )
        primary = validated[0]
        return OrchestrationResult(
            request_id=request.request_id,
            status=status,
            output=primary.response.output,
            response_hashes=tuple(item.output_hash for item in validated),
            disagreements=disagreements,
            execution_authorized=False,
            route_mode=route.mode,
            reasoning_contents=tuple(
                item.reasoning_content
                for item in responses
                if item.reasoning_content
            ),
            tool_calls=tuple(
                tool_call
                for item in responses
                for tool_call in item.tool_calls
            ),
            validated_outputs=tuple(
                dict(item.response.output)
                for item in validated
            ),
        )

    def _execute_single_route(
        self,
        *,
        request: AIRequest,
        prepared: PreparedAIRequest,
        route: TaskRoute,
        campaign_id: str,
    ) -> _ValidatedResponse:
        last_error: ProviderUnavailableError | ProviderResponseError | None = None
        for alias in (*route.model_aliases, *route.fallback_model_aliases):
            identity = self._model_registry.resolve(alias)
            try:
                self._assert_provider_available(
                    identity=identity,
                    request=request,
                    campaign_id=campaign_id,
                    requested_cost_ceiling_usd=request.cost_ceiling_usd,
                )
                return self._execute_identity(
                    identity=identity,
                    request=request,
                    prepared=prepared,
                )
            except (ProviderUnavailableError, ProviderResponseError) as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise ProviderUnavailableError("single AI route has no configured model alias")

    def _assert_provider_available(
        self,
        *,
        identity,
        request: AIRequest,
        campaign_id: str,
        requested_cost_ceiling_usd: float,
    ) -> None:
        if self._circuit_breaker is not None:
            self._circuit_breaker.assert_available(identity.provider)
        if self._budget_policy is not None:
            self._budget_policy.assert_available(
                provider=identity.provider,
                task_type=request.task_type,
                campaign_id=campaign_id,
                requested_cost_ceiling_usd=requested_cost_ceiling_usd,
            )

    def _execute_identity(
        self,
        *,
        identity,
        request: AIRequest,
        prepared: PreparedAIRequest,
    ) -> _ValidatedResponse:
        adapter = self._adapters.get(identity.provider)
        if adapter is None:
            raise ProviderUnavailableError(
                f"no provider adapter is configured for {identity.provider}"
            )
        try:
            response = adapter.generate(identity, prepared.as_request())
        except (ProviderUnavailableError, ProviderResponseError):
            if self._circuit_breaker is not None:
                self._circuit_breaker.record_failure(identity.provider)
            raise
        if self._circuit_breaker is not None:
            self._circuit_breaker.record_success(identity.provider)
        output_hash = validate_output(
            task_type=request.task_type,
            output=response.output,
            schema=request.response_schema,
            artifact_hashes=request.artifact_hashes,
        )
        return _ValidatedResponse(response=response, output_hash=output_hash)

    @staticmethod
    def _enforce_budget(request: AIRequest, responses: list[AIResponse]) -> None:
        total_cost = sum(item.usage.estimated_cost_usd for item in responses)
        if any(item.usage.output_tokens > request.token_ceiling for item in responses):
            raise BudgetExceededError("AI output token ceiling exceeded")
        if total_cost > request.cost_ceiling_usd:
            raise BudgetExceededError("AI cost ceiling exceeded")

    @staticmethod
    def _find_disagreements(
        validated: list[_ValidatedResponse], route: TaskRoute
    ) -> tuple[str, ...]:
        if len(validated) < 2:
            return ()
        first = validated[0].response.output
        disagreements = []
        for field in route.critical_fields:
            baseline = canonical_json(first.get(field))
            if any(canonical_json(item.response.output.get(field)) != baseline for item in validated[1:]):
                disagreements.append(field)
        return tuple(disagreements)

    def _record(
        self,
        *,
        prepared: PreparedAIRequest,
        route: TaskRoute,
        responses: list[AIResponse],
        validated: list[_ValidatedResponse],
        status: str,
        disagreements: tuple[str, ...],
        error_type: str,
        prompt: PromptDefinition,
    ) -> None:
        request = prepared.request
        route_mode = route.mode
        if (
            route.mode == "single"
            and responses
            and responses[0].model_alias in route.fallback_model_aliases
        ):
            route_mode = "single_fallback"
        self._audit_ledger.record(
            {
                "requestId": request.request_id,
                "taskType": request.task_type,
                "status": status,
                "routeMode": route_mode,
                "inputHash": prepared.input_hash,
                "responseHashes": [item.output_hash for item in validated],
                "reasoningContentHashes": [
                    "sha256:"
                    + hashlib.sha256(item.reasoning_content.encode("utf-8")).hexdigest()
                    for item in responses
                    if item.reasoning_content
                ],
                "providers": [item.provider for item in responses],
                "modelAliases": [item.model_alias for item in responses],
                "registryHash": self._model_registry.registry_hash,
                "promptVersion": request.prompt_version,
                "promptRegistryHash": self._prompt_registry.registry_hash,
                "promptContentHash": prompt.content_hash,
                "schemaValidationStatus": (
                    "passed" if validated else "failed" if status == "validation_failed" else "not_run"
                ),
                "semanticValidationStatus": (
                    "passed" if validated else "failed" if status == "validation_failed" else "not_run"
                ),
                "artifactHashes": list(request.artifact_hashes),
                "redactionCount": prepared.redaction_count,
                "disagreements": list(disagreements),
                "totalInputTokens": sum(item.usage.input_tokens for item in responses),
                "totalOutputTokens": sum(item.usage.output_tokens for item in responses),
                "totalTokens": sum(item.usage.total_tokens for item in responses),
                "estimatedCostUsd": sum(item.usage.estimated_cost_usd for item in responses),
                "latencyMs": sum(item.latency_ms for item in responses),
                "errorType": error_type,
            }
        )
