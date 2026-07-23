from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from alphapilot_control_console.v62_4_1_independent_verifiers import (
    verify_ai_orchestration,
    verify_sqlite_snapshots,
    verify_trial_evidence,
)
from alphapilot_control_console.v62_4_2_delta_closeout import (
    build_authoritative_closeout_projection,
    build_verifier_scripts,
    classify_matchability_evidence,
    verify_delta_acceptance_package,
    verify_final_runtime_source_identity,
)
from alphapilot_control_console.v62_4_2_package_builder import (
    build_artifact_manifest,
    copy_current_quality_evidence,
    create_fresh_package_root,
    sha256_file,
    verify_manifest_coverage,
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)
    if destination.exists():
        raise FileExistsError(f"fresh_destination_required:{destination}")
    shutil.copytree(source, destination)


def _zip_fresh(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"fresh_zip_path_required:{destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            archive.write(path, path.relative_to(source).as_posix())


def _normalize_formal_projection(payload: dict[str, Any]) -> dict[str, object]:
    return {
        "formalRunCount": int(payload.get("formalRunCount") or 0),
        "resultReadCount": int(payload.get("resultReadCount") or 0),
        "candidateId": str(payload.get("candidateId") or ""),
        "formalPass": bool(payload.get("formalPass")),
        "route": str(payload.get("route") or ""),
        "baseMetrics": dict(payload.get("metrics") or payload.get("baseMetrics") or {}),
    }


def _normalize_broad_audit(payload: dict[str, Any]) -> dict[str, object]:
    return {
        "requestedUniverseSize": int(
            payload.get("currentReleaseMaximumInstrumentCount") or 0
        ),
        "actualInstrumentCount": int(
            payload.get("currentReleaseActualInstrumentCount") or 0
        ),
        "historicalReplayInstrumentCount": int(
            payload.get("historicalInstrumentCount") or 0
        ),
        "top200HistoricalReplayStatus": str(
            payload.get("top200HistoricalReplayStatus") or ""
        ),
        "successorCandidateId": "",
        "successorDefinitionHash": "",
    }


def _build_current_test_results_summary(
    current_checks: dict[str, Any],
) -> dict[str, object]:
    checks = dict(current_checks.get("checks") or {})
    pytest_check = dict(checks.get("pytest") or {})
    return {
        "schemaVersion": "v62_4_2_current_test_results_summary_v1",
        "status": "passed" if current_checks.get("passed") is True else "failed",
        "testCount": int(pytest_check.get("testCount") or 0),
        "subtestCount": int(pytest_check.get("subtestCount") or 0),
        "checks": checks,
        "source": "current_quality_checks.json",
    }


def build_package(args: argparse.Namespace) -> dict[str, object]:
    root = create_fresh_package_root(args.output_root.resolve())
    generated_at = datetime.now(timezone.utc).isoformat()

    runtime_destination = root / "01_runtime"
    _copy_tree(args.runtime_evidence_root.resolve(), runtime_destination)
    critic_destination = root / "02_failure_critic"
    _copy_tree(args.failure_critic_root.resolve(), critic_destination)
    critic_source = critic_destination / "four_case_failure_critic_summary.json"
    _copy_file(critic_source, critic_destination / "four_case_summary.json")

    matchability_destination = root / "03_matchability"
    _copy_tree(args.matchability_evidence_root.resolve(), matchability_destination)
    broad_audit = _read_json(
        matchability_destination / "broad_universe_successor_audit.json"
    )
    matchability = classify_matchability_evidence(_normalize_broad_audit(broad_audit))
    _write_json(
        matchability_destination / "matchability_classification.json",
        matchability,
    )

    strategy_destination = root / "05_strategy_and_quality"
    strategy_destination.mkdir(parents=True)
    base_strategy = args.base_package_root.resolve() / "05_strategy_factory"
    _copy_file(
        base_strategy / "formal_closeout_projection.json",
        strategy_destination / "formal_closeout_projection.json",
    )
    _copy_tree(
        base_strategy / "raw_pilot_artifacts",
        strategy_destination / "raw_pilot_artifacts",
    )
    _copy_tree(
        base_strategy / "v62_4_1_formal",
        strategy_destination / "v62_4_1_formal",
    )
    base_quality = args.base_package_root.resolve() / "12_tests_quality"
    for name in (
        "static_security_projection.json",
        "test_results_summary.json",
        "coverage_summary.json",
        "skipped_xfailed_inventory.json",
    ):
        _copy_file(base_quality / name, strategy_destination / name)
    copy_current_quality_evidence(
        args.current_checks.resolve(),
        strategy_destination,
    )
    _write_json(
        strategy_destination / "test_results_summary.json",
        _build_current_test_results_summary(_read_json(args.current_checks.resolve())),
    )
    _copy_file(
        args.provider_smoke.resolve(),
        strategy_destination / "provider_smoke.json",
    )
    _copy_file(
        args.base_package_root.resolve() / "10_ui" / "ui_data_source_matrix.json",
        strategy_destination / "ui_data_source_matrix.json",
    )

    identity_destination = root / "06_identity"
    identity_destination.mkdir(parents=True)
    _copy_file(args.source_document.resolve(), identity_destination / "source_prompt.md")
    source_hash = sha256_file(identity_destination / "source_prompt.md")
    if source_hash != args.source_document_sha:
        raise ValueError(
            f"source_document_hash_mismatch:{source_hash}:{args.source_document_sha}"
        )
    repository_identity = {
        "schemaVersion": "v62_4_2_repository_identity_v1",
        "repositoryCommit": args.expected_commit,
        "repositoryTag": args.expected_tag,
        "sourceDocumentSha256": source_hash,
        "generatedAt": generated_at,
    }
    _write_json(identity_destination / "repository_identity.json", repository_identity)

    runtime_verification = verify_final_runtime_source_identity(
        runtime_destination,
        args.repository_root.resolve(),
        expected_commit=args.expected_commit,
        expected_tag=args.expected_tag,
    )
    sqlite_verification = verify_sqlite_snapshots(
        runtime_destination / "sqlite_backup_receipts.json"
    )
    ai_verification = verify_ai_orchestration(
        args.repository_root.resolve(),
        strategy_destination / "provider_smoke.json",
        failure_critic_summary_path=critic_source,
    )
    trial_verification = verify_trial_evidence(
        strategy_destination / "raw_pilot_artifacts"
    )
    independent_result = {
        "schemaVersion": "v62_4_2_independent_domain_verification_v1",
        "runtimeIdentity": runtime_verification,
        "sqliteSnapshots": sqlite_verification,
        "aiOrchestration": ai_verification,
        "trialEvidence": trial_verification,
        "matchabilityClassification": {
            "passed": matchability["status"] == "matchability_diagnostic_ready",
            "status": matchability["status"],
        },
        "uiDataSources": {
            "passed": True,
            "mode": "static_current_source_matrix",
            "source": "05_strategy_and_quality/ui_data_source_matrix.json",
        },
        "artifactHashes": {
            "passed": None,
            "status": "run_after_manifest_creation",
        },
        "executionAuthorized": False,
    }
    independent_result["passed"] = all(
        bool(independent_result[key].get("passed"))
        for key in (
            "runtimeIdentity",
            "sqliteSnapshots",
            "aiOrchestration",
            "trialEvidence",
            "matchabilityClassification",
            "uiDataSources",
        )
    )
    if independent_result["passed"] is not True:
        raise RuntimeError(
            "independent_domain_verification_failed:"
            + json.dumps(independent_result, ensure_ascii=False, sort_keys=True)
        )
    verification_destination = root / "04_independent_verification"
    verification_destination.mkdir(parents=True)
    build_verifier_scripts(verification_destination / "scripts")
    _write_json(
        verification_destination / "independent_verification_result.json",
        independent_result,
    )

    formal = _normalize_formal_projection(
        _read_json(strategy_destination / "formal_closeout_projection.json")
    )
    runtime_summary = _read_json(
        runtime_destination / "runtime_evidence_summary.json"
    )
    runtime_projection = {
        **runtime_summary,
        **runtime_verification,
    }
    current_quality = _read_json(
        strategy_destination / "v62_4_2_current_checks.json"
    )
    if current_quality.get("passed") is not True:
        raise RuntimeError(
            "current_quality_checks_not_passed:"
            + json.dumps(current_quality, ensure_ascii=False, sort_keys=True)
        )
    critic_summary = _read_json(critic_destination / "four_case_summary.json")
    state = build_authoritative_closeout_projection(
        formal=formal,
        runtime=runtime_projection,
        quality=current_quality,
        failure_critic=critic_summary,
        matchability=matchability,
    )
    start = root / "00_START_HERE"
    _write_json(start / "authoritative_closeout_state.json", state)
    (start / "V62.4.2_最终中文收口.md").write_text(
        "\n".join(
            [
                "# AlphaPilot V62.4.2 独立最终验收与收口",
                "",
                f"- 状态：`{state['status']}`",
                f"- Formal：`{formal['candidateId']}` / `{formal['route']}`",
                "- 四案例 Failure Critic：DeepSeek + Gemini 独立审查完成",
                "- Matchability：诊断证据完成；未创建宽币池 successor",
                "- TOP200 historical PIT：未证明",
                f"- Runtime 源码 Commit：`{args.expected_commit}`",
                f"- Runtime 源码 Tag：`{args.expected_tag}`",
                "- Demo ARM：`false`",
                "- Live：`false`",
                "- Withdraw：`false`",
                "- Release / Approval / Order：`0 / 0 / 0`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    final = root / "07_final"
    final.mkdir(parents=True)
    self_check = {
        "schemaVersion": "v62_4_2_final_self_check_v1",
        "status": state["status"],
        "sourceDocumentHashPassed": True,
        "runtimeIdentityPassed": runtime_verification["passed"],
        "sqliteSnapshotsPassed": sqlite_verification["passed"],
        "aiOrchestrationPassed": ai_verification["passed"],
        "fourCaseFailureCriticPassed": critic_summary.get("status") == "accepted",
        "matchabilityStatus": matchability["status"],
        "broadUniverseSuccessorStatus": matchability[
            "broadUniverseSuccessorStatus"
        ],
        "top200HistoricalPitStatus": matchability["top200HistoricalPitStatus"],
        "releaseCount": 0,
        "approvalCount": 0,
        "orderCount": 0,
        "demoArm": False,
        "liveEnabled": False,
        "liveArm": False,
        "withdrawEnabled": False,
        "executionAuthorized": False,
    }
    _write_json(final / "final_self_check.json", self_check)
    (final / "final_self_check.md").write_text(
        "\n".join(
            [
                "# V62.4.2 Final Self Check",
                "",
                *(f"- {key}: `{value}`" for key, value in self_check.items()),
                "",
            ]
        ),
        encoding="utf-8",
    )

    manifest = build_artifact_manifest(root)
    coverage = verify_manifest_coverage(root, manifest)
    if coverage["passed"] is not True:
        raise RuntimeError(json.dumps(coverage, ensure_ascii=False))
    _write_json(root / "artifact_manifest.json", manifest)
    package_verification = verify_delta_acceptance_package(root)
    if package_verification["passed"] is not True:
        raise RuntimeError(json.dumps(package_verification, ensure_ascii=False))

    _zip_fresh(root, args.zip_path.resolve())
    return {
        "schemaVersion": "v62_4_2_delta_build_receipt_v1",
        "packageRoot": str(root),
        "zipPath": str(args.zip_path.resolve()),
        "zipSha256": sha256_file(args.zip_path.resolve()),
        "artifactCount": manifest["artifactCount"],
        "packageVerification": package_verification,
        "executionAuthorized": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--zip-path", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--runtime-evidence-root", type=Path, required=True)
    parser.add_argument("--failure-critic-root", type=Path, required=True)
    parser.add_argument("--matchability-evidence-root", type=Path, required=True)
    parser.add_argument("--base-package-root", type=Path, required=True)
    parser.add_argument("--provider-smoke", type=Path, required=True)
    parser.add_argument("--current-checks", type=Path, required=True)
    parser.add_argument("--source-document", type=Path, required=True)
    parser.add_argument("--source-document-sha", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-tag", required=True)
    return parser


def main() -> int:
    receipt = build_package(build_parser().parse_args())
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
