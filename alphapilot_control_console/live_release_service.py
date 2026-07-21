"""Discover and validate immutable LiveRelease exports from Quant Engine."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .config import DATA_DIR, get_quant_engine_path


LOCAL_LIVE_RELEASE_DIR = DATA_DIR / "live_releases"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _reject_sensitive(value: Any, path: str = "liveRelease") -> None:
    sensitive = ("apikey", "secretkey", "passphrase", "password", "credential", "withdrawaddress")
    if isinstance(value, dict):
        for key, child in value.items():
            compact = str(key).replace("_", "").replace("-", "").lower()
            disabled = child is False or child is None or child == ""
            if any(part in compact for part in sensitive) and not disabled:
                raise ValueError(f"Credential-like field is forbidden in LiveRelease: {path}.{key}")
            _reject_sensitive(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{path}[{index}]")


def validate_live_release_export(export: dict[str, Any]) -> None:
    if export.get("schemaVersion") != "alphapilot_live_release_v1":
        raise ValueError("Unsupported LiveRelease export schema")
    if export.get("status") != "live_canary_approved":
        raise ValueError("LiveRelease is not Canary-approved")
    release = export.get("release") if isinstance(export.get("release"), dict) else {}
    expected_hash = hashlib.sha256(_canonical(release).encode("utf-8")).hexdigest()
    if export.get("liveReleaseHash") != expected_hash:
        raise ValueError("LiveRelease checksum mismatch")
    if release.get("schemaVersion") != "live_release_contract_v1":
        raise ValueError("Unsupported LiveRelease contract schema")
    boundary = release.get("executionBoundary") if isinstance(release.get("executionBoundary"), dict) else {}
    if boundary.get("environment") != "okx_live_canary_only":
        raise PermissionError("LiveRelease environment is not OKX Live Canary")
    if boundary.get("manualReleaseApprovalRequired") is not True:
        raise PermissionError("LiveRelease lacks the manual release approval boundary")
    if boundary.get("mechanicalExecutionAllowed") is not True or boundary.get("withdrawAllowed") is not False:
        raise PermissionError("LiveRelease execution boundary is invalid")
    protection = release.get("protectionPolicy") if isinstance(release.get("protectionPolicy"), dict) else {}
    required_true = (
        "attachedTakeProfitRequired",
        "attachedStopLossRequired",
        "privateStateReconciliationRequired",
        "restartRecoveryRequired",
        "unknownStatePausesEntries",
        "killSwitchRequired",
    )
    if any(protection.get(key) is not True for key in required_true):
        raise PermissionError("LiveRelease protection policy is incomplete")
    if float(protection.get("minimumRewardRiskRatio") or 0) <= 0:
        raise PermissionError("LiveRelease reward/risk boundary must be positive")
    _reject_sensitive(export)


def _paths() -> list[Path]:
    paths: list[Path] = []
    for directory in (LOCAL_LIVE_RELEASE_DIR, get_quant_engine_path() / "reports"):
        if directory.exists():
            paths.extend(directory.glob("live_release_*.json"))
    return sorted(set(path.resolve() for path in paths))


def discover_live_releases() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    releases: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in _paths():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("LiveRelease JSON must be an object")
            validate_live_release_export(payload)
            release_id = str(payload.get("liveReleaseId") or "")
            if not release_id:
                raise ValueError("LiveRelease id is required")
            if release_id not in seen:
                seen.add(release_id)
                releases.append({**payload, "sourcePath": str(path)})
        except (OSError, json.JSONDecodeError, ValueError, PermissionError) as error:
            rejected.append({"file": str(path), "reason": type(error).__name__})
    return releases, rejected


def build_live_release_status() -> dict[str, Any]:
    releases, rejected = discover_live_releases()
    return {
        "version": "V13.25.0",
        "source": "live_release_discovery_v1",
        "environment": "okx_live",
        "demoReleaseAccepted": False,
        "withdrawAllowed": False,
        "summary": {
            "approvedLiveReleaseCount": len(releases),
            "rejectedExportCount": len(rejected),
        },
        "releases": releases,
        "rejectedExports": rejected,
        "blockers": [] if releases else ["no_approved_live_release"],
    }
