"""No-order comparison harness for execution-core remediation cutovers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping


_TRANSIENT_FIELDS = {
    "completedAt",
    "decisionLatencyMs",
    "generatedAt",
    "observedAt",
    "runtimePid",
    "startedAt",
}


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in _TRANSIENT_FIELDS
        }
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(
        _canonical(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ShadowDecisionEvaluator:
    """Pure decision evaluator metadata; shadows must never own order access."""

    name: str
    evaluate: Callable[[dict[str, Any]], Mapping[str, Any]]
    order_access: bool = False


def _compare_cases(
    *,
    reference: ShadowDecisionEvaluator,
    shadow: ShadowDecisionEvaluator,
    cases: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, raw_case in enumerate(cases):
        case = dict(raw_case)
        case_id = str(case.get("caseId") or f"case-{index + 1}")
        reference_decision = _canonical(dict(reference.evaluate(dict(case))))
        shadow_decision = _canonical(dict(shadow.evaluate(dict(case))))
        reference_hash = _stable_hash(reference_decision)
        shadow_hash = _stable_hash(shadow_decision)
        rows.append({
            "caseId": case_id,
            "matched": reference_hash == shadow_hash,
            "referenceDecisionHash": reference_hash,
            "shadowDecisionHash": shadow_hash,
        })

    match_count = sum(1 for row in rows if row["matched"])
    case_count = len(rows)
    parity_rate = match_count / case_count if case_count else 1.0
    return {
        "caseCount": case_count,
        "matchCount": match_count,
        "parityRate": parity_rate,
        "mismatchCaseIds": [row["caseId"] for row in rows if not row["matched"]],
        "cases": rows,
    }


def run_execution_shadow_parity(
    *,
    reference: ShadowDecisionEvaluator,
    shadow: ShadowDecisionEvaluator,
    deterministic_fixtures: Iterable[Mapping[str, Any]],
    replay_events: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare decisions only; this harness cannot acquire execution authority."""

    if shadow.order_access:
        raise PermissionError("Shadow evaluator must not have order access")

    fixture_parity = _compare_cases(
        reference=reference,
        shadow=shadow,
        cases=deterministic_fixtures,
    )
    replay_parity = _compare_cases(
        reference=reference,
        shadow=shadow,
        cases=replay_events,
    )
    complete_evidence = (
        fixture_parity["caseCount"] > 0
        and replay_parity["caseCount"] > 0
    )
    passed = (
        complete_evidence
        and fixture_parity["parityRate"] == 1.0
        and replay_parity["parityRate"] == 1.0
    )
    core = {
        "schemaVersion": "execution_shadow_parity_v1",
        "status": "passed" if passed else "blocked",
        "passed": passed,
        "referenceEvaluator": reference.name,
        "shadowEvaluator": shadow.name,
        "shadowOrderAccessDisabled": True,
        "deterministicFixtureParity": fixture_parity,
        "replayParity": replay_parity,
        "cutoverEligible": passed,
        "cutoverPerformed": False,
        "createsOrders": False,
        "accessesPrivateExchangeApis": False,
    }
    return {**core, "evidenceHash": f"shadow_parity_{_stable_hash(core)}"}
