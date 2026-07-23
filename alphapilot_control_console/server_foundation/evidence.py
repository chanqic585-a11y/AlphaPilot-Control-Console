"""Truthful, reproducible evidence for the V63 local-first foundation."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import FOUNDATION_ROLES


_EXPECTED_ROLES = tuple(role.value for role in FOUNDATION_ROLES)
_UNSAFE_ROLE_FLAGS = (
    "orderCapabilityEnabled",
    "demoArmAllowed",
    "liveArmAllowed",
    "withdrawAllowed",
)


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _input_hash(value: Mapping[str, Any]) -> str:
    return _sha256_bytes(_canonical_json(value))


def _copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _require_false_flags(
    value: Mapping[str, Any],
    flags: Sequence[str],
    *,
    error_prefix: str,
) -> None:
    for flag in flags:
        if value.get(flag) is not False:
            raise ValueError(f"{error_prefix}:{flag}")


def _validate_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("mode") != "shadow_no_order":
        raise ValueError("foundation_manifest_not_shadow_no_order")
    if manifest.get("orderCapabilityEnabled") is not False:
        raise ValueError("foundation_manifest_order_capability_enabled")

    roles = manifest.get("roles")
    if not isinstance(roles, list):
        raise ValueError("foundation_manifest_roles_incomplete")
    role_names = [row.get("role") for row in roles if isinstance(row, Mapping)]
    if sorted(role_names) != sorted(_EXPECTED_ROLES):
        raise ValueError("foundation_manifest_roles_incomplete")
    if len(set(role_names)) != len(_EXPECTED_ROLES):
        raise ValueError("foundation_manifest_roles_duplicated")

    total_cpu = 0.0
    total_memory_mb = int(manifest.get("hostReserveMemoryMb", 0))
    ports: list[int] = []
    for row in roles:
        if row.get("enabled") is not True:
            raise ValueError(f"foundation_manifest_role_disabled:{row.get('role')}")
        total_cpu += float(row.get("cpu", 0))
        total_memory_mb += int(row.get("memoryMb", 0))
        ports.append(int(row.get("port", 0)))
    if total_cpu > 4.0:
        raise ValueError("foundation_manifest_cpu_budget_exceeded")
    if total_memory_mb > 8192:
        raise ValueError("foundation_manifest_memory_budget_exceeded")
    if len(set(ports)) != len(_EXPECTED_ROLES) or any(port <= 0 for port in ports):
        raise ValueError("foundation_manifest_ports_invalid")


def _validated_health_roles(
    health: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    roles = health.get("roles")
    if not isinstance(roles, list):
        raise ValueError("foundation_health_roles_incomplete")
    role_map = {
        str(row.get("role")): row
        for row in roles
        if isinstance(row, Mapping) and row.get("role")
    }
    if sorted(role_map) != sorted(_EXPECTED_ROLES) or len(roles) != len(
        _EXPECTED_ROLES
    ):
        raise ValueError("foundation_health_roles_incomplete")
    if health.get("healthy") is not True:
        raise ValueError("foundation_health_not_healthy")
    if int(health.get("healthyRoleCount", -1)) != len(_EXPECTED_ROLES):
        raise ValueError("foundation_health_count_mismatch")
    if int(health.get("expectedRoleCount", -1)) != len(_EXPECTED_ROLES):
        raise ValueError("foundation_health_count_mismatch")
    if health.get("manifestHash") != manifest.get("manifestHash"):
        raise ValueError("foundation_health_manifest_hash_mismatch")
    if health.get("configHash") != manifest.get("configHash"):
        raise ValueError("foundation_health_config_hash_mismatch")
    if health.get("orderCapabilityEnabled") is not False:
        raise ValueError("foundation_health_order_capability_enabled")

    for role in _EXPECTED_ROLES:
        row = role_map[role]
        if row.get("healthy") is not True:
            raise ValueError(f"foundation_health_role_unhealthy:{role}")
        if row.get("status") != "healthy_shadow_no_order":
            raise ValueError(f"foundation_health_role_status_invalid:{role}")
        if row.get("manifestHash") != manifest.get("manifestHash"):
            raise ValueError(f"foundation_health_manifest_hash_mismatch:{role}")
        if row.get("configHash") != manifest.get("configHash"):
            raise ValueError(f"foundation_health_config_hash_mismatch:{role}")
        reconciliation = row.get("reconciliation")
        if not isinstance(reconciliation, Mapping) or reconciliation.get(
            "passed"
        ) is not True:
            raise ValueError(f"foundation_health_reconciliation_failed:{role}")
        _require_false_flags(
            row,
            _UNSAFE_ROLE_FLAGS,
            error_prefix=f"foundation_health_unsafe:{role}",
        )
    return role_map


def _validate_resume(
    initial_roles: Mapping[str, Mapping[str, Any]],
    resumed_roles: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    transitions: list[dict[str, Any]] = []
    for role in _EXPECTED_ROLES:
        initial = initial_roles[role]
        resumed = resumed_roles[role]
        initial_token = int(initial.get("fencingToken", 0))
        resumed_token = int(resumed.get("fencingToken", 0))
        prior_token = resumed.get("resumedCheckpointFencingToken")
        if (
            resumed.get("resumedFromCheckpoint") is not True
            or resumed.get("checkpointResumeDisposition") != "resumed_same_identity"
            or int(prior_token or 0) != initial_token
            or resumed_token <= initial_token
            or int(resumed.get("cycleCount", 0))
            <= int(initial.get("cycleCount", 0))
        ):
            raise ValueError(f"foundation_resume_not_verified:{role}")
        transitions.append(
            {
                "role": role,
                "initialFencingToken": initial_token,
                "resumedFencingToken": resumed_token,
                "initialCycleCount": int(initial.get("cycleCount", 0)),
                "resumedCycleCount": int(resumed.get("cycleCount", 0)),
                "disposition": resumed.get("checkpointResumeDisposition"),
            }
        )
    return {
        "sameIdentityResumeVerified": True,
        "roleTransitions": transitions,
    }


def _validate_sqlite(
    backup_receipt: Mapping[str, Any],
    restore_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if backup_receipt.get("integrityPassed") is not True:
        raise ValueError("sqlite_backup_integrity_failed")
    if restore_receipt.get("integrityPassed") is not True:
        raise ValueError("sqlite_restore_integrity_failed")
    if backup_receipt.get("sha256") != restore_receipt.get("sha256"):
        raise ValueError("sqlite_backup_restore_hash_mismatch")
    if backup_receipt.get("tableCounts") != restore_receipt.get("tableCounts"):
        raise ValueError("sqlite_backup_restore_table_counts_mismatch")
    if backup_receipt.get("userVersion") != restore_receipt.get("userVersion"):
        raise ValueError("sqlite_backup_restore_user_version_mismatch")

    guard = restore_receipt.get("guard")
    if not isinstance(guard, Mapping):
        raise ValueError("sqlite_restore_guard_missing")
    if (
        guard.get("allRolesStopped") is not True
        or guard.get("demoArmed") is not False
        or guard.get("liveArmed") is not False
        or int(guard.get("activeLeaseCount", -1)) != 0
    ):
        raise ValueError("sqlite_restore_guard_unsafe")
    return {
        "backupRestoreVerified": True,
        "sha256": backup_receipt.get("sha256"),
        "integrityPassed": True,
        "journalMode": backup_receipt.get("journalMode"),
        "userVersion": backup_receipt.get("userVersion"),
        "tableCounts": _copy_json(backup_receipt.get("tableCounts", {})),
        "restoreGuard": _copy_json(guard),
    }


def _validate_track_b(track_b: Mapping[str, Any]) -> None:
    if track_b.get("status") != "preregistered_dry_preparation_only":
        raise ValueError("track_b_not_dry_preregistered")
    for field in ("formalRunCount", "lockedOosReadCount", "resultReadCount"):
        if int(track_b.get(field, -1)) != 0:
            raise ValueError(f"track_b_result_boundary_violated:{field}")
    safety = track_b.get("safety")
    if not isinstance(safety, Mapping):
        raise ValueError("track_b_safety_missing")
    _require_false_flags(
        safety,
        (
            "armAllowed",
            "liveAllowed",
            "orderCapabilityEnabled",
            "releaseApprovalAllowed",
            "withdrawAllowed",
        ),
        error_prefix="track_b_safety_unsafe",
    )


def _validate_track_c(track_c: Mapping[str, Any]) -> None:
    if track_c.get("overallStatus") not in {"passed", "completed_with_blockers"}:
        raise ValueError("track_c_status_invalid")
    checks = track_c.get("checks")
    if not isinstance(checks, Mapping) or not checks:
        raise ValueError("track_c_checks_missing")
    statuses = [row.get("status") for row in checks.values() if isinstance(row, Mapping)]
    if len(statuses) != len(checks) or any(
        status not in {"passed", "blocked", "not_run"} for status in statuses
    ):
        raise ValueError("track_c_check_status_invalid")
    _require_false_flags(
        track_c,
        (
            "orderCapabilityEnabled",
            "demoArmAllowed",
            "liveArmAllowed",
            "withdrawAllowed",
        ),
        error_prefix="track_c_safety_unsafe",
    )


def _validate_parallel_manifest(
    parallel_track_manifest: Mapping[str, Any],
    track_b: Mapping[str, Any],
) -> None:
    if parallel_track_manifest.get("campaignId") != track_b.get("campaignId"):
        raise ValueError("parallel_track_campaign_mismatch")
    safety = parallel_track_manifest.get("safety")
    if not isinstance(safety, Mapping):
        raise ValueError("parallel_track_safety_missing")
    _require_false_flags(
        safety,
        (
            "demoArmAllowed",
            "liveArmAllowed",
            "orderCapabilityEnabled",
            "withdrawAllowed",
        ),
        error_prefix="parallel_track_safety_unsafe",
    )


def build_foundation_evidence(
    *,
    manifest: Mapping[str, Any],
    initial_health: Mapping[str, Any],
    resumed_health: Mapping[str, Any],
    backup_receipt: Mapping[str, Any],
    restore_receipt: Mapping[str, Any],
    track_b: Mapping[str, Any],
    track_c: Mapping[str, Any],
    parallel_track_manifest: Mapping[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Validate source receipts and build one truthful V63 evidence object."""

    _validate_manifest(manifest)
    initial_roles = _validated_health_roles(initial_health, manifest)
    resumed_roles = _validated_health_roles(resumed_health, manifest)
    checkpoint_resume = _validate_resume(initial_roles, resumed_roles)
    sqlite_summary = _validate_sqlite(backup_receipt, restore_receipt)
    _validate_track_b(track_b)
    _validate_track_c(track_c)
    _validate_parallel_manifest(parallel_track_manifest, track_b)

    generated = generated_at or datetime.now(timezone.utc).isoformat()
    track_c_checks = _copy_json(track_c.get("checks", {}))
    research_has_blockers = any(
        row.get("status") in {"blocked", "not_run"}
        for row in track_c_checks.values()
    )
    return {
        "schemaVersion": "alphapilot_v63_foundation_evidence_v1",
        "generatedAt": generated,
        "status": (
            "foundation_passed_with_research_blockers"
            if research_has_blockers
            else "foundation_passed"
        ),
        "foundationIdentity": {
            "deploymentId": manifest.get("deploymentId"),
            "repositoryCommit": manifest.get("repositoryCommit"),
            "repositoryTag": manifest.get("repositoryTag"),
            "manifestHash": manifest.get("manifestHash"),
            "configHash": manifest.get("configHash"),
            "mode": manifest.get("mode"),
        },
        "runtime": {
            "healthy": True,
            "healthyRoleCount": len(_EXPECTED_ROLES),
            "roles": list(_EXPECTED_ROLES),
            "initialHealthHash": _input_hash(initial_health),
            "resumedHealthHash": _input_hash(resumed_health),
        },
        "checkpointResume": checkpoint_resume,
        "sqlite": sqlite_summary,
        "trackB": {
            "campaignId": track_b.get("campaignId"),
            "status": track_b.get("status"),
            "formalRunCount": int(track_b.get("formalRunCount", 0)),
            "lockedOosReadCount": int(track_b.get("lockedOosReadCount", 0)),
            "resultReadCount": int(track_b.get("resultReadCount", 0)),
            "sourceHash": _input_hash(track_b),
        },
        "trackC": {
            "overallStatus": track_c.get("overallStatus"),
            "counts": _copy_json(track_c.get("counts", {})),
            "checks": track_c_checks,
            "sourceHash": _input_hash(track_c),
        },
        "parallelTracks": {
            "artifactCount": int(
                parallel_track_manifest.get("artifactCount", 0)
            ),
            "manifestHash": parallel_track_manifest.get("manifestHash"),
            "sourceHash": _input_hash(parallel_track_manifest),
        },
        "sourceReceiptHashes": {
            "manifest": _input_hash(manifest),
            "backup": _input_hash(backup_receipt),
            "restore": _input_hash(restore_receipt),
        },
        "safety": {
            "ordersAllowed": False,
            "demoArmAllowed": False,
            "liveArmAllowed": False,
            "withdrawAllowed": False,
        },
    }


