from __future__ import annotations

import json
from pathlib import Path

from alphapilot_control_console.v62_4_1_delta_acceptance import (
    CONSOLE_CLOSEOUT_TAG,
    build_formal_closeout_projection,
    build_security_quality_projection,
    copy_evidence_tree,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_console_closeout_tag_does_not_reuse_the_frozen_acceptance_tag() -> None:
    assert CONSOLE_CLOSEOUT_TAG == "v13.27.1.62.4.1-closeout-console"
    assert CONSOLE_CLOSEOUT_TAG != "v13.27.1.62.4.1-acceptance-console"


def test_formal_closeout_projection_preserves_single_run_failure_truth(
    tmp_path: Path,
) -> None:
    result_root = tmp_path / "formal"
    _write_json(
        result_root / "campaign_summary.json",
        {
            "campaignId": "campaign-1",
            "candidateId": "candidate-1",
            "formalPass": False,
            "profitFactor": 0.48925,
            "averageNetR": -0.3602,
            "maximumDrawdownR": 19.29,
            "tradeCount": 36,
        },
    )
    _write_json(
        result_root / "route_decision.json",
        {"route": "archive_s01_current_version"},
    )
    _write_json(
        result_root / "gate_matrix.json",
        {
            "gates": [
                {"gateId": "minimum_profit_factor", "passed": False},
                {"gateId": "positive_average_net_r", "passed": False},
            ]
        },
    )

    projection = build_formal_closeout_projection(
        result_root=result_root,
        formal_run_count=1,
        result_read_count=1,
    )

    assert projection["formalRunCount"] == 1
    assert projection["resultReadCount"] == 1
    assert projection["formalPass"] is False
    assert projection["route"] == "archive_s01_current_version"
    assert projection["failedGateCount"] == 2
    assert projection["releaseCount"] == 0
    assert projection["orderCount"] == 0
    assert projection["demoArm"] is False
    assert projection["live"] is False
    assert projection["withdraw"] is False


def test_security_projection_is_truthful_about_nonblocking_review_findings(
    tmp_path: Path,
) -> None:
    bandit = tmp_path / "bandit.json"
    semgrep = tmp_path / "semgrep.json"
    pip_audit = tmp_path / "pip-audit.json"
    _write_json(
        bandit,
        {
            "errors": [],
            "metrics": {
                "_totals": {
                    "SEVERITY.HIGH": 0,
                    "SEVERITY.MEDIUM": 28,
                    "SEVERITY.LOW": 24,
                }
            },
        },
    )
    _write_json(
        semgrep,
        {
            "results": [{"check_id": f"rule-{index}"} for index in range(51)],
            "errors": [],
        },
    )
    _write_json(
        pip_audit,
        {
            "dependencies": [
                {"name": "example", "version": "1.0", "vulns": []}
            ]
        },
    )

    projection = build_security_quality_projection(
        bandit_path=bandit,
        semgrep_path=semgrep,
        pip_audit_path=pip_audit,
    )

    assert projection["status"] == "passed_with_review_findings"
    assert projection["bandit"] == {
        "high": 0,
        "medium": 28,
        "low": 24,
        "errors": 0,
    }
    assert projection["semgrep"]["findingCount"] == 51
    assert projection["semgrep"]["errorCount"] == 0
    assert projection["pipAudit"]["vulnerabilityCount"] == 0
    assert projection["blockingFindingCount"] == 0
    assert projection["reviewFindingCount"] == 103


def test_copy_evidence_tree_replaces_destination_instead_of_incremental_append(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    (source / "current.json").write_text('{"status":"current"}\n', encoding="utf-8")
    (destination / "stale.json").write_text('{"status":"stale"}\n', encoding="utf-8")

    receipt = copy_evidence_tree(source, destination)

    assert not (destination / "stale.json").exists()
    assert (destination / "current.json").is_file()
    assert receipt["fileCount"] == 1
    assert receipt["source"] == str(source.resolve())
    assert receipt["destination"] == str(destination.resolve())
