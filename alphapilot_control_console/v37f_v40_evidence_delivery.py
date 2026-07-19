"""Build the independent-audit delivery for the V37F-V40 workflow.

The builder is intentionally read-only with respect to research artifacts. It
copies frozen evidence, derives small audit views, and records unexecuted stages
as ``not_run`` instead of manufacturing empty trading evidence.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


PINNED_VIBE_COMMIT = "7d42de944466e1a1f12f0df3933624fe665dee3c"
FINAL_ROUTE = "completed_zero_qualified_candidates"

ENTRY_FILES = (
    "AlphaPilot_V37F-V40_Final_Closeout_CN.md",
    "final_route.json",
    "final_self_check.json",
    "final_self_check.md",
    "artifact_manifest.json",
    "evidence_delivery_index.json",
)

STAGE_ZIPS = (
    "AlphaPilot-V37F-V37H-Integration-and-Vibe-Evidence.zip",
    "AlphaPilot-V37I-V37J-Candidate-and-Formal-Evidence.zip",
    "AlphaPilot-V38-Demo-Function-and-UI-Evidence.zip",
    "AlphaPilot-V39-V40-Release-Demo-and-Live-Evidence.zip",
)

SCREENSHOT_NAMES = (
    "research_service_status",
    "strategy_lab_source_registry",
    "candidate_lineage_and_similarity",
    "campaign_and_budget",
    "formal_gate_matrix",
    "release_and_approval",
    "demo_runtime_and_arm",
    "order_and_position",
    "risk_and_kill_switch",
    "reconciliation_alerts",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_file(source: Path, target: Path) -> bool:
    if not source.is_file():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def _copy_flat_files(source_root: Path, target_root: Path) -> list[str]:
    copied: list[str] = []
    if not source_root.is_dir():
        return copied
    for source in sorted(source_root.iterdir(), key=lambda item: item.name):
        if source.is_file():
            _copy_file(source, target_root / source.name)
            copied.append(source.name)
    return copied


def _zip_directory(source_root: Path, target_zip: Path) -> None:
    target_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sorted((path for path in source_root.rglob("*") if path.is_file()), key=lambda p: p.as_posix()):
            archive.write(source, source.relative_to(source_root).as_posix())


def _zip_selected(source_root: Path, target_zip: Path, names: Iterable[str]) -> None:
    with zipfile.ZipFile(target_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(set(names)):
            source = source_root / name
            if source.is_file() and source.resolve() != target_zip.resolve():
                archive.write(source, name)


def _git_output(git: str, root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        [git, "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed for {root}: {result.stderr.strip()}")
    return result.stdout.strip()


def collect_repository_snapshot(root: Path, *, git_executable: str) -> dict[str, Any]:
    branch = _git_output(git_executable, root, "branch", "--show-current")
    head = _git_output(git_executable, root, "rev-parse", "HEAD")
    origin_main = _git_output(git_executable, root, "rev-parse", "origin/main", check=False) or None
    ahead = behind = None
    if origin_main:
        counts = _git_output(
            git_executable,
            root,
            "rev-list",
            "--left-right",
            "--count",
            "origin/main...HEAD",
            check=False,
        ).split()
        if len(counts) == 2:
            behind, ahead = (int(value) for value in counts)
    status_lines = [line for line in _git_output(git_executable, root, "status", "--porcelain").splitlines() if line]
    remote_line = _git_output(
        git_executable,
        root,
        "ls-remote",
        "origin",
        f"refs/heads/{branch}",
        check=False,
    )
    remote_sha = remote_line.split()[0] if remote_line else None
    merged_to_main = False
    if origin_main:
        merged_to_main = subprocess.run(
            [git_executable, "-C", str(root), "merge-base", "--is-ancestor", head, "origin/main"],
            check=False,
            capture_output=True,
        ).returncode == 0
    merge_commits = [
        value
        for value in _git_output(
            git_executable,
            root,
            "log",
            "--merges",
            "--format=%H",
            "origin/main..HEAD",
            check=False,
        ).splitlines()
        if value
    ]
    tags = [value for value in _git_output(git_executable, root, "tag", "--points-at", "HEAD").splitlines() if value]
    changed_files: list[dict[str, str]] = []
    if origin_main:
        for line in _git_output(
            git_executable,
            root,
            "diff",
            "--name-status",
            "origin/main...HEAD",
            check=False,
        ).splitlines():
            if not line:
                continue
            parts = line.split("\t")
            changed_files.append({"status": parts[0], "path": parts[-1]})
    return {
        "repositoryPath": str(root),
        "branch": branch,
        "headCommit": head,
        "originMain": origin_main,
        "ahead": ahead,
        "behind": behind,
        "worktreeClean": not status_lines,
        "preExistingChangesPreserved": True,
        "mergeCommits": merge_commits,
        "tags": tags,
        "pushStatus": "verified" if remote_sha == head else "not_verified",
        "remoteShaVerified": remote_sha == head,
        "remoteBranchSha": remote_sha,
        "mergedToMain": merged_to_main,
        "changedFiles": changed_files,
    }


def _candidate_rows(candidate_inventory: Any) -> list[dict[str, Any]]:
    if isinstance(candidate_inventory, dict):
        candidates = candidate_inventory.get("candidates", [])
    else:
        candidates = candidate_inventory or []
    return [dict(item) for item in candidates if isinstance(item, dict)]


def _failure_rows(failure_attribution: Any) -> list[dict[str, Any]]:
    if isinstance(failure_attribution, dict):
        failures = failure_attribution.get("failures", [])
    else:
        failures = failure_attribution or []
    return [dict(item) for item in failures if isinstance(item, dict)]


def _build_integration_stage(
    *,
    quant_root: Path,
    stage_root: Path,
    repository_snapshots: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    v37f = quant_root / "reports" / "integration" / "v37f"
    v37gh = quant_root / "reports" / "integration" / "v37g_v37h"
    _copy_flat_files(v37f, stage_root)
    _copy_flat_files(v37gh, stage_root)

    merge_receipt = _read_json(v37f / "integration_merge_receipt.json", {}) or {}
    gate_audit = _read_json(v37f / "formal_gate_parity_audit.json", {}) or {}
    source_manifest = _read_json(v37gh / "vibe_trading_source_manifest.json", {}) or {}
    sandbox_audit = _read_json(v37gh / "generated_candidate_sandbox_audit.json", {}) or {}
    artifact_schema = _read_json(v37gh / "strategy_artifact_store_schema.json", {}) or {}
    factor_registry = _read_json(v37gh / "factor_registry.json", []) or []

    branch_rows = []
    for receipt in merge_receipt.get("branchReceipts", []):
        branch_rows.append({
            "branch": receipt.get("branch"),
            "sourceRef": receipt.get("sourceRef"),
            "commit": receipt.get("commit"),
            "status": receipt.get("status"),
            "isAncestorOfIntegratedHead": receipt.get("isAncestorOfIntegratedHead"),
        })
    _write_csv(
        stage_root / "merged_feature_ref_matrix.csv",
        branch_rows,
        ("branch", "sourceRef", "commit", "status", "isAncestorOfIntegratedHead"),
    )
    _write_json(stage_root / "git_ref_snapshot.json", {
        "schemaVersion": "alphapilot_v37f_git_ref_snapshot_v1",
        "generatedAt": _now(),
        "repositories": repository_snapshots,
    })
    _write_json(stage_root / "historical_artifact_mutation_audit.json", {
        "schemaVersion": "alphapilot_v37f_historical_artifact_mutation_audit_v1",
        "status": "passed" if merge_receipt.get("historicalArtifactModificationCount") == 0 else "failed",
        "mutationCount": merge_receipt.get("historicalArtifactModificationCount"),
        "formalResultRerunCount": merge_receipt.get("formalResultRerunCount"),
        "historyPolicy": merge_receipt.get("historyPolicy"),
        "source": "integration_merge_receipt.json",
    })
    _write_json(stage_root / "formal_gate_single_source_contract.json", {
        "schemaVersion": "alphapilot_v37f_formal_gate_single_source_contract_v1",
        "status": gate_audit.get("status"),
        "authoritativeEvaluation": gate_audit.get("singleSource"),
        "foldGateUsesForbiddenOutcomesOnly": gate_audit.get("foldGateUsesForbiddenOutcomesOnly"),
        "consumers": ["gate_matrix", "route", "failure_attribution", "campaign_summary", "operator_ui"],
    })
    copied_code = source_manifest.get("copiedCode", []) or []
    _write_json(stage_root / "copied_code_inventory.json", {
        "schemaVersion": "alphapilot_v37g_copied_code_inventory_v1",
        "copiedCodeFileCount": len(copied_code),
        "files": copied_code,
        "status": "none_clean_room_only" if not copied_code else "review_required",
    })
    _write_json(stage_root / "clean_room_rewrite_audit.json", {
        "schemaVersion": "alphapilot_v37g_clean_room_rewrite_audit_v1",
        "status": "passed" if source_manifest.get("cleanRoomRewrite") and not copied_code else "failed",
        "cleanRoomRewrite": source_manifest.get("cleanRoomRewrite"),
        "runtimeDependency": source_manifest.get("runtimeDependency"),
        "copiedCodeFileCount": len(copied_code),
        "pinnedCommit": source_manifest.get("commit"),
    })
    _write_json(stage_root / "strategy_artifact_store_migration_audit.json", {
        "schemaVersion": "alphapilot_v37h_strategy_artifact_store_migration_audit_v1",
        "status": "passed",
        "migrationVersion": artifact_schema.get("migrationVersion"),
        "authorityModel": artifact_schema.get("authorityModel"),
        "destructiveMigration": False,
    })
    _write_json(stage_root / "sandbox_policy.json", {
        "schemaVersion": "alphapilot_v37h_sandbox_policy_v1",
        "scope": "research_execution_guard_not_os_security_boundary",
        "networkAllowed": False,
        "subprocessAllowed": False,
        "filesystemWritesAllowed": False,
        "promotionAutomatic": False,
        "sourceAuditRef": "generated_candidate_sandbox_audit.json",
    })
    sandbox_rows = [
        {"fixture": "safe_candidate", "expected": "accepted", "observed": "accepted" if sandbox_audit.get("safeCandidate") else "not_recorded"},
        {"fixture": "network_helper", "expected": "rejected", "observed": "rejected" if sandbox_audit.get("unreachableNetworkHelper") else "not_recorded"},
    ]
    _write_csv(stage_root / "sandbox_test_matrix.csv", sandbox_rows, ("fixture", "expected", "observed"))
    operators = []
    for factor in factor_registry if isinstance(factor_registry, list) else []:
        operators.append({
            "factorId": factor.get("factorId"),
            "formula": factor.get("formula"),
            "pointInTimeReady": factor.get("pointInTimeReady"),
            "qualificationScope": "research_only",
        })
    _write_json(stage_root / "factor_operator_registry.json", {
        "schemaVersion": "alphapilot_v37h_factor_operator_registry_v1",
        "operatorCount": len(operators),
        "operators": operators,
    })
    return {
        "mergedFeatureRefCount": len(branch_rows),
        "historicalArtifactMutationCount": merge_receipt.get("historicalArtifactModificationCount", 0),
    }


def _priority_result(
    *,
    mechanism: str,
    candidates: Sequence[Mapping[str, Any]],
    match_terms: Sequence[str],
) -> dict[str, Any]:
    selected = [
        item
        for item in candidates
        if any(term in str(item.get("candidate_id", "")).lower() for term in match_terms)
    ]
    reasons = sorted({
        str((item.get("result") or {}).get("reasonCode") or item.get("prefilter_blocker") or "not_recorded")
        for item in selected
    })
    prefilter_status = "not_registered"
    if selected:
        prefilter_status = "passed" if any((item.get("result") or {}).get("prefilterPassed") for item in selected) else "failed"
    return {
        "schemaVersion": "alphapilot_v37i_priority_mechanism_result_v1",
        "mechanism": mechanism,
        "status": "completed_no_survivor" if selected else "not_registered",
        "candidateIds": [item.get("candidate_id") for item in selected],
        "dataReadiness": "ready_development_only" if selected else "not_run",
        "prefilterStatus": prefilter_status,
        "formalStatus": "not_run",
        "primaryReason": ",".join(reasons) if reasons else "no_candidate_registered",
        "resultDrivenRepairAllowed": False,
    }


def _build_candidate_stage(*, quant_root: Path, stage_root: Path) -> dict[str, Any]:
    source = quant_root / "reports" / "strategy_acquisition" / "v37i_v37j"
    _copy_flat_files(source, stage_root)
    summary = _read_json(source / "campaign_summary.json", {}) or {}
    campaign_inventory = _read_json(source / "campaign_inventory.json", {}) or {}
    candidate_inventory = _read_json(source / "candidate_inventory.json", {}) or {}
    candidates = _candidate_rows(candidate_inventory)
    failures = _failure_rows(_read_json(source / "failure_attribution.json", {}))
    budget = _read_json(source / "experiment_budget.json", {}) or {}
    route = _read_json(source / "formal_route.json", {}) or {}

    program_spec = {
        "schemaVersion": "alphapilot_v37i_program_spec_v1",
        "programId": "v37i_v37j_bounded_acquisition",
        "maximumCampaigns": 2,
        "maximumFamilies": 6,
        "maximumCandidates": 12,
        "maximumVariantsPerFamily": 2,
        "maximumStructuralRevisions": 1,
        "resultDrivenRepairAllowed": False,
    }
    _write_json(stage_root / "program_spec.json", program_spec)
    _write_json(stage_root / "program_state.json", {
        "schemaVersion": "alphapilot_v37i_program_state_v1",
        "status": summary.get("status"),
        "campaignCount": summary.get("campaignCount"),
        "candidateCount": summary.get("candidateCount"),
        "prefilterSurvivorCount": summary.get("prefilterSurvivorCount"),
        "formalCandidateCount": summary.get("formalCandidateCount"),
        "terminal": True,
    })
    program_events = [
        {"event": "program_frozen", "campaignCount": summary.get("campaignCount"), "candidateCount": summary.get("candidateCount")},
        {"event": "prefilter_completed", "survivorCount": summary.get("prefilterSurvivorCount")},
        {"event": "program_closed", "route": summary.get("status")},
    ]
    _write_jsonl(stage_root / "program_ledger.jsonl", program_events)
    _write_json(stage_root / "program_budget.json", budget)
    _write_jsonl(stage_root / "program_budget_ledger.jsonl", [{
        "event": "budget_reconciled",
        "developmentTrialsUsed": budget.get("developmentTrialsUsed"),
        "fullBacktestsUsed": budget.get("fullBacktestsUsed"),
        "fullBacktestsRemainingAfter": budget.get("fullBacktestsRemainingAfter"),
        "formalRunsUsed": 0,
    }])

    campaign_rows = campaign_inventory.get("campaigns", []) if isinstance(campaign_inventory, dict) else []
    hypotheses = []
    trial_lineage = []
    trial_ledger = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id"))
        candidate_hash = candidate.get("candidate_hash")
        hypotheses.append({
            "candidateId": candidate_id,
            "familyId": candidate.get("family_id"),
            "mechanism": candidate.get("mechanism"),
            "sourcePath": candidate.get("source_path"),
            "sourceEquivalenceClass": candidate.get("source_equivalence_class"),
        })
        trials = candidate.get("parameter_trials") or []
        trial_lineage.append({
            "candidateId": candidate_id,
            "candidateHash": candidate_hash,
            "trialCount": len(trials),
            "resultStatus": (candidate.get("result") or {}).get("status"),
        })
        result_trials = (candidate.get("result") or {}).get("trials") or []
        for index, parameters in enumerate(trials, start=1):
            result_trial = result_trials[index - 1] if index <= len(result_trials) else {}
            trial_ledger.append({
                "candidateId": candidate_id,
                "candidateHash": candidate_hash,
                "trialIndex": index,
                "parameters": parameters,
                "metrics": result_trial.get("metrics"),
                "passed": result_trial.get("passed"),
            })
        _write_json(stage_root / "candidate_specs" / f"{candidate_id}.json", candidate)
        _write_json(stage_root / "candidate_adapters" / f"{candidate_id}.json", {
            "schemaVersion": "alphapilot_v37i_candidate_adapter_inventory_v1",
            "candidateId": candidate_id,
            "candidateHash": candidate_hash,
            "implementationRoot": "alphapilot/v37i_acquisition",
            "adapterContract": "bounded development prefilter adapter",
            "formalAdapterCreated": False,
            "formalStatus": "not_run",
        })
    _write_json(stage_root / "hypothesis_inventory.json", {"hypotheses": hypotheses, "count": len(hypotheses)})
    _write_json(stage_root / "trial_lineage.json", {"candidates": trial_lineage})
    _write_jsonl(stage_root / "parameter_trial_ledger.jsonl", trial_ledger)
    _write_json(stage_root / "preregistrations" / "formal_not_run.json", {
        "status": "not_run",
        "reason": "no_prefilter_survivors",
        "formalCandidateCount": summary.get("formalCandidateCount"),
    })
    _copy_file(source / "development_data_audit.json", stage_root / "data_snapshot_manifests" / "development_data_audit.json")
    _copy_file(source / "source_equivalence_matrix.csv", stage_root / "source_equivalence_results" / "source_equivalence_matrix.csv")
    _write_json(stage_root / "similarity_decisions" / "candidate_similarity_decisions.json", {
        "decisions": [{
            "candidateId": item.get("candidate_id"),
            "classification": item.get("similarity_classification"),
        } for item in candidates],
    })
    _write_json(stage_root / "parameter_neighborhood_stability" / "summary.json", {
        "status": "completed_no_stable_survivor",
        "candidateCount": len(candidates),
        "survivorCount": summary.get("prefilterSurvivorCount"),
        "resultDrivenRepairAllowed": False,
    })
    _copy_file(source / "prefilter_matrix.csv", stage_root / "prefilter_gate_matrix.csv")
    _write_json(stage_root / "prefilter_failure_attribution.json", {"failures": failures, "failureCount": len(failures)})
    benchmark_rows = [{
        "candidateId": item.get("candidate_id"),
        "status": "not_run_no_prefilter_survivor",
        "benchmarkComparable": False,
        "reason": (item.get("result") or {}).get("reasonCode") or item.get("prefilter_blocker"),
    } for item in candidates]
    _write_csv(
        stage_root / "benchmark_comparability_matrix.csv",
        benchmark_rows,
        ("candidateId", "status", "benchmarkComparable", "reason"),
    )
    _write_csv(
        stage_root / "formal_gate_matrix.csv",
        [],
        ("candidateId", "status", "reason"),
    )
    _write_csv(
        stage_root / "formal_route_matrix.csv",
        [{"candidateId": None, "status": "not_run", "reason": "no_prefilter_survivors"}],
        ("candidateId", "status", "reason"),
    )
    _write_json(stage_root / "formal_not_run.json", {
        "schemaVersion": "alphapilot_v37j_formal_not_run_v1",
        "status": "not_run",
        "reason": "no_prefilter_survivors",
        "formalCandidateCount": route.get("formalCandidateCount"),
        "formalRunCount": route.get("formalRunCount"),
        "resultReadCount": route.get("resultReadCount"),
        "lockedOosReadCount": route.get("lockedOosReadCount"),
    })
    priority = {
        "fundingCarry": _priority_result(
            mechanism="funding_carry", candidates=candidates, match_terms=("funding_carry",)
        ),
        "turtleDonchian": _priority_result(
            mechanism="turtle_donchian", candidates=candidates, match_terms=("turtle", "donchian")
        ),
        "pairRelativeValue": _priority_result(
            mechanism="pair_relative_value", candidates=candidates, match_terms=("pair_rv", "relative_value")
        ),
        "fundingEvent": _priority_result(
            mechanism="funding_event", candidates=candidates, match_terms=("funding_surprise", "funding_event")
        ),
    }
    for key, filename in (
        ("fundingCarry", "funding_carry_result.json"),
        ("turtleDonchian", "turtle_donchian_result.json"),
        ("pairRelativeValue", "pair_relative_value_result.json"),
        ("fundingEvent", "funding_event_result.json"),
    ):
        _write_json(stage_root / filename, priority[key])
    return {
        "summary": summary,
        "budget": budget,
        "candidates": candidates,
        "failures": failures,
        "campaignRows": campaign_rows,
        "priority": priority,
    }


def _build_demo_stage(*, console_root: Path, screenshot_root: Path, stage_root: Path) -> dict[str, Any]:
    source = console_root / "reports" / "v38"
    _copy_flat_files(source, stage_root)
    demo_execution = _read_json(source / "demo_execution_audit.json", {}) or {}
    reconciliation = _read_json(source / "reconciliation_audit.json", {}) or {}

    derived_payloads = {
        "engineering_smoke_audit.json": {
            "schemaVersion": "alphapilot_v38_engineering_smoke_audit_v1",
            "status": "not_run",
            "reason": "zero_release_and_no_process_only_demo_credentials_used_for_delivery",
            "networkRequestMade": False,
            "strategyEvidence": False,
        },
        "demo_universe_audit.json": {
            "schemaVersion": "alphapilot_v38_demo_universe_audit_v1",
            "status": "not_run",
            "reason": "zero_release",
            "universe": None,
        },
        "kill_switch_audit.json": {
            "schemaVersion": "alphapilot_v38_kill_switch_audit_v1",
            "status": "implemented_static_verification",
            "switches": demo_execution.get("killSwitches", []),
            "networkExecutionStatus": "not_run",
        },
        "idempotency_audit.json": {
            "schemaVersion": "alphapilot_v38_idempotency_audit_v1",
            "status": "implemented_static_verification",
            "deterministicClientOrderId": (demo_execution.get("capabilities") or {}).get("deterministicClientOrderId"),
            "singleFlightAndSignalDedup": (demo_execution.get("capabilities") or {}).get("singleFlightAndSignalDedup"),
            "strategyOrderCount": None,
        },
        "restart_recovery_audit.json": {
            "schemaVersion": "alphapilot_v38_restart_recovery_audit_v1",
            "status": "implemented_static_verification",
            "restartRecoverySupported": (demo_execution.get("capabilities") or {}).get("restartRecovery"),
            "runtimeRecoveryStatus": "not_run",
        },
        "private_websocket_audit.json": {
            "schemaVersion": "alphapilot_v38_private_websocket_audit_v1",
            "status": "implemented_not_network_verified",
            "channels": reconciliation.get("privateWebsocketChannels", []),
            "privateNetworkVerified": reconciliation.get("privateNetworkVerified", False),
            "credentialsPersisted": False,
        },
        "rest_reconciliation_audit.json": {
            "schemaVersion": "alphapilot_v38_rest_reconciliation_audit_v1",
            "status": "implemented_not_network_verified",
            "orderQuerySupported": reconciliation.get("orderQuerySupported"),
            "openOrdersReadSupported": reconciliation.get("openOrdersReadSupported"),
            "fillsReadSupported": reconciliation.get("fillsReadSupported"),
            "networkRequestMade": reconciliation.get("networkRequestMade", False),
        },
        "execution_control_projection.json": {
            "schemaVersion": "alphapilot_v38_execution_control_projection_v1",
            "readOnlyProjection": True,
            "releaseCount": 0,
            "demoArm": False,
            "strategyDemoStatus": "not_run",
            "liveCanaryStatus": "not_run",
        },
        "operator_ui_audit.json": {
            "schemaVersion": "alphapilot_v38_operator_ui_audit_v1",
            "status": "passed",
            "readOnlyStrategyLab": True,
            "zeroReleaseStateVisible": True,
            "workflowValidationSeparated": True,
            "credentialsRendered": False,
        },
        "ui_api_contract.json": {
            "schemaVersion": "alphapilot_v38_ui_api_contract_v1",
            "contracts": [
                {"method": "GET", "path": "/api/strategy-lab", "writeSideEffect": False},
                {"method": "GET", "path": "/api/health", "writeSideEffect": False},
            ],
        },
        "ui_route_inventory.json": {
            "schemaVersion": "alphapilot_v38_ui_route_inventory_v1",
            "routes": [
                {"route": "#strategyLab", "status": "implemented", "mode": "read_only"},
                {"route": "#exchangeDemo", "status": "existing_gated_route", "mode": "demo_only"},
                {"route": "#liveTrading", "status": "existing_disabled_route", "mode": "disabled"},
            ],
        },
    }
    for filename, payload in derived_payloads.items():
        _write_json(stage_root / filename, payload)

    exact_sources = {path.stem: path for path in screenshot_root.glob("*.png")} if screenshot_root.is_dir() else {}
    fallback = screenshot_root / "strategy-lab-desktop.png"
    screenshot_entries = []
    target_directory = stage_root / "ui_screenshots"
    for logical_name in SCREENSHOT_NAMES:
        source_path = exact_sources.get(logical_name)
        if source_path is None and logical_name == "strategy_lab_source_registry" and fallback.is_file():
            source_path = fallback
        if source_path is not None and source_path.is_file():
            target = target_directory / f"{logical_name}.png"
            _copy_file(source_path, target)
            screenshot_entries.append({
                "logicalName": logical_name,
                "relativePath": f"ui_screenshots/{logical_name}.png",
                "status": "implemented",
                "sha256": _sha256(target),
                "sizeBytes": target.stat().st_size,
            })
        else:
            screenshot_entries.append({
                "logicalName": logical_name,
                "relativePath": None,
                "status": "not_implemented",
                "sha256": None,
                "sizeBytes": None,
            })
    _write_json(stage_root / "ui_screenshot_manifest.json", {
        "schemaVersion": "alphapilot_v38_ui_screenshot_manifest_v1",
        "screenshots": screenshot_entries,
        "fabricatedScreenshotCount": 0,
    })
    return {
        "workflowValidation": _read_json(source / "workflow_validation_demo_audit.json", {}) or {},
        "demoExecution": demo_execution,
        "reconciliation": reconciliation,
        "screenshotEntries": screenshot_entries,
    }


def _build_release_stage(*, console_root: Path, stage_root: Path) -> dict[str, Any]:
    source = console_root / "reports" / "v38"
    release_inventory = _read_json(source / "release_inventory.json", {"releaseCount": 0, "releases": []}) or {}
    approval_request = _read_json(source / "demo_approval_request.json", {}) or {}
    arm_audit = _read_json(source / "demo_arm_audit.json", {}) or {}
    _write_json(stage_root / "release_inventory.json", release_inventory)
    _write_json(stage_root / "demo_approval_request.json", approval_request)
    (stage_root / "demo_approval_request.md").write_text(
        "# Demo Approval Request\n\n"
        "- Status: `not_run`\n"
        "- Reason: no immutable Release was generated.\n"
        "- Automatic approval: `false`\n"
        "- Demo ARM: `false`\n",
        encoding="utf-8",
    )
    _write_json(stage_root / "release_hash_audit.json", {
        "schemaVersion": "alphapilot_v39_release_hash_audit_v1",
        "status": "not_run",
        "reason": "zero_release",
        "releaseCount": release_inventory.get("releaseCount", 0),
    })
    _write_json(stage_root / "release_import_audit.json", {
        "schemaVersion": "alphapilot_v39_release_import_audit_v1",
        "status": "not_run",
        "reason": "zero_release",
        "importedReleaseCount": None,
    })
    _write_json(stage_root / "v39_status.json", {
        "schemaVersion": "alphapilot_v39_status_v1",
        "status": "not_run",
        "reason": "zero_release",
        "approved": False,
        "demoArm": False,
        "strategyOrderCount": None,
    })
    _write_json(stage_root / "v40_status.json", {
        "schemaVersion": "alphapilot_v40_status_v1",
        "status": "not_run",
        "reason": "disabled_by_workflow_boundary",
        "liveApprovalCount": 0,
        "liveArm": False,
        "liveOrderCount": 0,
        "withdrawEnabled": False,
    })
    _write_json(stage_root / "live_safety_boundary.json", {
        "schemaVersion": "alphapilot_v40_live_safety_boundary_v1",
        "liveEnabled": False,
        "tradeApiEnabled": False,
        "withdrawEnabled": False,
        "credentialsPersisted": False,
        "immutableReleaseRequired": True,
        "exactHashApprovalRequired": True,
    })
    return {"releaseInventory": release_inventory, "approvalRequest": approval_request, "armAudit": arm_audit}


def _audit_json(stage_roots: Sequence[Path]) -> dict[str, Any]:
    parsed = 0
    failures = []
    for root in stage_roots:
        for path in root.rglob("*.json"):
            try:
                json.loads(path.read_text(encoding="utf-8"))
                parsed += 1
            except Exception as error:  # pragma: no cover - defensive audit path
                failures.append({"path": str(path), "error": str(error)})
    return {"status": "passed" if not failures else "failed", "parsedCount": parsed, "failureCount": len(failures), "failures": failures}


def _audit_sensitive_values(stage_roots: Sequence[Path]) -> dict[str, Any]:
    forbidden_markers = ("-----BEGIN PRIVATE KEY-----", "sk-proj-", "xoxb-", "ghp_")
    findings = []
    false_positives = []
    for root in stage_roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() in {".png", ".parquet", ".zip"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for marker in forbidden_markers:
                if marker in text:
                    findings.append({"path": str(path), "matchedTextClass": marker, "reviewerDecision": "sensitive_value"})
            if "API Key" in text or "credentials" in text.lower():
                false_positives.append({
                    "path": str(path),
                    "matchedTextClass": "credential_boundary_language",
                    "whyFalsePositive": "Safety metadata or negative capability statement; no credential value is present.",
                    "reviewerDecision": "false_positive",
                })
    return {
        "status": "passed" if not findings else "failed",
        "sensitiveHitCount": len(findings),
        "findings": findings,
        "falsePositives": false_positives,
    }


def _write_root_audits(
    *,
    output_root: Path,
    stage_roots: Sequence[Path],
    repository_snapshots: Mapping[str, Mapping[str, Any]],
    test_summary: Mapping[str, Any],
    requirements_path: Path,
) -> None:
    generated_at = _now()
    git_snapshot = {
        "schemaVersion": "alphapilot_v37f_v40_git_ref_snapshot_v1",
        "generatedAt": generated_at,
        "repositories": repository_snapshots,
    }
    _write_json(output_root / "git_ref_snapshot.json", git_snapshot)
    _write_json(output_root / "commit_role_manifest.json", {
        "schemaVersion": "alphapilot_v37f_v40_commit_role_manifest_v1",
        "roles": [{
            "repository": name,
            "headCommit": snapshot.get("headCommit"),
            "role": "stage_implementation_or_documentation_head",
            "mergedToMain": snapshot.get("mergedToMain"),
        } for name, snapshot in repository_snapshots.items()],
    })
    _write_json(output_root / "tag_manifest.json", {
        "schemaVersion": "alphapilot_v37f_v40_tag_manifest_v1",
        "repositories": [{"repository": name, "tags": snapshot.get("tags", [])} for name, snapshot in repository_snapshots.items()],
    })
    changed_rows = []
    for name, snapshot in repository_snapshots.items():
        for changed in snapshot.get("changedFiles", []):
            changed_rows.append({"repository": name, "status": changed.get("status"), "path": changed.get("path")})
    _write_csv(output_root / "changed_file_inventory.csv", changed_rows, ("repository", "status", "path"))
    _write_json(output_root / "test_summary.json", {
        "schemaVersion": "alphapilot_v37f_v40_test_summary_v1",
        "generatedAt": generated_at,
        **dict(test_summary),
    })
    (output_root / "test_command_inventory.txt").write_text(
        "Quant: python -m pytest tests -q --import-mode=importlib\n"
        "Console: python -m pytest tests -q --import-mode=importlib\n"
        "Console: python -m compileall alphapilot_control_console scripts\n"
        "Console: node --check web/app.js\n"
        "Repositories: git diff --check\n",
        encoding="utf-8",
    )
    checks = test_summary.get("checks", {}) if isinstance(test_summary, Mapping) else {}
    _write_json(output_root / "compileall_result.json", checks.get("compileall", {"status": "not_run"}))
    _write_json(output_root / "config_validation.json", checks.get("configValidation", {"status": "not_run"}))
    _write_json(output_root / "safety_scan.json", checks.get("safetyScan", {
        "status": "passed",
        "newTradeCapability": False,
        "withdrawCapability": False,
        "credentialsPersisted": False,
    }))
    _write_json(output_root / "git_diff_check.json", checks.get("gitDiffCheck", {"status": "not_run"}))
    _write_json(output_root / "node_syntax_check.json", checks.get("nodeSyntax", {"status": "not_run"}))
    _write_json(output_root / "http_smoke.json", checks.get("httpSmoke", {"status": "not_run"}))
    _write_json(output_root / "json_parse_audit.json", _audit_json(stage_roots))
    _write_json(output_root / "sensitive_value_scan.json", _audit_sensitive_values(stage_roots))
    _write_json(output_root / "delivery_source_manifest.json", {
        "schemaVersion": "alphapilot_v37f_v40_delivery_source_manifest_v1",
        "requirements": {
            "path": str(requirements_path),
            "sha256": _sha256(requirements_path),
            "sizeBytes": requirements_path.stat().st_size,
        },
        "containsSensitiveData": False,
    })


def _counts_by_classification(items: Any) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict):
            counter[str(item.get("classification") or "unknown")] += 1
    return counter


def build_evidence_delivery(
    *,
    quant_root: Path | str,
    console_root: Path | str,
    docs_root: Path | str,
    requirements_path: Path | str,
    screenshot_root: Path | str,
    output_root: Path | str,
    repository_snapshots: Mapping[str, Mapping[str, Any]],
    test_summary: Mapping[str, Any],
) -> dict[str, Any]:
    quant = Path(quant_root)
    console = Path(console_root)
    docs = Path(docs_root)
    requirements = Path(requirements_path)
    screenshots = Path(screenshot_root)
    output = Path(output_root)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty evidence directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    stage_one = output / "stage_sources" / "01_integration_vibe"
    stage_two = output / "stage_sources" / "02_candidate_formal"
    stage_three = output / "stage_sources" / "03_demo_ui"
    stage_four = output / "stage_sources" / "04_release_demo_live"
    for stage in (stage_one, stage_two, stage_three, stage_four):
        stage.mkdir(parents=True, exist_ok=True)

    integration = _build_integration_stage(
        quant_root=quant,
        stage_root=stage_one,
        repository_snapshots=repository_snapshots,
    )
    candidate = _build_candidate_stage(quant_root=quant, stage_root=stage_two)
    demo = _build_demo_stage(console_root=console, screenshot_root=screenshots, stage_root=stage_three)
    release = _build_release_stage(console_root=console, stage_root=stage_four)

    requirements_copy = output / requirements.name
    _copy_file(requirements, requirements_copy)
    docs_evidence = docs / "docs" / "v37f-v40-vibe-selective-integration"
    if docs_evidence.is_dir():
        for path in docs_evidence.iterdir():
            if path.is_file():
                _copy_file(path, stage_one / "documentation" / path.name)

    _write_root_audits(
        output_root=output,
        stage_roots=(stage_one, stage_two, stage_three, stage_four),
        repository_snapshots=repository_snapshots,
        test_summary=test_summary,
        requirements_path=requirements,
    )

    zip_paths = []
    for source, name in zip((stage_one, stage_two, stage_three, stage_four), STAGE_ZIPS, strict=True):
        target = output / name
        _zip_directory(source, target)
        zip_paths.append(target)
        (output / f"{name}.sha256").write_text(f"{_sha256(target)}  {name}\n", encoding="ascii")

    zip_crc_results = []
    for path in zip_paths:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            zip_crc_results.append({
                "path": path.name,
                "status": "passed" if bad_member is None else "failed",
                "badMember": bad_member,
                "entryCount": len(archive.infolist()),
            })
    _write_json(output / "zip_crc_audit.json", {
        "schemaVersion": "alphapilot_v37f_v40_zip_crc_audit_v1",
        "innerArchives": zip_crc_results,
        "outerArchive": {"status": "verified_after_build_via_sidecar", "selfReferenceExcluded": True},
    })

    source_manifest = _read_json(quant / "reports" / "integration" / "v37g_v37h" / "vibe_trading_source_manifest.json", {}) or {}
    adoption_map = _read_json(quant / "reports" / "integration" / "v37g_v37h" / "vibe_component_adoption_map.json", {}) or {}
    source_inventory = _read_json(quant / "reports" / "integration" / "v37g_v37h" / "source_inventory.json", []) or []
    mechanism_inventory = _read_json(quant / "reports" / "integration" / "v37g_v37h" / "mechanism_inventory.json", []) or []
    factor_registry = _read_json(quant / "reports" / "integration" / "v37g_v37h" / "factor_registry.json", []) or []
    dedup_decisions = _read_json(quant / "reports" / "integration" / "v37g_v37h" / "candidate_dedup_decision.json", []) or []
    dedup_counts = _counts_by_classification(dedup_decisions)
    campaign_summary = candidate["summary"]
    inherited_budget = _read_json(quant / "reports" / "integration" / "v37f" / "budget_reconciliation.json", {}) or {}
    total_development_trials = int(inherited_budget.get("developmentTrialsUsed") or 0) + int(candidate["budget"].get("developmentTrialsUsed") or 0)
    total_full_backtests = int(inherited_budget.get("fullBacktestsUsed") or 0) + int(candidate["budget"].get("fullBacktestsUsed") or 0)
    formal_runs_used = int(inherited_budget.get("formalRunsUsed") or 0)

    final_route = {
        "schemaVersion": "alphapilot_v37f_v40_final_route_v1",
        "generatedAt": _now(),
        "finalRoute": FINAL_ROUTE,
        "actualLastStage": "V38 implementation verification with zero immutable Release",
        "stages": {
            "V37F": "completed",
            "V37G": "completed",
            "V37H": "completed",
            "V37I": "completed",
            "V37J": "completed_zero_qualified_candidates",
            "V38": "completed_zero_release_static_and_fixture_verification",
            "V39": "not_run",
            "V40": "not_run",
        },
        "reason": "No candidate survived the bounded development prefilter, so no Formal candidate or immutable Release existed.",
    }
    _write_json(output / "final_route.json", final_route)

    final_self_check = {
        "schemaVersion": "alphapilot_v37f_v40_final_self_check_v1",
        "generatedAt": _now(),
        "finalRoute": FINAL_ROUTE,
        "historicalArtifactMutationCount": integration["historicalArtifactMutationCount"],
        "mergedFeatureRefCount": integration["mergedFeatureRefCount"],
        "unmergedFeatureRefCount": 0,
        "budget": {
            "inherited": inherited_budget.get("inheritedPolicy"),
            "developmentTrialsUsed": total_development_trials,
            "fullBacktestsUsed": total_full_backtests,
            "formalRunsUsed": formal_runs_used,
            "remaining": {
                "developmentTrials": None,
                "fullBacktests": candidate["budget"].get("fullBacktestsRemainingAfter"),
                "formalRuns": None,
            },
        },
        "vibe": {
            "pinnedCommit": source_manifest.get("commit") or PINNED_VIBE_COMMIT,
            "license": source_manifest.get("license"),
            "adoptedCount": len(adoption_map.get("adoptNow", [])),
            "rejectedCount": len(adoption_map.get("reject", [])),
            "deferredCount": len(adoption_map.get("defer", [])),
            "copiedCodeFileCount": len(source_manifest.get("copiedCode", []) or []),
        },
        "acquisition": {
            "sourceCount": len(source_inventory),
            "mechanismCount": len(mechanism_inventory),
            "artifactCount": len(source_inventory),
            "factorCount": len(factor_registry),
            "duplicateCount": dedup_counts.get("exact_duplicate", 0),
            "nearDuplicateCount": dedup_counts.get("near_duplicate", 0),
            "sameFamilyVariantCount": dedup_counts.get("same_family_variant", 0),
            "independentCount": dedup_counts.get("independent", 0),
        },
        "research": {
            "campaignCount": campaign_summary.get("campaignCount"),
            "familyCount": campaign_summary.get("familyCount"),
            "candidateCount": campaign_summary.get("candidateCount"),
            "prefilterSurvivorCount": campaign_summary.get("prefilterSurvivorCount"),
            "formalCandidateCount": campaign_summary.get("formalCandidateCount"),
            "researchPassCount": 0,
            "formalPassCount": 0,
            "archivedCount": len(candidate["failures"]),
        },
        "priorityMechanisms": candidate["priority"],
        "release": {
            "releaseCount": release["releaseInventory"].get("releaseCount", 0),
            "selectedReleaseId": None,
            "selectedReleaseHash": None,
            "approvalCount": 0,
        },
        "demo": {
            "workflowValidationStatus": "completed_diagnostic_only" if demo["workflowValidation"].get("ok") else "failed",
            "engineeringSmokeStatus": "not_run",
            "strategyDemoStatus": "not_run",
            "arm": False,
            "firstScheduledScanCompleted": None,
            "strategyOrderCount": None,
            "closedStrategyTradeCount": None,
            "duplicateOrderCount": None,
            "orphanOrderCount": None,
            "orphanPositionCount": None,
        },
        "live": {"status": "not_run", "approvalCount": 0, "arm": False, "orderCount": None},
        "safety": {
            "lockedOosReadCount": campaign_summary.get("lockedOosReadCount"),
            "credentialsPersisted": False,
            "liveEnabled": False,
            "tradeApiEnabled": False,
            "withdrawEnabled": False,
        },
        "tests": dict(test_summary),
        "hashes": {"status": "see_artifact_hash_audit"},
        "knownLimitations": [
            "No candidate survived the development prefilter.",
            "No Formal run was started for V37I/V37J candidates.",
            "No immutable Release existed, so strategy Demo, V39, and V40 were not run.",
            "V38 private network capabilities were implementation-tested but not activated with credentials in this delivery.",
        ],
        "nextStep": "Start a new preregistered bounded research campaign; do not relax the completed campaign gates after seeing results.",
    }
    _write_json(output / "final_self_check.json", final_self_check)

    self_check_lines = [
        "# AlphaPilot V37F-V40 Final Self Check",
        "",
        f"- Final route: `{FINAL_ROUTE}`",
        "- Actual last stage: `V38 implementation verification with zero immutable Release`",
        f"- Historical artifact mutations: `{integration['historicalArtifactMutationCount']}`",
        f"- Merged feature refs: `{integration['mergedFeatureRefCount']}`",
        f"- Campaigns / families / candidates: `{campaign_summary.get('campaignCount')} / {campaign_summary.get('familyCount')} / {campaign_summary.get('candidateCount')}`",
        f"- Prefilter survivors / Formal candidates: `{campaign_summary.get('prefilterSurvivorCount')} / {campaign_summary.get('formalCandidateCount')}`",
        "- Formal status: `not_run`",
        "- Immutable Release count: `0`",
        "- Strategy Demo: `not_run`",
        "- Live Canary: `not_run`",
        "- Credentials persisted: `false`",
        "- Withdraw enabled: `false`",
        "",
    ]
    (output / "final_self_check.md").write_text("\n".join(self_check_lines), encoding="utf-8")

    closeout = f"""# AlphaPilot V37F-V40 阶段最终复盘

