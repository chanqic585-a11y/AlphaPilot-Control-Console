"""Resource budget validation for a 4 vCPU / 8 GB local server."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


MAX_CPU = 4.0
MAX_MEMORY_MB = 8192
MAX_BATCH_ROLES = 2


class _RoleBudget(Protocol):
    cpu: float
    memoryMb: int


class _ManifestBudget(Protocol):
    roles: dict[object, _RoleBudget]
    hostReserveMemoryMb: int
    maxConcurrentBatchRoles: int


@dataclass(frozen=True)
class ResourceBudgetDecision:
    passed: bool
    totalCpu: float
    workerMemoryMb: int
    hostReserveMemoryMb: int
    totalMemoryMb: int
    maxConcurrentBatchRoles: int
    reasonCodes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": "alphapilot_v63_resource_budget_v1",
            "passed": self.passed,
            "totalCpu": self.totalCpu,
            "workerMemoryMb": self.workerMemoryMb,
            "hostReserveMemoryMb": self.hostReserveMemoryMb,
            "totalMemoryMb": self.totalMemoryMb,
            "maxConcurrentBatchRoles": self.maxConcurrentBatchRoles,
            "reasonCodes": list(self.reasonCodes),
        }


def validate_resource_budget(manifest: _ManifestBudget) -> ResourceBudgetDecision:
    total_cpu = round(sum(float(role.cpu) for role in manifest.roles.values()), 4)
    worker_memory = sum(int(role.memoryMb) for role in manifest.roles.values())
    total_memory = worker_memory + int(manifest.hostReserveMemoryMb)
    reasons: list[str] = []
    if total_cpu > MAX_CPU:
        reasons.append("cpu_exceeds_4_vcpu")
    if total_memory > MAX_MEMORY_MB:
        reasons.append("memory_exceeds_8gb")
    if int(manifest.hostReserveMemoryMb) < 1024:
        reasons.append("host_reserve_below_1gb")
    if not 1 <= int(manifest.maxConcurrentBatchRoles) <= MAX_BATCH_ROLES:
        reasons.append("batch_concurrency_exceeds_limit")
    return ResourceBudgetDecision(
        passed=not reasons,
        totalCpu=total_cpu,
        workerMemoryMb=worker_memory,
        hostReserveMemoryMb=int(manifest.hostReserveMemoryMb),
        totalMemoryMb=total_memory,
        maxConcurrentBatchRoles=int(manifest.maxConcurrentBatchRoles),
        reasonCodes=tuple(reasons),
    )
