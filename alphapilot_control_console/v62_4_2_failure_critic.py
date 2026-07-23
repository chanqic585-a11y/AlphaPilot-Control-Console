"""Four-case, dual-model V62.4.2 Failure Critic closeout helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .ai_orchestration.bootstrap import build_ai_runtime
from .ai_orchestration.contracts import OrchestrationResult
from .ai_orchestration.validation import canonical_json
from .strategy_factory_v2.schemas import validate_failure
from .v62_4_1_failure_critic_acceptance import (
    build_failure_critic_request,
    deterministic_merge_failure_reviews,
    load_formal_failure_case,
    load_negative_research_memory,
)


EXPECTED_FAILURE_CASE_IDS = (
    "v35_pair_rv_crypto_adaptation",
    "v35_pair_rv_source_replication",
    "v35_tsmom_source_replication",
    "v35_tsmom_crypto_adaptation",
)

_DEVELOPMENT_FAILURE_CASE_IDS = EXPECTED_FAILURE_CASE_IDS[:3]
_REQUIRED_UNVERIFIED_QUESTIONS = (
    "Was the market regime causally established outside the supplied evidence?",
    "Was exchange execution slippage independently measured for this candidate?",
)
_FORBIDDEN_EXCHANGE_ENVIRONMENT = (
    "OKX_API_KEY",
    "OKX_SECRET_KEY",
    "OKX_PASSPHRASE",
    "OKX_DEMO_API_KEY",
    "OKX_DEMO_SECRET_KEY",
    "OKX_DEMO_PASSPHRASE",
    "OKX_LIVE_API_KEY",
    "OKX_LIVE_SECRET_KEY",
    "OKX_LIVE_PASSPHRASE",
)


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(canonical_json(value).encode("utf-8"))


def assert_ai_worker_environment() -> None:
    """Require both research providers and reject all exchange credentials."""

    if not os.environ.get("DEEPSEEK_API_KEY") or not os.environ.get(
        "GEMINI_API_KEY"
    ):
        raise RuntimeError("provider_credentials_required_deepseek_gemini")
    present = [
        name for name in _FORBIDDEN_EXCHANGE_ENVIRONMENT if os.environ.get(name)
    ]
    if present:
        raise RuntimeError("exchange_credentials_forbidden_in_ai_worker")


def load_development_failure_cases(
    failure_attribution_path: Path | str,
) -> list[dict[str, Any]]:
    """Load the exact three pilot failures from one hash-bound source artifact."""

    path = Path(failure_attribution_path).resolve()
    content = path.read_bytes()
    payload = json.loads(content.decode("utf-8"))
    failures = payload.get("failures") if isinstance(payload, Mapping) else None
    if not isinstance(failures, list):
        raise ValueError("development_failure_list_required")
    source_hash = _sha256_bytes(content)
    by_id = {
        str(item.get("candidateId") or ""): dict(item)
        for item in failures
        if isinstance(item, Mapping)
    }
    missing = [
        candidate_id
        for candidate_id in _DEVELOPMENT_FAILURE_CASE_IDS
        if candidate_id not in by_id
    ]
    if missing:
        raise ValueError(
            "development_failure_case_missing:" + ",".join(missing)
        )

    cases: list[dict[str, Any]] = []
    for candidate_id in _DEVELOPMENT_FAILURE_CASE_IDS:
        failure = by_id[candidate_id]
        reason_codes = [
            str(item) for item in list(failure.get("reasonCodes") or [])
        ]
        evidence = dict(failure.get("evidence") or {})
        failure_layer = str(failure.get("failureLayer") or "unspecified")
        cases.append(
            {
                "schemaVersion": "v62_4_2_development_failure_case_v1",
                "campaignId": "v62_4_1_strategy_factory_pilot",
                "candidateId": candidate_id,
                "formalPass": False,
                "route": "development_failure",
                "artifactHashes": [source_hash],
                "artifactManifest": [
                    {
                        "name": path.name,
                        "sha256": source_hash,
                        "sizeBytes": len(content),
                    }
                ],
                "trialResult": {
                    "candidateId": candidate_id,
                    "formalPass": False,
                    "route": "development_failure",
                    "baseMetrics": evidence,
                    "baseAcceptedTradeCount": int(
                        evidence.get("trialCount") or 0
                    ),
                    "blockers": reason_codes,
                    "primaryBlocker": failure_layer,
                    "strategyPerformanceFailure": True,
                    "failedAdmissionGateIds": reason_codes,
                    "repairability": str(
                        failure.get("repairability") or ""
                    ),
                    "prohibitedRepair": str(
                        failure.get("prohibitedRepair") or ""
                    ),
                    "formalRunCount": 0,
                    "formalInputReadCount": 0,
                    "releaseCount": 0,
                    "orderCount": 0,
                    "demoArm": False,
                },
            }
        )
    return cases


def find_negative_research_memory_hits(
    *,
    case: Mapping[str, Any],
    negative_memory: Mapping[str, Any],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return bounded candidate or reason-code matches from read-only memory."""

    bounded_limit = max(0, min(int(limit), 50))
    if bounded_limit == 0:
        return []
    candidate_id = str(case.get("candidateId") or "")
    trial_result = dict(case.get("trialResult") or {})
    reason_codes = {
        str(item) for item in list(trial_result.get("blockers") or [])
    }
    primary = str(trial_result.get("primaryBlocker") or "")
    if primary:
        reason_codes.add(primary)

    candidate_hits: list[dict[str, Any]] = []
    reason_hits: list[dict[str, Any]] = []
    for raw_record in list(negative_memory.get("records") or []):
        if not isinstance(raw_record, Mapping):
            continue
        record = dict(raw_record)
        record_candidate = str(record.get("candidateId") or "")
        record_reason = str(record.get("reason") or "")
        if record_candidate == candidate_id:
            candidate_hits.append({**record, "matchType": "candidate_id"})
        elif record_reason in reason_codes:
            reason_hits.append({**record, "matchType": "reason_code"})

    deduplicated: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for record in [*candidate_hits, *reason_hits]:
        identity = (
            str(record.get("candidateId") or ""),
            str(record.get("reason") or ""),
            str(record.get("sourceArtifactHash") or ""),
        )
        if identity in seen:
            continue
        seen.add(identity)
        deduplicated.append(record)
        if len(deduplicated) >= bounded_limit:
            break
    return deduplicated


