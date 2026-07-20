from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class BaselineAuditError(RuntimeError):
    pass


EXECUTION_SENSITIVE_PATHS = (
    "alphapilot_control_console/auto_execution_engine.py",
    "alphapilot_control_console/demo_arbitrator.py",
    "alphapilot_control_console/demo_entry_latency_policy.py",
    "alphapilot_control_console/demo_execution_engine.py",
    "alphapilot_control_console/demo_market_scan_service.py",
    "alphapilot_control_console/demo_prewarmed_market_state.py",
    "alphapilot_control_console/portfolio_risk.py",
    "alphapilot_control_console/unified_auto_execution_adapters.py",
    "alphapilot_control_console/unified_auto_execution_controller.py",
    "alphapilot_control_console/unified_auto_execution_runner.py",
    "alphapilot_control_console/exchange_connectors/okx_demo_client.py",
    "alphapilot_control_console/exchange_connectors/okx_demo_private_ws.py",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_json_bytes(value: bytes, *, source: str) -> dict[str, Any]:
    try:
        payload = json.loads(value.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BaselineAuditError(f"invalid JSON evidence: {source}") from error
    if not isinstance(payload, dict):
        raise BaselineAuditError(f"JSON evidence must be an object: {source}")
    return payload


def read_zip_json(bundle: zipfile.ZipFile, name: str) -> dict[str, Any]:
    try:
        value = bundle.read(name)
    except KeyError as error:
        raise BaselineAuditError(f"missing ZIP evidence: {name}") from error
    return _load_json_bytes(value, source=name)


def verify_evidence_zip(
    zip_path: Path | str,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    path = Path(zip_path)
    if not path.is_file():
        raise BaselineAuditError(f"evidence ZIP does not exist: {path}")

    zip_sha256 = _sha256_bytes(path.read_bytes())
    if zip_sha256.lower() != str(expected_sha256).lower():
        raise BaselineAuditError(
            f"evidence ZIP hash mismatch: expected {expected_sha256}, got {zip_sha256}"
        )

    missing: list[str] = []
    hash_mismatches: list[dict[str, Any]] = []
    size_mismatches: list[dict[str, Any]] = []
    with zipfile.ZipFile(path, "r") as bundle:
        corrupt_name = bundle.testzip()
        if corrupt_name is not None:
            raise BaselineAuditError(f"evidence ZIP CRC failure: {corrupt_name}")
        manifest = read_zip_json(bundle, "artifact_manifest.json")
        files = manifest.get("files")
        if not isinstance(files, list):
            raise BaselineAuditError("artifact manifest files must be an array")

        verified = 0
        for item in files:
            if not isinstance(item, dict) or not item.get("path"):
                raise BaselineAuditError("artifact manifest contains an invalid row")
            name = str(item["path"])
            try:
                value = bundle.read(name)
            except KeyError:
                missing.append(name)
                continue
            actual_sha256 = _sha256_bytes(value)
            expected_artifact_sha256 = str(item.get("sha256") or "")
            if actual_sha256 != expected_artifact_sha256:
                hash_mismatches.append(
                    {
                        "path": name,
                        "expected": expected_artifact_sha256,
                        "actual": actual_sha256,
                    }
                )
                continue
            expected_bytes = item.get("bytes")
            if expected_bytes is not None and len(value) != int(expected_bytes):
                size_mismatches.append(
                    {"path": name, "expected": int(expected_bytes), "actual": len(value)}
                )
                continue
            verified += 1

    declared_count = len(files)
    manifest_count = int(manifest.get("fileCount") or declared_count)
    blockers: list[str] = []
    if manifest_count != declared_count:
        blockers.append("manifest_file_count_mismatch")
    if missing:
        blockers.append("manifest_artifacts_missing")
    if hash_mismatches:
        blockers.append("manifest_artifact_hash_mismatch")
    if size_mismatches:
        blockers.append("manifest_artifact_size_mismatch")

    return {
        "schemaVersion": "v54_baseline_evidence_verification_v1",
        "status": "passed" if not blockers else "blocked",
        "zipPath": str(path.resolve()),
        "zipSha256": zip_sha256,
        "crcPassed": True,
        "manifestStatus": manifest.get("status"),
        "manifestDeclaredFileCount": manifest_count,
        "declaredArtifactCount": declared_count,
        "verifiedArtifactCount": verified,
        "missingArtifacts": missing,
        "hashMismatches": hash_mismatches,
        "sizeMismatches": size_mismatches,
        "blockers": blockers,
    }


def build_release_to_head_execution_diff_audit(
    release: Mapping[str, Any],
    *,
    final_head: str,
    changed_files: Iterable[str],
) -> dict[str, Any]:
    identity = release.get("executionIdentity")
    if not isinstance(identity, Mapping):
        raise BaselineAuditError("release executionIdentity is missing")
    release_commit = str(identity.get("consoleExecutionCommit") or "")
    if not release_commit:
        raise BaselineAuditError("release consoleExecutionCommit is missing")

    normalized = sorted({str(path).replace("\\", "/") for path in changed_files})
    sensitive = [path for path in normalized if path in EXECUTION_SENSITIVE_PATHS]
    control_or_projection = [path for path in normalized if path not in sensitive]
    return {
        "schemaVersion": "v54_release_to_head_execution_diff_audit_v1",
        "status": "passed" if not sensitive else "blocked",
        "releaseId": release.get("releaseId"),
        "releaseHash": release.get("releaseHash"),
        "releaseExecutionCommit": release_commit,
        "finalHead": str(final_head),
        "changedFileCount": len(normalized),
        "executionSensitiveChangedFiles": sensitive,
        "controlOrProjectionChangedFiles": control_or_projection,
        "blockers": [] if not sensitive else ["execution_path_changed_after_release_freeze"],
    }


def audit_repository_release_binding(
    repo_root: Path | str,
    release: Mapping[str, Any],
) -> dict[str, Any]:
    root = Path(repo_root)
    identity = release.get("executionIdentity")
    if not isinstance(identity, Mapping):
        raise BaselineAuditError("release executionIdentity is missing")
    release_commit = str(identity.get("consoleExecutionCommit") or "")
    if not release_commit:
        raise BaselineAuditError("release consoleExecutionCommit is missing")

    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise BaselineAuditError(completed.stderr.strip() or "git audit command failed")
        return completed.stdout.strip()

    final_head = git("rev-parse", "HEAD")
    changed_output = git("diff", "--name-only", f"{release_commit}..{final_head}")
    changed_files = [row for row in changed_output.splitlines() if row.strip()]
    return build_release_to_head_execution_diff_audit(
        release,
        final_head=final_head,
        changed_files=changed_files,
    )


def reconcile_strategy_order_scope(
    *,
    package_manifest: Mapping[str, Any],
    approval_request: Mapping[str, Any],
    engineering_smoke: Mapping[str, Any],
    strategy_ledger_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    manifest_count = int(package_manifest.get("strategyOrderCount") or 0)
    approval_strategy_count = int(approval_request.get("strategyOrderCount") or 0)
    approval_order_count = int(approval_request.get("orderCount") or 0)
    ledger_count = len(strategy_ledger_rows)
    observed = {
        manifest_count,
        approval_strategy_count,
        approval_order_count,
        ledger_count,
    }
    blockers: list[str] = []
    if len(observed) != 1:
        blockers.append("strategy_order_count_mismatch")

    return {
        "schemaVersion": "v54_strategy_order_scope_reconciliation_v1",
        "status": "passed" if not blockers else "blocked",
        "strategyScope": {
            "orderCount": ledger_count,
            "manifestOrderCount": manifest_count,
            "approvalStrategyOrderCount": approval_strategy_count,
            "approvalOrderCount": approval_order_count,
        },
        "engineeringSmokeScope": {
            "orderAttemptCount": int(engineering_smoke.get("orderAttempts") or 0),
            "fillCount": int(engineering_smoke.get("fills") or 0),
            "excludedFromStrategyEvidence": True,
        },
        "blockers": blockers,
    }


def write_json(path: Path | str, payload: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
