"""Narrow V62.4.2 acceptance closeout helpers.

This module only verifies and projects evidence. It has no release, approval,
ARM, risk mutation, or order authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .v62_4_1_independent_verifiers import (
    verify_artifact_manifest,
    verify_runtime_evidence,
)


MATCHABILITY_STATUS = "matchability_diagnostic_ready"
BROAD_SUCCESSOR_STATUS = "broad_universe_successor_not_created"
TOP200_PIT_STATUS = "top200_historical_pit_not_proven"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def classify_matchability_evidence(
    broad_audit: Mapping[str, object],
) -> dict[str, object]:
    """Classify replay evidence without claiming a successor or TOP200 PIT proof."""

    requested = int(broad_audit.get("requestedUniverseSize") or 0)
    replayed = int(broad_audit.get("historicalReplayInstrumentCount") or 0)
    actual = int(broad_audit.get("actualInstrumentCount") or 0)
    successor_id = str(broad_audit.get("successorCandidateId") or "")
    successor_hash = str(broad_audit.get("successorDefinitionHash") or "")
    top200_source_status = str(
        broad_audit.get("top200HistoricalReplayStatus") or ""
    )

    successor_status = (
        "broad_universe_successor_registered"
        if successor_id and successor_hash
        else BROAD_SUCCESSOR_STATUS
    )
    top200_proven = (
        requested >= 200
        and replayed >= requested
        and top200_source_status in {"passed", "proven", "completed"}
    )
    return {
        "schemaVersion": "v62_4_2_matchability_classification_v1",
        "status": MATCHABILITY_STATUS,
        "broadUniverseSuccessorStatus": successor_status,
        "top200HistoricalPitStatus": (
            "top200_historical_pit_proven" if top200_proven else TOP200_PIT_STATUS
        ),
        "requestedUniverseSize": requested,
        "actualDemoEligibleInstrumentCount": actual,
        "historicalReplayInstrumentCount": replayed,
        "sourceTop200HistoricalReplayStatus": top200_source_status,
        "successorCandidateId": successor_id or None,
        "successorDefinitionHash": successor_hash or None,
        "matchabilityProblemSolved": False,
        "releaseCount": 0,
        "orderCount": 0,
        "demoArm": False,
        "liveArm": False,
        "executionAuthorized": False,
    }


def build_authoritative_closeout_projection(
    *,
    formal: Mapping[str, object],
    runtime: Mapping[str, object],
    quality: Mapping[str, object],
    failure_critic: Mapping[str, object],
    matchability: Mapping[str, object],
) -> dict[str, object]:
    """Build the top-level state exclusively from child evidence."""

    formal_projection = {
        "formalRunCount": int(formal.get("formalRunCount") or 0),
        "resultReadCount": int(formal.get("resultReadCount") or 0),
        "candidateId": str(formal.get("candidateId") or ""),
        "formalPass": bool(formal.get("formalPass")),
        "route": str(formal.get("route") or ""),
        "baseMetrics": dict(formal.get("baseMetrics") or {}),
    }
    runtime_projection = {
        "passed": bool(runtime.get("passed")),
        "sourceRuntimeOnline": bool(runtime.get("sourceRuntimeOnline")),
        "privateReconciliationStatus": str(
            runtime.get("privateReconciliationStatus")
            or "not_run_credentials_unavailable"
        ),
        "activeExecutionLeaseCount": int(
            runtime.get("activeExecutionLeaseCount") or 0
        ),
    }
    failure_projection = {
        "status": str(failure_critic.get("status") or "not_run"),
        "caseCount": int(failure_critic.get("caseCount") or 0),
        "acceptedCaseCount": int(
            failure_critic.get("acceptedCaseCount") or 0
        ),
    }
    matchability_projection = {
        "status": str(matchability.get("status") or ""),
        "broadUniverseSuccessorStatus": str(
            matchability.get("broadUniverseSuccessorStatus") or ""
        ),
        "top200HistoricalPitStatus": str(
            matchability.get("top200HistoricalPitStatus") or ""
        ),
    }
    local_closeout_complete = (
        formal_projection["formalRunCount"] == 1
        and formal_projection["resultReadCount"] == 1
        and formal_projection["formalPass"] is False
        and formal_projection["route"] == "archive_s01_current_version"
        and runtime_projection["passed"] is True
        and runtime_projection["activeExecutionLeaseCount"] == 0
        and failure_projection["status"] == "accepted"
        and failure_projection["caseCount"] == 4
        and failure_projection["acceptedCaseCount"] == 4
        and matchability_projection["status"] == MATCHABILITY_STATUS
        and matchability_projection["broadUniverseSuccessorStatus"]
        == BROAD_SUCCESSOR_STATUS
        and matchability_projection["top200HistoricalPitStatus"]
        == TOP200_PIT_STATUS
    )
    return {
        "schemaVersion": "v62_4_2_authoritative_closeout_projection_v1",
        "status": (
            "v62_4_2_delta_closeout_completed"
            if local_closeout_complete
            else "v62_4_2_delta_closeout_blocked"
        ),
        "formal": formal_projection,
        "runtime": runtime_projection,
        "quality": dict(quality),
        "failureCritic": failure_projection,
        "matchability": matchability_projection,
        "releaseCount": 0,
        "approvalCount": 0,
        "orderCount": 0,
        "demoArm": False,
        "liveEnabled": False,
        "liveArm": False,
        "withdrawEnabled": False,
        "automaticApproval": False,
        "executionAuthorized": False,
    }


def verify_final_runtime_source_identity(
    evidence_root: Path | str,
    repository_root: Path | str,
    *,
    expected_commit: str,
    expected_tag: str,
) -> dict[str, object]:
    """Verify runtime evidence against the exact final source identity."""

    root = Path(evidence_root)
    repository = Path(repository_root)
    base = verify_runtime_evidence(root)
    findings = list(base.get("findings") or [])
    capture_path = root / "runtime_identity_capture.json"
    try:
        capture = json.loads(capture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        capture = {}
        findings.append("runtime_identity_capture_unreadable")
    identity = (
        capture.get("runtimeIdentity")
        if isinstance(capture, Mapping)
        and isinstance(capture.get("runtimeIdentity"), Mapping)
        else {}
    )
    repository_commit = str(identity.get("repositoryCommit") or "")
    repository_tag = str(identity.get("repositoryTag") or "")
    if repository_commit != expected_commit:
        findings.append("final_repository_commit_mismatch")
    if repository_tag != expected_tag:
        findings.append("final_repository_tag_mismatch")

    module_hashes = identity.get("moduleHashes")
    verified_module_count = 0
    if not isinstance(module_hashes, Mapping) or not module_hashes:
        findings.append("module_hashes_missing")
    else:
        for relative, expected_hash in module_hashes.items():
            relative_path = Path(str(relative))
            if relative_path.is_absolute() or ".." in relative_path.parts:
                findings.append(f"module_path_invalid:{relative}")
                continue
            module_path = repository / relative_path
            if not module_path.is_file():
                findings.append(f"module_missing:{relative}")
                continue
            if _sha256_file(module_path) != str(expected_hash):
                findings.append(f"module_hash_mismatch:{relative}")
                continue
            verified_module_count += 1

    active_lease_count = int(capture.get("activeExecutionLeaseCount") or 0)
    if active_lease_count != 0:
        findings.append("active_execution_lease_present")
    summary_path = root / "runtime_evidence_summary.json"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        summary = {}
    private_status = str(
        summary.get("privateReconciliationStatus")
        or capture.get("privateReconciliationStatus")
        or "not_run_credentials_unavailable"
    )
    return {
        "schemaVersion": "v62_4_2_final_runtime_source_verifier_v1",
        "passed": bool(base.get("passed")) and not findings,
        "findings": sorted(set(str(item) for item in findings)),
        "repositoryCommit": repository_commit,
        "repositoryTag": repository_tag,
        "moduleHashesVerified": verified_module_count,
        "activeExecutionLeaseCount": active_lease_count,
        "privateReconciliationStatus": private_status,
        "sourceRuntimeOnline": bool(base.get("sourceRuntimeOnline")),
        "executionAuthorized": False,
    }


_VERIFIER_SOURCES: dict[str, str] = {
    "verify_acceptance_package.py": """
