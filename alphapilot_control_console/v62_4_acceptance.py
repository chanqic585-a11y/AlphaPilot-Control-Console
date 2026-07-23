"""Truth-preserving helpers for the V62.4 acceptance handoff.

The acceptance layer is read-only. It projects existing research, runtime and
repository evidence without approving releases, arming runtimes or submitting
orders.
"""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL = (
    "00_START_HERE",
    "01_identity",
    "02_source_and_diff",
    "03_runtime",
    "04_authority_and_security",
    "05_strategy_factory",
    "06_ai_orchestration",
    "07_matchability_forward",
    "08_factor_model",
    "09_demo_live_execution",
    "10_ui",
    "11_database",
    "12_tests_quality",
    "13_performance",
    "14_known_issues",
    "15_independent_verification",
    "16_final",
)

REQUIRED_SECTION_FILES: dict[str, tuple[str, ...]] = {
    "00_START_HERE": (
        "README_CN.md", "package_scope.json", "current_mechanical_state.json",
        "current_authoritative_identity.json", "repository_role_map.json",
        "evidence_authority_index.json", "version_timeline.json",
        "known_issues_summary.json", "exclusion_summary.json",
    ),
    "01_identity": (
        "repository_snapshot.json", "remote_ref_verification.json", "tag_map.json",
        "worktree_status.json", "recent_commit_graph.txt", "git_bundle_verify.json", "git_fsck.json",
    ),
    "02_source_and_diff": (
        "source_file_manifest.json", "source_language_summary.json",
        "baseline_to_current_diff.patch", "changed_file_inventory.json",
        "generated_vs_handwritten_audit.json", "large_file_manifest.json",
    ),
    "03_runtime": (
        "runtime_identity.json", "process_inventory.json", "module_load_path.json",
        "runtime_source_parity.json", "runtime_lease.json", "scheduler_inventory.json",
        "listening_ports.json", "last_scan_summary.json", "reconciliation_summary.json",
    ),
    "04_authority_and_security": (
        "authoritative_object_map.json", "duplicate_authority_audit.json",
        "legacy_route_retirement_audit.json", "live_admission_call_graph.json",
        "release_approval_arm_matrix.json", "runtime_lease_audit.json",
        "http_write_route_matrix.json", "csrf_origin_audit.json", "credential_scan.json",
        "kill_switch_audit.json", "actual_position_risk_audit.json", "pit_missing_value_audit.json",
    ),
    "05_strategy_factory": (
        "factory_state_machine.json", "factory_call_graph.json", "worker_inventory.json",
        "queue_snapshot.json", "trial_ledger.jsonl", "formal_job_ledger.jsonl",
        "worker_heartbeat.jsonl", "job_lease_audit.json", "checkpoint_recovery_audit.json",
        "dead_letter_queue.jsonl", "pilot_campaign_summary.json", "pilot_candidate_manifest.json",
        "pilot_trial_manifest.json", "pilot_failure_attribution.json", "pilot_formal_handoff.json",
    ),
    "06_ai_orchestration": (
        "provider_contracts.json", "ai_model_registry.json", "routing_policy.json",
        "task_type_matrix.json", "ai_task_schema.json", "ai_call_ledger_sample.json",
        "dual_review_audit.json", "provider_fallback_audit.json", "provider_health_snapshot.json",
        "redaction_audit.json", "prompt_injection_audit.json",
        "structured_output_validation.json", "semantic_validation.json",
        "batch_idempotency_audit.json", "cost_budget_audit.json", "forbidden_tool_audit.json",
    ),
    "07_matchability_forward": (
        "strategy_matchability_by_component.json", "matchability_30d.json", "matchability_90d.json",
        "condition_rejection_matrix.csv", "broad_universe_successor_audit.json",
        "mechanism_diversity_audit.json", "frequency_tier_audit.json", "forward_task_schema.json",
        "forward_task_snapshot.json", "forward_task_action_audit.json",
    ),
    "08_factor_model": (
        "production_factor_registry.json", "factor_available_at_audit.json",
        "real_factor_bench_summary.json", "alpha101_audit.json",
        "alpha191_compatibility_audit.json", "validated_crypto_factor_subset.json",
        "training_dataset_manifest.json", "purged_walk_forward_report.json",
        "qlib_campaign_manifest.json", "model_registry.json", "model_artifact_manifest.json",
        "model_loader_audit.json", "inference_test_vectors.json", "demo_live_feature_parity.json",
        "base_vs_model_comparison.json", "drift_monitor_audit.json", "rollback_audit.json",
    ),
    "09_demo_live_execution": (
        "demo_execution_call_graph.json", "live_execution_call_graph.json",
        "order_lifecycle_trace_sample.json", "idempotency_audit.json", "restart_recovery_audit.json",
        "unknown_order_audit.json", "orphan_order_position_audit.json", "protection_order_audit.json",
        "execution_environment_isolation.json",
    ),
    "10_ui": (
        "ui_data_source_matrix.json", "ui_api_contract_map.json", "strategy_factory_desktop.png",
        "strategy_factory_mobile_390.png", "demo_desktop.png", "demo_mobile_390.png",
        "live_desktop.png", "live_mobile_390.png", "strategy_detail_drawer.png",
        "failure_analysis_drawer.png", "forward_task_panel.png", "ai_control_panel.png",
        "order_lifecycle_trace.png", "ui_browser_test_results.json",
    ),
    "11_database": (
        "database_inventory.json", "schema_only.sql", "pragma_audit.json",
        "migration_inventory.json", "foreign_key_audit.json", "integrity_check.json",
        "table_counts.json", "max_sequence_ids.json", "append_only_audit.json",
        "online_backup_receipt.json", "backup_restore_test.json",
    ),
    "12_tests_quality": (
        "test_command_ledger.jsonl", "test_results_summary.json", "skipped_xfailed_inventory.json",
        "coverage.xml", "coverage_summary.json", "ruff.json", "type_check.json",
        "bandit_semgrep.json", "dead_code_scan.json", "complexity_hotspots.json",
        "dependency_vulnerability_scan.json", "npm_audit.json", "playwright_results.json",
        "mutation_test_results.json", "disconnect_test_results.json",
    ),
    "13_performance": (
        "latency_segments.json", "research_worker_resource_usage.json",
        "ai_task_latency_and_cost.json", "sqlite_contention.json", "runtime_cpu_memory.json",
        "llm_hot_path_audit.json",
    ),
    "14_known_issues": (
        "open_issue_ledger.json", "not_run_matrix.json", "approved_exceptions.json",
        "manual_assumptions.json", "open_questions_for_acceptance.md",
    ),
    "15_independent_verification": (
        "verify_acceptance_package.py", "verify_runtime_identity.py", "verify_trial_ledger.py",
        "verify_ai_router.py", "verify_ui_data_sources.py", "verify_sqlite_snapshots.py",
        "verify_hashes.py", "independent_verification_result.json",
    ),
    "16_final": (
        "artifact_manifest.json", "package_hash_verification.json", "credential_scan.json",
        "final_self_check.json", "final_self_check.md", "final_closeout_cn.md",
    ),
}

