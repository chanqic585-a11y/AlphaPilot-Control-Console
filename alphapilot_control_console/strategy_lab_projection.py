"""Read-only Strategy Lab projection over bounded Quant research evidence."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import get_quant_engine_path


_SOURCE_RELATIVE = Path("research/external_capabilities/vibe_trading")
_INTEGRATION_RELATIVE = Path("reports/integration/v37g_v37h")
_CAMPAIGN_RELATIVE = Path("reports/strategy_acquisition/v37i_v37j")
_MECHANISM_RELATIVE = Path("reports/mechanism_breakthrough")


def _load_json(path: Path, fallback: Any) -> Any:
    if not path.is_file():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except (OSError, csv.Error):
        return []


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _integer(*values: Any) -> int:
    for value in values:
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def _latest_mechanism_research(root: Path) -> Path | None:
    mechanism_root = root / _MECHANISM_RELATIVE
    if not mechanism_root.is_dir():
        return None
    candidates = sorted(
        (
            path / "research"
            for path in mechanism_root.iterdir()
            if (path / "research" / "campaign_summary.json").is_file()
        ),
        key=lambda path: path.parent.name,
    )
    return candidates[-1] if candidates else None


def build_strategy_lab_projection(quant_root: Path | str | None = None) -> dict[str, Any]:
    """Join V37G-H source evidence with V37I-J campaign evidence without mutation."""

    root = Path(quant_root) if quant_root is not None else get_quant_engine_path()
    source_root = root / _SOURCE_RELATIVE
    integration_root = root / _INTEGRATION_RELATIVE
    campaign_root = root / _CAMPAIGN_RELATIVE
    required_paths = {
        "sourceManifest": source_root / "source_manifest.json",
        "adoptionMap": source_root / "component_adoption_map.json",
        "sourceInventory": integration_root / "source_inventory.json",
        "factorRegistry": integration_root / "factor_registry.json",
        "campaignSummary": campaign_root / "campaign_summary.json",
        "candidateInventory": campaign_root / "candidate_inventory.json",
        "experimentBudget": campaign_root / "experiment_budget.json",
        "failureAttribution": campaign_root / "failure_attribution.json",
        "formalRoute": campaign_root / "formal_route.json",
    }
    missing = [str(path.relative_to(root)).replace("\\", "/") for path in required_paths.values() if not path.is_file()]

    source_manifest = _dict(_load_json(required_paths["sourceManifest"], {}))
    adoption_map = _dict(_load_json(required_paths["adoptionMap"], {}))
    source_inventory = _list(_load_json(required_paths["sourceInventory"], []))
    factor_registry = _list(_load_json(required_paths["factorRegistry"], []))
    campaign_summary = _dict(_load_json(required_paths["campaignSummary"], {}))
    candidate_inventory_raw = _load_json(required_paths["candidateInventory"], {})
    candidate_inventory = _dict(candidate_inventory_raw)
    candidates = _list(candidate_inventory.get("candidates")) if isinstance(candidate_inventory_raw, dict) else _list(candidate_inventory_raw)
    experiment_budget = _dict(_load_json(required_paths["experimentBudget"], {}))
    failure_attribution = _dict(_load_json(required_paths["failureAttribution"], {}))
    formal_route = _dict(_load_json(required_paths["formalRoute"], {}))
    source_equivalence = _load_csv(integration_root / "source_equivalence_matrix.csv")
    similarity_matrix = _load_csv(integration_root / "artifact_similarity_summary.csv")
    factor_bench = _load_csv(integration_root / "factor_bench_matrix.csv")
    mechanism_research = _latest_mechanism_research(root)
    mechanism_summary = (
        _dict(_load_json(mechanism_research / "campaign_summary.json", {}))
        if mechanism_research else {}
    )
    formal_gate_matrix = _load_csv(mechanism_research / "formal_gate_matrix.csv") if mechanism_research else []
    mechanism_status = str(mechanism_summary.get("status") or "not_available")
    mechanism_prefilter_survivors = _integer(mechanism_summary.get("prefilterSurvivorCount"))
    mechanism_formal_runs = _integer(mechanism_summary.get("formalRunCount"))
    if mechanism_formal_runs > 0:
        formal_gate_status = "completed"
    elif mechanism_status == "completed_zero_qualified_candidates" and mechanism_prefilter_survivors == 0:
        formal_gate_status = "not_run_zero_prefilter_survivors"
    else:
        formal_gate_status = "not_run"

    formal_count = _integer(
        formal_route.get("formalCandidateCount"),
        formal_route.get("formalCandidates"),
        campaign_summary.get("formalCandidateCount"),
    )
    release_count = _integer(formal_route.get("releaseCount"))
    route_status = "formal_candidates_available" if formal_count > 0 else "zero_qualified_candidates"
    artifacts = [
        {
            "artifactId": str(_dict(item).get("artifactId") or ""),
            "name": str(_dict(item).get("name") or _dict(item).get("artifactId") or "未命名来源"),
            "artifactType": str(_dict(item).get("artifactType") or "unknown"),
            "familyId": str(_dict(item).get("familyId") or "unclassified"),
            "status": str(_dict(item).get("status") or "unknown"),
            "sourceEquivalenceClass": str(_dict(item).get("sourceEquivalenceClass") or "unknown"),
        }
        for item in source_inventory
        if isinstance(item, dict)
    ]
    lineage = [
        {
            "candidateId": str(_dict(item).get("candidate_id") or _dict(item).get("candidateId") or ""),
            "candidateHash": str(_dict(item).get("candidate_hash") or _dict(item).get("candidateHash") or ""),
            "familyId": str(_dict(item).get("family_id") or _dict(item).get("familyId") or ""),
            "sourcePath": str(_dict(item).get("source_path") or _dict(item).get("sourcePath") or ""),
            "status": str(_dict(item).get("status") or _dict(_dict(item).get("result")).get("status") or "unknown"),
            "reasonCode": str(_dict(_dict(item).get("result")).get("reasonCode") or _dict(item).get("prefilter_blocker") or ""),
        }
        for item in candidates
        if isinstance(item, dict)
    ]

    return {
        "schemaVersion": "alphapilot_strategy_lab_projection_v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "status": "ready" if not missing else "blocked_missing_evidence",
        "readOnly": True,
        "projectionAuthority": "quant_evidence_only",
        "missingEvidence": missing,
        "summary": {
            "sourceArtifactCount": len(artifacts),
            "factorCount": len(factor_registry),
            "candidateCount": len(lineage),
            "campaignCount": _integer(campaign_summary.get("campaignCount"), experiment_budget.get("campaignsUsed")),
            "formalCandidateCount": formal_count,
            "releaseCount": release_count,
            "failureCount": _integer(failure_attribution.get("failureCount")),
        },
        "sourceRegistry": {
            "repository": str(source_manifest.get("repository") or ""),
            "repositoryUrl": str(source_manifest.get("repositoryUrl") or ""),
            "commit": str(source_manifest.get("commit") or ""),
            "commitUrl": str(source_manifest.get("commitUrl") or ""),
            "license": str(source_manifest.get("license") or "unknown"),
            "runtimeDependency": bool(source_manifest.get("runtimeDependency", False)),
            "sourceCount": len(_list(source_manifest.get("paths"))),
            "adopted": _list(adoption_map.get("adoptNow")),
            "deferred": _list(adoption_map.get("defer")),
            "rejected": _list(adoption_map.get("reject")),
        },
        "artifactCards": artifacts,
        "sourceEquivalence": source_equivalence,
        "candidateLineage": lineage,
        "similarityMatrix": similarity_matrix,
        "factorRegistry": factor_registry,
        "factorBench": factor_bench,
        "mechanismCampaign": {
            "campaignId": str(mechanism_summary.get("campaignId") or ""),
            "status": mechanism_status,
            "candidateCount": _integer(mechanism_summary.get("candidateCount")),
            "prefilterSurvivorCount": mechanism_prefilter_survivors,
            "formalCandidateCount": _integer(mechanism_summary.get("formalCandidateCount")),
            "formalRunCount": mechanism_formal_runs,
            "releaseCount": _integer(mechanism_summary.get("releaseCount")),
            "lockedOosReadCount": _integer(mechanism_summary.get("lockedOosReadCount")),
            "formalGateStatus": formal_gate_status,
            "evidenceRoot": (
                str(mechanism_research.relative_to(root)).replace("\\", "/")
                if mechanism_research else ""
            ),
        },
        "formalGateMatrix": formal_gate_matrix,
        "campaigns": _list(campaign_summary.get("campaigns")),
        "campaignSummary": campaign_summary,
        "experimentBudget": experiment_budget,
        "failureAttribution": failure_attribution,
        "route": {
            **formal_route,
            "status": route_status,
            "formalCandidateCount": formal_count,
            "releaseCount": release_count,
            "demoArm": bool(formal_route.get("demoArm", False)) if release_count else False,
        },
        "decayState": {
            "status": "inactive_insufficient_real_evidence",
            "activationRequirement": "three_independent_periodic_benches_or_sufficient_closed_demo_trades",
            "activeReleaseMutationAllowed": False,
        },
        "capabilities": {
            "canMutateFrozenCandidate": False,
            "canEditFormalGates": False,
            "canReadLockedOos": False,
            "canApproveRelease": False,
            "canCreateOrder": False,
        },
    }
