"""Read-only, hash-verified projection of one bounded Quant campaign."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .config import get_quant_engine_path


CAMPAIGN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path.name}")
    return value


def build_backtest_screening_projection(
    campaign_id: str,
    *,
    quant_root: Path | str | None = None,
) -> dict[str, Any]:
    if not CAMPAIGN_ID_PATTERN.fullmatch(campaign_id):
        raise ValueError("invalid campaign id")
    root = Path(quant_root) if quant_root is not None else get_quant_engine_path()
    campaign_dir = root / "reports" / "backtest_screening" / campaign_id
    if not campaign_dir.is_dir():
        raise FileNotFoundError("backtest campaign not found")
    manifest = _load_json(campaign_dir / "artifact_manifest.json")
    verified = []
    for artifact in manifest.get("artifacts") or []:
        relative = str(artifact.get("path") or "")
        candidate = (root / relative).resolve() if relative.startswith("reports/") else (campaign_dir / relative).resolve()
        if campaign_dir.resolve() not in candidate.parents and candidate != campaign_dir.resolve():
            raise ValueError("artifact manifest path escapes campaign")
        if not candidate.is_file():
            raise ValueError(f"campaign artifact missing: {relative}")
        actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if actual != artifact.get("sha256"):
            raise ValueError(f"campaign artifact hash mismatch: {relative}")
        verified.append(relative)

    summary = _load_json(campaign_dir / "campaign_summary.json")
    console = _load_json(campaign_dir / "console_projection.json")
    budget = _load_json(campaign_dir / "experiment_budget.json")
    failures = _load_json(campaign_dir / "failure_attribution.json")
    gates = _load_json(campaign_dir / "gate_matrix.json")
    generation = _load_json(campaign_dir / "candidate_releases" / "generation_summary.json")
    release_files = []
    release_dir = campaign_dir / "candidate_releases"
    if release_dir.is_dir():
        for path in sorted(release_dir.glob("*.json")):
            if path.name in {"generation_summary.json", "demo_risk_profile.json"}:
                continue
            payload = _load_json(path)
            if payload.get("schemaVersion") == "strategy_validation_release_v1":
                release_files.append({
                    "releaseId": payload.get("releaseId"),
                    "releaseHash": payload.get("releaseHash"),
                    "candidateId": payload.get("candidateId"),
                    "approved": False,
                })
    formal_count = int(summary.get("formalPassCount") or console.get("formalPassCount") or 0)
    return {
        "campaignId": campaign_id,
        "readOnly": True,
        "hashesVerified": True,
        "verifiedArtifactCount": len(verified),
        "dataReadiness": summary.get("dataReadiness") or console.get("dataReadiness") or {},
        "externalReferences": summary.get("externalReferences") or {},
        "factorShortlist": summary.get("factorShortlist") or console.get("factorShortlist") or {},
        "preregistration": summary.get("preregistration") or {},
        "candidateCount": int(summary.get("candidateCount") or 0),
        "prescreenPassCount": int(summary.get("prescreenPassCount") or 0),
        "fullBacktestCount": int(summary.get("fullBacktestCount") or 0),
        "basePassCount": int(summary.get("basePassCount") or 0),
        "formalPassCount": formal_count,
        "failureAttribution": failures,
        "gateMatrix": gates,
        "experimentBudget": budget,
        "releaseCount": int(generation.get("releaseCount") or len(release_files)),
        "candidateReleases": release_files,
        "ordersCreated": 0,
        "approvalsCreated": 0,
    }
