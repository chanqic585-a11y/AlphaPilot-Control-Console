from __future__ import annotations

import json
import time
from typing import Any

from .config import SAFETY_BOUNDARY
from .exchange_connectors.public_exchange_registry import list_public_exchange_sources
from .pre_live_preparation_pack import build_pre_live_preparation_pack
from .state_store import now_iso, read_exchange_probe_results
from .testnet_design_boundary import build_testnet_design_boundary
from .testnet_drill import build_testnet_drill
from .testnet_readiness_pack import REQUIRED_TESTNET_CONTROLS


CONTROL_CONSOLE_VERSION = "V13.8.10"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8_10"
AUDIT_CACHE_TTL_SECONDS = 60
_AUDIT_CACHE: dict[str, Any] | None = None
_AUDIT_CACHE_EXPIRES_AT = 0.0


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _status(label: str, passed: bool, detail: str, severity: str = "required") -> dict[str, Any]:
    return {
        "label": label,
        "passed": bool(passed),
        "status": "passed" if passed else "blocked",
        "severity": severity,
        "detail": detail,
    }


def _build_lightweight_readiness_summary(testnet_candidates: int) -> tuple[dict[str, Any], list[str]]:
    missing_controls = [
        item for item in REQUIRED_TESTNET_CONTROLS if item.get("required") and not item.get("implemented")
    ]
    blockers = [str(item.get("label")) for item in missing_controls]
    probe = read_exchange_probe_results() or {}
    public_sources = list_public_exchange_sources()
    if testnet_candidates <= 0:
        blockers.append("没有策略达到 testnet readiness candidate 门槛")
    if not probe:
        blockers.append("尚未完成本地 public exchange probe 复核")
    return {
        "readinessStage": "blocked" if blockers else "design_review_only",
        "readinessStageLabel": "阻塞中" if blockers else "仅可进入设计复核",
        "testnetCandidateCount": testnet_candidates,
        "implementedControlCount": sum(1 for item in REQUIRED_TESTNET_CONTROLS if item.get("implemented")),
        "missingRequiredControlCount": len(missing_controls),
        "blockerCount": len(blockers),
        "publicSourceCount": len(public_sources.get("sources", [])) if isinstance(public_sources, dict) else 0,
        "hasPublicProbe": bool(probe),
        "testnetEnabled": False,
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "nextAction": (
            "先完成 testnet 凭据隔离、订单生命周期模拟、kill switch 和限额模型设计。"
            if blockers
            else "可以写 testnet 设计文档，但仍不能接密钥或下单。"
        ),
    }, blockers