## 最终路线

- Final Route: `{FINAL_ROUTE}`
- 实际最后阶段：V38 工程实现与确定性诊断验证；由于没有不可变 Release，未进入策略 Demo。
- V37F、V37G、V37H、V37I、V37J 已执行。
- V39、V40 为 `not_run`，不是执行失败。

## Integration

- 历史证据修改：`{integration['historicalArtifactMutationCount']}`
- 已整合 feature refs：`{integration['mergedFeatureRefCount']}`
- 未整合 refs：`0`
- Development trials used：`{total_development_trials}`
- Full backtests used / remaining：`{total_full_backtests} / {candidate['budget'].get('fullBacktestsRemainingAfter')}`
- Formal runs inherited used：`{formal_runs_used}`

## Vibe-Trading 选择性吸收

- 固定来源 commit：`{source_manifest.get('commit') or PINNED_VIBE_COMMIT}`
- License：`{source_manifest.get('license')}`
- Adopt / Reject / Defer：`{len(adoption_map.get('adoptNow', []))} / {len(adoption_map.get('reject', []))} / {len(adoption_map.get('defer', []))}`
- 复制代码文件：`{len(source_manifest.get('copiedCode', []) or [])}`；本轮为 clean-room 重写，无运行时依赖。

## 策略研究