from _bootstrap import load_domain
from pathlib import Path
import argparse, json
domain = load_domain()
parser = argparse.ArgumentParser()
parser.add_argument("--package-root", type=Path, required=True)
args = parser.parse_args()
print(json.dumps(domain.verify_delta_acceptance_package(args.package_root), indent=2, sort_keys=True))
""",
    "verify_ai_router.py": """
from _bootstrap import load_domain
from pathlib import Path
import argparse, json
domain = load_domain()
parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--provider-smoke", type=Path, required=True)
args = parser.parse_args()
print(json.dumps(domain.verify_ai_orchestration(args.repository_root, args.provider_smoke), indent=2, sort_keys=True))
""",
    "verify_hashes.py": """
from _bootstrap import load_domain
from pathlib import Path
import argparse, json
domain = load_domain()
parser = argparse.ArgumentParser()
parser.add_argument("--package-root", type=Path, required=True)
parser.add_argument("--manifest", type=Path, required=True)
args = parser.parse_args()
print(json.dumps(domain.verify_artifact_manifest(args.package_root, args.manifest), indent=2, sort_keys=True))
""",
    "verify_runtime_identity.py": """
from _bootstrap import load_delta
from pathlib import Path
import argparse, json
delta = load_delta()
parser = argparse.ArgumentParser()
parser.add_argument("--evidence-root", type=Path, required=True)
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--expected-commit", required=True)
parser.add_argument("--expected-tag", required=True)
args = parser.parse_args()
print(json.dumps(delta.verify_final_runtime_source_identity(args.evidence_root, args.repository_root, expected_commit=args.expected_commit, expected_tag=args.expected_tag), indent=2, sort_keys=True))
""",
    "verify_sqlite_snapshots.py": """
