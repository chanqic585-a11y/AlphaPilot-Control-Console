"""Build a deterministic manifest for the V59 adaptive-learning evidence set."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_artifact_manifest(
    root: Path | str,
    *,
    generated_at: str,
    status: str,
) -> dict[str, Any]:
    evidence_root = Path(root).expanduser().resolve()
    files = sorted(
        path
        for path in evidence_root.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"
    )
    manifest: dict[str, Any] = {
        "schemaVersion": "alphapilot_v59_adaptive_learning_manifest_v1",
        "generatedAt": generated_at,
        "status": status,
        "selfReferenceExclusions": ["artifact_manifest.json"],
        "fileCount": len(files),
        "files": [
            {
                "path": path.relative_to(evidence_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in files
        ],
    }
    manifest["manifestHash"] = f"v59_artifact_manifest_{_stable_hash(manifest)}"
    return manifest


def write_artifact_manifest(path: Path | str, payload: dict[str, Any]) -> None:
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(output)
