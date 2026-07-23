"""Immutable identity for each independently startable V63 worker."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .contracts import FoundationRole
from .manifest import FoundationManifest


def _canonical_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class FoundationRuntimeIdentity:
    schemaVersion: str
    runtimeId: str
    deploymentId: str
    environment: str
    role: FoundationRole
    mode: str
    processId: int
    repositoryCommit: str
    repositoryTag: str
    manifestHash: str
    configHash: str
    leaseId: str
    fencingToken: int
    startedAt: str
    orderCapabilityEnabled: bool
    identityHash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": self.schemaVersion,
            "runtimeId": self.runtimeId,
            "deploymentId": self.deploymentId,
            "environment": self.environment,
            "role": self.role.value,
            "mode": self.mode,
            "processId": self.processId,
            "repositoryCommit": self.repositoryCommit,
            "repositoryTag": self.repositoryTag,
            "manifestHash": self.manifestHash,
            "configHash": self.configHash,
            "leaseId": self.leaseId,
            "fencingToken": self.fencingToken,
            "startedAt": self.startedAt,
            "orderCapabilityEnabled": self.orderCapabilityEnabled,
            "identityHash": self.identityHash,
        }


def build_runtime_identity(
    *,
    manifest: FoundationManifest,
    role: FoundationRole,
    process_id: int,
    started_at: str,
    lease_id: str,
    fencing_token: int,
) -> FoundationRuntimeIdentity:
    payload: dict[str, object] = {
        "schemaVersion": "alphapilot_v63_runtime_identity_v1",
        "runtimeId": f"{manifest.deploymentId}:{role.value}:{fencing_token}",
        "deploymentId": manifest.deploymentId,
        "environment": manifest.environment,
        "role": role.value,
        "mode": manifest.mode.value,
        "processId": int(process_id),
        "repositoryCommit": manifest.repositoryCommit,
        "repositoryTag": manifest.repositoryTag,
        "manifestHash": manifest.manifestHash,
        "configHash": manifest.configHash,
        "leaseId": lease_id,
        "fencingToken": int(fencing_token),
        "startedAt": started_at,
        "orderCapabilityEnabled": False,
    }
    return FoundationRuntimeIdentity(
        schemaVersion=str(payload["schemaVersion"]),
        runtimeId=str(payload["runtimeId"]),
        deploymentId=str(payload["deploymentId"]),
        environment=str(payload["environment"]),
        role=FoundationRole(str(payload["role"])),
        mode=str(payload["mode"]),
        processId=int(payload["processId"]),
        repositoryCommit=str(payload["repositoryCommit"]),
        repositoryTag=str(payload["repositoryTag"]),
        manifestHash=str(payload["manifestHash"]),
        configHash=str(payload["configHash"]),
        leaseId=str(payload["leaseId"]),
        fencingToken=int(payload["fencingToken"]),
        startedAt=str(payload["startedAt"]),
        orderCapabilityEnabled=False,
        identityHash=_canonical_hash(payload),
    )
