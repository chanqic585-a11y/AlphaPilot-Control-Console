"""Discover Live candidate packages and expose a non-executing manual review boundary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import DATA_DIR, get_quant_engine_path
from .live_approval_store import LiveApprovalStore


APPROVAL_STORE_PATH = DATA_DIR / "live_approval.sqlite"
LOCAL_PACKAGE_DIR = DATA_DIR / "live_candidate_packages"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _reject_sensitive_keys(value: Any, path: str = "package") -> None:
    sensitive = ("apikey", "secretkey", "passphrase", "password", "credential", "accesstoken")
    if isinstance(value, dict):
        for key, child in value.items():
            compact = str(key).replace("_", "").replace("-", "").lower()
            safe_disabled_marker = child is False or child is None or child == ""
            if any(part in compact for part in sensitive) and not safe_disabled_marker:
                raise ValueError(f"Credential-like field is forbidden in Live candidate package: {path}.{key}")
            _reject_sensitive_keys(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_sensitive_keys(child, f"{path}[{index}]")


def validate_live_candidate_export(export: dict[str, Any]) -> None:
    if export.get("schemaVersion") != "alphapilot_live_candidate_review_v1":
        raise ValueError("Unsupported Live candidate package schema")
    package = export.get("package") if isinstance(export.get("package"), dict) else {}
    expected_hash = hashlib.sha256(_canonical(package).encode("utf-8")).hexdigest()
    if not export.get("packageHash") or export.get("packageHash") != expected_hash:
        raise ValueError("Live candidate package checksum mismatch")
    if export.get("status") != "awaiting_manual_approval":
        raise ValueError("Live candidate package is not awaiting manual approval")
    boundary = export.get("approvalBoundary") if isinstance(export.get("approvalBoundary"), dict) else {}
    required_false = (
        "automaticApprovalAllowed",
        "approvalEnablesExecution",
        "liveExecutionAdapterPresent",
        "withdrawAllowed",
    )
    if boundary.get("manualApprovalRequired") is not True or any(boundary.get(key) is not False for key in required_false):
        raise PermissionError("Live candidate approval boundary is invalid")
    if package.get("manualApprovalRequired") is not True:
        raise PermissionError("Live candidate package does not require manual approval")
    if any(package.get(key) is not False for key in ("automaticApprovalAllowed", "liveExecutionAdapterPresent", "liveExecutionEnabled", "withdrawAllowed")):
        raise PermissionError("Live candidate package attempted to enable execution")
    _reject_sensitive_keys(export)


def _package_paths() -> list[Path]:
    paths: list[Path] = []
    for directory in (LOCAL_PACKAGE_DIR, get_quant_engine_path() / "reports"):
        if directory.exists():
            paths.extend(directory.glob("live_candidate_package_*.json"))
    return sorted(set(path.resolve() for path in paths))


def discover_live_candidate_packages() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    packages: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in _package_paths():
        try:
            export = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(export, dict):
                raise ValueError("Package JSON must be an object")
            validate_live_candidate_export(export)
            package_id = str(export["liveCandidatePackageId"])
            if package_id not in seen:
                seen.add(package_id)
                packages.append(export)
        except (OSError, json.JSONDecodeError, ValueError, PermissionError) as error:
            rejected.append({"file": str(path), "reason": type(error).__name__})
    return packages, rejected


def build_live_candidate_status() -> dict[str, Any]:
    packages, rejected = discover_live_candidate_packages()
    store = LiveApprovalStore(APPROVAL_STORE_PATH)
    try:
        rows = []
        for export in packages:
            package_id = str(export["liveCandidatePackageId"])
            package_hash = str(export["packageHash"])
            rows.append({**export, "approval": store.get_state(package_id, package_hash)})
        actions = [asdict(action) for action in store.list_actions()[-20:]]
    finally:
        store.close()
    approved = sum(row["approval"]["status"] == "approved_for_future_release_review" for row in rows)
    return {
        "version": "V13.15.0",
        "source": "live_candidate_manual_boundary_v1",
        "summary": {
            "packageCount": len(rows),
            "awaitingApprovalCount": sum(row["approval"]["status"] == "awaiting_manual_approval" for row in rows),
            "approvedForFutureReviewCount": approved,
            "revokedCount": sum(row["approval"]["status"] == "revoked" for row in rows),
            "invalidatedByChecksumCount": sum(row["approval"]["status"] == "checksum_changed_approval_invalid" for row in rows),
            "liveExecutionEnabledCount": 0,
        },
        "packages": rows,
        "recentApprovalActions": actions,
        "rejectedPackages": rejected,
        "blockers": [] if rows else ["no_live_candidate_package"],
        "safetyBoundary": {
            "manualApprovalRequired": True,
            "automaticApprovalAllowed": False,
            "aiApprovalAllowed": False,
            "banditApprovalAllowed": False,
            "mlApprovalAllowed": False,
            "approvalEnablesExecution": False,
            "liveExecutionAdapterPresent": False,
            "withdrawAllowed": False,
            "rawCredentialStorageAllowed": False,
        },
    }


def _find_package(package_id: str, package_hash: str) -> dict[str, Any]:
    packages, _ = discover_live_candidate_packages()
    export = next(
        (item for item in packages if item.get("liveCandidatePackageId") == package_id and item.get("packageHash") == package_hash),
        None,
    )
    if export is None:
        raise ValueError("Checksum-bound Live candidate package was not found")
    return export


def approve_live_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    package_id = str(payload.get("liveCandidatePackageId") or "")
    package_hash = str(payload.get("packageHash") or "")
    export = _find_package(package_id, package_hash)
    package = export["package"]
    risk_budget = package.get("proposedRiskBudget") if isinstance(package.get("proposedRiskBudget"), dict) else {}
    store = LiveApprovalStore(APPROVAL_STORE_PATH)
    try:
        action = store.approve(
            packageId=package_id,
            packageHash=package_hash,
            riskBudget=risk_budget,
            confirmation=str(payload.get("confirmation") or ""),
            actor=str(payload.get("actor") or ""),
        )
    finally:
        store.close()
    return {"ok": True, "action": asdict(action), "liveCandidates": build_live_candidate_status()}


def revoke_live_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    package_id = str(payload.get("liveCandidatePackageId") or "")
    package_hash = str(payload.get("packageHash") or "")
    _find_package(package_id, package_hash)
    store = LiveApprovalStore(APPROVAL_STORE_PATH)
    try:
        action = store.revoke(packageId=package_id, packageHash=package_hash, actor=str(payload.get("actor") or ""))
    finally:
        store.close()
    return {"ok": True, "action": asdict(action), "liveCandidates": build_live_candidate_status()}
