"""Compact projections and local actions for strategy-validation Demo v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .backtest_screening_projection import build_backtest_screening_projection
from .config import get_quant_engine_path
from .strategy_validation_approval_service import (
    approve_strategy_validation_release,
    revoke_strategy_validation_release,
)
from .strategy_validation_approval_store import StrategyValidationApprovalStore
from .strategy_validation_demo_store import StrategyValidationDemoStore
from .strategy_validation_forward_review import build_strategy_validation_forward_review
from .strategy_validation_release_service import StrategyValidationReleaseService
from .strategy_validation_release_store import StrategyValidationReleaseStore
from .strategy_validation_risk_store import StrategyValidationRiskStore
from .strategy_validation_runtime_admission import StrategyValidationRuntimeAdmission


def find_latest_backtest_campaign(*, quant_root: Path | str | None = None) -> str | None:
    root = Path(quant_root) if quant_root is not None else get_quant_engine_path()
    base = root / "reports" / "backtest_screening"
    if not base.is_dir():
        return None
    candidates = [
        path for path in base.iterdir()
        if path.is_dir() and (path / "campaign_summary.json").is_file()
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda path: ((path / "campaign_summary.json").stat().st_mtime_ns, path.name))
    return candidates[-1].name


def build_strategy_validation_status(
    *, campaign_id: str | None = None, quant_root: Path | str | None = None
) -> dict[str, Any]:
    current_campaign = campaign_id or find_latest_backtest_campaign(quant_root=quant_root)
    screening: dict[str, Any]
    if current_campaign:
        try:
            screening = build_backtest_screening_projection(current_campaign, quant_root=quant_root)
        except (FileNotFoundError, ValueError) as error:
            screening = {"campaignId": current_campaign, "status": "blocked", "error": str(error)}
    else:
        screening = {"campaignId": None, "status": "empty", "formalPassCount": 0, "releaseCount": 0}

    releases = StrategyValidationReleaseStore()
    approvals = StrategyValidationApprovalStore(release_store=releases)
    runtime = StrategyValidationRuntimeAdmission(release_store=releases, approval_store=approvals)
    demo = StrategyValidationDemoStore()
    risk = StrategyValidationRiskStore()
    try:
        rows = []
        for release in releases.list_releases(current_campaign):
            approval = approvals.get_state(release["releaseId"])
            rows.append({
                **release,
                "approvalStatus": approval.get("status"),
                "approved": bool(approval.get("approved")),
            })
        demo_summary = demo.summary()
        review = build_strategy_validation_forward_review(store=demo)
        runtime_state = runtime.state()
        risk_state = risk.state()
        return {
            "version": "strategy_validation_demo_v2",
            "campaignId": current_campaign,
            "screening": screening,
            "releaseSummary": {
                "imported": len(rows),
                "waitingApproval": sum(1 for row in rows if not row["approved"]),
                "approved": sum(1 for row in rows if row["approved"]),
                "maximumPerCampaign": 3,
            },
            "releases": rows,
            "runtime": runtime_state,
            "risk": risk_state,
            "demoLedger": demo_summary,
            "forwardReview": review,
            "engineeringEvidenceIncluded": False,
            "shadowEvidenceIncluded": False,
            "legacyEvidenceIncluded": False,
            "localSimulationIncluded": False,
            "liveEnabled": False,
            "withdrawEnabled": False,
        }
    finally:
        risk.close()
        demo.close()
        runtime.close()
        approvals.close()
        releases.close()


def import_strategy_validation_campaign(payload: dict[str, Any]) -> dict[str, Any]:
    campaign_id = str(payload.get("campaignId") or "")
    releases = StrategyValidationReleaseStore()
    try:
        return StrategyValidationReleaseService(releases).import_campaign(campaign_id)
    finally:
        releases.close()


def run_strategy_validation_approval_action(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    releases = StrategyValidationReleaseStore()
    approvals = StrategyValidationApprovalStore(release_store=releases)
    try:
        if action == "approve":
            return approve_strategy_validation_release(payload, approvals)
        if action == "revoke":
            return revoke_strategy_validation_release(payload, approvals)
        raise ValueError("unsupported approval action")
    finally:
        approvals.close()
        releases.close()


def run_strategy_validation_runtime_action(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    releases = StrategyValidationReleaseStore()
    approvals = StrategyValidationApprovalStore(release_store=releases)
    runtime = StrategyValidationRuntimeAdmission(release_store=releases, approval_store=approvals)
    try:
        reason = str(payload.get("reason") or "")
        if action == "arm":
            return runtime.arm(reason=reason, actor="human_local_operator")
        if action == "disarm":
            return runtime.disarm(reason=reason, actor="human_local_operator")
        raise ValueError("unsupported Runtime action")
    finally:
        runtime.close()
        approvals.close()
        releases.close()


def resume_strategy_validation_risk(payload: dict[str, Any]) -> dict[str, Any]:
    risk = StrategyValidationRiskStore()
    try:
        return risk.manual_resume(
            reason=str(payload.get("reason") or ""), actor="human_local_operator"
        )
    finally:
        risk.close()