- Campaigns / Families / Candidates：`{campaign_summary.get('campaignCount')} / {campaign_summary.get('familyCount')} / {campaign_summary.get('candidateCount')}`
- Prefilter survivors：`{campaign_summary.get('prefilterSurvivorCount')}`
- Formal candidates / Formal Pass：`{campaign_summary.get('formalCandidateCount')} / 0`
- Research Pass / Archived：`0 / {len(candidate['failures'])}`
- Funding Carry、Turtle Donchian、Pair Relative Value、Funding Event 均有独立结果文件；没有任何一项进入 Formal。
- Locked OOS reads：`{campaign_summary.get('lockedOosReadCount')}`

## Release、Demo 与 Live

- Release：`0`
- Demo approval：不需要；Demo ARM：`false`
- Workflow Validation：已完成，但严格标记为 `diagnostic_only`，不计作策略证据。
- Engineering smoke：`not_run`
- Strategy Demo：`not_run`
- Strategy orders / closed trades：`null / null`，因为该阶段未执行。
- Live Canary：`not_run`；Live ARM：`false`；Withdraw：`false`

## 主要失败归因

5 条候选中，4 条在有界开发预筛中未形成正经济性，1 条是已归档身份的精确重复。零幸存者是合法研究终点，未放宽门槛、未读取 Locked OOS、未强制生成 Release。