MANIFEST_RELATIVE_PATH = "16_final/artifact_manifest.json"

MARKET_DATA_SUFFIXES = {".csv", ".parquet", ".pq", ".feather"}
MARKET_DATA_TOKENS = ("usdt", "swap", "ohlcv", "candle", "kline", "ticker", "market")
PACKAGE_BINARY_SUFFIXES = {".png", ".zip", ".sqlite", ".db", ".bundle"}

_ASSIGNMENT_SECRET = re.compile(
    r"(?i)\b(?:deepseek|gemini|openai|okx)?[_-]?(?:api[_-]?key|secret[_-]?key|passphrase|password|token)\s*[:=]\s*"
    r"(?!\b(?:absent|none|null|missing|process-only|redacted|not[_ -]?set)\b)([^\s,;}{]+)"
)
_PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def _find_pilot_report_root(root: Path) -> Path:
    direct = root / "campaign_summary.json"
    if direct.exists():
        return root
    candidates = sorted(root.glob("reports/*/campaign_summary.json"))
    if len(candidates) != 1:
        raise ValueError(
            f"Expected exactly one Pilot campaign_summary.json below {root}; found {len(candidates)}"
        )
    return candidates[0].parent


def load_pilot_evidence(root: Path) -> dict[str, Any]:
    """Load and cross-check a bounded real-trial Pilot evidence directory."""

    report_root = _find_pilot_report_root(root)
    summary = _read_object(report_root / "campaign_summary.json")
    preregistration = _read_object(report_root / "preregistration.json")
    projections = _read_object(report_root / "development_projection.json")
    formal_handoff = _read_object(report_root / "formal_handoff.json")

    candidate_ids = preregistration.get("candidateIds", [])
    trials_by_candidate = preregistration.get("trialsByCandidate", {})
    if not isinstance(candidate_ids, list) or not isinstance(trials_by_candidate, dict):
        raise ValueError("Pilot preregistration has an invalid candidate/trial shape")

    candidates: list[dict[str, Any]] = []
    trials: list[dict[str, Any]] = []
    projection_by_trial = {
        item.get("trialId"): item
        for item in projections.get("projections", [])
        if isinstance(item, dict) and item.get("trialId")
    }
    for candidate_id in candidate_ids:
        candidate_trials = trials_by_candidate.get(candidate_id, [])
        if not isinstance(candidate_trials, list):
            raise ValueError(f"Pilot trials are invalid for candidate {candidate_id}")
        families = sorted(
            {item.get("familyId") for item in candidate_trials if isinstance(item, dict) and item.get("familyId")}
        )
        candidates.append(
            {
                "candidateId": candidate_id,
                "familyIds": families,
                "trialCount": len(candidate_trials),
                "eligible": candidate_id in preregistration.get("eligibleCandidateIds", []),
            }
        )
        for trial in candidate_trials:
            if not isinstance(trial, dict):
                raise ValueError(f"Pilot trial is not an object for candidate {candidate_id}")
            trial_id = trial.get("trialId")
            enriched = dict(trial)
            enriched["result"] = projection_by_trial.get(trial_id)
            enriched["status"] = "completed" if trial_id in projection_by_trial else "missing_result"
            trials.append(enriched)

    expected_candidate_count = int(summary.get("candidateCount", -1))
    expected_trial_count = int(summary.get("trialCount", -1))
    completed_trial_count = int(summary.get("completedTrialCount", -1))
    if expected_candidate_count != len(candidates):
        raise ValueError(
            f"Pilot candidate count mismatch: summary={expected_candidate_count}, projected={len(candidates)}"
        )
    if expected_trial_count != len(trials):
        raise ValueError(f"Pilot trial count mismatch: summary={expected_trial_count}, projected={len(trials)}")
    completed = sum(1 for trial in trials if trial["status"] == "completed")
    if completed_trial_count != completed:
        raise ValueError(
            f"Pilot completed trial mismatch: summary={completed_trial_count}, projected={completed}"
        )

    return {
        "reportRoot": str(report_root),
        "summary": summary,
        "candidates": candidates,
        "trials": trials,
        "formalHandoff": formal_handoff,
        "sourceArtifacts": {
            name: str(report_root / name)
            for name in (
                "artifact_manifest.json",
                "campaign_summary.json",
                "development_projection.json",
                "development_replay_audit.json",
                "formal_handoff.json",
                "formal_route.json",
                "immutable_releases.json",
                "neighborhood_selection.json",
                "preregistration.json",
            )
            if (report_root / name).exists()
        },
    }


