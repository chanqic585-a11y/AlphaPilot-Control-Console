"""V62.4.1 read-only acceptance helpers for a real dual-model failure review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from copy import deepcopy
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from uuid import uuid4

from .ai_orchestration.bootstrap import build_ai_runtime
from .ai_orchestration.contracts import AIRequest, OrchestrationResult
from .ai_orchestration.validation import canonical_json
from .strategy_factory_v2.schemas import FAILURE_RESPONSE_SCHEMA, validate_failure


_CRITICAL_FIELDS = ("failureLayer", "repairability", "changedVariable")
_FORMAL_ARTIFACT_NAMES = (
    "campaign_summary.json",
    "failure_attribution.json",
    "gate_matrix.json",
    "route_decision.json",
)


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(canonical_json(value).encode("utf-8"))


def _read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path.name}")
    return value


def load_formal_failure_case(
    formal_result_root: Path | str,
    *,
    candidate_id: str,
) -> dict[str, Any]:
    """Load the frozen failed Formal result from four hash-bound artifacts."""

    root = Path(formal_result_root).resolve()
    documents: dict[str, dict[str, Any]] = {}
    artifact_hashes: list[str] = []
    artifact_manifest: list[dict[str, Any]] = []
    for name in _FORMAL_ARTIFACT_NAMES:
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(path)
        content = path.read_bytes()
        artifact_hash = _sha256_bytes(content)
        documents[name] = json.loads(content.decode("utf-8"))
        artifact_hashes.append(artifact_hash)
        artifact_manifest.append(
            {
                "name": name,
                "sha256": artifact_hash,
                "sizeBytes": len(content),
            }
        )

    summary = documents["campaign_summary.json"]
    failure = documents["failure_attribution.json"]
    gates = documents["gate_matrix.json"]
    route = documents["route_decision.json"]
    return {
        "schemaVersion": "v62_4_1_formal_failure_case_v1",
        "campaignId": str(summary.get("campaignId") or route.get("campaignId") or ""),
        "candidateId": candidate_id,
        "formalPass": bool(summary.get("formalPass")),
        "route": str(summary.get("route") or route.get("route") or ""),
        "artifactHashes": artifact_hashes,
        "artifactManifest": artifact_manifest,
        "trialResult": {
            "candidateId": candidate_id,
            "formalPass": bool(summary.get("formalPass")),
            "route": str(summary.get("route") or route.get("route") or ""),
            "baseMetrics": dict(summary.get("baseMetrics") or {}),
            "baseAcceptedTradeCount": int(summary.get("baseAcceptedTradeCount") or 0),
            "blockers": list(summary.get("blockers") or []),
            "primaryBlocker": str(failure.get("primaryBlocker") or ""),
            "strategyPerformanceFailure": bool(
                failure.get("strategyPerformanceFailure")
            ),
            "failedAdmissionGateIds": list(
                gates.get("failedAdmissionGateIds") or []
            ),
            "gateCounts": {
                "passed": int(gates.get("passedCount") or 0),
                "failed": int(gates.get("failedCount") or 0),
                "notEvaluable": int(gates.get("notEvaluableCount") or 0),
            },
            "formalRunCount": int(route.get("formalRunCount") or 0),
            "formalInputReadCount": int(route.get("formalInputReadCount") or 0),
            "releaseCount": int(route.get("releaseCount") or 0),
            "orderCount": int(route.get("orderCount") or 0),
            "demoArm": bool(route.get("demoArm")),
        },
    }


def load_negative_research_memory(
    database_path: Path | str,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """Read historical Strategy Factory failure archives without mutating SQLite."""

    database = Path(database_path).resolve()
    if not database.is_file():
        raise FileNotFoundError(database)
    bounded_limit = max(1, min(int(limit), 500))
    uri = "file:" + database.as_posix() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        rows = connection.execute(
            """
            SELECT eventId, runId, payloadJson, createdAt
            FROM StrategyFactoryEvents
            WHERE eventType = 'candidate_failures_archived'
            ORDER BY eventId DESC
            LIMIT ?
            """,
            (bounded_limit,),
        ).fetchall()
    finally:
        connection.close()

    records: list[dict[str, Any]] = []
    source_hashes: list[str] = []
    for event_id, run_id, payload_json, created_at in rows:
        payload = json.loads(payload_json)
        archive_path = Path(str(payload.get("archivePath") or "")).resolve()
        if not archive_path.is_file():
            continue
        archive_bytes = archive_path.read_bytes()
        archive_hash = _sha256_bytes(archive_bytes)
        archive = json.loads(archive_bytes.decode("utf-8"))
        candidates = archive.get("archivedCandidates") if isinstance(archive, dict) else None
        if not isinstance(candidates, list):
            continue
        source_hashes.append(archive_hash)
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            records.append(
                {
                    "eventId": int(event_id),
                    "runId": str(run_id),
                    "candidateId": str(candidate.get("candidateId") or ""),
                    "reason": str(candidate.get("reason") or "unspecified"),
                    "status": str(candidate.get("status") or "archived"),
                    "createdAt": str(created_at),
                    "sourceArtifactHash": archive_hash,
                }
            )
    records = records[:bounded_limit]
    return {
        "schemaVersion": "v62_4_1_negative_research_memory_v1",
        "recordCount": len(records),
        "records": records,
        "sourceArtifactHashes": sorted(set(source_hashes)),
        "retrievalMode": "sqlite_read_only_plus_hash_bound_archives",
    }


def deterministic_merge_failure_reviews(
    reviews: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Merge two validated critics or route critical disagreement for review."""

    if len(reviews) != 2:
        raise ValueError("exactly_two_failure_reviews_required")
    normalized = [validate_failure(review) for review in reviews]
    disagreements = [
        field
        for field in _CRITICAL_FIELDS
        if canonical_json(normalized[0].get(field))
        != canonical_json(normalized[1].get(field))
    ]
    proposals = [
        {
            "reviewerIndex": index,
            "changedVariable": review["changedVariable"],
            "changedVariableCount": 1,
            "nextExperiment": review["nextExperiment"],
        }
        for index, review in enumerate(normalized, start=1)
    ]
    merged: dict[str, Any] = {
        "schemaVersion": "v62_4_1_failure_critic_merge_v1",
        "status": (
            "critical_disagreement_requires_human_review"
            if disagreements
            else "accepted"
        ),
        "criticalDisagreements": disagreements,
        "reviewerExperimentProposals": proposals,
        "singleVariableNextExperiment": None,
        "executionAuthorized": False,
        "automaticPromotionAllowed": False,
        "reviewHashes": [_sha256_json(review) for review in normalized],
    }
    if not disagreements:
        first = normalized[0]
        merged["singleVariableNextExperiment"] = {
            "changedVariable": first["changedVariable"],
            "changedVariableCount": 1,
            "nextExperiment": first["nextExperiment"],
            "requiresNewPreregistration": True,
            "lockedOosReadAllowed": False,
            "gateRelaxationAllowed": False,
        }
    merged["mergeHash"] = _sha256_json(merged)
    return merged


