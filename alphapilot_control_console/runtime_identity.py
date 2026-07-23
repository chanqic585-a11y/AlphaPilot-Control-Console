"""Immutable runtime identity and fail-closed new-entry authorization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping


RUNTIME_IDENTITY_VERIFIED = "runtime_identity_verified"
RUNTIME_IDENTITY_UNVERIFIED = "runtime_identity_unverified"

_CRITICAL_TEXT_FIELDS = (
    "runtimeId",
    "repositoryCommit",
    "releaseId",
    "releaseHash",
    "riskOverlayHash",
    "modelHash",
    "modelPolicyHash",
    "approvalHash",
    "armHash",
    "runtimeLeaseId",
    "startedAt",
    "lastHeartbeatAt",
    "lastScanAt",
    "nextScanAt",
)


class RuntimeIdentityMismatch(PermissionError):
    """Raised when a runtime cannot prove its exact execution identity."""


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class RuntimeIdentityDecision:
    newEntriesAllowed: bool
    route: str
    reasonCodes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "newEntriesAllowed": self.newEntriesAllowed,
            "route": self.route,
            "reasonCodes": list(self.reasonCodes),
        }


@dataclass(frozen=True)
class RuntimeIdentity:
    runtimeId: str
    environment: str
    processId: int
    repositoryCommit: str
    repositoryTag: str | None
    moduleRootHashes: Mapping[str, str]
    releaseId: str
    releaseHash: str
    riskOverlayHash: str
    modelHash: str
    modelPolicyHash: str
    approvalHash: str
    armHash: str
    runtimeLeaseId: str
    startedAt: str
    lastHeartbeatAt: str
    lastScanAt: str
    nextScanAt: str

    def __post_init__(self) -> None:
        normalized = {
            str(key): str(value)
            for key, value in self.moduleRootHashes.items()
            if str(key).strip() and str(value).strip()
        }
        object.__setattr__(self, "moduleRootHashes", MappingProxyType(normalized))

    def to_dict(self, *, expected: Mapping[str, Any] | None = None) -> dict[str, Any]:
        decision = evaluate_runtime_identity(self, expected=expected)
        return {
            "schemaVersion": "alphapilot_runtime_identity_v1",
            "runtimeId": self.runtimeId,
            "environment": self.environment,
            "processId": self.processId,
            "repositoryCommit": self.repositoryCommit,
            "repositoryTag": self.repositoryTag,
            "moduleRootHashes": dict(self.moduleRootHashes),
            "releaseId": self.releaseId,
            "releaseHash": self.releaseHash,
            "riskOverlayHash": self.riskOverlayHash,
            "modelHash": self.modelHash,
            "modelPolicyHash": self.modelPolicyHash,
            "approvalHash": self.approvalHash,
            "armHash": self.armHash,
            "runtimeLeaseId": self.runtimeLeaseId,
            "startedAt": self.startedAt,
            "lastHeartbeatAt": self.lastHeartbeatAt,
            "lastScanAt": self.lastScanAt,
            "nextScanAt": self.nextScanAt,
            **decision.to_dict(),
        }


def evaluate_runtime_identity(
    identity: RuntimeIdentity | None,
    *,
    expected: Mapping[str, Any] | None = None,
) -> RuntimeIdentityDecision:
    reasons: list[str] = []
    if identity is None:
        reasons.append("runtimeIdentity_missing")
    else:
        if identity.environment not in {"okx_demo", "okx_live"}:
            reasons.append("environment_invalid")
        if not isinstance(identity.processId, int) or identity.processId <= 0:
            reasons.append("processId_invalid")
        for field in _CRITICAL_TEXT_FIELDS:
            if not str(getattr(identity, field, "") or "").strip():
                reasons.append(field)
        if not identity.moduleRootHashes:
            reasons.append("moduleRootHashes")
        elif any(not key or not value for key, value in identity.moduleRootHashes.items()):
            reasons.append("moduleRootHashes_invalid")

        parsed = {
            field: _parse_timestamp(str(getattr(identity, field, "") or ""))
            for field in ("startedAt", "lastHeartbeatAt", "lastScanAt", "nextScanAt")
        }
        for field, value in parsed.items():
            if value is None:
                reasons.append(f"{field}_invalid")
        started = parsed["startedAt"]
        heartbeat = parsed["lastHeartbeatAt"]
        last_scan = parsed["lastScanAt"]
        next_scan = parsed["nextScanAt"]
        if started is not None and heartbeat is not None and heartbeat < started:
            reasons.append("lastHeartbeatAt_before_startedAt")
        if started is not None and last_scan is not None and last_scan < started:
            reasons.append("lastScanAt_before_startedAt")
        if last_scan is not None and next_scan is not None and next_scan < last_scan:
            reasons.append("nextScanAt_before_lastScanAt")

        for field, expected_value in dict(expected or {}).items():
            if not hasattr(identity, field):
                reasons.append(f"{field}_unsupported_expectation")
            elif getattr(identity, field) != expected_value:
                reasons.append(f"{field}_mismatch")

    unique_reasons = tuple(dict.fromkeys(reasons))
    verified = not unique_reasons
    return RuntimeIdentityDecision(
        newEntriesAllowed=verified,
        route=RUNTIME_IDENTITY_VERIFIED if verified else RUNTIME_IDENTITY_UNVERIFIED,
        reasonCodes=unique_reasons,
    )


def assert_runtime_identity(
    identity: RuntimeIdentity | None,
    *,
    expected: Mapping[str, Any] | None = None,
) -> RuntimeIdentity:
    decision = evaluate_runtime_identity(identity, expected=expected)
    if not decision.newEntriesAllowed:
        details = ",".join(decision.reasonCodes) or "unknown"
        raise RuntimeIdentityMismatch(f"{decision.route}: {details}")
    assert identity is not None
    return identity