def build_formal_job_rows(pilot: dict[str, Any]) -> list[dict[str, Any]]:
    """Represent ready Formal work without fabricating a Formal run or result."""

    summary = pilot["summary"]
    rows = []
    for candidate in pilot["formalHandoff"].get("readyCandidates", []):
        rows.append(
            {
                "campaignId": summary["campaignId"],
                "candidateId": candidate["candidateId"],
                "selectedTrialId": candidate["selectedTrialId"],
                "status": "not_run_awaiting_preregistration_and_frozen_input",
                "formalRunCount": int(summary.get("formalRunCount", 0)),
                "resultReadCount": int(summary.get("resultReadCount", 0)),
                "executionAuthorized": False,
            }
        )
    return rows


def build_runtime_projection(
    *,
    health: dict[str, Any] | None,
    runtime: dict[str, Any] | None,
    network_error: str | None,
) -> dict[str, Any]:
    observed = health is not None and runtime is not None
    if not observed:
        return {
            "runtimeObserved": False,
            "runtimeSourceParity": "unverified",
            "newEntriesAllowed": False,
            "liveArmVerified": False,
            "withdrawVerifiedDisabled": False,
            "networkError": network_error or "runtime evidence unavailable",
            "health": None,
            "runtime": None,
        }
    return {
        "runtimeObserved": True,
        "runtimeSourceParity": runtime.get("runtimeSourceParity", "unverified"),
        "newEntriesAllowed": bool(runtime.get("newEntriesAllowed", False)),
        "liveArmVerified": bool(runtime.get("liveArmed", False)),
        "withdrawVerifiedDisabled": runtime.get("withdrawEnabled") is False,
        "networkError": None,
        "health": health,
        "runtime": runtime,
    }


