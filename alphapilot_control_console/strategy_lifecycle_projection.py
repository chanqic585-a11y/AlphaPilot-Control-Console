"""Build one read-only current lifecycle stage for every strategy identity."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Callable

from .config import SAFETY_BOUNDARY
from .evolution_demo_service import build_evolution_demo_status
from .importer import scan_quant_engine
from .live_candidate_service import build_live_candidate_status
from .simulation_review import build_simulation_review
from .state_store import list_strategy_stage_assignments, now_iso
from .strategy_promotion_gate import build_strategy_promotion_gate
from .usable_strategy_catalog import build_usable_strategy_catalog


CONTROL_CONSOLE_VERSION = "V13.26.2"
CONTROL_CONSOLE_SOURCE = "strategy_lifecycle_projection_v2"

STAGE_ORDER = {
    "research_candidate": 10,
    "backtest_passed": 20,
    "local_simulation_running": 30,
    "local_simulation_passed": 40,
    "demo_trial": 45,
    "demo_validation_running": 50,
    "demo_validated": 60,
    "live_candidate": 70,
    "archived": 90,
}

STAGE_LABELS = {
    "research_candidate": "候选待测",
    "backtest_passed": "回测通过",
    "local_simulation_running": "本地模拟中",
    "local_simulation_passed": "本地模拟通过",
    "demo_trial": "Demo 观察中",
    "demo_validation_running": "Demo 验证中",
    "demo_validated": "Demo 通过",
    "live_candidate": "实盘候选",
    "archived": "已归档",
}

STAGE_PAGES = {
    "research_candidate": "strategy",
    "backtest_passed": "strategy",
    "local_simulation_running": "local_simulation",
    "local_simulation_passed": "local_simulation",
    "demo_trial": "demo",
    "demo_validation_running": "demo",
    "demo_validated": "demo",
    "live_candidate": "live",
    "archived": "archive",
}

NEXT_GATES = {
    "research_candidate": "完成可追溯回测，并形成正式回测通过决定。",
    "backtest_passed": "建立本地模拟观察任务。",
    "local_simulation_running": "完成样本、稳定性、集中度、成本和风险复核，再形成正式本地通过决定。",
    "local_simulation_passed": "生成不可变 Demo Release。",
    "demo_trial": "继续 Demo 行情观察；达到正式门槛后再生成不可变 Demo Release。",
    "demo_validation_running": "完成 Demo 闭合验证和异常复核。",
    "demo_validated": "生成不可变 Live Candidate Package。",
    "live_candidate": "等待人工发布复核；批准不会启用实盘执行。",
    "archived": "仅保留研究追溯，不再进入主流程。",
}


def _as_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any, prefix: str) -> str:
    digest = hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


def _first_text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _strategy_id(row: dict[str, Any]) -> str:
    direct = _first_text(
        row,
        "strategyCandidateId",
        "strategyId",
        "candidateId",
        "itemId",
        "taskId",
        "catalogId",
    )
    if direct:
        return direct
    identity_seed = {
        "name": _first_text(row, "name", "title", "strategyName", "shortName"),
        "timeframe": row.get("timeframe"),
        "family": row.get("family"),
        "direction": row.get("direction"),
        "source": row.get("source") or row.get("sourceReport"),
    }
    return _hash(identity_seed, "legacy_strategy")[:40]


def _display_name(row: dict[str, Any], fallback: str) -> str:
    return _first_text(row, "name", "title", "strategyName", "shortName", "displayName") or fallback


def _content_hash(row: dict[str, Any]) -> str:
    explicit = _first_text(row, "contentHash", "strategyHash", "definitionHash")
    if explicit:
        return explicit
    seed = {
        "strategyId": _strategy_id(row),
        "timeframe": row.get("timeframe"),
        "family": row.get("family"),
        "direction": row.get("direction"),
        "params": row.get("params") if isinstance(row.get("params"), dict) else {},
    }
    return _hash(seed, "legacy_content")


def _unique_text(values: list[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _load_source(
    label: str,
    builder: Callable[[], dict[str, Any]],
    fallback: dict[str, Any],
    warnings: list[dict[str, str]],
) -> dict[str, Any]:
    try:
        payload = builder()
    except Exception as error:  # A read-only dashboard should degrade per source.
        warnings.append({"source": label, "reason": type(error).__name__})
        return fallback
    return payload if isinstance(payload, dict) else fallback


def _new_record(row: dict[str, Any], source_kind: str) -> dict[str, Any]:
    strategy_id = _strategy_id(row)
    content_hash = _content_hash(row)
    return {
        "lifecycleId": _hash({"strategyId": strategy_id, "contentHash": content_hash}, "lifecycle")[:42],
        "strategyId": strategy_id,
        "displayName": _display_name(row, strategy_id),
        "contentHash": content_hash,
        "sourceKind": source_kind,
        "timeframe": row.get("timeframe"),
        "frequencyLabel": row.get("frequencyLabel"),
        "direction": row.get("direction"),
        "metrics": {},
        "blockers": [],
        "history": [],
        "terminalArchived": False,
        "formalDemoRelease": False,
        "formalLiveCandidate": False,
        "consistencyReasons": [],
    }


def _merge_metadata(record: dict[str, Any], row: dict[str, Any]) -> None:
    record["displayName"] = _display_name(row, record["displayName"])
    for key in ("timeframe", "frequencyLabel", "direction"):
        if not record.get(key) and row.get(key):
            record[key] = row.get(key)
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    record["metrics"].update(metrics)


def _add_evidence(
    records: dict[str, dict[str, Any]],
    row: dict[str, Any],
    stage: str,
    source_kind: str,
    *,
    source_label: str,
    details: dict[str, Any] | None = None,
    blockers: list[Any] | None = None,
) -> dict[str, Any]:
    strategy_id = _strategy_id(row)
    key = strategy_id.casefold()
    record = records.setdefault(key, _new_record(row, source_kind))
    _merge_metadata(record, row)
    observed_at = _first_text(row, "stageEnteredAt", "updatedAt", "createdAt", "generatedAt") or None
    evidence = {
        "stage": stage,
        "stageLabel": STAGE_LABELS[stage],
        "sourceKind": source_kind,
        "sourceLabel": source_label,
        "observedAt": observed_at,
        "details": details or {},
    }
    if evidence not in record["history"]:
        record["history"].append(evidence)
    record["blockers"] = _unique_text(record["blockers"] + list(blockers or []))
    return record


def _stage_from_decision(decision: dict[str, Any]) -> str | None:
    value = _first_text(decision, "currentStage", "stage", "decision", "status").casefold()
    if value in STAGE_ORDER:
        return value
    if value in {"approved_for_demo", "promoted_to_demo", "local_passed", "local_simulation_approved"}:
        return "local_simulation_passed"
    if value in {"passed_backtest", "backtest_approved", "research_passed"}:
        return "backtest_passed"
    if value in {"archive", "archived", "rejected", "retired"}:
        return "archived"
    return None


def _evidence_summary(record: dict[str, Any], stage: str) -> str:
    closed_samples = _safe_int(record.get("metrics", {}).get("closedSamples"))
    if stage == "research_candidate":
        return "研究闸门保留的候选；尚未形成正式回测通过决定。"
    if stage == "backtest_passed":
        return "已存在正式回测通过决定；尚未进入本地模拟。"
    if stage == "local_simulation_running":
        if closed_samples >= 30:
            return f"已闭合 {closed_samples} 个本地样本；达到复核起点，但没有正式晋级决定。"
        return f"正在本地模拟观察；已闭合 {closed_samples} 个样本。"
    if stage == "local_simulation_passed":
        return "已有正式本地模拟通过决定；等待生成 Demo Release。"
    if stage == "demo_trial":
        return "已从本地模拟移入 Demo 观察；历史样本保留，但尚未生成正式 Demo Release。"
    if stage == "demo_validation_running":
        return "已有不可变 Demo Release；正在进行 Demo 验证。"
    if stage == "demo_validated":
        return "Demo 已通过正式验证；等待生成 Live Candidate Package。"
    if stage == "live_candidate":
        return "已有不可变 Live Candidate Package；只等待人工发布复核。"
    return "已归档，只保留研究追溯。"


def _finalize_record(record: dict[str, Any]) -> dict[str, Any]:
    history = sorted(record["history"], key=lambda row: STAGE_ORDER.get(str(row.get("stage")), 0))
    stages = [str(row.get("stage")) for row in history]
    stage = "archived" if record["terminalArchived"] else max(stages, key=lambda item: STAGE_ORDER[item])
    if stage == "live_candidate" and not record["formalDemoRelease"]:
        record["consistencyReasons"].append("live_candidate_missing_demo_release")
    consistency_reasons = _unique_text(record["consistencyReasons"])
    current_evidence = [row for row in history if row.get("stage") == stage]
    stage_entered_at = next((row.get("observedAt") for row in reversed(current_evidence) if row.get("observedAt")), None)
    current_source_kind = str(current_evidence[-1].get("sourceKind") or record["sourceKind"]) if current_evidence else record["sourceKind"]
    return {
        "lifecycleId": record["lifecycleId"],
        "strategyId": record["strategyId"],
        "displayName": record["displayName"],
        "currentStage": stage,
        "stageLabel": STAGE_LABELS[stage],
        "page": STAGE_PAGES[stage],
        "sourceKind": current_source_kind,
        "contentHash": record["contentHash"],
        "stageEnteredAt": stage_entered_at,
        "timeframe": record.get("timeframe"),
        "frequencyLabel": record.get("frequencyLabel"),
        "direction": record.get("direction"),
        "consistencyStatus": "reconciliation_required" if consistency_reasons else "consistent",
        "consistencyReasons": consistency_reasons,
        "evidenceSummary": _evidence_summary(record, stage),
        "metrics": record["metrics"],
        "nextGate": NEXT_GATES[stage],
        "blockers": _unique_text(record["blockers"]),
        "history": history,
        "archived": stage == "archived",
    }


def build_strategy_lifecycle_projection(
    *,
    catalog: dict[str, Any] | None = None,
    simulation_review: dict[str, Any] | None = None,
    promotion_gate: dict[str, Any] | None = None,
    evolution_demo: dict[str, Any] | None = None,
    live_candidates: dict[str, Any] | None = None,
    artifact_index: dict[str, Any] | None = None,
    promotion_decisions: list[dict[str, Any]] | None = None,
    strategy_stage_assignments: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_warnings: list[dict[str, str]] = []
    scan_payload: dict[str, Any] | None = None

    def scan() -> dict[str, Any]:
        nonlocal scan_payload
        if scan_payload is None:
            scan_payload = _load_source("quant_engine", scan_quant_engine, {}, source_warnings)
        return scan_payload

    catalog = catalog if isinstance(catalog, dict) else _load_source(
        "usable_strategy_catalog", build_usable_strategy_catalog, {"strategies": [], "summary": {}}, source_warnings
    )
    simulation_review = simulation_review if isinstance(simulation_review, dict) else _load_source(
        "simulation_review", build_simulation_review, {"queue": [], "summary": {}}, source_warnings
    )
    promotion_gate = promotion_gate if isinstance(promotion_gate, dict) else _load_source(
        "strategy_promotion_gate",
        lambda: build_strategy_promotion_gate(scan()),
        {"buckets": {}, "summary": {}},
        source_warnings,
    )
    evolution_demo = evolution_demo if isinstance(evolution_demo, dict) else _load_source(
        "evolution_demo", build_evolution_demo_status, {"contracts": [], "summary": {}}, source_warnings
    )
    live_candidates = live_candidates if isinstance(live_candidates, dict) else _load_source(
        "live_candidates", build_live_candidate_status, {"packages": [], "summary": {}}, source_warnings
    )
    artifact_index = artifact_index if isinstance(artifact_index, dict) else (
        scan().get("strategyArtifactIndex") if isinstance(scan().get("strategyArtifactIndex"), dict) else {}
    )
    if promotion_decisions is None:
        raw_decisions = scan().get("promotionDecisions")
        promotion_decisions = _as_rows(raw_decisions)
    if strategy_stage_assignments is None:
        try:
            strategy_stage_assignments = list_strategy_stage_assignments()
        except Exception as error:  # Keep the read-only projection available if local state cannot be read.
            source_warnings.append({"source": "strategy_stage_assignments", "reason": type(error).__name__})
            strategy_stage_assignments = {}
    assignment_by_id = {
        str(strategy_id).casefold(): assignment
        for strategy_id, assignment in strategy_stage_assignments.items()
        if isinstance(assignment, dict)
    }

    records: dict[str, dict[str, Any]] = {}
    release_strategy_ids: dict[str, str] = {}
    archive_ids: set[str] = set()

    for row in _as_rows(catalog.get("strategies")):
        strategy_id = _strategy_id(row)
        assignment = assignment_by_id.get(strategy_id.casefold(), {})
        assigned_stage = str(assignment.get("stage") or "local_sandbox")
        projection_stage = {
            "local_sandbox": "local_simulation_running",
            "demo_trial": "demo_trial",
            "demo_validated": "demo_validated",
            "live_candidate": "live_candidate",
            "archived": "archived",
        }.get(assigned_stage, "local_simulation_running")
        record = _add_evidence(
            records,
            {**row, **assignment, "strategyId": strategy_id},
            projection_stage,
            "strategy_stage_assignment",
            source_label="当前策略阶段分配",
            details={
                "assignedStage": assigned_stage,
                "sandboxReady": bool(row.get("sandboxReady", True)),
                "sampleDataPreserved": bool(assignment.get("sampleDataPreserved", True)),
                "formalDemoRelease": False,
            },
            blockers=list(row.get("riskNotes") or []),
        )
        if projection_stage == "archived":
            record["terminalArchived"] = True
            archive_ids.add(strategy_id)

    for row in _as_rows(simulation_review.get("queue")):
        metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
        sample_gate = row.get("sampleGate") if isinstance(row.get("sampleGate"), dict) else {}
        enriched = {**row, "metrics": {**metrics, "closedSamples": sample_gate.get("closedSamples", metrics.get("closedSamples"))}}
        _add_evidence(
            records,
            enriched,
            "local_simulation_running",
            "legacy_simulation_review",
            source_label="本地模拟复核进度",
            details={
                "legacyStatus": row.get("status"),
                "reviewReady": bool(sample_gate.get("isReviewReady")),
                "formalPromotion": False,
            },
            blockers=list(row.get("warnings") or []),
        )

    buckets = promotion_gate.get("buckets") if isinstance(promotion_gate.get("buckets"), dict) else {}
    for row in _as_rows(buckets.get("survivors")):
        _add_evidence(
            records,
            row,
            "research_candidate",
            "legacy_research_survivor",
            source_label="旧研究闸门幸存者",
            details={"formalPromotion": False},
            blockers=list(row.get("reasons") or []),
        )
    for bucket_name in ("watchlist", "needsWork", "archived", "negativeSamples"):
        for row in _as_rows(buckets.get(bucket_name)):
            archive_ids.add(_first_text(row, "artifactId", "itemId", "strategyId") or _hash(row, "archive"))

    for decision in _as_rows(promotion_decisions):
        stage = _stage_from_decision(decision)
        if not stage:
            continue
        record = _add_evidence(
            records,
            decision,
            stage,
            "formal_promotion_decision",
            source_label="正式晋级决定",
            details={"decisionId": decision.get("decisionId")},
            blockers=list(decision.get("blockers") or []),
        )
        if stage == "archived":
            record["terminalArchived"] = True
            archive_ids.add(record["strategyId"])

    for contract in _as_rows(evolution_demo.get("contracts")):
        release_id = _first_text(contract, "demoReleaseId")
        strategy_id = _first_text(contract, "strategyCandidateId", "strategyId") or f"demo_release::{release_id}"
        release_strategy_ids[release_id] = strategy_id
        validation_status = _first_text(contract, "validationStatus", "demoValidationStatus").casefold()
        stage = "demo_validated" if validation_status in {"passed", "validated", "completed"} else "demo_validation_running"
        record = _add_evidence(
            records,
            {**contract, "strategyCandidateId": strategy_id},
            stage,
            "formal_demo_release",
            source_label="不可变 Demo Release",
            details={"demoReleaseId": release_id, "contractStatus": contract.get("status")},
        )
        record["formalDemoRelease"] = True

    for export in _as_rows(live_candidates.get("packages")):
        package = export.get("package") if isinstance(export.get("package"), dict) else {}
        release_id = _first_text(export, "demoReleaseId") or _first_text(package, "demoReleaseId")
        strategy_id = (
            _first_text(export, "strategyCandidateId", "strategyId")
            or _first_text(package, "strategyCandidateId", "strategyId")
            or release_strategy_ids.get(release_id, "")
            or f"live_candidate::{_first_text(export, 'liveCandidatePackageId')}"
        )
        approval = export.get("approval") if isinstance(export.get("approval"), dict) else {}
        record = _add_evidence(
            records,
            {**export, **package, "strategyCandidateId": strategy_id},
            "live_candidate",
            "formal_live_candidate_package",
            source_label="不可变 Live Candidate Package",
            details={
                "liveCandidatePackageId": export.get("liveCandidatePackageId"),
                "demoReleaseId": release_id,
                "approvalStatus": approval.get("status"),
            },
        )
        record["formalLiveCandidate"] = True
        if release_id and release_id in release_strategy_ids:
            record["formalDemoRelease"] = True

    artifacts = _as_rows(artifact_index.get("artifacts"))
    for row in artifacts:
        archive_ids.add(_first_text(row, "artifactId", "sourceFile") or _hash(row, "artifact"))

    finalized = [_finalize_record(record) for record in records.values() if record.get("history")]
    active_items = [row for row in finalized if not row["archived"]]
    active_items.sort(key=lambda row: (-STAGE_ORDER[row["currentStage"]], row["displayName"], row["strategyId"]))
    archived_items = [row for row in finalized if row["archived"]]
    stage_counts = Counter(row["currentStage"] for row in active_items)
    reconciliation_count = sum(row["consistencyStatus"] == "reconciliation_required" for row in active_items)
    archive_count = len(archive_ids | {row["strategyId"] for row in archived_items})
    summary = {
        "activeStrategyCount": len(active_items),
        "strategyCandidateCount": stage_counts["research_candidate"],
        "backtestPassedCount": stage_counts["backtest_passed"],
        "localSimulationRunningCount": stage_counts["local_simulation_running"],
        "localSimulationPassedCount": stage_counts["local_simulation_passed"],
        "demoTrialCount": stage_counts["demo_trial"],
        "demoValidationRunningCount": stage_counts["demo_validation_running"],
        "demoValidatedCount": stage_counts["demo_validated"],
        "liveCandidateCount": stage_counts["live_candidate"],
        "archivedCount": archive_count,
        "reconciliationRequiredCount": reconciliation_count,
    }
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": summary,
        "items": active_items,
        "byStage": {
            stage: [row for row in active_items if row["currentStage"] == stage]
            for stage in STAGE_LABELS
            if stage != "archived"
        },
        "archiveSummary": {
            "researchArtifactCount": len(artifacts),
            "archivedStrategyCount": len(archived_items),
            "totalArchivedCount": archive_count,
        },
        "archivedItems": archived_items,
        "sourceWarnings": source_warnings,
        "safetyBoundary": {
            **SAFETY_BOUNDARY,
            "readOnlyProjection": True,
            "createsPromotionDecision": False,
            "createsDemoRelease": False,
            "createsLiveCandidate": False,
            "createsOrders": False,
            "liveExecutionEnabled": False,
        },
    }
