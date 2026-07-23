"""Fresh-directory packaging helpers for the V62.4.2 acceptance delta."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def create_fresh_package_root(path: Path | str) -> Path:
    """Create a package root only when no previous output exists."""

    root = Path(path)
    if root.exists():
        raise FileExistsError(f"fresh_output_directory_required:{root}")
    root.mkdir(parents=True)
    return root


def copy_current_quality_evidence(
    current_checks_path: Path | str,
    destination: Path | str,
) -> list[str]:
    """Copy the quality receipt and only the log files it references."""

    checks_path = Path(current_checks_path)
    target = Path(destination)
    payload = json.loads(checks_path.read_text(encoding="utf-8"))
    checks = payload.get("checks")
    if not isinstance(checks, dict):
        raise ValueError("current_quality_checks_missing")

    log_names = {
        str(value["log"])
        for value in checks.values()
        if isinstance(value, dict) and isinstance(value.get("log"), str)
    }
    target.mkdir(parents=True, exist_ok=True)
    receipt_name = "v62_4_2_current_checks.json"
    shutil.copy2(checks_path, target / receipt_name)
    copied = {receipt_name}
    for name in sorted(log_names):
        relative = Path(name)
        if (
            relative.is_absolute()
            or len(relative.parts) != 1
            or name in {"", ".", ".."}
        ):
            raise ValueError(f"unsafe_current_quality_log_path:{name}")
        source = checks_path.parent / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, target / relative.name)
        copied.add(relative.name)
    return sorted(copied)


def build_artifact_manifest(package_root: Path | str) -> dict[str, Any]:
    """Hash every packaged file except the self-referential manifest."""

    root = Path(package_root)
    artifacts: list[dict[str, object]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative == "artifact_manifest.json":
            continue
        artifacts.append(
            {
                "relativePath": relative,
                "sizeBytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schemaVersion": "v62_4_2_delta_artifact_manifest_v1",
        "artifactCount": len(artifacts),
        "artifacts": artifacts,
    }


def verify_manifest_coverage(
    package_root: Path | str,
    manifest: dict[str, Any],
) -> dict[str, object]:
    """Check exact path coverage before independent hash verification."""

    root = Path(package_root)
    expected = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.relative_to(root).as_posix() != "artifact_manifest.json"
    }
    rows = manifest.get("artifacts")
    if not isinstance(rows, list):
        return {
            "schemaVersion": "v62_4_2_manifest_coverage_v1",
            "passed": False,
            "findings": ["manifest_artifacts_missing"],
        }
    actual = {
        str(row.get("relativePath") or "")
        for row in rows
        if isinstance(row, dict)
    }
    findings = [
        *(f"unlisted:{path}" for path in sorted(expected - actual)),
        *(f"missing:{path}" for path in sorted(actual - expected)),
    ]
    if len(actual) != len(rows):
        findings.append("duplicate_manifest_paths")
    if int(manifest.get("artifactCount") or -1) != len(rows):
        findings.append("artifact_count_mismatch")
    return {
        "schemaVersion": "v62_4_2_manifest_coverage_v1",
        "passed": not findings,
        "findings": findings,
        "artifactCount": len(rows),
    }
