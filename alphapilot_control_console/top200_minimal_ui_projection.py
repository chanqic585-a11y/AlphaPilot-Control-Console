from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path
from typing import Any

from .config import DATA_DIR, PROJECT_ROOT
from .strategy_factory_orchestrator import (
    DEFAULT_ARTIFACT_ROOT as DEFAULT_STRATEGY_FACTORY_ARTIFACT_ROOT,
    DEFAULT_STATE_PATH as DEFAULT_STRATEGY_FACTORY_STATE_PATH,
    StrategyFactoryOrchestrator,
)
from .trading_terminal_projection import TradingTerminalProjection


DEFAULT_TOP200_MINIMAL_UI_EVIDENCE_ROOT = DATA_DIR / "top200_minimal_ui"


class ProjectionEvidenceError(RuntimeError):
    pass


class Top200MinimalUiProjection:
    RESEARCH_RUN_ID = "top200_minimal_ui_20260720"
    RESULT_CLASSES = (
        "canEnterDemo",
        "needsForwardValidation",
        "failed",
        "dataInsufficient",
        "systemIssue",
    )

    def __init__(
        self,
        evidence_root: Path,
        matchability_root: Path | None = None,
        *,
        release_root: Path | None = None,
        control_audit_root: Path | None = None,
        strategy_factory_state_path: Path | None = None,
        strategy_factory_artifact_root: Path | None = None,
        strategy_factory_quant_root: Path | None = None,
        live_readiness_root: Path | None = None,
        adaptive_governance_root: Path | None = None,
        terminal_projection: TradingTerminalProjection | None = None,
        current_pilot_path: Path | None = None,
    ) -> None:
        self.evidence_root = Path(evidence_root)
        self.matchability_root = (
            Path(matchability_root) if matchability_root is not None else self.evidence_root
        )
        self.release_root = Path(release_root) if release_root is not None else None
        self.control_audit_root = (
            Path(control_audit_root) if control_audit_root is not None else None
        )
        self.strategy_factory_state_path = (
            Path(strategy_factory_state_path)
            if strategy_factory_state_path is not None
            else None
        )
        self.strategy_factory_artifact_root = (
            Path(strategy_factory_artifact_root)
            if strategy_factory_artifact_root is not None
            else DEFAULT_STRATEGY_FACTORY_ARTIFACT_ROOT
        )
        self.strategy_factory_quant_root = (
            Path(strategy_factory_quant_root)
            if strategy_factory_quant_root is not None
            else None
        )
        self.live_readiness_root = (
            Path(live_readiness_root) if live_readiness_root is not None else None
        )
        self.adaptive_governance_root = (
            Path(adaptive_governance_root)
            if adaptive_governance_root is not None
            else None
        )
        self.terminal_projection = terminal_projection
        self.current_pilot_path = (
            Path(current_pilot_path) if current_pilot_path is not None else None
        )

    @staticmethod
    def _terminal_connection_status(summary: dict[str, Any]) -> str:
        if summary.get("lastError"):
            return "runtime_error"
        if summary.get("desiredEnabled") and summary.get("armed"):
            return "connected_armed"
        if summary.get("desiredEnabled"):
            return "waiting_for_arm"
        return str(summary.get("runtimeStatus") or "offline")

    def _load(self, name: str) -> dict[str, Any]:
        path = self.evidence_root / name
        if not path.is_file():
            raise ProjectionEvidenceError(f"missing projection evidence: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ProjectionEvidenceError(f"invalid projection evidence: {path}") from error
        if not isinstance(payload, dict):
            raise ProjectionEvidenceError(f"projection evidence must be an object: {path}")
        return payload

    def _load_matchability(self, name: str) -> dict[str, Any] | None:
        path = self.matchability_root / name
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _load_live(self, name: str) -> dict[str, Any]:
        payload = self._load_optional(self.live_readiness_root, name)
        if payload is None:
            raise ProjectionEvidenceError(
                f"missing Live readiness evidence: {self.live_readiness_root / name if self.live_readiness_root else name}"
            )
        return payload

    @staticmethod
    def _load_optional(root: Path | None, name: str) -> dict[str, Any] | None:
        if root is None:
            return None
        path = root / name
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _release(self) -> dict[str, Any]:
        return self._load_optional(
            self.release_root,
            "final_superseding_provisional_release.json",
        ) or self._load("superseding_provisional_release.json")

    def _approval(self) -> dict[str, Any]:
        release = self._release()
        approval = dict(
            self._load_optional(self.release_root, "final_demo_approval_request.json")
            or self._load("superseding_demo_approval_request.json")
        )
        overlay = self._load_optional(
            self.control_audit_root,
            "demo_approval_overlay.json",
        )
        if overlay and all(
            overlay.get(field) == release.get(field)
            for field in ("releaseId", "releaseHash")
        ):
            approval.update(overlay)
            if overlay.get("approved") and not overlay.get("demoArm"):
                approval["route"] = (
                    overlay.get("route")
                    or overlay.get("status")
                    or "approved_not_armed"
                )
        arm = self._load_optional(self.control_audit_root, "demo_arm_audit.json")
        if arm and all(
            arm.get(field) == release.get(field)
            for field in ("releaseId", "releaseHash")
        ):
            armed = arm.get("action") == "arm" and arm.get("status") == "armed"
            approval["demoArm"] = armed
            approval["route"] = "armed" if armed else "approved_not_armed"
        return approval

    def _approval_with_current_demo_runtime(self) -> dict[str, Any]:
        approval = self._approval()
        if self.terminal_projection is None:
            return approval
        terminal = self.terminal_projection.summary("okx_demo")
        armed = bool(terminal.get("armed")) and bool(approval.get("approved"))
        approval["demoArm"] = armed
        approval["strategyOrderCount"] = int(
            terminal.get("strategyOrderCount") or 0
        )
        approval["runtimeUpdatedAt"] = terminal.get("updatedAt")
        if approval.get("approved"):
            approval["route"] = "armed" if armed else "approved_not_armed"
        return approval

    def _snapshot(self) -> dict[str, Any]:
        return self._load("initial_top200_demo_universe_snapshot.json")

    def _smoke(self) -> dict[str, Any]:
        return self._load("engineering_smoke_final_self_check.json")

    def _read_strategy_factory(self, method: str, *args: object) -> Any | None:
        state_path = self.strategy_factory_state_path
        if state_path is None or not state_path.is_file():
            return None
        factory = StrategyFactoryOrchestrator(
            state_path=state_path,
            artifact_root=self.strategy_factory_artifact_root,
            quant_root=self.strategy_factory_quant_root,
        )
        try:
            return getattr(factory, method)(*args)
        finally:
            factory.close()

    def research_factory_summary(self) -> dict[str, Any]:
        persisted = self._read_strategy_factory("summary")
        if persisted and persisted.get("researchRunId"):
            return persisted
        release = self._release()
        snapshot = self._snapshot()
        return {
            "researchRunId": self.RESEARCH_RUN_ID,
            "mode": "portfolio_supersession",
            "stage": "release_ready",
            "stageIndex": 6,
            "stageCount": 7,
            "completedCount": 6,
            "totalCount": 7,
            "progressPercent": 86,
            "currentCandidate": release.get("releaseId"),
            "startedAt": snapshot.get("generatedAt"),
            "updatedAt": release.get("generatedAt"),
            "status": "waiting_exact_release_approval",
            "primaryBlocker": release.get("route"),
            "nextAction": "review_exact_release",
            "resultClass": "can_enter_demo",
            "readOnly": True,
            "source": "frozen_top200_artifacts",
        }

    def research_factory_runs(self) -> dict[str, Any]:
        self._read_strategy_factory("summary")
        persisted = self._read_strategy_factory("list_runs", 20)
        if persisted:
            return {"runs": persisted, "readOnly": False}
        return {"runs": [self.research_factory_summary()], "readOnly": True}

    def research_factory_run(self, research_run_id: str) -> dict[str, Any]:
        try:
            persisted = self._read_strategy_factory("refresh_run", research_run_id)
        except KeyError:
            persisted = None
        if persisted:
            return persisted
        if research_run_id != self.RESEARCH_RUN_ID:
            raise KeyError(research_run_id)
        return self.research_factory_summary()

    def _strategy_factory_outcomes(self) -> dict[str, Any]:
        runs = self._read_strategy_factory("list_runs", 100) or []
        requests = self._read_strategy_factory("list_candidate_review_requests", 500) or []
        counts = {key: 0 for key in self.RESULT_CLASSES}
        archived_failure_count = 0
        updated_at = None
        for run in runs:
            updated = run.get("updatedAt")
            if updated and (updated_at is None or str(updated) > str(updated_at)):
                updated_at = updated
            result_class = str(run.get("resultClass") or "")
            if not result_class:
                continue
            review_count = int(run.get("candidateReviewRequestCount") or 0)
            archived_count = int(run.get("archivedFailureCount") or 0)
            archived_failure_count += archived_count
            if result_class == "can_enter_demo":
                counts["canEnterDemo"] += review_count
                counts["failed"] += archived_count
            elif result_class == "needs_forward_validation":
                counts["needsForwardValidation"] += max(
                    review_count,
                    int(run.get("survivorCount") or 0),
                )
                counts["failed"] += archived_count
            elif result_class == "data_insufficient":
                counts["dataInsufficient"] += max(
                    archived_count,
                    int(run.get("maxCandidateCount") or 0),
                    1,
                )
            elif result_class == "system_issue":
                counts["systemIssue"] += max(
                    archived_count,
                    int(run.get("maxCandidateCount") or 0),
                    1,
                )
            elif result_class == "failed":
                counts["failed"] += max(
                    archived_count,
                    int(run.get("maxCandidateCount") or 0),
                    1,
                )
        review_projections = [
            {
                "candidateReviewId": request.get("requestHash"),
                "candidateId": request.get("candidateId"),
                "strategyId": request.get("candidateId"),
                "displayName": request.get("candidateId"),
                "releaseId": request.get("candidateId"),
                "releaseHash": request.get("immutableReleaseHash"),
                "immutableResearchCandidateHash": request.get("immutableReleaseHash"),
                "runId": request.get("runId"),
                "campaignId": request.get("campaignId"),
                "timeframe": request.get("timeframe"),
                "status": "pending_human_review",
                "resultClass": "can_enter_demo",
                "approvalRequestActionable": bool(request.get("approvalRequestActionable")),
                "automaticApprovalAllowed": False,
                "approved": False,
                "demoArm": False,
                "strategyOrderCount": 0,
                "orderCount": 0,
                "createdAt": request.get("createdAt"),
                "readOnly": True,
                "source": "strategy_factory_candidate_review_ledger",
            }
            for request in requests
        ]
        return {
            "resultCounts": counts,
            "pendingCandidateReviewCount": len(review_projections),
            "archivedFailureCount": archived_failure_count,
            "candidateReviews": review_projections,
            "updatedAt": updated_at,
        }

    def _current_pilot_projection(self) -> dict[str, Any] | None:
        path = self.current_pilot_path
        if path is None or not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("authority") != "current_v62_4_acceptance_pilot":
            return None
        return {
            "schemaVersion": payload.get("schemaVersion"),
            "authority": payload.get("authority"),
            "campaignId": payload.get("campaignId"),
            "status": payload.get("status"),
            "candidateCount": int(payload.get("candidateCount") or 0),
            "trialCount": int(payload.get("trialCount") or 0),
            "stableSelectionCount": int(payload.get("stableSelectionCount") or 0),
            "formalReadyCandidateCount": int(
                payload.get("formalReadyCandidateCount") or 0
            ),
            "formalBlockedCandidateCount": int(
                payload.get("formalBlockedCandidateCount") or 0
            ),
            "formalRunCount": int(payload.get("formalRunCount") or 0),
            "resultReadCount": int(payload.get("resultReadCount") or 0),
            "formalReadyCandidateIds": list(
                payload.get("formalReadyCandidateIds") or []
            ),
            "formalBlockedCandidateIds": list(
                payload.get("formalBlockedCandidateIds") or []
            ),
            "sourceHashes": dict(payload.get("sourceHashes") or {}),
            "readOnly": True,
        }

    def strategy_summary(self) -> dict[str, Any]:
        release = self._release()
        approval = self._approval_with_current_demo_runtime()
        factory = self._strategy_factory_outcomes()
        result_counts = {key: 0 for key in self.RESULT_CLASSES}
        result_counts["canEnterDemo"] = 1
        for key, count in factory["resultCounts"].items():
            result_counts[key] += int(count)
        return {
            "componentStrategyCount": len(release.get("componentIds") or []),
            "portfolioCandidateCount": 1 + sum(factory["resultCounts"].values()),
            "formalPassCount": int(bool(release.get("formalPass"))),
            "resultCounts": result_counts,
            "releaseReadyCount": 1 + int(factory["pendingCandidateReviewCount"]),
            "pendingCandidateReviewCount": factory["pendingCandidateReviewCount"],
            "archivedFailureCount": factory["archivedFailureCount"],
            "approvedReleaseCount": int(bool(approval.get("approved"))),
            "armedReleaseCount": int(bool(approval.get("demoArm"))),
            "strategyOrderCount": int(approval.get("strategyOrderCount") or 0),
            "approved": bool(approval.get("approved")),
            "demoArm": bool(approval.get("demoArm")),
            "route": approval.get("route"),
            "currentPilot": self._current_pilot_projection(),
            "updatedAt": (
                approval.get("runtimeUpdatedAt")
                or factory["updatedAt"]
                or release.get("generatedAt")
            ),
            "readOnly": True,
        }

    def _current_release_projection(self) -> dict[str, Any]:
        release = self._release()
        approval = self._approval_with_current_demo_runtime()
        return {
            "releaseId": release.get("releaseId"),
            "releaseHash": release.get("releaseHash"),
            "name": "V46 三机制 TOP200 组合",
            "type": "portfolio",
            "status": "can_enter_demo",
            "statusLabel": "可进入 Demo",
            "primaryAction": "查看并批准",
            "route": approval.get("route"),
            "approved": bool(approval.get("approved")),
            "demoArm": bool(approval.get("demoArm")),
            "formalPass": bool(release.get("formalPass")),
            "componentIds": list(release.get("componentIds") or []),
            "actualInstrumentCount": int(release.get("actualInstrumentCount") or 0),
            "maximumInstrumentCount": int(release.get("maximumInstrumentCount") or 0),
            "universePolicyId": release.get("dynamicUniversePolicyId"),
            "universePolicyHash": release.get("dynamicUniversePolicyHash"),
            "universeSnapshotHash": release.get("dynamicUniverseSnapshotHash"),
            "snapshotBindingMode": release.get("snapshotBindingMode"),
            "activationSnapshotHash": release.get("activationSnapshotHash"),
            "riskOverlayHash": release.get("riskOverlayHash"),
            "generatedAt": release.get("generatedAt"),
            "supersedesReleaseId": release.get("supersedesReleaseId"),
            "supersedesReleaseHash": release.get("supersedesReleaseHash"),
            "evidenceRole": "current_demo_release",
        }

    def strategy_releases(self) -> dict[str, Any]:
        factory = self._strategy_factory_outcomes()
        old = self._load("old_release_supersession_overlay.json")
        historical = {
            "releaseId": old.get("oldReleaseId"),
            "releaseHash": old.get("oldReleaseHash"),
            "name": "V46 历史 Release",
            "type": "historical",
            "status": old.get("status") or "superseded_unapproved",
            "statusLabel": "已被新版替代",
            "primaryAction": "查看审计",
            "approved": bool(old.get("oldApproved")),
            "demoArm": bool(old.get("oldDemoArm")),
            "readOnly": True,
        }
        return {
            "releases": [self._current_release_projection()],
            "historicalReleases": [historical],
            "candidateReviews": factory["candidateReviews"],
            "candidateReviewCount": factory["pendingCandidateReviewCount"],
            "activeReleaseCount": 1,
            "readOnly": True,
        }

    def strategy_release(self, release_id: str) -> dict[str, Any]:
        current = self._current_release_projection()
        if release_id == current["releaseId"]:
            return current
        projected = self.strategy_releases()
        for release in [
            *projected["releases"],
            *projected["historicalReleases"],
        ]:
            if release.get("releaseId") == release_id:
                return release
        raise KeyError(release_id)

    def forward_validation(self, release_id: str) -> dict[str, Any]:
        release = self.strategy_release(release_id)
        return {
            "releaseId": release.get("releaseId"),
            "status": "waiting_start",
            "startedAt": None,
            "closedTradeCount": 0,
            "targetClosedTradeCount": None,
            "runningDayCount": 0,
            "netPnl": None,
            "maximumDrawdown": None,
            "blocker": release.get("route"),
            "engineeringSmokeExcluded": True,
            "legacyExcluded": True,
            "shadowExcluded": True,
            "historicalBacktestExcluded": True,
            "readOnly": True,
        }

    def demo_summary(self) -> dict[str, Any]:
        release = self._release()
        approval = self._approval_with_current_demo_runtime()
        smoke = self._smoke()
        reconciliation = self._load("engineering_smoke_rest_reconciliation_audit.json")
        smoke_passed = smoke.get("status") == "passed" and bool(
            smoke.get("engineeringSmokeReady")
        )
        static_summary = {
            "connectionStatus": (
                "engineering_smoke_passed" if smoke_passed else "engineering_smoke_blocked"
            ),
            "equity": None,
            "todayPnl": None,
            "floatingPnl": None,
            "approvedStrategyCount": int(bool(approval.get("approved"))),
            "runningStrategyCount": int(
                bool(approval.get("approved")) and bool(approval.get("demoArm"))
            ),
            "openPositionCount": 0,
            "strategyOrderCount": int(approval.get("strategyOrderCount") or 0),
            "universeCount": int(release.get("actualInstrumentCount") or 0),
            "universeMaximum": int(release.get("maximumInstrumentCount") or 0),
            "route": approval.get("route"),
            "canRunApprovedStrategies": bool(
                approval.get("approved")
                and approval.get("demoArm")
                and smoke_passed
                and release.get("actualInstrumentCount")
            ),
            "issues": [
                {
                    "severity": "warning",
                    "code": "exact_release_approval_required",
                    "message": "TOP200 Release 已冻结，等待精确批准。",
                }
            ]
            if not approval.get("approved")
            else [],
            "engineeringSmoke": {
                "status": smoke.get("status"),
                "ready": bool(smoke.get("engineeringSmokeReady")),
                "duplicateOrderCount": int(smoke.get("duplicateOrderCount") or 0),
                "orphanOrderCount": int(smoke.get("orphanOrderCount") or 0),
                "orphanPositionCount": int(smoke.get("orphanPositionCount") or 0),
                "unknownStateCount": int(smoke.get("unknownStateCount") or 0),
                "recentFillCount": int(reconciliation.get("recentFillCount") or 0),
                "strategyEvidenceDelta": int(smoke.get("formalEvidenceDelta") or 0)
                + int(smoke.get("forwardEvidenceDelta") or 0),
                "strategyOrdersExcluded": True,
            },
            "matchability": self.demo_matchability(),
            "updatedAt": release.get("generatedAt"),
            "readOnly": True,
        }
        if self.terminal_projection is None:
            return static_summary
        terminal = self.terminal_projection.summary("okx_demo")
        return {
            **static_summary,
            **terminal,
            "connectionStatus": self._terminal_connection_status(terminal),
            "approvedStrategyCount": int(bool(approval.get("approved"))),
            "universeCount": int(release.get("actualInstrumentCount") or 0),
            "universeMaximum": int(release.get("maximumInstrumentCount") or 0),
            "route": approval.get("route"),
            "canRunApprovedStrategies": bool(
                approval.get("approved")
                and terminal.get("armed")
                and smoke_passed
                and release.get("actualInstrumentCount")
            ),
            "engineeringSmoke": static_summary["engineeringSmoke"],
            "matchability": static_summary["matchability"],
            "issues": [
                *static_summary["issues"],
                *list(terminal.get("issues") or []),
            ],
            "equitySource": terminal.get("source"),
            "releaseId": release.get("releaseId"),
            "releaseHash": release.get("releaseHash"),
            "riskOverlayHash": release.get("riskOverlayHash"),
            "readOnly": True,
        }

    def demo_matchability(self) -> dict[str, Any]:
        window_30d = self._load_matchability("signal_matchability_30d.json")
        window_90d = self._load_matchability("signal_matchability_90d.json")
        funnel = self._load_matchability("pre_arm_scan_funnel.json")
        if window_30d is None or window_90d is None or funnel is None:
            return {
                "status": "not_available",
                "releaseInstrumentCount": None,
                "compatibleComponentCount": None,
                "signalCount30d": None,
                "signalCount90d": None,
                "warningCount": 0,
            }
        return {
            "status": funnel.get("status"),
            "releaseInstrumentCount": int(funnel.get("releaseInstrumentCount") or 0),
            "compatibleComponentCount": int(
                funnel.get("compatibleComponentCount") or 0
            ),
            "signalCount30d": int(window_30d.get("signalCount") or 0),
            "signalCount90d": int(window_90d.get("signalCount") or 0),
            "warningCount": len(funnel.get("warnings") or []),
        }

    def demo_strategies(self) -> dict[str, Any]:
        if self.terminal_projection is not None:
            return self.terminal_projection.strategies("okx_demo")
        release = self._current_release_projection()
        if release["demoArm"]:
            status = "armed"
        elif release["approved"]:
            status = "approved_not_armed"
        else:
            status = "waiting_approval"
        return {
            "strategies": [
                {
                    "releaseId": release["releaseId"],
                    "releaseHash": release["releaseHash"],
                    "name": release["name"],
                    "status": status,
                    "timeframes": ["1h", "1d"],
                    "scanInstrumentCount": release["actualInstrumentCount"],
                    "latestScanAt": None,
                    "latestSignalAt": None,
                    "openPositionCount": 0,
                    "todayPnl": None,
                    "approved": release["approved"],
                    "demoArm": release["demoArm"],
                }
            ],
            "readOnly": True,
        }

    def demo_positions(self) -> dict[str, Any]:
        if self.terminal_projection is not None:
            return self.terminal_projection.positions("okx_demo")
        return {
            "positions": [],
            "openPositionCount": 0,
            "source": "strategy_position_ledger",
            "engineeringSmokeExcluded": True,
            "readOnly": True,
        }

    def demo_orders(self) -> dict[str, Any]:
        if self.terminal_projection is not None:
            return self.terminal_projection.orders("okx_demo")
        return {
            "orders": [],
            "strategyOrderCount": 0,
            "source": "strategy_order_ledger",
            "engineeringSmokeExcluded": True,
            "readOnly": True,
        }

    def live_summary(self) -> dict[str, Any]:
        if self.terminal_projection is not None:
            terminal = self.terminal_projection.summary("okx_live")
            return {
                **terminal,
                "connectionStatus": self._terminal_connection_status(terminal),
                "equitySource": terminal.get("source"),
                "readOnly": True,
            }
        return {
            "connectionStatus": "readiness_only",
            "equity": None,
            "availableBalance": None,
            "todayPnl": None,
            "floatingPnl": None,
            "openPositionCount": 0,
            "runningStrategyCount": 0,
            "strategyOrderCount": 0,
            "issues": [],
            "readOnly": True,
        }

    def live_strategies(self) -> dict[str, Any]:
        if self.terminal_projection is not None:
            return self.terminal_projection.strategies("okx_live")
        return {"environment": "okx_live", "strategies": [], "readOnly": True}

    def live_positions(self) -> dict[str, Any]:
        if self.terminal_projection is not None:
            return self.terminal_projection.positions("okx_live")
        return {
            "environment": "okx_live",
            "positions": [],
            "openPositionCount": 0,
            "readOnly": True,
        }

    def live_orders(self) -> dict[str, Any]:
        if self.terminal_projection is not None:
            return self.terminal_projection.orders("okx_live")
        return {
            "environment": "okx_live",
            "orders": [],
            "strategyOrderCount": 0,
            "readOnly": True,
        }

    def demo_universe(self) -> dict[str, Any]:
        snapshot = self._snapshot()
        readiness = self._load("top200_universe_readiness_audit.json")
        return {
            "policyId": snapshot.get("policyId"),
            "policyHash": snapshot.get("policyHash"),
            "snapshotHash": snapshot.get("snapshotHash"),
            "utcDate": snapshot.get("utcDate"),
            "actualInstrumentCount": int(snapshot.get("actualInstrumentCount") or 0),
            "maximumInstrumentCount": int(snapshot.get("maximumInstrumentCount") or 0),
            "instrumentIds": list(snapshot.get("instrumentIds") or []),
            "rankedInstruments": list(snapshot.get("rankedInstruments") or []),
            "funnel": {
                "publicInstrumentCount": int(readiness.get("publicInstrumentCount") or 0),
                "authenticatedDemoInstrumentCount": int(
                    readiness.get("authenticatedDemoInstrumentCount") or 0
                ),
                "eligibleInstrumentCount": int(readiness.get("eligibleInstrumentCount") or 0),
                "selectedInstrumentCount": int(readiness.get("selectedInstrumentCount") or 0),
                "collectionErrorCount": int(readiness.get("collectionErrorCount") or 0),
            },
            "status": snapshot.get("status"),
            "dailyFrozen": bool(snapshot.get("dailyFrozen")),
            "readOnly": True,
        }

    def demo_reconciliation(self) -> dict[str, Any]:
        smoke = self._smoke()
        reconciliation = self._load("engineering_smoke_rest_reconciliation_audit.json")
        return {
            "status": reconciliation.get("status"),
            "pendingOrderCount": int(reconciliation.get("pendingOrderCount") or 0),
            "nonzeroPositionCount": int(reconciliation.get("nonzeroPositionCount") or 0),
            "orphanPositionCount": int(reconciliation.get("orphanPositionCount") or 0),
            "unknownOrderCount": int(reconciliation.get("unknownOrderCount") or 0),
            "duplicateOrderCount": int(smoke.get("duplicateOrderCount") or 0),
            "strategyEvidenceDelta": int(smoke.get("formalEvidenceDelta") or 0)
            + int(smoke.get("forwardEvidenceDelta") or 0),
            "engineeringOnly": True,
            "readOnly": True,
        }

    def live_canary_readiness(self) -> dict[str, Any]:
        release = self._load_live("experimental_live_release.json")
        approval = self._load_live("exact_live_approval_request.json")
        adaptive = self._load_optional(
            self.adaptive_governance_root,
            "adaptive_learning_technical_readiness_gate.json",
        ) or self._load_live("adaptive_learning_live_readiness.json")
        smoke = self._load_live("live_engineering_smoke_binding.json")
        execution = self._load_live("live_execution_state.json")
        profile = self._load_live("live_experiment_profile.json")
        orders = self._load_live("live_order_ledger.json")
        fills = self._load_live("live_fill_ledger.json")
        positions = self._load_live("live_position_ledger.json")

        adaptive_passed = adaptive.get("passed") is True
        approval_completed = execution.get("approvalStatus") == "approved"
        arm_completed = execution.get("armStatus") == "armed"
        smoke_passed = smoke.get("status") == "completed_canceled_and_reconciled"
        issues: list[dict[str, str]] = []
        if not adaptive_passed:
            issues.append(
                {
                    "severity": "warning",
                    "code": "adaptive_learning_live_readiness_not_passed",
                    "message": "自适应学习实盘证据尚未完成，当前只能保留为实验性 Live 候选。",
                }
            )
        if not approval_completed:
            issues.append(
                {
                    "severity": "info",
                    "code": "exact_live_release_approval_not_run",
                    "message": "精确 Live Release 与风险覆盖尚未批准。",
                }
            )

        def ledger_projection(payload: dict[str, Any]) -> dict[str, Any]:
            records = payload.get("records")
            return {
                "status": payload.get("status") or "not_run",
                "count": len(records) if isinstance(records, list) else 0,
            }

        status = "ready_for_exact_approval" if adaptive_passed else "blocked_not_ready"
        if approval_completed and arm_completed:
            status = "armed"
        return {
            "status": status,
            "statusLabel": (
                "已 ARM" if status == "armed" else
                "待精确批准" if status == "ready_for_exact_approval" else
                "证据未就绪"
            ),
            "release": {
                "releaseId": release.get("releaseId"),
                "releaseHash": release.get("releaseHash"),
                "generatedAt": release.get("generatedAt"),
                "formalPass": bool(release.get("formalPass")),
                "productionQualified": bool(release.get("productionQualified")),
            },
            "risk": {
                "allocatedCapitalUSDT": profile.get("allocatedCapitalUSDT"),
                "maximumAcceptedLossUSDT": profile.get("maximumAcceptedLossUSDT"),
                "riskPerTradeUSDT": profile.get("riskPerTradeUSDT"),
                "maximumPortfolioOpenRiskUSDT": profile.get("maximumPortfolioOpenRiskUSDT"),
                "maximumConcurrentPositions": profile.get("maximumConcurrentPositions"),
                "maximumLeverage": profile.get("maximumLeverage"),
                "marginMode": profile.get("marginMode"),
                "scanTopN": profile.get("scanTopN"),
            },
            "engineeringSmoke": {
                "status": "passed" if smoke_passed else "blocked",
                "contractStatus": smoke.get("status"),
                "cancelConfirmed": bool((smoke.get("checks") or {}).get("cancelConfirmed")),
                "zeroOpenPositions": bool((smoke.get("checks") or {}).get("zeroOpenPositions")),
                "zeroOpenOrders": bool((smoke.get("checks") or {}).get("zeroOpenOrders")),
            },
            "adaptiveLearning": {
                "status": adaptive.get("status"),
                "passed": adaptive_passed,
                "modelMode": adaptive.get("modelMode"),
                "exactApprovalEvaluated": bool(
                    adaptive.get("exactApprovalEvaluated")
                ),
                "blockerCount": len(adaptive.get("blockers") or []),
                "blockers": list(adaptive.get("blockers") or []),
            },
            "execution": {
                "approvalStatus": execution.get("approvalStatus") or "not_run",
                "armStatus": execution.get("armStatus") or "not_run",
                "strategyOrderStatus": execution.get("strategyOrderStatus") or "not_run",
                "liveEnabled": bool(execution.get("liveEnabled")),
                "withdrawAllowed": bool(execution.get("withdrawAllowed")),
            },
            "orders": ledger_projection(orders),
            "fills": ledger_projection(fills),
            "positions": ledger_projection(positions),
            "latency": {"status": "not_run", "signalToOrderP95Ms": None},
            "nextAction": (
                "review_exact_live_release_approval"
                if adaptive_passed
                else "complete_adaptive_learning_readiness"
            ),
            "issues": issues,
            "audit": {
                "releaseHash": release.get("releaseHash"),
                "riskOverlayHash": release.get("riskOverlayHash"),
                "adaptiveLearningReadinessHash": release.get(
                    "adaptiveLearningReadinessHash"
                ),
                "approvalRequestHash": approval.get("approvalRequestHash"),
                "engineeringSmokeContractHash": smoke.get("contractHash"),
                "sourceDemoRelease": release.get("sourceDemoRelease"),
            },
            "readOnly": True,
        }


def build_top200_minimal_ui_projection() -> Top200MinimalUiProjection:
    configured = os.environ.get("ALPHAPILOT_TOP200_MINIMAL_UI_EVIDENCE_ROOT")
    root = Path(configured).expanduser().resolve() if configured else DEFAULT_TOP200_MINIMAL_UI_EVIDENCE_ROOT
    configured_matchability = os.environ.get("ALPHAPILOT_DEMO_MATCHABILITY_ROOT")
    matchability_root = (
        Path(configured_matchability).expanduser().resolve()
        if configured_matchability
        else DATA_DIR / "v54_v60" / "matchability"
    )
    release_root = DATA_DIR / "v54_v60" / "release"
    control_audit_root = DATA_DIR / "v54_v60" / "control" / "audit"
    live_readiness_root = (
        PROJECT_ROOT / "reports" / "v54_v60" / "v59_v60_live_canary_readiness"
    )
    adaptive_governance_parent = (
        PROJECT_ROOT / "reports" / "v60_1_adaptive_learning_governance"
    )
    adaptive_governance_root = next(
        (
            path
            for path in sorted(adaptive_governance_parent.glob("*"), reverse=True)
            if path.is_dir()
            and (path / "adaptive_learning_technical_readiness_gate.json").is_file()
        ),
        None,
    )
    configured_current_pilot = os.environ.get(
        "ALPHAPILOT_V62_4_CURRENT_PILOT_PATH"
    )
    default_current_pilot = (
        PROJECT_ROOT
        / "reports"
        / "v62_4_1_acceptance"
        / "current_pilot_projection.json"
    )
    current_pilot_path = (
        Path(configured_current_pilot).expanduser().resolve()
        if configured_current_pilot
        else default_current_pilot
    )
    return Top200MinimalUiProjection(
        root,
        matchability_root,
        release_root=(
            release_root
            if (release_root / "final_superseding_provisional_release.json").is_file()
            else None
        ),
        control_audit_root=control_audit_root,
        strategy_factory_state_path=DEFAULT_STRATEGY_FACTORY_STATE_PATH,
        strategy_factory_artifact_root=DEFAULT_STRATEGY_FACTORY_ARTIFACT_ROOT,
        live_readiness_root=(
            live_readiness_root
            if (live_readiness_root / "experimental_live_release.json").is_file()
            else None
        ),
        adaptive_governance_root=adaptive_governance_root,
        terminal_projection=TradingTerminalProjection(),
        current_pilot_path=(
            current_pilot_path if current_pilot_path.is_file() else None
        ),
    )


def _write_json_artifact(path: Path, payload: dict[str, Any]) -> str:
    body = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(body)
    temporary.replace(path)
    return sha256(body).hexdigest()


def write_top200_minimal_ui_projection_artifacts(
    projection: Top200MinimalUiProjection,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "research_factory_progress_projection.json": projection.research_factory_summary(),
        "strategy_summary_projection.json": {
            "summary": projection.strategy_summary(),
            "releases": projection.strategy_releases(),
        },
        "demo_summary_projection.json": {
            "summary": projection.demo_summary(),
            "strategies": projection.demo_strategies(),
            "positions": projection.demo_positions(),
            "orders": projection.demo_orders(),
            "reconciliation": projection.demo_reconciliation(),
        },
        "demo_scan_funnel_projection.json": projection.demo_universe(),
    }
    if projection.live_readiness_root is not None:
        payloads["live_canary_readiness_projection.json"] = (
            projection.live_canary_readiness()
        )
    artifacts = []
    for name, payload in payloads.items():
        path = output_dir / name
        artifacts.append(
            {
                "path": name,
                "sha256": _write_json_artifact(path, payload),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schemaVersion": "alphapilot_top200_minimal_ui_projection_manifest_v1",
        "artifactCount": len(artifacts),
        "artifacts": artifacts,
        "readOnlyProjection": True,
        "approved": False,
        "demoArm": False,
        "strategyOrderCount": 0,
        "route": projection.strategy_summary().get("route"),
    }
    _write_json_artifact(output_dir / "projection_artifact_manifest.json", manifest)
    return manifest
