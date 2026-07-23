"""Read-only AI control-plane projection with no provider invocation."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Mapping


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _table_count(path: Path, table: str) -> int:
    if not path.is_file():
        return 0
    try:
        uri = f"file:{path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except (sqlite3.Error, OSError):
        return 0


def build_ai_control_projection(
    *,
    repository_root: Path | str,
    data_root: Path | str,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    root = Path(repository_root)
    storage = Path(data_root) / "ai_orchestration"
    env = dict(os.environ if environment is None else environment)
    registry = _read_json(root / "config" / "ai_model_registry.json")
    models = registry.get("aliases") or registry.get("models") or {}
    enabled_models = {
        str(alias): dict(value)
        for alias, value in models.items()
        if isinstance(value, Mapping) and bool(value.get("enabled", True))
    }
    prompt_registry = _read_json(root / "config" / "ai_prompt_registry.json")
    budget = _read_json(root / "config" / "ai_budget_policy.json")
    provider_health = {
        "deepseek": "configured" if bool(env.get("DEEPSEEK_API_KEY")) else "credentials_missing",
        "gemini": "configured" if bool(env.get("GEMINI_API_KEY")) else "credentials_missing",
    }
    audit_count = _table_count(storage / "ai_orchestration_audit.sqlite", "AIOrchestrationAuditEvents")
    batch_count = _table_count(storage / "ai_batch.sqlite", "AIBatchJobs")
    status = (
        "ready"
        if all(value == "configured" for value in provider_health.values())
        else "provider_credentials_required"
    )
    return {
        "schemaVersion": "alphapilot_ai_control_projection_v1",
        "status": status,
        "providerHealth": provider_health,
        "modelCount": len(enabled_models),
        "models": [
            {
                "alias": alias,
                "provider": value.get("provider"),
                "modelId": value.get("modelId"),
                "capabilities": value.get("capabilities") or [],
            }
            for alias, value in sorted(enabled_models.items())
        ],
        "promptVersionCount": len(prompt_registry.get("prompts") or {}),
        "queue": {
            "status": "empty" if batch_count == 0 else "has_jobs",
            "batchJobCount": batch_count,
        },
        "auditEventCount": audit_count,
        "budget": {
            "dailyProviderLimitsUsd": budget.get("dailyProviderLimitsUsd") or {},
            "dailyTaskLimitsUsd": budget.get("dailyTaskLimitsUsd") or {},
            "defaultCampaignLimitUsd": budget.get("defaultCampaignLimitUsd"),
        },
        "routing": {
            "strategyHypothesis": "deepseek_primary_gemini_independent_review",
            "failureAttribution": "deepseek_primary_gemini_independent_review",
            "largeDocuments": "gemini_primary_deepseek_review",
            "batch": "gemini_batch_or_local_bounded_queue",
        },
        "credentialsPersisted": False,
        "exchangeCredentialsAvailableToWorker": False,
        "executionAuthorized": False,
    }
