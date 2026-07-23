from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from alphapilot_control_console.ai_orchestration.contracts import OrchestrationResult
from alphapilot_control_console.v62_4_1_failure_critic_acceptance import (
    _write_acceptance_report,
    build_failure_critic_request,
    build_failure_critic_acceptance_report,
    deterministic_merge_failure_reviews,
    load_formal_failure_case,
    load_negative_research_memory,
)


def _review(
    *,
    failure_layer: str = "Signal Edge",
    repairability: str = "bounded_single_variable_experiment",
    changed_variable: str = "trendLookback",
) -> dict:
    return {
        "failureLayer": failure_layer,
        "facts": ["Formal PF and average net R are below their frozen gates."],
        "inferences": ["The signal definition lacks robust edge after costs."],
        "repairability": repairability,
        "prohibitedRepair": ["read_locked_oos", "relax_gate_after_result"],
        "nextExperiment": "Change only the preregistered trend lookback.",
        "changedVariable": changed_variable,
        "parentStrategy": "v35_tsmom_crypto_adaptation",
        "familyFingerprint": "tsmom_crypto_v35",
        "signalCorrelation": 0.6,
        "sourceArtifactHashes": ["sha256:formal"],
    }


def test_deterministic_merger_accepts_only_one_shared_changed_variable() -> None:
    merged = deterministic_merge_failure_reviews([_review(), _review()])

    assert merged["status"] == "accepted"
    assert merged["criticalDisagreements"] == []
    assert merged["singleVariableNextExperiment"]["changedVariable"] == "trendLookback"
    assert merged["singleVariableNextExperiment"]["changedVariableCount"] == 1
    assert merged["executionAuthorized"] is False
    assert merged["mergeHash"].startswith("sha256:")


def test_deterministic_merger_routes_critical_disagreement_without_auto_selection() -> None:
    merged = deterministic_merge_failure_reviews(
        [_review(), _review(changed_variable="volatilityFilter")]
    )

    assert merged["status"] == "critical_disagreement_requires_human_review"
    assert merged["criticalDisagreements"] == ["changedVariable"]
    assert merged["singleVariableNextExperiment"] is None
    assert all(
        proposal["changedVariableCount"] == 1
        for proposal in merged["reviewerExperimentProposals"]
    )
    assert merged["executionAuthorized"] is False


