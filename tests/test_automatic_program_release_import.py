from __future__ import annotations

import json
from pathlib import Path

import pytest

from alphapilot_control_console.automatic_program_release_import import (
    import_automatic_program_releases,
)
from alphapilot_control_console.strategy_validation_hashing import stable_hash


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _zero_release_program(root: Path) -> Path:
    plan = {
        "schemaVersion": "automatic_v23_release_plan_v1",
        "campaignId": "campaign-a",
        "maximumReleaseCount": 3,
        "eligibleCandidateCount": 0,
        "releaseCount": 0,
        "releaseHashes": [],
        "releases": [],
        "approvalRequired": False,
        "automaticApprovalAllowed": False,
        "demoArm": False,
        "orderCount": 0,
        "terminalRoute": "completed_zero_qualified_candidates",
    }
    plan["releasePlanHash"] = stable_hash(plan, "automatic_v23_release_plan")
    _write_json(root / "release_inventory.json", plan)
    _write_json(
        root / "zero_release_route.json",
        {
            "schemaVersion": "automatic_v23_zero_release_route_v1",
            "applies": True,
            "terminalRoute": "completed_zero_qualified_candidates",
            "importCount": 0,
            "approvalCount": 0,
            "demoArm": False,
            "orderCount": 0,
        },
    )
    (root / "candidate_releases").mkdir(parents=True)
    return root


def _one_release_program(root: Path) -> tuple[Path, dict]:
    overlay = {
        "schemaVersion": "automatic_v23_demo_risk_overlay_v1",
        "overlayClass": "research_forward_strict",
        "maximumConcurrentPositions": 1,
        "maximumOpenRiskPctEquity": 0.10,
        "addingAllowed": False,
        "averagingAllowed": False,
        "martingaleAllowed": False,
        "retryPolicy": "bounded",
        "exitPolicyMode": "exact_frozen",
        "mayWidenFrozenRisk": False,
    }
    risk_hash = stable_hash(overlay, "automatic_demo_risk_overlay")
    identity = {
        "campaignId": "campaign-a",
        "candidateId": "candidate-a",
        "releaseClass": "research_forward",
        "evidenceClass": "demo_research_forward",
    }
    release = {
        "schemaVersion": "automatic_v23_immutable_demo_release_v1",
        "releaseId": f"automatic_demo_release_{stable_hash(identity)[:16]}",
        "campaignId": "campaign-a",
        "candidateId": "candidate-a",
        "strategyId": "strategy-a",
        "familyId": "family-a",
        "formalStatus": "research_pass_no_clean_holdout",
        "formalPass": False,
        "releaseClass": "research_forward",
        "releasePurpose": "research_forward_validation",
        "evidenceClass": "demo_research_forward",
        "strategyQualification": False,
        "forwardReviewEligible": True,
        "livePromotionEligible": False,
        "approvalRequired": True,
        "approved": False,
        "environment": "demo",
        "demoArm": False,
        "orderCount": 0,
        "riskOverlay": overlay,
        "riskOverlayHash": risk_hash,
        "createdAt": "2026-07-18T00:00:00Z",
        "strategyDefinitionHash": "strategy-hash",
        "exitPolicyHash": "exit-hash",
        "dataProfileHash": "profile-hash",
        "dataManifestHash": "manifest-hash",
        "preregistrationHash": "prereg-hash",
        "costModelHash": "cost-hash",
        "capitalPolicyHash": "capital-hash",
        "benchmarkHash": "benchmark-hash",
        "formalGateHash": "gate-hash",
        "backtestReportHash": "report-hash",
    }
    release["releaseHash"] = stable_hash(release, "automatic_demo_release")
    plan = {
        "schemaVersion": "automatic_v23_release_plan_v1",
        "campaignId": "campaign-a",
        "maximumReleaseCount": 3,
        "eligibleCandidateCount": 1,
        "releaseCount": 1,
        "releaseHashes": [release["releaseHash"]],
        "releases": [release],
        "approvalRequired": True,
        "automaticApprovalAllowed": False,
        "demoArm": False,
        "orderCount": 0,
        "terminalRoute": None,
    }
    plan["releasePlanHash"] = stable_hash(plan, "automatic_v23_release_plan")
    _write_json(root / "release_inventory.json", plan)
    _write_json(root / "candidate_releases" / f"{release['releaseId']}.json", release)
    return root, release


def test_zero_release_route_imports_nothing_and_never_arms(tmp_path: Path) -> None:
    quant_program_root = _zero_release_program(tmp_path / "quant-program")

    result = import_automatic_program_releases(
        quant_program_root=quant_program_root,
        output_root=tmp_path / "console-evidence",
        release_store_path=tmp_path / "releases.sqlite",
        contract_dir=tmp_path / "contracts",
        generated_at="2026-07-18T00:00:00Z",
    )

    assert result["status"] == "completed_zero_qualified_candidates"
    assert result["releaseCount"] == 0
    assert result["importedReleaseCount"] == 0
    assert result["approvalCount"] == 0
    assert result["demoArm"] is False
    assert result["orderCount"] == 0
    assert result["engineeringSmokeCountedAsStrategyEvidence"] is False
    evidence_root = tmp_path / "console-evidence"
    assert (evidence_root / "demo_approval_request.json").is_file()
    assert (evidence_root / "demo_approval_request.md").is_file()
    assert (evidence_root / "demo_approval_overlay.json").is_file()
    assert (evidence_root / "final_self_check.md").is_file()


def test_tampered_release_plan_is_rejected_before_import(tmp_path: Path) -> None:
    quant_program_root = _zero_release_program(tmp_path / "quant-program")
    inventory = json.loads((quant_program_root / "release_inventory.json").read_text(encoding="utf-8"))
    inventory["maximumReleaseCount"] = 2
    _write_json(quant_program_root / "release_inventory.json", inventory)

    with pytest.raises(ValueError, match="release plan hash mismatch"):
        import_automatic_program_releases(
            quant_program_root=quant_program_root,
            output_root=tmp_path / "console-evidence",
            release_store_path=tmp_path / "releases.sqlite",
            contract_dir=tmp_path / "contracts",
            generated_at="2026-07-18T00:00:00Z",
        )


def test_valid_v23_release_imports_unapproved_and_never_arms(tmp_path: Path) -> None:
    quant_program_root, release = _one_release_program(tmp_path / "quant-program")

    result = import_automatic_program_releases(
        quant_program_root=quant_program_root,
        output_root=tmp_path / "console-evidence",
        release_store_path=tmp_path / "releases.sqlite",
        contract_dir=tmp_path / "contracts",
        generated_at="2026-07-18T00:00:00Z",
    )

    assert result["status"] == "blocked_waiting_exact_release_approval"
    assert result["releaseCount"] == 1
    assert result["importedReleaseCount"] == 1
    assert result["importedReleases"][0]["releaseHash"] == release["releaseHash"]
    assert result["importedReleases"][0]["status"] == "demo_waiting_approval"
    assert result["approvalCount"] == 0
    assert result["demoArm"] is False
    assert result["orderCount"] == 0
