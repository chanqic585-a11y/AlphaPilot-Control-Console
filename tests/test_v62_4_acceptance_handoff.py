from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import alphapilot_control_console.v62_4_acceptance as acceptance_helpers

from alphapilot_control_console.v62_4_acceptance import (
    REQUIRED_TOP_LEVEL,
    REQUIRED_SECTION_FILES,
    build_artifact_manifest,
    build_formal_job_rows,
    build_runtime_projection,
    detect_credential_material,
    load_pilot_evidence,
    verify_acceptance_package,
    validate_data_omission_policy,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_acceptance_builder_cli_loads_from_repository_root() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            str(repository_root / "scripts" / "build_v62_4_acceptance_handoff.py"),
            "--help",
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--output-root" in completed.stdout


def test_acceptance_redacts_credential_assignments_before_packaging() -> None:
    assert hasattr(acceptance_helpers, "redact_credential_assignments")

    redacted = acceptance_helpers.redact_credential_assignments(
        'DEEPSEEK_API_KEY=sk-real-secret\nGEMINI_API_KEY="test-only-placeholder"'
    )

    assert "sk-real-secret" not in redacted
    assert "test-only-placeholder" not in redacted
    assert detect_credential_material(redacted) == []


def test_acceptance_uses_foundation_sample_only_root(tmp_path: Path) -> None:
    assert hasattr(acceptance_helpers, "find_foundation_sample_root")
    preferred = tmp_path / "sample_only"
    legacy = tmp_path / "data-governance" / "sample_only"
    preferred.mkdir(parents=True)
    legacy.mkdir(parents=True)

    assert acceptance_helpers.find_foundation_sample_root(tmp_path) == preferred


def test_acceptance_final_scan_excludes_transient_foundation(tmp_path: Path) -> None:
    assert hasattr(acceptance_helpers, "iter_package_text_files")
    transient = tmp_path / ".foundation" / "tool.py"
    visible = tmp_path / "00_START_HERE" / "README_CN.md"
    transient.parent.mkdir(parents=True)
    visible.parent.mkdir(parents=True)
    transient.write_text("DEEPSEEK_API_KEY=sk-real-secret", encoding="utf-8")
    visible.write_text("No credentials are present.", encoding="utf-8")

    packaged = list(acceptance_helpers.iter_package_text_files(tmp_path))

    assert visible in packaged
    assert transient not in packaged


def test_acceptance_layout_covers_all_required_handoff_sections() -> None:
    assert REQUIRED_TOP_LEVEL == tuple(f"{index:02d}_{name}" for index, name in (
        (0, "START_HERE"),
        (1, "identity"),
        (2, "source_and_diff"),
        (3, "runtime"),
        (4, "authority_and_security"),
        (5, "strategy_factory"),
        (6, "ai_orchestration"),
        (7, "matchability_forward"),
        (8, "factor_model"),
        (9, "demo_live_execution"),
        (10, "ui"),
        (11, "database"),
        (12, "tests_quality"),
        (13, "performance"),
        (14, "known_issues"),
        (15, "independent_verification"),
        (16, "final"),
    ))


def test_real_pilot_projection_preserves_trial_and_formal_truth(tmp_path: Path) -> None:
    report = tmp_path / "reports" / "pilot"
    _write_json(
        report / "campaign_summary.json",
        {
            "campaignId": "pilot-real",
            "campaignHash": "campaign_hash",
            "candidateCount": 4,
            "eligibleCandidateCount": 4,
            "trialCount": 12,
            "completedTrialCount": 12,
            "formalReadyCandidateCount": 1,
            "formalRunCount": 0,
            "resultReadCount": 0,
            "releaseCount": 0,
            "orderCount": 0,
            "demoArm": False,
            "status": "awaiting_formal_validation",
        },
    )
    _write_json(
        report / "preregistration.json",
        {
            "candidateIds": ["a", "b", "c", "d"],
            "trialsByCandidate": {
                candidate: [
                    {
                        "candidateId": candidate,
                        "familyId": "family",
                        "trialId": f"{candidate}-{index}",
                        "trialIndex": index,
                    }
                    for index in range(3)
                ]
                for candidate in ("a", "b", "c", "d")
            },
        },
    )
    _write_json(
        report / "development_projection.json",
        {
            "projections": [
                {
                    "candidateId": candidate,
                    "trialId": f"{candidate}-{index}",
                    "selectionNetR": 0.1,
                    "profitFactor": 1.1,
                    "maxDrawdownR": 1.0,
                    "prefilterPassed": True,
                }
                for candidate in ("a", "b", "c", "d")
                for index in range(3)
            ]
        },
    )
    _write_json(
        report / "formal_handoff.json",
        {
            "status": "partially_ready_to_freeze",
            "formalReadyCandidateCount": 1,
            "formalRunCount": 0,
            "resultReadCount": 0,
            "readyCandidates": [
                {"candidateId": "c", "selectedTrialId": "c-1", "readinessStatus": "ready"}
            ],
            "blockedCandidates": [],
        },
    )

    evidence = load_pilot_evidence(tmp_path)

    assert evidence["summary"]["completedTrialCount"] == 12
    assert len(evidence["candidates"]) == 4
    assert len(evidence["trials"]) == 12
    assert evidence["summary"]["formalReadyCandidateCount"] == 1
    jobs = build_formal_job_rows(evidence)
    assert jobs == [
        {
            "campaignId": "pilot-real",
            "candidateId": "c",
            "selectedTrialId": "c-1",
            "status": "not_run_awaiting_preregistration_and_frozen_input",
            "formalRunCount": 0,
            "resultReadCount": 0,
            "executionAuthorized": False,
        }
    ]


def test_offline_runtime_projection_disables_new_entries() -> None:
    projection = build_runtime_projection(
        health=None,
        runtime=None,
        network_error="connection refused",
    )

    assert projection["runtimeObserved"] is False
    assert projection["runtimeSourceParity"] == "unverified"
    assert projection["newEntriesAllowed"] is False
    assert projection["liveArmVerified"] is False
    assert projection["withdrawVerifiedDisabled"] is False


def test_acceptance_rejects_credentials_and_zero_byte_market_placeholders(tmp_path: Path) -> None:
    assert detect_credential_material("DEEPSEEK_API_KEY=sk-real-secret")
    assert not detect_credential_material("DEEPSEEK_API_KEY is process-only and absent")

    (tmp_path / "omitted_data_manifest.json").write_text("[]", encoding="utf-8")
    sample = tmp_path / "sample_only" / "sample.json"
    sample.parent.mkdir()
    sample.write_text('{"sampleOnly": true}', encoding="utf-8")
    bad = tmp_path / "BTC-USDT-SWAP-5m.csv"
    bad.write_bytes(b"")

    result = validate_data_omission_policy(tmp_path)

    assert result["passed"] is False
    assert result["zeroByteMarketPlaceholders"] == ["BTC-USDT-SWAP-5m.csv"]


def _write_minimum_acceptance_tree(root: Path) -> None:
    for directory, names in REQUIRED_SECTION_FILES.items():
        for name in names:
            path = root / directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".json":
                _write_json(path, {"status": "not_run"})
            elif path.suffix == ".jsonl":
                path.write_text('', encoding="utf-8")
            elif path.suffix == ".csv":
                path.write_text('status\nnot_run\n', encoding="utf-8")
            elif path.suffix == ".png":
                path.write_bytes(b"\x89PNG\r\n\x1a\nfixture-free-placeholder-for-test")
            else:
                path.write_text('not_run\n', encoding="utf-8")


def test_independent_verifier_accepts_a_complete_truthful_tree(tmp_path: Path) -> None:
    _write_minimum_acceptance_tree(tmp_path)
    _write_json(
        tmp_path / "05_strategy_factory" / "pilot_campaign_summary.json",
        {"candidateCount": 4, "trialCount": 12, "completedTrialCount": 12, "formalRunCount": 0},
    )
    _write_json(
        tmp_path / "05_strategy_factory" / "pilot_candidate_manifest.json",
        [{"candidateId": str(index)} for index in range(4)],
    )
    _write_json(
        tmp_path / "05_strategy_factory" / "pilot_trial_manifest.json",
        [{"trialId": str(index), "status": "completed"} for index in range(12)],
    )
    (tmp_path / "05_strategy_factory" / "formal_job_ledger.jsonl").write_text('', encoding="utf-8")
    _write_json(
        tmp_path / "10_ui" / "ui_data_source_matrix.json",
        {"productionFixtureData": False, "fields": []},
    )
    _write_json(
        tmp_path / "06_ai_orchestration" / "forbidden_tool_audit.json",
        {"forbiddenTradingToolCallCount": 0},
    )
    manifest = build_artifact_manifest(tmp_path)
    _write_json(tmp_path / "16_final" / "artifact_manifest.json", manifest)

    result = verify_acceptance_package(tmp_path)

    assert result["missing"] == []
    assert result["extra"] == []
    assert result["hashMismatch"] == []
    assert result["invalidJson"] == []
    assert result["credentialHits"] == []
    assert result["trialCountMismatch"] == []
    assert result["formalCountMismatch"] == []
    assert result["fixtureInProductionUi"] == []
    assert result["forbiddenLlmToolCalls"] == []
    assert result["passed"] is True


def test_independent_verifier_reports_tampering_credentials_and_fixture_ui(tmp_path: Path) -> None:
    _write_minimum_acceptance_tree(tmp_path)
    _write_json(
        tmp_path / "05_strategy_factory" / "pilot_campaign_summary.json",
        {"candidateCount": 1, "trialCount": 2, "completedTrialCount": 2, "formalRunCount": 1},
    )
    _write_json(tmp_path / "05_strategy_factory" / "pilot_candidate_manifest.json", [{"candidateId": "a"}])
    _write_json(tmp_path / "05_strategy_factory" / "pilot_trial_manifest.json", [{"trialId": "one"}])
    (tmp_path / "05_strategy_factory" / "formal_job_ledger.jsonl").write_text('', encoding="utf-8")
    _write_json(
        tmp_path / "10_ui" / "ui_data_source_matrix.json",
        {"productionFixtureData": True, "fields": [{"field": "balance", "source": "fixture"}]},
    )
    _write_json(tmp_path / "06_ai_orchestration" / "forbidden_tool_audit.json", {"forbiddenTradingToolCallCount": 1})
    manifest = build_artifact_manifest(tmp_path)
    _write_json(tmp_path / "16_final" / "artifact_manifest.json", manifest)
    (tmp_path / "00_START_HERE" / "README_CN.md").write_text(
        "DEEPSEEK_API_KEY=test-only-placeholder", encoding="utf-8"
    )

    result = verify_acceptance_package(tmp_path)

    assert result["hashMismatch"]
    assert result["credentialHits"]
    assert result["trialCountMismatch"]
    assert result["formalCountMismatch"]
    assert result["fixtureInProductionUi"]
    assert result["forbiddenLlmToolCalls"]
    assert result["passed"] is False


def test_independent_verifier_reports_a_manifested_file_deleted_after_packaging(tmp_path: Path) -> None:
    _write_minimum_acceptance_tree(tmp_path)
    manifest = build_artifact_manifest(tmp_path)
    _write_json(tmp_path / "16_final" / "artifact_manifest.json", manifest)
    (tmp_path / "14_known_issues" / "open_issue_ledger.json").unlink()

    result = verify_acceptance_package(tmp_path)

    assert "14_known_issues/open_issue_ledger.json" in result["missing"]
    assert "14_known_issues/open_issue_ledger.json:missing" in result["hashMismatch"]
    assert result["passed"] is False