def build_failure_case_inventory(
    *,
    development_failures: Sequence[Mapping[str, Any]],
    formal_failure: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build the exact three-development plus one-formal critic inventory."""

    by_id = {
        str(item.get("candidateId") or ""): dict(item)
        for item in development_failures
    }
    formal_id = str(formal_failure.get("candidateId") or "")
    if formal_id:
        by_id[formal_id] = dict(formal_failure)
    missing = [candidate_id for candidate_id in EXPECTED_FAILURE_CASE_IDS if candidate_id not in by_id]
    extra = sorted(set(by_id) - set(EXPECTED_FAILURE_CASE_IDS))
    if missing or extra:
        raise ValueError(
            "failure_case_inventory_mismatch:"
            f"missing={','.join(missing)};extra={','.join(extra)}"
        )
    inventory: list[dict[str, Any]] = []
    for candidate_id in EXPECTED_FAILURE_CASE_IDS:
        source = by_id[candidate_id]
        inventory.append(
            {
                **source,
                "candidateId": candidate_id,
                "caseClass": (
                    "formal_failure"
                    if candidate_id == "v35_tsmom_crypto_adaptation"
                    else "development_failure"
                ),
                "executionAuthorized": False,
                "automaticPromotionAllowed": False,
            }
        )
    return inventory


def categorize_validated_review(
    review: Mapping[str, Any],
    *,
    required_questions: Sequence[str],
) -> dict[str, Any]:
    """Expose the validated schema as explicit fact/inference/recommendation lanes."""

    normalized = validate_failure(review)
    return {
        "Fact": list(normalized.get("facts") or []),
        "Inference": list(normalized.get("inferences") or []),
        "Recommendation": [str(normalized.get("nextExperiment") or "")],
        "Unverified": [str(item) for item in required_questions if str(item)],
        "failureLayer": normalized["failureLayer"],
        "repairability": normalized["repairability"],
        "prohibitedRepair": list(normalized["prohibitedRepair"]),
        "changedVariable": normalized["changedVariable"],
        "changedVariableCount": 1,
        "parentStrategy": normalized["parentStrategy"],
        "familyFingerprint": normalized["familyFingerprint"],
        "signalCorrelation": normalized["signalCorrelation"],
        "sourceArtifactHashes": list(normalized["sourceArtifactHashes"]),
        "executionAuthorized": False,
    }


def build_case_review_receipt(
    *,
    case: Mapping[str, Any],
    result: OrchestrationResult,
    negative_memory_hits: Sequence[Mapping[str, Any]],
    audit_projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one redacted, deterministic dual-model case receipt."""

    reviews = [dict(item) for item in result.validated_outputs]
    if len(reviews) != 2:
        raise ValueError("dual_model_validated_outputs_required")
    merger = deterministic_merge_failure_reviews(reviews)
    critical_disagreements = list(
        dict.fromkeys(
            [
                *list(result.disagreements),
                *list(merger.get("criticalDisagreements") or []),
            ]
        )
    )
    status = (
        "accepted"
        if result.status == "accepted" and merger["status"] == "accepted"
        else "completed_with_critical_disagreement"
    )
    receipt: dict[str, Any] = {
        "schemaVersion": "v62_4_2_failure_critic_case_receipt_v1",
        "candidateId": str(case.get("candidateId") or ""),
        "caseClass": str(case.get("caseClass") or ""),
        "status": status,
        "requestId": result.request_id,
        "routeMode": result.route_mode,
        "orchestrationStatus": result.status,
        "responseHashes": list(result.response_hashes),
        "sourceArtifactHashes": list(case.get("artifactHashes") or []),
        "deepseek": categorize_validated_review(
            reviews[0],
            required_questions=_REQUIRED_UNVERIFIED_QUESTIONS,
        ),
        "gemini": categorize_validated_review(
            reviews[1],
            required_questions=_REQUIRED_UNVERIFIED_QUESTIONS,
        ),
        "criticalDisagreements": critical_disagreements,
        "deterministicMerger": merger,
        "singleVariableNextExperiment": merger.get(
            "singleVariableNextExperiment"
        ),
        "negativeResearchMemoryHits": [
            dict(item) for item in negative_memory_hits
        ],
        "auditProjection": {
            "eventCount": int(audit_projection.get("eventCount") or 0),
            "projectionHash": _sha256_json(audit_projection),
        },
        "releaseCount": 0,
        "approvalCount": 0,
        "orderCount": 0,
        "demoArm": False,
        "liveEnabled": False,
        "liveArm": False,
        "withdrawEnabled": False,
        "automaticPromotionAllowed": False,
        "executionAuthorized": False,
    }
    receipt["receiptHash"] = _sha256_json(receipt)
    return receipt


def summarize_four_case_reviews(
    cases: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize four case receipts without promotion or execution authority."""

    candidate_ids = [str(item.get("candidateId") or "") for item in cases]
    if candidate_ids != list(EXPECTED_FAILURE_CASE_IDS):
        raise ValueError("four_case_review_order_or_identity_mismatch")
    accepted = sum(1 for item in cases if item.get("status") == "accepted")
    disagreement = sum(
        1 for item in cases if list(item.get("criticalDisagreements") or [])
    )
    memory_hits = sum(
        1 for item in cases if list(item.get("negativeResearchMemoryHits") or [])
    )
    return {
        "schemaVersion": "v62_4_2_four_case_failure_critic_summary_v1",
        "status": "accepted" if accepted == 4 else "completed_with_blockers",
        "caseCount": len(cases),
        "acceptedCaseCount": accepted,
        "criticalDisagreementCaseCount": disagreement,
        "memoryHitCaseCount": memory_hits,
        "candidateIds": candidate_ids,
        "cases": [dict(item) for item in cases],
        "releaseCount": 0,
        "approvalCount": 0,
        "orderCount": 0,
        "demoArm": False,
        "liveEnabled": False,
        "liveArm": False,
        "withdrawEnabled": False,
        "automaticPromotionAllowed": False,
        "executionAuthorized": False,
    }


def _write_four_case_evidence(
    output_root: Path,
    *,
    inventory: Sequence[Mapping[str, Any]],
    case_receipts: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    negative_memory: Mapping[str, Any],
) -> None:
    output_root.mkdir(parents=True, exist_ok=False)
    cases_root = output_root / "cases"
    cases_root.mkdir()
    (output_root / "failure_case_inventory.json").write_text(
        json.dumps(
            list(inventory),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    for receipt in case_receipts:
        candidate_id = str(receipt.get("candidateId") or "unknown")
        (cases_root / f"{candidate_id}.json").write_text(
            json.dumps(
                dict(receipt),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    (output_root / "four_case_failure_critic_summary.json").write_text(
        json.dumps(
            dict(summary),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    memory_receipt = {
        "schemaVersion": "v62_4_2_negative_research_memory_receipt_v1",
        "recordCount": int(negative_memory.get("recordCount") or 0),
        "retrievalMode": str(negative_memory.get("retrievalMode") or ""),
        "sourceArtifactHashes": list(
            negative_memory.get("sourceArtifactHashes") or []
        ),
        "recordsHash": _sha256_json(negative_memory.get("records") or []),
    }
    (output_root / "negative_research_memory_receipt.json").write_text(
        json.dumps(
            memory_receipt,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    lines = [
        "# V62.4.2 四案例双模型 Failure Critic",
        "",
        f"- 状态：`{summary['status']}`",
        f"- 案例：{summary['caseCount']}（3 个开发失败 + 1 个 Formal 失败）",
        f"- 双模型完成：{summary['acceptedCaseCount']}",
        f"- 关键分歧案例：{summary['criticalDisagreementCaseCount']}",
        f"- 命中历史负向记忆：{summary['memoryHitCaseCount']}",
        "- 自动晋级：`false`",
        "- Demo ARM：`false`",
        "- Live：`false`",
        "- 订单：`0`",
        "- Withdraw：`false`",
        "",
        "## 案例",
        "",
    ]
    for receipt in case_receipts:
        next_experiment = receipt.get("singleVariableNextExperiment")
        changed_variable = (
            str(next_experiment.get("changedVariable") or "")
            if isinstance(next_experiment, Mapping)
            else "等待人工复核关键分歧"
        )
        lines.extend(
            [
                f"- `{receipt['candidateId']}`：`{receipt['status']}`；"
                f"下一单变量 `{changed_variable}`；"
                f"记忆命中 {len(receipt['negativeResearchMemoryHits'])}",
            ]
        )
    (output_root / "four_case_failure_critic_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_four_case_failure_critic(
    *,
    repository_root: Path | str,
    strategy_factory_evidence_root: Path | str,
    formal_result_root: Path | str,
    strategy_factory_database: Path | str,
    output_root: Path | str,
) -> dict[str, Any]:
    """Run four bounded dual-model reviews in a credential-isolated AI worker."""

    assert_ai_worker_environment()
    repository = Path(repository_root).resolve()
    evidence_root = Path(strategy_factory_evidence_root).resolve()
    output = Path(output_root).resolve()
    if output.exists():
        raise FileExistsError(output)

    development_failures = load_development_failure_cases(
        evidence_root / "pilot_failure_attribution.json"
    )
    formal_failure = load_formal_failure_case(
        formal_result_root,
        candidate_id="v35_tsmom_crypto_adaptation",
    )
    inventory = build_failure_case_inventory(
        development_failures=development_failures,
        formal_failure=formal_failure,
    )
    negative_memory = load_negative_research_memory(
        strategy_factory_database,
        limit=100,
    )
    runtime_data_root = output.parent / f".{output.name}-ai-runtime"
    if runtime_data_root.exists():
        raise FileExistsError(runtime_data_root)

    case_receipts: list[dict[str, Any]] = []
    with build_ai_runtime(
        repository_root=repository,
        data_root=runtime_data_root,
    ) as runtime:
        for case in inventory:
            request = build_failure_critic_request(
                formal_case=case,
                negative_memory=negative_memory,
            )
            result = runtime.service.execute(request)
            memory_hits = find_negative_research_memory_hits(
                case=case,
                negative_memory=negative_memory,
                limit=10,
            )
            case_receipts.append(
                build_case_review_receipt(
                    case=case,
                    result=result,
                    negative_memory_hits=memory_hits,
                    audit_projection=runtime.audit_ledger.projection(),
                )
            )

    summary = summarize_four_case_reviews(case_receipts)
    summary["negativeResearchMemoryRecordCount"] = int(
        negative_memory.get("recordCount") or 0
    )
    summary["modelOrder"] = [
        "deepseek_reasoning_primary",
        "gemini_reasoning_primary",
    ]
    summary["summaryHash"] = _sha256_json(summary)
    _write_four_case_evidence(
        output,
        inventory=inventory,
        case_receipts=case_receipts,
        summary=summary,
        negative_memory=negative_memory,
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the V62.4.2 four-case dual-model Failure Critic."
    )
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument(
        "--strategy-factory-evidence-root",
        type=Path,
        required=True,
    )
    parser.add_argument("--formal-result-root", type=Path, required=True)
    parser.add_argument(
        "--strategy-factory-database",
        type=Path,
        required=True,
    )
    parser.add_argument("--output-root", type=Path, required=True)
    arguments = parser.parse_args()
    summary = run_four_case_failure_critic(
        repository_root=arguments.repository_root,
        strategy_factory_evidence_root=arguments.strategy_factory_evidence_root,
        formal_result_root=arguments.formal_result_root,
        strategy_factory_database=arguments.strategy_factory_database,
        output_root=arguments.output_root,
    )
    print(
        json.dumps(
            {
                "status": summary["status"],
                "caseCount": summary["caseCount"],
                "acceptedCaseCount": summary["acceptedCaseCount"],
                "criticalDisagreementCaseCount": summary[
                    "criticalDisagreementCaseCount"
                ],
                "summaryHash": summary["summaryHash"],
                "executionAuthorized": False,
                "outputRoot": str(arguments.output_root.resolve()),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