def build_failure_critic_request(
    *,
    formal_case: Mapping[str, Any],
    negative_memory: Mapping[str, Any],
) -> AIRequest:
    """Create one bounded, tool-free dual review request."""

    artifact_hashes = tuple(
        dict.fromkeys(
            [
                *list(formal_case.get("artifactHashes") or []),
                *list(negative_memory.get("sourceArtifactHashes") or []),
            ]
        )
    )
    return AIRequest(
        request_id=f"v62-4-1-failure-attribution-{uuid4().hex}",
        task_type="failure_attribution",
        payload={
            "candidateId": str(formal_case.get("candidateId") or ""),
            "formalCampaignId": str(formal_case.get("campaignId") or ""),
            "trialResult": dict(formal_case.get("trialResult") or {}),
            "negativeResearchMemory": list(negative_memory.get("records") or []),
            "failureTree": [
                "Implementation",
                "Data / PIT",
                "Signal Edge",
                "Cost / Capacity",
                "Stability / Regime",
                "Risk / Portfolio",
                "Promotion / Execution",
            ],
            "constraints": {
                "factInferenceSeparation": True,
                "oneVariableAtATime": True,
                "lockedOosTuningAllowed": False,
                "gateRelaxationAfterResultsAllowed": False,
                "automaticPromotionAllowed": False,
                "executionAuthorityAllowed": False,
            },
            "boundSourceArtifactHashes": list(artifact_hashes),
        },
        response_schema=FAILURE_RESPONSE_SCHEMA,
        sensitivity="internal",
        prompt_version="failure-attribution-v1",
        artifact_hashes=artifact_hashes,
        tool_names=(),
        quant_research=True,
        dual_review=True,
        human_review_required=True,
        cost_ceiling_usd=0.5,
        token_ceiling=2_048,
        metadata={
            "researchCampaignId": str(formal_case.get("campaignId") or "v62_4_1"),
            "candidateId": str(formal_case.get("candidateId") or ""),
            "acceptanceScope": "v62_4_1_failure_critic",
        },
    )


