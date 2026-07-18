"""Hash-verified V24 import boundary for automatic V23 Demo releases."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .strategy_validation_hashing import stable_hash
from .strategy_validation_release_store import StrategyValidationReleaseStore


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def _verify_release_plan(plan: dict[str, Any]) -> None:
    supplied = plan.get("releasePlanHash")
    canonical = {key: value for key, value in plan.items() if key != "releasePlanHash"}
    if supplied != stable_hash(canonical, "automatic_v23_release_plan"):
        raise ValueError("release plan hash mismatch")
    release_count = int(plan.get("releaseCount") or 0)
    if release_count < 0 or release_count > 3:
        raise ValueError("release count exceeds frozen campaign cap")
    releases = plan.get("releases")
    hashes = plan.get("releaseHashes")
    if not isinstance(releases, list) or not isinstance(hashes, list):
        raise ValueError("release plan arrays are invalid")
    if release_count != len(releases) or release_count != len(hashes):
        raise ValueError("release plan count mismatch")
    if plan.get("automaticApprovalAllowed") is not False:
        raise ValueError("automatic release approval is forbidden")
    if plan.get("demoArm") is not False or int(plan.get("orderCount") or 0) != 0:
        raise ValueError("V23 release plan must arrive unarmed with zero orders")


def _artifact_manifest(root: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != "artifact_manifest.json"):
        artifacts.append(
            {
                "relativePath": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "sizeBytes": path.stat().st_size,
            }
        )
    manifest = {
        "schemaVersion": "automatic_v24_console_artifact_manifest_v1",
        "artifactCount": len(artifacts),
        "artifacts": artifacts,
    }
    manifest["manifestHash"] = stable_hash(manifest, "automatic_v24_console_manifest")
    return manifest


def import_automatic_program_releases(
    *,
    quant_program_root: Path,
    output_root: Path,
    release_store_path: Path,
    contract_dir: Path,
    generated_at: str,
) -> dict[str, Any]:
    """Import only immutable hash-verified releases, without approval or runtime action."""

    quant_root = Path(quant_program_root).resolve()
    output = Path(output_root)
    plan_path = quant_root / "release_inventory.json"
    if not plan_path.is_file():
        raise FileNotFoundError(plan_path)
    plan = _read_json(plan_path)
    _verify_release_plan(plan)
    release_count = int(plan["releaseCount"])
    release_dir = quant_root / "candidate_releases"
    release_files = sorted(release_dir.glob("*.json")) if release_dir.is_dir() else []
    if len(release_files) != release_count:
        raise ValueError("immutable release file count mismatch")
    files_by_id = {path.stem: path for path in release_files}
    imported: list[dict[str, Any]] = []
    store = StrategyValidationReleaseStore(release_store_path, contract_dir=contract_dir)
    try:
        for release in plan["releases"]:
            if not isinstance(release, dict):
                raise ValueError("release plan entry must be an object")
            release_id = str(release.get("releaseId") or "")
            path = files_by_id.get(release_id)
            if path is None:
                raise ValueError(f"immutable release file missing: {release_id}")
            file_payload = _read_json(path)
            if file_payload != release:
                raise ValueError(f"release inventory and file differ: {release_id}")
            if release.get("releaseHash") not in plan["releaseHashes"]:
                raise ValueError(f"release hash absent from inventory: {release_id}")
            imported.append(store.import_file(path))
    finally:
        store.close()

    if release_count == 0:
        zero_route = _read_json(quant_root / "zero_release_route.json")
        if (
            zero_route.get("applies") is not True
            or zero_route.get("terminalRoute") != "completed_zero_qualified_candidates"
            or any(int(zero_route.get(key) or 0) != 0 for key in ("importCount", "approvalCount", "orderCount"))
            or zero_route.get("demoArm") is not False
        ):
            raise ValueError("zero release route is invalid")
        status = "completed_zero_qualified_candidates"
    else:
        status = "blocked_waiting_exact_release_approval"

    audit = {
        "schemaVersion": "automatic_v24_release_import_audit_v1",
        "generatedAt": generated_at,
        "quantProgramRoot": quant_root.as_posix(),
        "campaignId": str(plan["campaignId"]),
        "releasePlanHash": str(plan["releasePlanHash"]),
        "releaseCount": release_count,
        "importedReleaseCount": len(imported),
        "importedReleases": imported,
        "approvalCount": 0,
        "approvalRequired": release_count > 0,
        "exactHashApprovalRecorded": False,
        "demoArm": False,
        "orderCount": 0,
        "runtimeEnabled": False,
        "engineeringSmokeCountedAsStrategyEvidence": False,
        "status": status,
    }
    audit["auditHash"] = stable_hash(audit, "automatic_v24_release_import_audit")
    store_record = {
        "schemaVersion": "automatic_v24_release_store_record_v1",
        "campaignId": audit["campaignId"],
        "releaseCount": release_count,
        "importedReleaseCount": len(imported),
        "releaseHashes": [str(row["releaseHash"]) for row in imported],
        "status": "demo_waiting_approval" if release_count else "no_release",
    }
    smoke_isolation = {
        "schemaVersion": "automatic_v24_engineering_smoke_isolation_v1",
        "engineeringSmokeLedger": "isolated_demo_engineering_smoke_store",
        "strategyValidationLedger": "strategy_validation_release_store",
        "engineeringSmokeRunCount": 0,
        "strategyEvidenceContributionCount": 0,
        "promotionEvidenceContributionCount": 0,
        "isolated": True,
    }
    final_route = {
        "schemaVersion": "automatic_v24_final_route_v1",
        "status": status,
        "terminalRoute": status,
        "releaseCount": release_count,
        "importedReleaseCount": len(imported),
        "approvalCount": 0,
        "demoArm": False,
        "orderCount": 0,
        "liveTradingEnabled": False,
        "withdrawEnabled": False,
    }
    approval_request = {
        "schemaVersion": "automatic_v24_demo_approval_request_v1",
        "applies": release_count > 0,
        "approvalRequired": release_count > 0,
        "requiredApprovalType": "exact_release_hash" if release_count else None,
        "releaseHashes": [str(row["releaseHash"]) for row in imported],
        "automaticApprovalAllowed": False,
        "status": "waiting_exact_release_hash" if release_count else "not_required_zero_release",
    }
    approval_overlay = {
        "schemaVersion": "automatic_v24_demo_approval_overlay_v1",
        "approvalCount": 0,
        "approvedReleaseHashes": [],
        "riskOverlayHashes": [],
        "approver": None,
        "approvedAt": None,
        "demoArm": False,
        "orderCount": 0,
    }
    _write_json(output / "release_import_audit.json", audit)
    _write_json(output / "release_store_record.json", store_record)
    _write_json(output / "engineering_smoke_isolation_audit.json", smoke_isolation)
    _write_json(output / "demo_universe_audit.json", {"status": "not_run_waiting_exact_approval" if release_count else "not_run_zero_release", "intersectionCount": 0, "fallbackUsed": False})
    _write_json(output / "demo_arm_audit.json", {"status": "not_armed", "approvalHashMatched": False, "demoArm": False, "orderCount": 0})
    _write_json(output / "demo_approval_request.json", approval_request)
    _write_json(output / "demo_approval_overlay.json", approval_overlay)
    _write_text(
        output / "demo_approval_request.md",
        (
            "# Demo Approval Request\n\n"
            + (
                "Exact Release Hash approval is required before any Demo universe or ARM action.\n"
                if release_count
                else "No eligible Release exists. Exact-hash approval is not requested.\n"
            )
        ),
    )
    _write_json(output / "final_route_decision.json", final_route)
    _write_text(
        output / "final_self_check.md",
        "\n".join(
            (
                "# V24 Final Self Check",
                "",
                f"- Route: `{status}`",
                f"- Release count: {release_count}",
                f"- Imported count: {len(imported)}",
                "- Approval count: 0",
                "- Demo ARM: false",
                "- Order count: 0",
                "- Live trading: false",
                "- Withdraw: false",
                "- Engineering smoke counted as strategy evidence: false",
                "",
            )
        ),
    )
    _write_json(output / "artifact_manifest.json", _artifact_manifest(output))
    return audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quant-program-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--release-store", type=Path, required=True)
    parser.add_argument("--contract-dir", type=Path, required=True)
    parser.add_argument("--generated-at", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = import_automatic_program_releases(
        quant_program_root=args.quant_program_root,
        output_root=args.output_root,
        release_store_path=args.release_store,
        contract_dir=args.contract_dir,
        generated_at=args.generated_at,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