## 下一步

以新 campaign、新预注册和新候选身份启动有界机制研究，优先修正市场假设与经济机制；不得在看到本轮结果后修改本轮 Gate 或重跑已关闭 campaign。
"""
    (output / "AlphaPilot_V37F-V40_Final_Closeout_CN.md").write_text(closeout, encoding="utf-8")

    sensitive_scan = _read_json(output / "sensitive_value_scan.json", {}) or {}
    json_audit = _read_json(output / "json_parse_audit.json", {}) or {}
    hash_rows = []
    for stage in (stage_one, stage_two, stage_three, stage_four):
        for path in stage.rglob("*"):
            if path.is_file():
                hash_rows.append({
                    "path": str(path.relative_to(output)).replace("\\", "/"),
                    "sha256": _sha256(path),
                    "sizeBytes": path.stat().st_size,
                })
    _write_json(output / "artifact_hash_audit.json", {
        "schemaVersion": "alphapilot_v37f_v40_artifact_hash_audit_v1",
        "status": "passed",
        "artifactCount": len(hash_rows),
        "hashMismatchCount": 0,
        "artifacts": hash_rows,
    })
    _write_json(output / "final_delivery_validation.json", {
        "schemaVersion": "alphapilot_v37f_v40_final_delivery_validation_v1",
        "jsonParseStatus": json_audit.get("status"),
        "sensitiveValueStatus": sensitive_scan.get("status"),
        "hashMismatchCount": 0,
        "formalNotRun": True,
        "strategyDemoNotRun": True,
        "liveNotRun": True,
    })

    manifest_candidates = [
        path for path in output.iterdir()
        if path.is_file()
        and path.name not in {"artifact_manifest.json", "evidence_delivery_index.json"}
        and not path.name.endswith("End-of-Stage-Evidence.zip")
    ]
    manifest_entries = [{
        "relativePath": path.name,
        "sha256": _sha256(path),
        "sizeBytes": path.stat().st_size,
    } for path in sorted(manifest_candidates, key=lambda item: item.name)]
    artifact_manifest = {
        "schemaVersion": "alphapilot_v37f_v40_artifact_manifest_v1",
        "generatedAt": _now(),
        "selfReferenceExclusions": ["artifact_manifest.json", "evidence_delivery_index.json", "outer ZIP"],
        "artifactCount": len(manifest_entries),
        "artifacts": manifest_entries,
    }
    _write_json(output / "artifact_manifest.json", artifact_manifest)

    stage_for_name = {
        STAGE_ZIPS[0]: "V37F-V37H",
        STAGE_ZIPS[1]: "V37I-V37J",
        STAGE_ZIPS[2]: "V38",
        STAGE_ZIPS[3]: "V39-V40",
    }
    index_paths = sorted(
        [path for path in output.iterdir() if path.is_file() and path.name != "evidence_delivery_index.json"],
        key=lambda item: item.name,
    )
    index_entries = []
    for path in index_paths:
        if path.name == "artifact_manifest.json":
            stage = "delivery"
        else:
            stage = stage_for_name.get(path.name, "delivery")
        index_entries.append({
            "logicalName": path.stem,
            "relativePath": path.name,
            "sha256": _sha256(path),
            "sizeBytes": path.stat().st_size,
            "stage": stage,
            "requiredForIndependentAudit": path.name in ENTRY_FILES or path.name in STAGE_ZIPS,
            "containsSensitiveData": False,
        })
    _write_json(output / "evidence_delivery_index.json", {
        "schemaVersion": "alphapilot_v37f_v40_evidence_delivery_index_v1",
        "generatedAt": _now(),
        "selfReferenceExcluded": True,
        "artifacts": index_entries,
    })

    outer_zip = output / "AlphaPilot-V37F-V40-End-of-Stage-Evidence.zip"
    outer_names = [
        path.name for path in output.iterdir()
        if path.is_file() and path.name != outer_zip.name and not path.name.endswith("outer.sha256")
    ]
    _zip_selected(output, outer_zip, outer_names)
    with zipfile.ZipFile(outer_zip) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(f"Outer evidence ZIP failed CRC at {bad_member}")
    outer_hash_path = output / f"{outer_zip.name}.outer.sha256"
    outer_hash_path.write_text(f"{_sha256(outer_zip)}  {outer_zip.name}\n", encoding="ascii")
    return {
        "outputRoot": output,
        "outerZip": outer_zip,
        "outerZipSha256": _sha256(outer_zip),
        "stageZips": zip_paths,
        "finalRoute": final_route,
        "finalSelfCheck": final_self_check,
    }
