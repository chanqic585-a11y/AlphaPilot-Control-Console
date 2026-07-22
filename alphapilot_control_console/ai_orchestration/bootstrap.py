"""Single composition root for the research-only AI boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .audit import AIAuditLedger
from .batch import AIBatchLedger
from .batch_service import AIBatchOrchestrationService
from .budget import AIBudgetLedger, AIBudgetPolicy
from .circuit_breaker import ProviderCircuitBreaker
from .model_registry import AIModelRegistry
from .prompt_registry import PromptRegistry
from .provider_adapters.batch_adapters import GeminiBatchAdapter, OpenAIBatchAdapter
from .provider_adapters.gemini_adapter import GeminiAdapter
from .provider_adapters.openai_adapter import OpenAIAdapter
from .service import AIOrchestrationService


@dataclass(slots=True)
class AIOrchestrationRuntime:
    """Own services and close every local metadata ledger deterministically."""

    service: AIOrchestrationService
    batch_service: AIBatchOrchestrationService
    audit_ledger: AIAuditLedger
    batch_ledger: AIBatchLedger
    budget_ledger: AIBudgetLedger
    model_registry_hash: str
    prompt_registry_hash: str

    def close(self) -> None:
        self.batch_ledger.close()
        self.budget_ledger.close()
        self.audit_ledger.close()

    def __enter__(self) -> "AIOrchestrationRuntime":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _load_budget_policy(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != "alphapilot_ai_budget_policy_v1":
        raise ValueError("unsupported AI budget policy schema")
    return payload


def build_ai_runtime(
    *,
    repository_root: Path | str,
    data_root: Path | str,
) -> AIOrchestrationRuntime:
    """Build the only supported provider-enabled AlphaPilot AI runtime."""

    root = Path(repository_root).resolve()
    storage = Path(data_root).resolve() / "ai_orchestration"
    storage.mkdir(parents=True, exist_ok=True)

    # Validate all immutable configuration before opening SQLite handles.
    model_registry = AIModelRegistry.from_path(root / "config" / "ai_model_registry.json")
    prompt_registry = PromptRegistry.from_path(root / "config" / "ai_prompt_registry.json")
    budget_config = _load_budget_policy(root / "config" / "ai_budget_policy.json")

    sync_adapters = {
        "openai": OpenAIAdapter(),
        "gemini": GeminiAdapter(),
    }
    batch_adapters = {
        "openai": OpenAIBatchAdapter(),
        "gemini": GeminiBatchAdapter(),
    }

    audit_ledger = AIAuditLedger(storage / "ai_orchestration_audit.sqlite")
    budget_ledger = AIBudgetLedger(storage / "ai_budget.sqlite")
    batch_ledger = AIBatchLedger(storage / "ai_batch.sqlite")
    budget_policy = AIBudgetPolicy(
        ledger=budget_ledger,
        daily_provider_limits=budget_config.get("dailyProviderLimitsUsd") or {},
        daily_task_limits=budget_config.get("dailyTaskLimitsUsd") or {},
        campaign_limits=budget_config.get("campaignLimitsUsd") or {},
        default_campaign_limit_usd=float(
            budget_config.get("defaultCampaignLimitUsd") or 0.0
        ),
    )
    service = AIOrchestrationService(
        model_registry=model_registry,
        prompt_registry=prompt_registry,
        adapters=sync_adapters,
        audit_ledger=audit_ledger,
        budget_policy=budget_policy,
        circuit_breaker=ProviderCircuitBreaker(),
    )
    batch_service = AIBatchOrchestrationService(
        model_registry=model_registry,
        prompt_registry=prompt_registry,
        adapters=batch_adapters,
        ledger=batch_ledger,
    )
    return AIOrchestrationRuntime(
        service=service,
        batch_service=batch_service,
        audit_ledger=audit_ledger,
        batch_ledger=batch_ledger,
        budget_ledger=budget_ledger,
        model_registry_hash=model_registry.registry_hash,
        prompt_registry_hash=prompt_registry.registry_hash,
    )
