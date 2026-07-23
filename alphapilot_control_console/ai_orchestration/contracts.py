"""Stable contracts shared by the orchestration service and provider adapters."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping


_SENSITIVITIES = {
    "public",
    "internal",
    "confidential",
    "restricted_trading",
    "secret",
}


@dataclass(frozen=True, slots=True)
class AIUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    alias: str
    provider: str
    model_id: str
    capabilities: frozenset[str] = frozenset()
    registry_hash: str = ""
    input_cost_per_million_usd: float = 0.0
    output_cost_per_million_usd: float = 0.0


@dataclass(frozen=True, slots=True)
class AIRequest:
    request_id: str
    task_type: str
    payload: Mapping[str, Any]
    response_schema: Mapping[str, Any]
    sensitivity: str
    prompt_version: str
    artifact_hashes: tuple[str, ...] = ()
    tool_names: tuple[str, ...] = ()
    long_context: bool = False
    multimodal: bool = False
    coding: bool = False
    quant_research: bool = True
    dual_review: bool = False
    human_review_required: bool = False
    latency_class: str = "standard"
    cost_ceiling_usd: float = 1.0
    token_ceiling: int = 4_096
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("AI request_id is required")
        if not self.task_type.strip():
            raise ValueError("AI task_type is required")
        if self.sensitivity not in _SENSITIVITIES:
            raise ValueError(f"Unsupported AI sensitivity: {self.sensitivity}")
        if not self.prompt_version.strip():
            raise ValueError("AI prompt_version is required")
        if self.token_ceiling <= 0:
            raise ValueError("AI token_ceiling must be positive")
        if self.cost_ceiling_usd < 0:
            raise ValueError("AI cost ceiling cannot be negative")

    def with_payload(self, payload: Mapping[str, Any]) -> "AIRequest":
        return replace(self, payload=payload)


@dataclass(frozen=True, slots=True)
class PreparedAIRequest:
    request: AIRequest
    payload: Mapping[str, Any]
    input_hash: str
    redaction_count: int
    redacted_paths: tuple[str, ...]

    def as_request(self) -> AIRequest:
        return self.request.with_payload(self.payload)


@dataclass(frozen=True, slots=True)
class AIProviderToolCall:
    call_id: str
    name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class AIResponse:
    request_id: str
    provider: str
    model_alias: str
    model_id: str
    output: Mapping[str, Any]
    usage: AIUsage
    latency_ms: int
    provider_request_id: str = ""
    reasoning_content: str = ""
    tool_calls: tuple[AIProviderToolCall, ...] = ()


@dataclass(frozen=True, slots=True)
class TaskRoute:
    mode: str
    model_aliases: tuple[str, ...]
    fallback_model_aliases: tuple[str, ...] = ()
    critical_fields: tuple[str, ...] = ()
    requires_human_on_disagreement: bool = False


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    request_id: str
    status: str
    output: Mapping[str, Any]
    response_hashes: tuple[str, ...]
    disagreements: tuple[str, ...] = ()
    execution_authorized: bool = False
    route_mode: str = "single"
    reasoning_contents: tuple[str, ...] = ()
    tool_calls: tuple[AIProviderToolCall, ...] = ()
    validated_outputs: tuple[Mapping[str, Any], ...] = ()
