from __future__ import annotations

import json
from pathlib import Path

import pytest

from alphapilot_control_console.ai_orchestration.contracts import (
    OrchestrationResult,
)
from alphapilot_control_console.v62_4_2_failure_critic import (
    EXPECTED_FAILURE_CASE_IDS,
    assert_ai_worker_environment,
    build_case_review_receipt,
    build_failure_case_inventory,
    build_v62_4_2_failure_critic_request,
    categorize_validated_review,
    find_negative_research_memory_hits,
    load_development_failure_cases,
    summarize_four_case_reviews,
)


def _review(changed_variable: str = "trendLookback") -> dict:
    return {
        "failureLayer": "Signal Edge",
        "facts": ["The frozen result failed its profit-factor gate."],
        "inferences": ["The signal edge did not survive costs."],
        "repairability": "bounded_single_variable_experiment",
        "prohibitedRepair": ["read_locked_oos", "relax_gate_after_result"],
        "nextExperiment": "Change only the preregistered trend lookback.",
        "changedVariable": changed_variable,
        "parentStrategy": "candidate",
        "familyFingerprint": "fingerprint",
        "signalCorrelation": 0.4,
        "sourceArtifactHashes": ["sha256:source"],
    }


def test_four_case_inventory_has_three_development_and_one_formal_failure() -> None:
    inventory = build_failure_case_inventory(
        development_failures=[
            {
                "candidateId": "v35_pair_rv_crypto_adaptation",
                "failureLayer": "development_selection",
                "reasonCodes": ["unstable_parameter_neighborhood"],
            },
            {
                "candidateId": "v35_pair_rv_source_replication",
                "failureLayer": "development_selection",
                "reasonCodes": ["unstable_parameter_neighborhood"],
            },
            {
                "candidateId": "v35_tsmom_source_replication",
                "failureLayer": "formal_readiness",
                "reasonCodes": ["purged_walk_forward_capacity_insufficient"],
            },
        ],
        formal_failure={
            "candidateId": "v35_tsmom_crypto_adaptation",
            "failureLayer": "formal_validation",
            "formalPass": False,
            "route": "archive_s01_current_version",
        },
    )

    assert [item["candidateId"] for item in inventory] == list(
        EXPECTED_FAILURE_CASE_IDS
    )
    assert [item["caseClass"] for item in inventory].count(
        "development_failure"
    ) == 3
    assert [item["caseClass"] for item in inventory].count("formal_failure") == 1
    assert all(item["executionAuthorized"] is False for item in inventory)


def test_review_categories_separate_fact_inference_recommendation_and_unknown() -> None:
    categorized = categorize_validated_review(
        _review(),
        required_questions=[
            "Was market regime causally established?",
            "Was execution slippage independently measured?",
        ],
    )

    assert categorized["Fact"] == [
        "The frozen result failed its profit-factor gate."
    ]
    assert categorized["Inference"] == [
        "The signal edge did not survive costs."
    ]
    assert categorized["Recommendation"] == [
        "Change only the preregistered trend lookback."
    ]
    assert categorized["Unverified"] == [
        "Was market regime causally established?",
        "Was execution slippage independently measured?",
    ]
    assert categorized["changedVariableCount"] == 1


def test_four_case_summary_preserves_disagreement_and_memory_hits() -> None:
    cases = []
    for candidate_id in EXPECTED_FAILURE_CASE_IDS:
        cases.append(
            {
                "candidateId": candidate_id,
                "status": "accepted",
                "deepseek": categorize_validated_review(
                    _review(),
                    required_questions=[],
                ),
                "gemini": categorize_validated_review(
                    _review(),
                    required_questions=[],
                ),
                "criticalDisagreements": [],
                "negativeResearchMemoryHits": [
                    {
                        "candidateId": "archived_001",
                        "reason": "negative_average_net_r",
                    }
                ],
                "singleVariableNextExperiment": {
                    "changedVariable": "trendLookback",
                    "changedVariableCount": 1,
                    "requiresNewPreregistration": True,
                },
                "executionAuthorized": False,
            }
        )

    result = summarize_four_case_reviews(cases)

    assert result["status"] == "accepted"
    assert result["caseCount"] == 4
    assert result["acceptedCaseCount"] == 4
    assert result["criticalDisagreementCaseCount"] == 0
    assert result["memoryHitCaseCount"] == 4
    assert result["releaseCount"] == 0
    assert result["orderCount"] == 0
    assert result["demoArm"] is False
    assert result["liveArm"] is False
    assert result["withdrawEnabled"] is False


