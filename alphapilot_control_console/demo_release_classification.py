from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .config import DATA_DIR
from .demo_release_classification_store import DemoReleaseClassificationStore


DEFAULT_CLASSIFICATION_PATH = DATA_DIR / "demo_release_classification.sqlite"


def release_file_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def classify_release_files(
    paths: Iterable[Path],
    *,
    store: DemoReleaseClassificationStore,
    reason: str,
) -> dict[str, Any]:
    before: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    selected = [Path(path).expanduser().resolve() for path in paths]
    for path in selected:
        before[str(path)] = release_file_hash(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Release contract must be an object: {path.name}")
        release_id = str(payload.get("demoReleaseId") or "").strip()
        if not release_id:
            raise ValueError(f"Release contract is missing demoReleaseId: {path.name}")
        rows.append(
            store.classify_legacy_diagnostic(
                release_id=release_id,
                release_hash=before[str(path)],
                reason=reason,
            )
        )
    after = {str(path): release_file_hash(path) for path in selected}
    if before != after:
        raise RuntimeError("release_file_changed_during_classification")
    return {
        "classifiedCount": len(rows),
        "releaseIds": [row["releaseId"] for row in rows],
        "fileHashesUnchanged": True,
        "beforeHashes": before,
        "afterHashes": after,
    }


def release_classification(
    release_id: str,
    *,
    classification_path: Path = DEFAULT_CLASSIFICATION_PATH,
) -> dict[str, Any] | None:
    path = Path(classification_path)
    if not path.exists():
        return None
    store = DemoReleaseClassificationStore(path)
    try:
        return store.get_latest(release_id)
    finally:
        store.close()


def legacy_release_projection(
    paths: Iterable[Path],
    *,
    classification_path: Path = DEFAULT_CLASSIFICATION_PATH,
) -> dict[str, Any]:
    path = Path(classification_path)
    classifications: dict[str, dict[str, Any]] = {}
    if path.exists():
        store = DemoReleaseClassificationStore(path)
        try:
            classifications = {row["releaseId"]: row for row in store.list_all()}
        finally:
            store.close()

    candidates: list[dict[str, Any]] = []
    family_counts: dict[str, int] = {}
    for contract_path in paths:
        payload = json.loads(Path(contract_path).read_text(encoding="utf-8"))
        release_id = str(payload.get("demoReleaseId") or "")
        classification = classifications.get(release_id)
        if not classification or classification.get("releasePurpose") != "legacy_diagnostic":
            continue
        strategy = payload.get("strategy") if isinstance(payload.get("strategy"), dict) else {}
        family_id = str(strategy.get("familyKey") or payload.get("strategyCandidateId") or "unknown")
        family_counts[family_id] = family_counts.get(family_id, 0) + 1
        candidates.append(
            {
                "releaseId": release_id,
                "strategyCandidateId": str(payload.get("strategyCandidateId") or ""),
                "strategyFamilyId": family_id,
                "classification": classification,
            }
        )
    for row in candidates:
        row["variantLabel"] = (
            "同源变体，不是独立假设"
            if family_counts.get(row["strategyFamilyId"], 0) > 1
            else "历史诊断 Release"
        )
    return {
        "legacyDiagnosticCount": len(candidates),
        "independentFamilyCount": len(family_counts),
        "releases": candidates,
    }