from _bootstrap import load_domain
from pathlib import Path
import argparse, json
domain = load_domain()
parser = argparse.ArgumentParser()
parser.add_argument("--receipts", type=Path, required=True)
args = parser.parse_args()
print(json.dumps(domain.verify_sqlite_snapshots(args.receipts), indent=2, sort_keys=True))
""",
    "verify_trial_ledger.py": """
from _bootstrap import load_domain
from pathlib import Path
import argparse, json
domain = load_domain()
parser = argparse.ArgumentParser()
parser.add_argument("--evidence-root", type=Path, required=True)
args = parser.parse_args()
print(json.dumps(domain.verify_trial_evidence(args.evidence_root), indent=2, sort_keys=True))
""",
    "verify_ui_data_sources.py": """
from _bootstrap import load_domain
import argparse, json
domain = load_domain()
parser = argparse.ArgumentParser()
parser.add_argument("--base-url", required=True)
parser.add_argument("--campaign-id", required=True)
args = parser.parse_args()
print(json.dumps(domain.verify_ui_endpoint(args.base_url, expected_campaign_id=args.campaign_id), indent=2, sort_keys=True))
""",
}


def build_verifier_scripts(destination: Path | str) -> list[Path]:
    """Write seven executable scripts that call their domain verifier directly."""

    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    bootstrap = """from __future__ import annotations
import importlib
import os
import sys
from pathlib import Path

def _repo_root() -> Path:
    configured = os.environ.get("ALPHAPILOT_VERIFIER_REPOSITORY_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[2]

def _load(module_name: str):
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return importlib.import_module(module_name)

def load_domain():
    return _load("alphapilot_control_console.v62_4_1_independent_verifiers")

def load_delta():
    return _load("alphapilot_control_console.v62_4_2_delta_closeout")
"""
    (root / "_bootstrap.py").write_text(bootstrap, encoding="utf-8")
    generated: list[Path] = []
    for filename, body in sorted(_VERIFIER_SOURCES.items()):
        path = root / filename
        path.write_text(
            "from __future__ import annotations\n" + body.strip() + "\n",
            encoding="utf-8",
        )
        generated.append(path)
    return generated


def verify_delta_acceptance_package(package_root: Path | str) -> dict[str, object]:
    """Verify required delta sections, manifest, and immutable safety state."""

    root = Path(package_root)
    required = (
        "00_START_HERE/authoritative_closeout_state.json",
        "01_runtime/runtime_source_verification.json",
        "02_failure_critic/four_case_summary.json",
        "03_matchability/matchability_classification.json",
        "04_independent_verification/independent_verification_result.json",
        "07_final/final_self_check.json",
        "artifact_manifest.json",
    )
    findings = [
        f"missing:{relative}"
        for relative in required
        if not (root / relative).is_file()
    ]
    manifest_result: dict[str, object] = {
        "passed": False,
        "findings": ["manifest_not_checked"],
    }
    manifest = root / "artifact_manifest.json"
    if manifest.is_file():
        manifest_result = verify_artifact_manifest(root, manifest)
        if manifest_result.get("passed") is not True:
            findings.extend(
                f"manifest:{item}" for item in manifest_result.get("findings") or []
            )
    state_path = root / "00_START_HERE" / "authoritative_closeout_state.json"
    state: Mapping[str, object] = {}
    if state_path.is_file():
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
        if isinstance(loaded, Mapping):
            state = loaded
        else:
            findings.append("authoritative_state_invalid")
    for field in (
        "releaseCount",
        "approvalCount",
        "orderCount",
        "demoArm",
        "liveEnabled",
        "liveArm",
        "withdrawEnabled",
        "automaticApproval",
        "executionAuthorized",
    ):
        value = state.get(field)
        if isinstance(value, bool):
            invalid = value
        else:
            invalid = int(value or 0) != 0
        if invalid:
            findings.append(f"unsafe_state:{field}")
    return {
        "schemaVersion": "v62_4_2_delta_package_verifier_v1",
        "passed": not findings,
        "findings": sorted(set(findings)),
        "requiredArtifactCount": len(required),
        "manifestPassed": manifest_result.get("passed") is True,
        "executionAuthorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, required=True)
    args = parser.parse_args()
    result = verify_delta_acceptance_package(args.package_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