def _render_closeout(evidence: Mapping[str, Any]) -> str:
    track_c = evidence["trackC"]
    lines = [
        "# AlphaPilot V63.0 Local-first Server Foundation Closeout",
        "",
        f"- 状态：`{evidence['status']}`",
        f"- 运行角色：`{evidence['runtime']['healthyRoleCount']}/6`",
        "- 运行模式：`shadow_no_order`",
        "- 同身份断点续跑：已验证",
        "- SQLite Online Backup / Guarded Restore：已验证",
        f"- Track B：`{evidence['trackB']['status']}`，正式运行 `0` 次",
        f"- Track C：`{track_c['overallStatus']}`",
        "- Demo ARM：关闭",
        "- Live ARM：关闭",
        "- 订单能力：关闭",
        "- Withdraw：关闭",
        "",
        "## Track C 真实状态",
        "",
    ]
    for name, row in sorted(track_c["checks"].items()):
        lines.append(f"- `{name}`：`{row['status']}`")
    lines.extend(
        [
            "",
            "V63 基础设施验收通过不代表被阻塞或未运行的研究任务已通过。",
            "",
        ]
    )
    return "\n".join(lines)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_foundation_evidence(
    output_root: Path | str,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Atomically write evidence, closeout, and a manifest for both artifacts."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    evidence_path = root / "v63_foundation_evidence.json"
    closeout_path = root / "v63_foundation_closeout.md"
    manifest_path = root / "artifact_manifest.json"

    evidence_bytes = (
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    closeout_bytes = _render_closeout(evidence).encode("utf-8")
    _atomic_write(evidence_path, evidence_bytes)
    _atomic_write(closeout_path, closeout_bytes)

    artifacts = []
    for path in (evidence_path, closeout_path):
        content = path.read_bytes()
        artifacts.append(
            {
                "path": path.name,
                "sha256": _sha256_bytes(content),
                "sizeBytes": len(content),
            }
        )
    manifest: dict[str, Any] = {
        "schemaVersion": "alphapilot_v63_foundation_artifact_manifest_v1",
        "artifactCount": len(artifacts),
        "artifacts": artifacts,
    }
    manifest["manifestHash"] = _sha256_bytes(_canonical_json(manifest))
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    _atomic_write(manifest_path, manifest_bytes)

    return {
        "status": "written",
        "artifactCount": len(artifacts),
        "manifestHash": manifest["manifestHash"],
        "outputRoot": str(root),
    }