def test_load_development_failure_cases_binds_source_artifact_hash(
    tmp_path: Path,
) -> None:
    failure_path = tmp_path / "pilot_failure_attribution.json"
    failure_path.write_text(
        json.dumps(
            {
                "failureCount": 3,
                "failures": [
                    {
                        "candidateId": candidate_id,
                        "failureLayer": "development_selection",
                        "reasonCodes": ["unstable_parameter_neighborhood"],
                        "evidence": {"trialCount": 3},
                        "repairability": "new_bounded_hypothesis_required",
                        "prohibitedRepair": "do_not_force_pass",
                    }
                    for candidate_id in EXPECTED_FAILURE_CASE_IDS[:3]
                ],
            }
        ),
        encoding="utf-8",
    )

    cases = load_development_failure_cases(failure_path)

    assert [item["candidateId"] for item in cases] == list(
        EXPECTED_FAILURE_CASE_IDS[:3]
    )
    assert all(item["artifactHashes"][0].startswith("sha256:") for item in cases)
    assert all(item["trialResult"]["formalPass"] is False for item in cases)


def test_negative_memory_hits_are_bounded_and_reason_aware() -> None:
    hits = find_negative_research_memory_hits(
        case={
            "candidateId": "v35_pair_rv_crypto_adaptation",
            "trialResult": {
                "blockers": ["unstable_parameter_neighborhood"],
                "primaryBlocker": "development_selection",
            },
        },
        negative_memory={
            "records": [
                {
                    "candidateId": "v35_pair_rv_crypto_adaptation",
                    "reason": "negative_average_net_r",
                },
                {
                    "candidateId": "other",
                    "reason": "unstable_parameter_neighborhood",
                },
                {
                    "candidateId": "irrelevant",
                    "reason": "other",
                },
            ]
        },
        limit=2,
    )

    assert len(hits) == 2
    assert hits[0]["matchType"] == "candidate_id"
    assert hits[1]["matchType"] == "reason_code"


def test_v62_4_2_failure_critic_request_has_bounded_structured_output_headroom() -> None:
    request = build_v62_4_2_failure_critic_request(
        formal_case={
            "candidateId": "v35_tsmom_crypto_adaptation",
            "campaignId": "formal-campaign",
            "artifactHashes": ["sha256:case"],
            "trialResult": {"formalPass": False},
        },
        negative_memory={
            "records": [],
            "sourceArtifactHashes": ["sha256:memory"],
        },
    )

    assert request.request_id.startswith("v62-4-2-failure-attribution-")
    assert request.token_ceiling == 8_192
    assert request.cost_ceiling_usd == 0.5
    assert request.dual_review is True
    assert request.tool_names == ()
    assert request.metadata["acceptanceScope"] == (
        "v62_4_2_four_case_failure_critic"
    )


def test_case_review_receipt_preserves_dual_outputs_and_no_execution() -> None:
    result = OrchestrationResult(
        request_id="request-1",
        status="accepted",
        output={},
        response_hashes=("sha256:deepseek", "sha256:gemini"),
        route_mode="dual_independent",
        validated_outputs=(_review(), _review()),
    )

    receipt = build_case_review_receipt(
        case={
            "candidateId": "v35_pair_rv_crypto_adaptation",
            "caseClass": "development_failure",
            "artifactHashes": ["sha256:case"],
            "trialResult": {"blockers": ["unstable_parameter_neighborhood"]},
        },
        result=result,
        negative_memory_hits=[],
        audit_projection={"eventCount": 2, "events": [{"eventId": 2}]},
    )

    assert receipt["status"] == "accepted"
    assert receipt["deepseek"]["changedVariableCount"] == 1
    assert receipt["gemini"]["changedVariableCount"] == 1
    assert receipt["singleVariableNextExperiment"]["changedVariableCount"] == 1
    assert receipt["executionAuthorized"] is False
    assert receipt["automaticPromotionAllowed"] is False
    assert receipt["orderCount"] == 0


def test_ai_worker_rejects_exchange_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("OKX_API_KEY", "forbidden")

    with pytest.raises(
        RuntimeError,
        match="exchange_credentials_forbidden_in_ai_worker",
    ):
        assert_ai_worker_environment()


def test_secure_four_case_launcher_is_process_only_and_strips_exchange_keys() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    script = (
        repository_root
        / "scripts"
        / "start_v62_4_2_four_case_failure_critic.ps1"
    ).read_text(encoding="utf-8")

    assert "Read-Host -Prompt $Prompt -AsSecureString" in script
    assert 'EnvironmentVariables["DEEPSEEK_API_KEY"]' in script
    assert 'EnvironmentVariables["GEMINI_API_KEY"]' in script
    assert '"OKX_API_KEY"' in script
    assert '"OKX_DEMO_API_KEY"' in script
    assert '"OKX_LIVE_API_KEY"' in script
    assert "alphapilot_control_console.v62_4_2_failure_critic" in script
    assert "RUN_V62_4_2_FAILURE_CRITIC" in script


def test_secure_four_case_launcher_is_ascii_for_windows_powershell_5() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    script = (
        repository_root
        / "scripts"
        / "start_v62_4_2_four_case_failure_critic.ps1"
    ).read_text(encoding="utf-8")

    assert script.isascii()
