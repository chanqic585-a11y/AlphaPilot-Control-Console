"""Versioned model aliases resolved only from repository configuration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import ModelIdentity
from .errors import ModelRegistryError


_CREDENTIAL_FRAGMENTS = (
    "apikey",
    "api_key",
    "secret",
    "passphrase",
    "privatekey",
    "private_key",
    "authorization",
    "cookie",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _reject_credentials(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).replace("-", "").lower()
            if any(fragment.replace("_", "") in normalized.replace("_", "") for fragment in _CREDENTIAL_FRAGMENTS):
                raise ModelRegistryError(f"credential field is forbidden in model registry: {path}{key}")
            _reject_credentials(nested, f"{path}{key}.")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_credentials(nested, f"{path}{index}.")


@dataclass(frozen=True, slots=True)
class _RegistryEntry:
    alias: str
    provider: str
    model_id: str
    capabilities: frozenset[str]
    batch_alias: str | None = None
    supports_structured_output: bool = False
    supports_function_calling: bool = False
    supports_files: bool = False
    supports_images: bool = False
    supports_batch: bool = False
    context_limit: int = 0
    latency_tier: str = "standard"
    cost_tier: str = "standard"
    preview_or_stable: str = "stable"
    input_cost_per_million_usd: float = 0.0
    output_cost_per_million_usd: float = 0.0
    enabled: bool = True


class AIModelRegistry:
    def __init__(self, *, entries: Mapping[str, _RegistryEntry], registry_hash: str) -> None:
        self._entries = dict(entries)
        self.registry_hash = registry_hash

    @classmethod
    def from_path(cls, path: Path | str) -> "AIModelRegistry":
        source = Path(path)
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ModelRegistryError(f"cannot load AI model registry: {source}") from exc
        return cls.from_mapping(payload)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "AIModelRegistry":
        _reject_credentials(payload)
        if payload.get("schemaVersion") != "alphapilot_ai_model_registry_v1":
            raise ModelRegistryError("unsupported AI model registry schema")
        raw_aliases = payload.get("aliases")
        if not isinstance(raw_aliases, Mapping) or not raw_aliases:
            raise ModelRegistryError("AI model registry aliases are required")
        entries: dict[str, _RegistryEntry] = {}
        for alias, raw in raw_aliases.items():
            if not isinstance(raw, Mapping):
                raise ModelRegistryError(f"invalid model registry entry: {alias}")
            provider = str(raw.get("provider") or "").strip().lower()
            model_id = str(raw.get("modelId") or "").strip()
            capabilities = raw.get("capabilities") or []
            if provider not in {"openai", "gemini"}:
                raise ModelRegistryError(f"unsupported provider for alias {alias}")
            if not model_id:
                raise ModelRegistryError(f"modelId is required for alias {alias}")
            if "modelIdEnv" in raw:
                raise ModelRegistryError(f"modelIdEnv is forbidden for alias {alias}")
            if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
                raise ModelRegistryError(f"invalid capabilities for alias {alias}")
            input_cost = float(raw.get("inputUsdPerMillionTokens") or 0.0)
            output_cost = float(raw.get("outputUsdPerMillionTokens") or 0.0)
            if input_cost < 0 or output_cost < 0:
                raise ModelRegistryError(f"negative token pricing is forbidden for alias {alias}")
            entries[str(alias)] = _RegistryEntry(
                alias=str(alias),
                provider=provider,
                model_id=model_id,
                capabilities=frozenset(capabilities),
                batch_alias=str(raw.get("batchAlias") or "").strip() or None,
                supports_structured_output=bool(raw.get("supportsStructuredOutput", False)),
                supports_function_calling=bool(raw.get("supportsFunctionCalling", False)),
                supports_files=bool(raw.get("supportsFiles", False)),
                supports_images=bool(raw.get("supportsImages", False)),
                supports_batch=bool(raw.get("supportsBatch", False)),
                context_limit=max(0, int(raw.get("contextLimit") or 0)),
                latency_tier=str(raw.get("latencyTier") or "standard"),
                cost_tier=str(raw.get("costTier") or "standard"),
                preview_or_stable=str(raw.get("previewOrStable") or "stable"),
                input_cost_per_million_usd=input_cost,
                output_cost_per_million_usd=output_cost,
                enabled=bool(raw.get("enabled", True)),
            )
        registry_hash = "sha256:" + hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        return cls(entries=entries, registry_hash=registry_hash)

    def resolve(self, alias: str) -> ModelIdentity:
        try:
            entry = self._entries[alias]
        except KeyError as exc:
            raise ModelRegistryError(f"unknown model alias: {alias}") from exc
        if not entry.enabled:
            raise ModelRegistryError(f"model alias is disabled: {alias}")
        return ModelIdentity(
            alias=entry.alias,
            provider=entry.provider,
            model_id=entry.model_id,
            capabilities=entry.capabilities,
            registry_hash=self.registry_hash,
            input_cost_per_million_usd=entry.input_cost_per_million_usd,
            output_cost_per_million_usd=entry.output_cost_per_million_usd,
        )

    def describe(self) -> dict[str, Any]:
        return {
            "schemaVersion": "alphapilot_ai_model_registry_projection_v1",
            "registryHash": self.registry_hash,
            "aliases": [
                {
                    "alias": entry.alias,
                    "provider": entry.provider,
                    "modelId": entry.model_id,
                    "capabilities": sorted(entry.capabilities),
                    "batchAlias": entry.batch_alias,
                    "supportsStructuredOutput": entry.supports_structured_output,
                    "supportsFunctionCalling": entry.supports_function_calling,
                    "supportsFiles": entry.supports_files,
                    "supportsImages": entry.supports_images,
                    "supportsBatch": entry.supports_batch,
                    "contextLimit": entry.context_limit,
                    "latencyTier": entry.latency_tier,
                    "costTier": entry.cost_tier,
                    "previewOrStable": entry.preview_or_stable,
                    "inputUsdPerMillionTokens": entry.input_cost_per_million_usd,
                    "outputUsdPerMillionTokens": entry.output_cost_per_million_usd,
                    "enabled": entry.enabled,
                    "configured": bool(entry.model_id),
                }
                for entry in sorted(self._entries.values(), key=lambda item: item.alias)
            ],
        }