def test_negative_memory_retrieval_is_read_only_and_hash_bound(tmp_path: Path) -> None:
    archive = tmp_path / "failure_archive.json"
    archive.write_text(
        json.dumps(
            {
                "schemaVersion": "strategy_factory_failure_archive_v1",
                "runId": "run_001",
                "campaignId": "campaign_001",
                "archivedFailureCount": 1,
                "archivedCandidates": [
                    {
                        "candidateId": "candidate_failed_001",
                        "reason": "negative_average_net_r",
                        "status": "archived",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    database = tmp_path / "factory.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE StrategyFactoryEvents (
            eventId INTEGER PRIMARY KEY,
            runId TEXT NOT NULL,
            eventType TEXT NOT NULL,
            payloadJson TEXT NOT NULL,
            createdAt TEXT NOT NULL
        );
        """
    )
    connection.execute(
        """
        INSERT INTO StrategyFactoryEvents(runId, eventType, payloadJson, createdAt)
        VALUES (?, ?, ?, ?)
        """,
        (
            "run_001",
            "candidate_failures_archived",
            json.dumps(
                {
                    "archivePath": str(archive),
                    "archivedFailureCount": 1,
                }
            ),
            "2026-07-23T00:00:00Z",
        ),
    )
    connection.commit()
    before = database.read_bytes()
    connection.close()

    memory = load_negative_research_memory(database, limit=10)

    assert memory["recordCount"] == 1
    assert memory["records"][0]["candidateId"] == "candidate_failed_001"
    assert memory["records"][0]["reason"] == "negative_average_net_r"
    assert memory["records"][0]["sourceArtifactHash"].startswith("sha256:")
    assert "archivePath" not in repr(memory)
    assert database.read_bytes() == before


def test_acceptance_report_contains_real_dual_review_and_negative_route() -> None:
    formal_case = {
        "campaignId": "campaign_001",
        "candidateId": "v35_tsmom_crypto_adaptation",
        "formalPass": False,
        "route": "archive_s01_current_version",
        "artifactHashes": ["sha256:formal"],
        "trialResult": {"profitFactor": 0.49, "averageNetR": -0.36},
    }
    memory = {
        "recordCount": 1,
        "records": [
            {
                "candidateId": "failed_001",
                "reason": "negative_average_net_r",
                "sourceArtifactHash": "sha256:memory",
            }
        ],
        "sourceArtifactHashes": ["sha256:memory"],
        "retrievalMode": "sqlite_read_only_plus_hash_bound_archives",
    }
    result = OrchestrationResult(
        request_id="failure-attribution-001",
        status="accepted",
        output=_review(),
        response_hashes=("sha256:deepseek", "sha256:gemini"),
        route_mode="dual",
        validated_outputs=(_review(), _review()),
    )
    report = build_failure_critic_acceptance_report(
        formal_case=formal_case,
        negative_memory=memory,
        result=result,
        audit_projection={
            "eventCount": 1,
            "events": [
                {
                    "taskType": "failure_attribution",
                    "providers": ["deepseek", "gemini"],
                    "status": "accepted",
                }
            ],
        },
    )

    assert report["status"] == "accepted"
    assert report["dualModelReview"]["reviewCount"] == 2
    assert report["negativeResearchMemory"]["recordCount"] == 1
    assert report["deterministicMerger"]["singleVariableNextExperiment"][
        "changedVariableCount"
    ] == 1
    assert report["criticalDisagreementRouteTest"]["status"] == (
        "critical_disagreement_requires_human_review"
    )
    assert report["safety"]["executionAuthorized"] is False


def test_failure_critic_request_is_dual_read_only_and_hash_bound() -> None:
    request = build_failure_critic_request(
        formal_case={
            "campaignId": "campaign_001",
            "candidateId": "candidate_001",
            "trialResult": {"profitFactor": 0.49},
            "artifactHashes": ["sha256:formal"],
        },
        negative_memory={
            "records": [{"candidateId": "old_failed"}],
            "sourceArtifactHashes": ["sha256:memory"],
        },
    )

    assert request.task_type == "failure_attribution"
    assert request.dual_review is True
    assert request.human_review_required is True
    assert request.tool_names == ()
    assert request.artifact_hashes == ("sha256:formal", "sha256:memory")
    assert request.payload["constraints"]["oneVariableAtATime"] is True
    assert request.payload["constraints"]["automaticPromotionAllowed"] is False


def test_formal_failure_case_is_loaded_from_hash_bound_artifacts(
    tmp_path: Path,
) -> None:
    payloads = {
        "campaign_summary.json": {
            "campaignId": "campaign_001",
            "formalPass": False,
            "route": "archive_s01_current_version",
            "baseMetrics": {"profitFactor": 0.49, "averageNetR": -0.36},
            "blockers": ["minimum_profit_factor"],
        },
        "failure_attribution.json": {
            "primaryBlocker": "minimum_profit_factor",
            "strategyPerformanceFailure": True,
        },
        "gate_matrix.json": {
            "failedAdmissionGateIds": ["minimum_profit_factor"],
            "passedCount": 7,
            "failedCount": 1,
        },
        "route_decision.json": {
            "route": "archive_s01_current_version",
            "formalRunCount": 1,
            "orderCount": 0,
        },
    }
    for name, payload in payloads.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")

    formal_case = load_formal_failure_case(
        tmp_path,
        candidate_id="candidate_001",
    )

    assert formal_case["campaignId"] == "campaign_001"
    assert formal_case["candidateId"] == "candidate_001"
    assert formal_case["formalPass"] is False
    assert formal_case["trialResult"]["baseMetrics"]["profitFactor"] == 0.49
    assert len(formal_case["artifactHashes"]) == 4
    assert all(value.startswith("sha256:") for value in formal_case["artifactHashes"])


def test_markdown_report_is_utf8_chinese_without_mojibake(tmp_path: Path) -> None:
    report = build_failure_critic_acceptance_report(
        formal_case={
            "campaignId": "campaign_001",
            "candidateId": "candidate_001",
            "formalPass": False,
            "route": "archive_s01_current_version",
            "artifactHashes": ["sha256:formal"],
        },
        negative_memory={
            "recordCount": 1,
            "records": [{"candidateId": "failed_001"}],
            "sourceArtifactHashes": ["sha256:memory"],
            "retrievalMode": "sqlite_read_only_plus_hash_bound_archives",
        },
        result=OrchestrationResult(
            request_id="failure-attribution-001",
            status="accepted",
            output=_review(),
            response_hashes=("sha256:deepseek", "sha256:gemini"),
            route_mode="dual",
            validated_outputs=(_review(), _review()),
        ),
        audit_projection={"eventCount": 0, "events": []},
    )

    _write_acceptance_report(tmp_path / "report", report)

    markdown = (tmp_path / "report" / "failure_critic_acceptance.md").read_text(
        encoding="utf-8"
    )
    assert "# V62.4.1 双模型失败归因独立验收" in markdown
    assert "单变量下一实验" in markdown
    assert "鍙" not in markdown


def test_secure_launcher_is_process_only_and_strips_exchange_credentials() -> None:
    launcher = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "start_v62_4_1_failure_critic_acceptance.ps1"
    )

    text = launcher.read_text(encoding="utf-8")

    assert "Read-Host -Prompt $Prompt -AsSecureString" in text
    assert "DEEPSEEK_API_KEY" in text
    assert "GEMINI_API_KEY" in text
    assert "OKX_DEMO_API_KEY" in text
    assert "OKX_LIVE_API_KEY" in text
    assert "v62_4_1_failure_critic_acceptance" in text
    assert "SetEnvironmentVariable" not in text
    assert "Start-Transcript" not in text