def detect_credential_material(text: str) -> list[str]:
    """Return redacted reasons when likely raw credential material is present."""

    reasons: list[str] = []
    if _PRIVATE_KEY.search(text):
        reasons.append("private_key_material")
    for match in _ASSIGNMENT_SECRET.finditer(text):
        value = match.group(1).strip("'\"")
        if value and set(value) != {"*"} and value.lower() not in {
            "absent",
            "none",
            "null",
            "missing",
            "redacted",
        }:
            reasons.append("credential_assignment")
            break
    return reasons


def redact_credential_assignments(text: str) -> str:
    """Redact assignment-shaped credential fixtures before evidence export."""

    def replace(match: re.Match[str]) -> str:
        value_start = match.start(1) - match.start(0)
        return f"{match.group(0)[:value_start]}redacted"

    return _ASSIGNMENT_SECRET.sub(replace, text)


def find_foundation_sample_root(foundation_root: Path) -> Path:
    """Return the canonical sample-only root with legacy layout fallback."""

    preferred = foundation_root / "sample_only"
    if preferred.exists():
        return preferred
    return foundation_root / "data-governance" / "sample_only"


def iter_package_text_files(root: Path):
    """Yield final package text candidates, excluding transient build inputs."""

    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == ".foundation":
            continue
        if path.suffix.lower() in PACKAGE_BINARY_SUFFIXES:
            continue
        yield path


def select_remote_tag_commit(ls_remote_output: str, tag: str) -> str | None:
    """Resolve annotated or lightweight tags to the committed object SHA."""

    refs: dict[str, str] = {}
    for line in ls_remote_output.splitlines():
        parts = line.split()
        if len(parts) == 2:
            refs[parts[1]] = parts[0]
    direct = f"refs/tags/{tag}"
    return refs.get(f"{direct}^{{}}") or refs.get(direct)


def validate_data_omission_policy(root: Path) -> dict[str, Any]:
    omitted = root / "omitted_data_manifest.json"
    sample_root = root / "sample_only"
    zero_placeholders = []
    for path in root.rglob("*"):
        if not path.is_file() or path.stat().st_size != 0:
            continue
        lowered = path.name.lower()
        if path.suffix.lower() in MARKET_DATA_SUFFIXES and any(token in lowered for token in MARKET_DATA_TOKENS):
            zero_placeholders.append(path.relative_to(root).as_posix())
    samples = [path for path in sample_root.rglob("*") if path.is_file()] if sample_root.exists() else []
    return {
        "passed": omitted.exists() and bool(samples) and not zero_placeholders,
        "omittedManifestPresent": omitted.exists(),
        "sampleFileCount": len(samples),
        "zeroByteMarketPlaceholders": sorted(zero_placeholders),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_artifact_manifest(root: Path) -> list[dict[str, Any]]:
    """Build a deterministic manifest without recursively hashing itself."""

    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative == MANIFEST_RELATIVE_PATH:
            continue
        rows.append(
            {
                "relativePath": relative,
                "sha256": _sha256(path),
                "sizeBytes": path.stat().st_size,
                "sourceRepository": "acceptance_handoff",
                "sourceCommit": "recorded_in_01_identity",
                "classification": "authoritative_current",
            }
        )
    return rows


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"Expected JSONL object in {path}")
            rows.append(value)
    return rows


