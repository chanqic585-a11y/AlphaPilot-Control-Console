"""Versioned deployment manifest for the V63 local-first runtime."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .contracts import FOUNDATION_ROLES, FoundationRole, RuntimeMode
from .resource_budget import validate_resource_budget


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


@dataclass(frozen=True)
class RoleManifest:
    role: FoundationRole
    enabled: bool
    cpu: float
    memoryMb: int
    port: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "role": self.role.value,
            "enabled": self.enabled,
            "cpu": self.cpu,
            "memoryMb": self.memoryMb,
            "port": self.port,
        }


@dataclass(frozen=True)
class FoundationManifest:
    schemaVersion: str
    deploymentId: str
    environment: str
    mode: RuntimeMode
    stateRoot: Path
    repositoryCommit: str
    repositoryTag: str
    configVersion: str
    roles: Mapping[FoundationRole, RoleManifest]
    hostReserveMemoryMb: int
    maxConcurrentBatchRoles: int
    manifestHash: str
    configHash: str
    orderCapabilityEnabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "roles", MappingProxyType(dict(self.roles)))

    @classmethod
    def load(cls, path: Path | str) -> "FoundationManifest":
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        if payload.get("schemaVersion") != "alphapilot_v63_server_manifest_v1":
            raise ValueError("unsupported_foundation_manifest_schema")
        if payload.get("mode") != RuntimeMode.SHADOW_NO_ORDER.value:
            raise ValueError("v63_foundation_requires_shadow_no_order")

        role_entries = payload.get("roles")
        if not isinstance(role_entries, list):
            raise ValueError("foundation_roles_must_be_a_list")
        roles: dict[FoundationRole, RoleManifest] = {}
        for entry in role_entries:
            if not isinstance(entry, dict):
                raise ValueError("foundation_role_entry_invalid")
            role = FoundationRole(str(entry.get("role", "")))
            if role in roles:
                raise ValueError(f"duplicate_foundation_role:{role.value}")
            port_value = entry.get("port")
            port = None if port_value is None else int(port_value)
            roles[role] = RoleManifest(
                role=role,
                enabled=bool(entry.get("enabled", False)),
                cpu=float(entry.get("cpu", 0)),
                memoryMb=int(entry.get("memoryMb", 0)),
                port=port,
            )
        if set(roles) != set(FOUNDATION_ROLES):
            raise ValueError("foundation_manifest_requires_exact_six_roles")
        if any(role.cpu <= 0 or role.memoryMb <= 0 for role in roles.values()):
            raise ValueError("foundation_role_budget_must_be_positive")

        canonical_payload = {
            **payload,
            "roles": [
                roles[role].to_dict()
                for role in FOUNDATION_ROLES
            ],
        }
        manifest_hash = hashlib.sha256(_canonical_json(canonical_payload)).hexdigest()
        config_hash = hashlib.sha256(
            _canonical_json(
                {
                    "configVersion": payload.get("configVersion"),
                    "environment": payload.get("environment"),
                    "mode": payload.get("mode"),
                    "roles": canonical_payload["roles"],
                    "hostReserveMemoryMb": payload.get("hostReserveMemoryMb"),
                    "maxConcurrentBatchRoles": payload.get(
                        "maxConcurrentBatchRoles"
                    ),
                }
            )
        ).hexdigest()
        manifest = cls(
            schemaVersion=str(payload["schemaVersion"]),
            deploymentId=str(payload.get("deploymentId", "")).strip(),
            environment=str(payload.get("environment", "")).strip().lower(),
            mode=RuntimeMode(str(payload["mode"])),
            stateRoot=Path(str(payload.get("stateRoot", ""))).expanduser().resolve(),
            repositoryCommit=str(payload.get("repositoryCommit", "")).strip(),
            repositoryTag=str(payload.get("repositoryTag", "")).strip(),
            configVersion=str(payload.get("configVersion", "")).strip(),
            roles=roles,
            hostReserveMemoryMb=int(payload.get("hostReserveMemoryMb", 0)),
            maxConcurrentBatchRoles=int(
                payload.get("maxConcurrentBatchRoles", 0)
            ),
            manifestHash=manifest_hash,
            configHash=config_hash,
        )
        manifest._assert_valid()
        return manifest

    def _assert_valid(self) -> None:
        if not self.deploymentId or not self.environment or not self.configVersion:
            raise ValueError("foundation_manifest_identity_incomplete")
        if len(self.repositoryCommit) != 40:
            raise ValueError("foundation_repository_commit_invalid")
        if not self.repositoryTag:
            raise ValueError("foundation_repository_tag_missing")
        decision = validate_resource_budget(self)
        if not decision.passed:
            raise ValueError(
                "resource_budget_exceeded:" + ",".join(decision.reasonCodes)
            )

    def role(self, role: FoundationRole) -> RoleManifest:
        return self.roles[role]

    def to_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": self.schemaVersion,
            "deploymentId": self.deploymentId,
            "environment": self.environment,
            "mode": self.mode.value,
            "stateRoot": str(self.stateRoot),
            "repositoryCommit": self.repositoryCommit,
            "repositoryTag": self.repositoryTag,
            "configVersion": self.configVersion,
            "roles": [
                self.roles[role].to_dict()
                for role in FOUNDATION_ROLES
            ],
            "hostReserveMemoryMb": self.hostReserveMemoryMb,
            "maxConcurrentBatchRoles": self.maxConcurrentBatchRoles,
            "manifestHash": self.manifestHash,
            "configHash": self.configHash,
            "orderCapabilityEnabled": self.orderCapabilityEnabled,
        }
