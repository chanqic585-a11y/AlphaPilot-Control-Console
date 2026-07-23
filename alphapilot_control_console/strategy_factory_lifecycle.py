from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


FORMAL_EVIDENCE_FIELDS = (
    ("formalJobCount", "Formal Job"),
    ("formalClaimCount", "Formal Claim"),
    ("formalAttemptCount", "Formal Attempt"),
    ("formalResultCount", "Formal Result"),
    ("resultReadCount", "Formal Read"),
)


def _integer(value: object) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _stable_hash(prefix: str, value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()}"


def project_strategy_factory_lifecycle(
    *,
    legacy_status: str,
    config: Mapping[str, Any],
    receipt: Mapping[str, Any],
    execution_evidence: Mapping[str, Any],
    outcome: Mapping[str, Any],
) -> dict[str, Any]:
    development = execution_evidence.get("development")
    development = development if isinstance(development, Mapping) else {}
    formal = execution_evidence.get("formal")
    formal = formal if isinstance(formal, Mapping) else {}

    completed_trial_count = _integer(
        development.get("trialCount")
        or receipt.get("completedTrialCount")
        or receipt.get("trialCount")
    )
    survivor_count = _integer(
        outcome.get("formalValidationCandidateCount")
        or receipt.get("survivorCount")
    )
    formal_counts = {
        field: _integer(formal.get(field) or receipt.get(field))
        for field, _ in FORMAL_EVIDENCE_FIELDS
    }
    formal_missing = [
        label
        for field, label in FORMAL_EVIDENCE_FIELDS
        if formal_counts[field] < 1
    ]
    formal_started = any(value > 0 for value in formal_counts.values())
    formal_complete = not formal_missing
    development_complete = (
        str(development.get("status") or "") == "completed"
        and completed_trial_count > 0
    )

    normalized_status = str(legacy_status or "").strip().lower()
    receipt_status = str(receipt.get("status") or "").strip().lower()
    blockers: list[str] = []
    if normalized_status in {"failed", "error", "cancelled"}:
        blockers.append(f"legacy_status_{normalized_status}")
    if normalized_status == "paused":
        blockers.append("paused_by_operator")
    if "blocked" in receipt_status or receipt_status in {"failed", "error"}:
        blockers.append(receipt_status or "receipt_blocked")
    if normalized_status in {"completed", "awaiting_formal_validation"} and completed_trial_count == 0:
        blockers.append("completed_trial_count_zero")

    release_count = _integer(formal.get("releaseCount") or receipt.get("releaseCount"))
    review_request_count = _integer(outcome.get("candidateReviewRequestCount"))
    if release_count > 0 or review_request_count > 0:
        state = "demo_release_draft" if formal_complete else "blocked"
        if not formal_complete:
            blockers.append("formal_evidence_chain_incomplete")
    elif formal_complete:
        state = "formal_complete"
    elif formal_started:
        state = "formal_running"
    elif survivor_count > 0:
        state = "formal_queued"
    elif development_complete:
        state = "development_complete"
    elif normalized_status in {"running", "pause_requested"}:
        state = "trial_running"
    elif normalized_status == "queued":
        state = "trial_queued"
    elif blockers:
        state = "blocked"
    elif config.get("candidateIds"):
        state = "candidate_build"
    else:
        state = "hypothesis_draft"

    if blockers and state not in {"trial_running", "trial_queued"}:
        state = "blocked"

    return {
        "state": state,
        "legacyStatus": legacy_status,
        "completedTrialCount": completed_trial_count,
        "developmentComplete": development_complete,
        "survivorCount": survivor_count,
        "legalZeroSurvivor": development_complete and survivor_count == 0,
        "formalCounts": formal_counts,
        "formalMissing": formal_missing,
        "formalComplete": formal_complete,
        "blockers": sorted(set(blockers)),
    }


def _failure_layer(reason_codes: list[str], receipt_status: str) -> str:
    text = " ".join([receipt_status, *reason_codes]).lower()
    if any(term in text for term in ("data", "pit", "partition", "snapshot", "lookback")):
        return "Data / PIT"
    if any(term in text for term in ("cost", "capacity", "slippage", "liquidity")):
        return "Cost / Capacity"
    if any(term in text for term in ("stability", "regime", "walk_forward", "walk-forward")):
        return "Stability / Regime"
    if any(term in text for term in ("risk", "drawdown", "portfolio", "exposure")):
        return "Risk / Portfolio"
    if any(term in text for term in ("release", "approval", "arm", "execution", "order")):
        return "Promotion / Execution"
    if any(term in text for term in ("implementation", "system", "exception", "error", "failed")):
        return "Implementation"
    return "Signal Edge"


def build_failure_attributions(
    *,
    config: Mapping[str, Any],
    receipt: Mapping[str, Any],
    execution_evidence: Mapping[str, Any],
    outcome: Mapping[str, Any],
) -> list[dict[str, Any]]:
    receipt_status = str(receipt.get("status") or "").strip()
    reason_rows = receipt.get("reasonCodes")
    reason_codes = (
        [str(value) for value in reason_rows if str(value).strip()]
        if isinstance(reason_rows, list)
        else ([receipt_status] if receipt_status else [])
    )
    has_failure = bool(
        reason_codes
        or _integer(outcome.get("archivedFailureCount"))
        or receipt_status in {"failed", "error", "research_blocked_data"}
    )
    if not has_failure:
        return []

    candidate_ids = [str(value) for value in config.get("candidateIds") or []]
    family_ids = [str(value) for value in config.get("familyIds") or []]
    failure_layer = _failure_layer(reason_codes, receipt_status)
    changed_variable = {
        "Data / PIT": "minimum_history_window",
        "Cost / Capacity": "maximum_participation_rate",
        "Stability / Regime": "regime_filter",
        "Risk / Portfolio": "position_risk_fraction",
        "Promotion / Execution": "execution_eligibility_rule",
        "Implementation": "implementation_defect",
        "Signal Edge": "entry_threshold",
    }[failure_layer]
    rows = []
    for index, candidate_id in enumerate(candidate_ids or [None]):
        family_id = (
            family_ids[min(index, len(family_ids) - 1)] if family_ids else None
        )
        fingerprint_input = {
            "familyId": family_id,
            "timeframe": config.get("timeframe"),
            "hypothesis": config.get("hypothesis"),
        }
        rows.append({
            "candidateId": candidate_id,
            "familyId": family_id,
            "parentStrategy": receipt.get("parentStrategyId"),
            "failureLayer": failure_layer,
            "fact": {
                "receiptStatus": receipt_status or None,
                "reasonCodes": reason_codes,
            },
            "inference": None,
            "repairability": "requires_new_version",
            "prohibitedRepair": [
                "lower_gate_after_result",
                "locked_oos_tuning",
                "multi_variable_edit",
                "force_pass",
            ],
            "nextSingleVariableExperiment": {
                "changedVariable": changed_variable,
                "maximumChangedVariables": 1,
                "requiresNewCandidateVersion": True,
            },
            "changedVariable": changed_variable,
            "familyFingerprint": _stable_hash(
                "family_fingerprint", fingerprint_input
            ),
            "signalCorrelation": None,
            "reasonCodes": reason_codes,
            "requiredRows": receipt.get("requiredRows"),
            "availableRows": receipt.get("availableRows"),
            "instrument": receipt.get("instrument"),
        })
    return rows
