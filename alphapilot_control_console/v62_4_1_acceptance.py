from __future__ import annotations

from typing import Any


_CLOSED_ISSUE_STATUSES = {
    "already_fixed",
    "closed",
    "obsolete",
    "superseded",
}


def derive_acceptance_status(
    *,
    credential_scan_passed: bool,
    data_omission_passed: bool,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    blocking_issue_ids = sorted(
        str(issue["issueId"])
        for issue in issues
        if str(issue.get("severity", "")).upper() in {"P0", "P1"}
        and str(issue.get("status", "")).lower() not in _CLOSED_ISSUE_STATUSES
    )
    non_blocking_issue_ids = sorted(
        str(issue["issueId"])
        for issue in issues
        if str(issue.get("severity", "")).upper() not in {"P0", "P1"}
        and str(issue.get("status", "")).lower() not in _CLOSED_ISSUE_STATUSES
    )

    if not credential_scan_passed or not data_omission_passed:
        status = "failed"
    elif blocking_issue_ids:
        status = "blocked_remediation_required"
    else:
        status = "accepted_with_nonblocking_p2"

    return {
        "status": status,
        "blockingIssueIds": blocking_issue_ids,
        "nonBlockingIssueIds": non_blocking_issue_ids,
    }


def _candidate_projection_evidence(
    candidate_id: str,
    projections: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = [
        projection
        for projection in projections
        if projection.get("candidateId") == candidate_id
    ]
    selection_net_r = [
        float(row["selectionNetR"])
        for row in rows
        if isinstance(row.get("selectionNetR"), (int, float))
    ]
    profit_factors = [
        float(row["profitFactor"])
        for row in rows
        if isinstance(row.get("profitFactor"), (int, float))
    ]
    drawdowns = [
        float(row["maxDrawdownR"])
        for row in rows
        if isinstance(row.get("maxDrawdownR"), (int, float))
    ]
    return {
        "trialCount": len(rows),
        "positiveSelectionNetRCount": sum(value > 0 for value in selection_net_r),
        "bestSelectionNetR": max(selection_net_r) if selection_net_r else None,
        "worstSelectionNetR": min(selection_net_r) if selection_net_r else None,
        "bestProfitFactor": max(profit_factors) if profit_factors else None,
        "worstProfitFactor": min(profit_factors) if profit_factors else None,
        "maximumDrawdownR": max(drawdowns) if drawdowns else None,
        "prefilterPassedCount": sum(
            row.get("prefilterPassed") is True for row in rows
        ),
        "trialIds": [
            str(row["trialId"]) for row in rows if row.get("trialId") is not None
        ],
    }


def build_candidate_failure_attribution(
    *,
    candidate_ids: list[str],
    projections: list[dict[str, Any]],
    selections: list[dict[str, Any]],
    formal_handoff: dict[str, Any],
) -> dict[str, Any]:
    selection_by_candidate = {
        str(selection["candidateId"]): selection
        for selection in selections
        if selection.get("candidateId") is not None
    }
    ready_candidate_ids = {
        str(candidate["candidateId"])
        for candidate in formal_handoff.get("readyCandidates", [])
        if candidate.get("candidateId") is not None
    }
    blocked_by_candidate = {
        str(candidate["candidateId"]): candidate
        for candidate in formal_handoff.get("blockedCandidates", [])
        if candidate.get("candidateId") is not None
    }

    failures: list[dict[str, Any]] = []
    unattributed: list[str] = []
    for candidate_id in candidate_ids:
        if candidate_id in ready_candidate_ids:
            continue

        selection = selection_by_candidate.get(candidate_id, {})
        projection_evidence = _candidate_projection_evidence(
            candidate_id,
            projections,
        )
        formal_blocker = blocked_by_candidate.get(candidate_id)
        if formal_blocker is not None:
            reason_codes = [
                str(reason) for reason in formal_blocker.get("blockers", [])
            ]
            failures.append(
                {
                    "candidateId": candidate_id,
                    "selectedTrialId": formal_blocker.get("selectedTrialId"),
                    "failureLayer": "formal_readiness",
                    "reasonCodes": reason_codes
                    or ["formal_readiness_blocked_without_reason"],
                    "evidence": {
                        **projection_evidence,
                        "selectionGate": selection.get("gate"),
                        "selectionReason": selection.get("reason"),
                    },
                    "repairability": "new_preregistered_campaign_required",
                }
            )
            continue

        if not selection.get("eligible") or not selection.get("selectedTrialId"):
            reason = selection.get("reason")
            failures.append(
                {
                    "candidateId": candidate_id,
                    "selectedTrialId": selection.get("selectedTrialId"),
                    "failureLayer": "development_selection",
                    "reasonCodes": [
                        str(reason)
                        if reason
                        else "development_selection_not_eligible"
                    ],
                    "evidence": {
                        **projection_evidence,
                        "selectionGate": selection.get("gate"),
                    },
                    "repairability": "new_bounded_hypothesis_required",
                }
            )
            continue

        unattributed.append(candidate_id)

    return {
        "failureCount": len(failures),
        "failures": failures,
        "unattributedCandidateIds": unattributed,
    }
