from __future__ import annotations

from alphapilot_control_console.v62_4_1_acceptance import (
    build_candidate_failure_attribution,
    derive_acceptance_status,
)


def test_open_p1_issue_blocks_acceptance_even_when_package_checks_pass() -> None:
    result = derive_acceptance_status(
        credential_scan_passed=True,
        data_omission_passed=True,
        issues=[
            {
                "issueId": "V62.4-RUNTIME-OFFLINE",
                "severity": "P1",
                "status": "open",
            },
            {
                "issueId": "V62.4-UI-COSMETIC",
                "severity": "P2",
                "status": "open",
            },
        ],
    )

    assert result == {
        "status": "blocked_remediation_required",
        "blockingIssueIds": ["V62.4-RUNTIME-OFFLINE"],
        "nonBlockingIssueIds": ["V62.4-UI-COSMETIC"],
    }


def test_only_closed_p1_and_open_p2_can_be_accepted() -> None:
    result = derive_acceptance_status(
        credential_scan_passed=True,
        data_omission_passed=True,
        issues=[
            {
                "issueId": "V62.4-RUNTIME-OFFLINE",
                "severity": "P1",
                "status": "closed",
            },
            {
                "issueId": "V62.4-UI-COSMETIC",
                "severity": "P2",
                "status": "open",
            },
        ],
    )

    assert result["status"] == "accepted_with_nonblocking_p2"
    assert result["blockingIssueIds"] == []


def test_package_integrity_failure_is_not_reported_as_remediation_only() -> None:
    result = derive_acceptance_status(
        credential_scan_passed=False,
        data_omission_passed=True,
        issues=[],
    )

    assert result["status"] == "failed"


def test_candidate_attribution_covers_unselected_and_formal_blocked_candidates() -> None:
    result = build_candidate_failure_attribution(
        candidate_ids=[
            "pair-adaptation",
            "pair-replication",
            "tsmom-ready",
            "tsmom-capacity-blocked",
        ],
        projections=[
            {
                "candidateId": "pair-adaptation",
                "trialId": "pair-a-0",
                "selectionNetR": -0.01,
                "profitFactor": 0.99,
                "maxDrawdownR": 1.5,
                "prefilterPassed": True,
            },
            {
                "candidateId": "pair-adaptation",
                "trialId": "pair-a-1",
                "selectionNetR": -0.02,
                "profitFactor": 0.98,
                "maxDrawdownR": 1.2,
                "prefilterPassed": True,
            },
            {
                "candidateId": "pair-replication",
                "trialId": "pair-r-0",
                "selectionNetR": -0.03,
                "profitFactor": 0.97,
                "maxDrawdownR": 2.0,
                "prefilterPassed": True,
            },
            {
                "candidateId": "tsmom-ready",
                "trialId": "tsmom-ready-0",
                "selectionNetR": 0.5,
                "profitFactor": 1.8,
                "maxDrawdownR": 4.0,
                "prefilterPassed": True,
            },
            {
                "candidateId": "tsmom-capacity-blocked",
                "trialId": "tsmom-capacity-0",
                "selectionNetR": 0.8,
                "profitFactor": 2.0,
                "maxDrawdownR": 3.0,
                "prefilterPassed": True,
            },
        ],
        selections=[
            {
                "candidateId": "pair-adaptation",
                "eligible": False,
                "selectedTrialId": None,
                "reason": "unstable_parameter_neighborhood",
                "gate": {
                    "trialCount": 2,
                    "positiveTrialCount": 0,
                    "sameDirectionMajority": False,
                },
            },
            {
                "candidateId": "pair-replication",
                "eligible": False,
                "selectedTrialId": None,
                "reason": "unstable_parameter_neighborhood",
                "gate": {
                    "trialCount": 1,
                    "positiveTrialCount": 0,
                    "sameDirectionMajority": False,
                },
            },
            {
                "candidateId": "tsmom-ready",
                "eligible": True,
                "selectedTrialId": "tsmom-ready-0",
                "reason": "stable_parameter_neighborhood",
                "gate": {
                    "trialCount": 1,
                    "positiveTrialCount": 1,
                    "sameDirectionMajority": True,
                },
            },
            {
                "candidateId": "tsmom-capacity-blocked",
                "eligible": True,
                "selectedTrialId": "tsmom-capacity-0",
                "reason": "stable_parameter_neighborhood",
                "gate": {
                    "trialCount": 1,
                    "positiveTrialCount": 1,
                    "sameDirectionMajority": True,
                },
            },
        ],
        formal_handoff={
            "readyCandidates": [
                {
                    "candidateId": "tsmom-ready",
                    "selectedTrialId": "tsmom-ready-0",
                    "readinessStatus": "ready",
                }
            ],
            "blockedCandidates": [
                {
                    "candidateId": "tsmom-capacity-blocked",
                    "selectedTrialId": "tsmom-capacity-0",
                    "readinessStatus": "blocked",
                    "blockers": ["purged_walk_forward_capacity_insufficient"],
                }
            ],
        },
    )

    assert result["failureCount"] == 3
    assert result["unattributedCandidateIds"] == []
    by_candidate = {item["candidateId"]: item for item in result["failures"]}

    pair_failure = by_candidate["pair-adaptation"]
    assert pair_failure["failureLayer"] == "development_selection"
    assert pair_failure["reasonCodes"] == ["unstable_parameter_neighborhood"]
    assert pair_failure["evidence"]["trialCount"] == 2
    assert pair_failure["evidence"]["positiveSelectionNetRCount"] == 0
    assert pair_failure["evidence"]["bestSelectionNetR"] == -0.01

    formal_failure = by_candidate["tsmom-capacity-blocked"]
    assert formal_failure["failureLayer"] == "formal_readiness"
    assert formal_failure["reasonCodes"] == [
        "purged_walk_forward_capacity_insufficient"
    ]
    assert formal_failure["selectedTrialId"] == "tsmom-capacity-0"

    assert "tsmom-ready" not in by_candidate
