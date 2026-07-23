"""Deterministic research governance around provider-generated strategy drafts."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping


ALLOWED_DRAFT_TYPES = frozenset({"HypothesisDraft", "CandidateDraft", "ExperimentDraft"})


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(prefix: str, value: object) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()}"


def _tokens(value: object) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", str(value or "").lower())
        if len(token) > 1
    }


def load_negative_research_memory(path: Path | str) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("recordHash"):
            records.append(payload)
    return records


def append_negative_research_records(
    path: Path | str,
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    target = Path(path)
    existing = load_negative_research_memory(target)
    by_hash = {
        str(record["recordHash"]): dict(record)
        for record in existing
        if record.get("recordHash")
    }
    before = len(by_hash)
    for record in records:
        normalized = dict(record)
        record_hash = str(normalized.get("recordHash") or "").strip()
        if record_hash:
            by_hash.setdefault(record_hash, normalized)
    ordered = [by_hash[key] for key in sorted(by_hash)]
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        "".join(_canonical(record) + "\n" for record in ordered),
        encoding="utf-8",
    )
    os.replace(temporary, target)
    return {
        "schemaVersion": "alphapilot_negative_research_memory_receipt_v1",
        "path": str(target),
        "recordCount": len(ordered),
        "appendedCount": len(ordered) - before,
        "memoryHash": _hash("negative_research_memory", ordered),
    }


def build_negative_research_record(
    *,
    strategy_id: str,
    family_id: str,
    parent_version: str,
    hypothesis: str,
    failure_layer: str,
    metrics: Mapping[str, Any],
    cost: Mapping[str, Any],
    capacity: Mapping[str, Any],
    stability: Mapping[str, Any],
    regime: Mapping[str, Any],
    signal_correlation: float | None,
    prohibited_repeats: Iterable[str],
) -> dict[str, Any]:
    core = {
        "schemaVersion": "alphapilot_negative_research_memory_v1",
        "strategyId": str(strategy_id),
        "familyId": str(family_id),
        "parentVersion": str(parent_version),
        "hypothesis": str(hypothesis),
        "failureLayer": str(failure_layer),
        "metrics": dict(metrics),
        "cost": dict(cost),
        "capacity": dict(capacity),
        "stability": dict(stability),
        "regime": dict(regime),
        "signalCorrelation": signal_correlation,
        "prohibitedRepeats": sorted({str(value) for value in prohibited_repeats}),
    }
    core["familyFingerprint"] = _hash(
        "strategy_family",
        {
            "familyId": core["familyId"],
            "hypothesisTokens": sorted(_tokens(core["hypothesis"])),
        },
    )
    core["recordHash"] = _hash("negative_research_record", core)
    return core


class AIResearchGovernor:
    """Retrieve negative memory and reject unsafe or non-falsifiable drafts."""

    def __init__(self, records: Iterable[Mapping[str, Any]]) -> None:
        self._records = [dict(record) for record in records]

    def prepare_generation_context(
        self,
        *,
        family_id: str,
        hypothesis: str,
        timeframe: str,
        direction: str,
    ) -> dict[str, Any]:
        query_tokens = _tokens(hypothesis)
        scored: list[tuple[int, dict[str, Any]]] = []
        for record in self._records:
            score = 0
            if str(record.get("familyId") or "") == family_id:
                score += 10
            score += len(query_tokens.intersection(_tokens(record.get("hypothesis"))))
            if score:
                scored.append((score, record))
        hits = [record for _, record in sorted(scored, key=lambda item: (-item[0], str(item[1].get("strategyId"))))[:10]]
        prohibited = sorted(
            {
                str(value)
                for hit in hits
                for value in hit.get("prohibitedRepeats") or []
            }
        )
        return {
            "schemaVersion": "alphapilot_ai_research_context_v1",
            "familyId": family_id,
            "hypothesis": hypothesis,
            "timeframe": timeframe,
            "direction": direction,
            "memoryHitCount": len(hits),
            "memoryHits": hits,
            "prohibitedRepeats": prohibited,
            "constraints": {
                "gateLoweringAllowed": False,
                "lockedOosTuningAllowed": False,
                "multiVariableRevisionAllowed": False,
                "automaticPromotionAllowed": False,
            },
            "executionAuthorized": False,
        }

    def validate_draft(self, draft: Mapping[str, Any]) -> dict[str, Any]:
        schema_type = str(draft.get("schemaType") or "")
        blockers: list[str] = []
        if schema_type not in ALLOWED_DRAFT_TYPES:
            blockers.append("draft_schema_type_invalid")
        changed = [str(value) for value in draft.get("changedVariables") or [] if str(value)]
        if schema_type in {"CandidateDraft", "ExperimentDraft"} and len(changed) != 1:
            blockers.append("single_variable_experiment_required")
        if dict(draft.get("gateOverrides") or {}):
            blockers.append("gate_override_forbidden")
        if bool(draft.get("lockedOosUsedForTuning")):
            blockers.append("locked_oos_tuning_forbidden")
        if bool(draft.get("automaticPromotionAllowed")):
            blockers.append("automatic_promotion_forbidden")
        if bool(draft.get("executionAuthorized")):
            blockers.append("execution_authority_forbidden")

        required_identity = ("candidateId", "familyId")
        if schema_type in {"CandidateDraft", "ExperimentDraft"} and any(
            not str(draft.get(field) or "").strip() for field in required_identity
        ):
            blockers.append("draft_identity_incomplete")

        run_card = {
            "schemaVersion": "alphapilot_strategy_experiment_run_card_v1",
            "candidateId": draft.get("candidateId"),
            "familyId": draft.get("familyId"),
            "parentVersion": draft.get("parentVersion"),
            "changedVariable": changed[0] if len(changed) == 1 else None,
            "dataSnapshotId": draft.get("dataSnapshotId"),
            "costPolicyHash": draft.get("costPolicyHash"),
            "capitalPolicyHash": draft.get("capitalPolicyHash"),
            "benchmarkPolicyHash": draft.get("benchmarkPolicyHash"),
            "randomSeed": draft.get("randomSeed"),
            "automaticPromotionAllowed": False,
            "executionAuthorized": False,
        }
        run_card["runCardHash"] = _hash("strategy_experiment_run_card", run_card)
        return {
            "schemaVersion": "alphapilot_ai_research_draft_validation_v1",
            "valid": not blockers,
            "blockers": sorted(set(blockers)),
            "runCard": run_card,
            "deterministicValidationRequired": True,
            "humanApprovalCreated": False,
            "executionAuthorized": False,
        }