def build_failure_critic_acceptance_report(
    *,
    formal_case: Mapping[str, Any],
    negative_memory: Mapping[str, Any],
    result: OrchestrationResult,
    audit_projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a redacted evidence report from two schema-validated model reviews."""

    reviews = [dict(item) for item in result.validated_outputs]
    if len(reviews) != 2:
        raise ValueError("dual_model_validated_outputs_required")
    merged = deterministic_merge_failure_reviews(reviews)

    disagreement_fixture = deepcopy(reviews)
    original_variable = str(disagreement_fixture[1]["changedVariable"])
    disagreement_fixture[1]["changedVariable"] = (
        "volatilityFilter"
        if original_variable != "volatilityFilter"
        else "trendLookback"
    )
    disagreement_fixture[1]["nextExperiment"] = (
        "Change only the alternate preregistered variable in a new campaign."
    )
    disagreement_route = deterministic_merge_failure_reviews(disagreement_fixture)

    events = audit_projection.get("events")
    safe_events = list(events) if isinstance(events, list) else []
    latest_event = dict(safe_events[-1]) if safe_events else {}
    report_status = (
        "accepted"
        if result.status == "accepted" and merged["status"] == "accepted"
        else "completed_with_critical_disagreement"
    )
    report: dict[str, Any] = {
        "schemaVersion": "v62_4_1_failure_critic_acceptance_v1",
        "status": report_status,
        "formalCase": {
            "campaignId": str(formal_case.get("campaignId") or ""),
            "candidateId": str(formal_case.get("candidateId") or ""),
            "formalPass": bool(formal_case.get("formalPass")),
            "route": str(formal_case.get("route") or ""),
            "artifactHashes": list(formal_case.get("artifactHashes") or []),
        },
        "negativeResearchMemory": {
            "recordCount": int(negative_memory.get("recordCount") or 0),
            "retrievalMode": str(negative_memory.get("retrievalMode") or ""),
            "memoryHash": _sha256_json(negative_memory.get("records") or []),
            "sourceArtifactHashes": list(
                negative_memory.get("sourceArtifactHashes") or []
            ),
        },
        "dualModelReview": {
            "requestId": result.request_id,
            "routeMode": result.route_mode,
            "orchestrationStatus": result.status,
            "reviewCount": len(reviews),
            "responseHashes": list(result.response_hashes),
            "criticalDisagreements": list(result.disagreements),
            "validatedReviewerOutputs": reviews,
        },
        "deterministicMerger": merged,
        "criticalDisagreementRouteTest": disagreement_route,
        "auditLedgerProjection": {
            "eventCount": int(audit_projection.get("eventCount") or 0),
            "latestEvent": latest_event,
            "projectionHash": _sha256_json(audit_projection),
        },
        "safety": {
            "executionAuthorized": False,
            "automaticPromotionAllowed": False,
            "demoArm": False,
            "liveArm": False,
            "orderCount": 0,
            "withdrawEnabled": False,
            "exchangeCredentialsAvailableToAIWorker": False,
        },
    }
    report["reportHash"] = _sha256_json(report)
    return report


def _write_acceptance_report(output_root: Path, report: Mapping[str, Any]) -> None:
    output_root.mkdir(parents=True, exist_ok=False)
    json_path = output_root / "failure_critic_acceptance.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    merger = report["deterministicMerger"]
    lines = [
        "# V62.4.1 双模型失败归因独立验收",
        "",
        f"- 状态：`{report['status']}`",
        f"- 候选：`{report['formalCase']['candidateId']}`",
        f"- Formal 路由：`{report['formalCase']['route']}`",
        f"- 负向研究记忆：{report['negativeResearchMemory']['recordCount']} 条",
        f"- 双模型结构化审查：{report['dualModelReview']['reviewCount']} 份",
        f"- 确定性合并：`{merger['status']}`",
        f"- 关键分歧：{', '.join(merger['criticalDisagreements']) or '无'}",
        (
            "- 单变量下一实验："
            + (
                f"`{merger['singleVariableNextExperiment']['changedVariable']}`"
                if merger["singleVariableNextExperiment"]
                else "未自动选择，等待人工复核"
            )
        ),
        "- 强制分歧负向测试：`critical_disagreement_requires_human_review`",
        "- 执行授权：`false`",
        "- Demo ARM：`false`",
        "- Live ARM：`false`",
        "- 订单：`0`",
        "- Withdraw：`false`",
        "",
        f"报告哈希：`{report['reportHash']}`",
    ]
    (output_root / "failure_critic_acceptance.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_failure_critic_acceptance(
    *,
    repository_root: Path | str,
    formal_result_root: Path | str,
    strategy_factory_database: Path | str,
    output_root: Path | str,
    candidate_id: str,
) -> dict[str, Any]:
    """Execute the bounded real-provider dual review and persist redacted evidence."""

    if not os.environ.get("DEEPSEEK_API_KEY") or not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("provider_credentials_required_deepseek_gemini")
    forbidden_exchange_environment = (
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
    present = [name for name in forbidden_exchange_environment if os.environ.get(name)]
    if present:
        raise RuntimeError("exchange_credentials_forbidden_in_ai_worker")

    output = Path(output_root).resolve()
    if output.exists():
        raise FileExistsError(output)
    formal_case = load_formal_failure_case(
        formal_result_root,
        candidate_id=candidate_id,
    )
    negative_memory = load_negative_research_memory(
        strategy_factory_database,
        limit=50,
    )
    if int(negative_memory.get("recordCount") or 0) < 1:
        raise RuntimeError("negative_research_memory_required")
    request = build_failure_critic_request(
        formal_case=formal_case,
        negative_memory=negative_memory,
    )
    runtime_data_root = output.parent / f".{output.name}-runtime"
    if runtime_data_root.exists():
        raise FileExistsError(runtime_data_root)
    with build_ai_runtime(
        repository_root=repository_root,
        data_root=runtime_data_root,
    ) as runtime:
        result = runtime.service.execute(request)
        audit_projection = runtime.audit_ledger.projection()

    report = build_failure_critic_acceptance_report(
        formal_case=formal_case,
        negative_memory=negative_memory,
        result=result,
        audit_projection=audit_projection,
    )
    _write_acceptance_report(output, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the bounded V62.4.1 dual-model failure critic acceptance."
    )
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--formal-result-root", type=Path, required=True)
    parser.add_argument("--strategy-factory-database", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--candidate-id",
        default="v35_tsmom_crypto_adaptation",
    )
    arguments = parser.parse_args()
    report = run_failure_critic_acceptance(
        repository_root=arguments.repository_root,
        formal_result_root=arguments.formal_result_root,
        strategy_factory_database=arguments.strategy_factory_database,
        output_root=arguments.output_root,
        candidate_id=arguments.candidate_id,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "reportHash": report["reportHash"],
                "responseHashes": report["dualModelReview"]["responseHashes"],
                "outputRoot": str(arguments.output_root.resolve()),
                "executionAuthorized": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