def build_testnet_audit_pack() -> dict[str, Any]:
    global _AUDIT_CACHE, _AUDIT_CACHE_EXPIRES_AT
    current_time = time.monotonic()
    if _AUDIT_CACHE is not None and current_time < _AUDIT_CACHE_EXPIRES_AT:
        return _AUDIT_CACHE

    drill = build_testnet_drill()
    boundary = build_testnet_design_boundary()
    pre_live = build_pre_live_preparation_pack()

    drill_summary = drill.get("summary") if isinstance(drill.get("summary"), dict) else {}
    boundary_summary = boundary.get("summary") if isinstance(boundary.get("summary"), dict) else {}
    pre_live_summary = pre_live.get("summary") if isinstance(pre_live.get("summary"), dict) else {}
    rehearsal_summary = drill.get("rehearsalSummary") if isinstance(drill.get("rehearsalSummary"), dict) else {}
    stage_counts = drill_summary.get("stageCounts") if isinstance(drill_summary.get("stageCounts"), dict) else {}
    testnet_drill_candidates = _safe_int(stage_counts.get("testnetDrillCandidate"))
    readiness_summary, readiness_blockers = _build_lightweight_readiness_summary(testnet_drill_candidates)
    audit_items = [
        _status(
            "本地通过路径演练",
            _safe_int(rehearsal_summary.get("passed")) > 0,
            "至少需要一条通过风控的本地生命周期演练记录。",
        ),
        _status(
            "本地拒绝路径演练",
            _safe_int(rehearsal_summary.get("rejected")) > 0,
            "至少需要一条被风控拒绝的本地生命周期演练记录。",
        ),
        _status(
            "策略本地复核样本",
            _safe_int(stage_counts.get("localReviewCandidate")) >= 5,
            "至少 5 条策略应具备本地复核样本；当前仍只允许研究复核。",
        ),
        _status(
            "Testnet 连接仍关闭",
            drill_summary.get("testnetEnabled") is False and boundary_summary.get("testnetEnabled") is False,
            "连接交易所 testnet 仍必须关闭，直到凭据隔离和人工解锁完成。",
            "safety",
        ),
        _status(
            "订单创建仍关闭",
            drill_summary.get("orderCreationEnabled") is False and boundary_summary.get("orderCreationEnabled") is False,
            "当前不能创建 testnet 或真实订单。",
            "safety",
        ),
        _status(
            "凭据保险箱未实现",
            pre_live_summary.get("credentialVaultImplemented") is True,
            "这是未来 testnet 连接前的硬阻塞项；当前不允许输入或保存 API Key。",
        ),
        _status(
            "人工解锁未实现",
            False,
            "未来任何 testnet 连接或订单能力都必须先做人工解锁和二次确认。",
        ),
        _status(
            "公共行情探测",
            bool(readiness_summary.get("hasPublicProbe")),
            "需要 public exchange probe 作为只读连通性证据；这不是交易权限。",
            "recommended",
        ),
    ]
    hard_blockers = [
        item["label"]
        for item in audit_items
        if item["severity"] == "required" and not item["passed"]
    ]
    safety_failures = [
        item["label"]
        for item in audit_items
        if item["severity"] == "safety" and not item["passed"]
    ]
    stage = "blocked_from_testnet_connection"
    if safety_failures:
        stage = "safety_boundary_violation"
    elif not hard_blockers:
        stage = "local_design_review_ready"
    critical_blockers = hard_blockers + [str(item) for item in readiness_blockers[:6]]
    payload = {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "auditStage": stage,
            "auditStageLabel": (
                "安全边界异常"
                if stage == "safety_boundary_violation"
                else "仅可进入本地设计复核"
                if stage == "local_design_review_ready"
                else "禁止连接 Testnet"
            ),
            "canEnterLocalDesignReview": stage == "local_design_review_ready",
            "canConnectTestnet": False,
            "canStoreApiKey": False,
            "canCreateOrders": False,
            "localLifecycleComplete": bool(rehearsal_summary.get("localPathsComplete")),
            "reviewCandidateCount": _safe_int(stage_counts.get("localReviewCandidate")),
            "testnetDrillCandidateCount": testnet_drill_candidates,
            "rehearsalCount": _safe_int(rehearsal_summary.get("total")),
            "passedRehearsals": _safe_int(rehearsal_summary.get("passed")),
            "rejectedRehearsals": _safe_int(rehearsal_summary.get("rejected")),
            "hardBlockerCount": len(hard_blockers),
            "safetyFailureCount": len(safety_failures),
            "readinessBlockerCount": len(readiness_blockers),
            "nextAction": (
                "先补凭据保险箱设计、人工解锁、max-loss/max-order 模型和只读 public probe；不要接 API Key 或订单能力。"
                if stage != "local_design_review_ready"
                else "可以写 Testnet 连接设计文档，但仍不能输入 API Key、不能连接私有接口、不能创建订单。"
            ),
        },
        "auditItems": audit_items,
        "criticalBlockers": critical_blockers,
        "hardBlockers": hard_blockers,
        "safetyFailures": safety_failures,
        "readinessBlockers": readiness_blockers,
        "drillSummary": drill_summary,
        "readinessSummary": readiness_summary,
        "boundarySummary": boundary_summary,
        "preLiveSummary": pre_live_summary,
        "disabledExecution": drill.get("disabledExecution", []),
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Testnet audit is local review only. It cannot store API keys, connect private endpoints, run exchange dry-run, create orders, or trade automatically.",
    }
    _AUDIT_CACHE = payload
    _AUDIT_CACHE_EXPIRES_AT = current_time + AUDIT_CACHE_TTL_SECONDS
    return payload


if __name__ == "__main__":
    print(json.dumps(build_testnet_audit_pack(), ensure_ascii=False, indent=2))
