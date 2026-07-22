"""Versioned local prompt registry owned by the orchestration boundary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .errors import AIOrchestrationError


@dataclass(frozen=True, slots=True)
class PromptDefinition:
    version: str
    task_types: frozenset[str]
    content: str
    content_hash: str


class PromptRegistry:
    def __init__(self, *, definitions: Mapping[str, PromptDefinition], registry_hash: str) -> None:
        self._definitions = dict(definitions)
        self.registry_hash = registry_hash

    @classmethod
    def from_path(cls, path: Path | str) -> "PromptRegistry":
        source = Path(path).resolve()
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AIOrchestrationError(f"cannot load AI prompt registry: {source}") from exc
        if payload.get("schemaVersion") != "alphapilot_prompt_registry_v1":
            raise AIOrchestrationError("unsupported AI prompt registry schema")
        raw_prompts = payload.get("prompts")
        if not isinstance(raw_prompts, Mapping) or not raw_prompts:
            raise AIOrchestrationError("AI prompt registry entries are required")
        definitions: dict[str, PromptDefinition] = {}
        root = source.parent.resolve()
        for version, raw in raw_prompts.items():
            if not isinstance(raw, Mapping):
                raise AIOrchestrationError(f"invalid prompt definition: {version}")
            if not bool(raw.get("enabled", True)):
                continue
            task_types = raw.get("taskTypes")
            relative_path = str(raw.get("path") or "").strip()
            if not isinstance(task_types, list) or not task_types:
                raise AIOrchestrationError(f"prompt taskTypes are required: {version}")
            if not relative_path:
                raise AIOrchestrationError(f"prompt path is required: {version}")
            prompt_path = (root / relative_path).resolve()
            try:
                prompt_path.relative_to(root)
            except ValueError as exc:
                raise AIOrchestrationError(f"prompt path escapes registry root: {version}") from exc
            try:
                content = prompt_path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise AIOrchestrationError(f"cannot load prompt content: {version}") from exc
            if not content:
                raise AIOrchestrationError(f"prompt content is empty: {version}")
            content_hash = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
            definitions[str(version)] = PromptDefinition(
                version=str(version),
                task_types=frozenset(str(item) for item in task_types),
                content=content,
                content_hash=content_hash,
            )
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        registry_hash = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return cls(definitions=definitions, registry_hash=registry_hash)

    def resolve(self, version: str, task_type: str) -> PromptDefinition:
        try:
            definition = self._definitions[version]
        except KeyError as exc:
            raise AIOrchestrationError(f"unknown or disabled AI prompt version: {version}") from exc
        if task_type not in definition.task_types:
            raise AIOrchestrationError(
                f"prompt version {version} is not registered for task type {task_type}"
            )
        return definition

    def projection(self) -> dict[str, Any]:
        return {
            "schemaVersion": "alphapilot_prompt_registry_projection_v1",
            "registryHash": self.registry_hash,
            "prompts": [
                {
                    "version": item.version,
                    "taskTypes": sorted(item.task_types),
                    "contentHash": item.content_hash,
                }
                for item in sorted(self._definitions.values(), key=lambda value: value.version)
            ],
        }