def verify_acceptance_package(root: Path) -> dict[str, Any]:
    """Independently verify handoff structure, counts, hashes and safety facts."""

    required = {
        f"{directory}/{name}"
        for directory, names in REQUIRED_SECTION_FILES.items()
        for name in names
    }
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    missing = sorted(required - actual)

    manifest_path = root / MANIFEST_RELATIVE_PATH
    manifest_rows: list[dict[str, Any]] = []
    invalid_json: list[str] = []
    if manifest_path.exists():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                manifest_rows = [row for row in payload if isinstance(row, dict)]
            else:
                invalid_json.append(MANIFEST_RELATIVE_PATH)
        except (UnicodeDecodeError, json.JSONDecodeError):
            invalid_json.append(MANIFEST_RELATIVE_PATH)

    expected_by_path = {
        str(row.get("relativePath")): row
        for row in manifest_rows
        if row.get("relativePath")
    }
    actual_manifestable = actual - {MANIFEST_RELATIVE_PATH}
    extra = sorted(actual_manifestable - set(expected_by_path))
    hash_mismatch = []
    for relative, row in expected_by_path.items():
        path = root / relative
        if not path.is_file():
            hash_mismatch.append(f"{relative}:missing")
            continue
        if row.get("sha256") != _sha256(path) or int(row.get("sizeBytes", -1)) != path.stat().st_size:
            hash_mismatch.append(relative)

    credential_hits = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.suffix.lower() in {".png", ".zip", ".sqlite", ".db", ".bundle"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relative = path.relative_to(root).as_posix()
        reasons = detect_credential_material(text)
        if reasons:
            credential_hits.append({"relativePath": relative, "reasonKinds": reasons})
        if path.suffix.lower() == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError:
                invalid_json.append(relative)

    trial_mismatch = []
    formal_mismatch = []
    summary_path = root / "05_strategy_factory" / "pilot_campaign_summary.json"
    trials_path = root / "05_strategy_factory" / "pilot_trial_manifest.json"
    candidates_path = root / "05_strategy_factory" / "pilot_candidate_manifest.json"
    formal_path = root / "05_strategy_factory" / "formal_job_ledger.jsonl"
    if all(path.exists() for path in (summary_path, trials_path, candidates_path, formal_path)):
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            trials = json.loads(trials_path.read_text(encoding="utf-8"))
            candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
            formal = _read_jsonl(formal_path)
            if int(summary.get("trialCount", -1)) != len(trials) or int(summary.get("completedTrialCount", -1)) != sum(1 for row in trials if row.get("status") == "completed"):
                trial_mismatch.append("pilot_trial_counts")
            if int(summary.get("candidateCount", -1)) != len(candidates):
                trial_mismatch.append("pilot_candidate_counts")
            if int(summary.get("formalRunCount", -1)) != sum(1 for row in formal if int(row.get("formalRunCount", 0)) > 0):
                formal_mismatch.append("pilot_formal_run_counts")
        except (TypeError, ValueError, json.JSONDecodeError):
            trial_mismatch.append("pilot_count_evidence_invalid")

    fixture_in_ui = []
    ui_matrix = root / "10_ui" / "ui_data_source_matrix.json"
    if ui_matrix.exists():
        try:
            matrix = json.loads(ui_matrix.read_text(encoding="utf-8"))
            if matrix.get("productionFixtureData") is not False:
                fixture_in_ui.append("productionFixtureData")
        except json.JSONDecodeError:
            fixture_in_ui.append("ui_data_source_matrix_invalid")

    forbidden_calls = []
    forbidden_audit = root / "06_ai_orchestration" / "forbidden_tool_audit.json"
    if forbidden_audit.exists():
        try:
            audit = json.loads(forbidden_audit.read_text(encoding="utf-8"))
            if int(audit.get("forbiddenTradingToolCallCount", -1)) != 0:
                forbidden_calls.append("forbiddenTradingToolCallCount")
        except (TypeError, ValueError, json.JSONDecodeError):
            forbidden_calls.append("forbidden_tool_audit_invalid")

    runtime_mismatch = []
    runtime_parity = root / "03_runtime" / "runtime_source_parity.json"
    if runtime_parity.exists():
        try:
            parity = json.loads(runtime_parity.read_text(encoding="utf-8"))
            if parity.get("runtimeObserved") is False and parity.get("newEntriesAllowed") is not False:
                runtime_mismatch.append("offline_runtime_must_disable_new_entries")
        except json.JSONDecodeError:
            runtime_mismatch.append("runtime_source_parity_invalid")

    result = {
        "missing": missing,
        "extra": extra,
        "hashMismatch": sorted(hash_mismatch),
        "invalidJson": sorted(set(invalid_json)),
        "credentialHits": credential_hits,
        "runtimeIdentityMismatch": runtime_mismatch,
        "trialCountMismatch": trial_mismatch,
        "formalCountMismatch": formal_mismatch,
        "fixtureInProductionUi": fixture_in_ui,
        "forbiddenLlmToolCalls": forbidden_calls,
    }
    result["passed"] = not any(result[key] for key in result if key != "passed")
    return result
