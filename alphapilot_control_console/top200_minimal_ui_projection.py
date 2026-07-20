from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path
from typing import Any

from .config import DATA_DIR


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

    def __init__(self, evidence_root: Path) -> None:
        self.evidence_root = Path(evidence_root)

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

    def _release(self) -> dict[str, Any]:
        return self._load("superseding_provisional_release.json")

    def _approval(self) -> dict[str, Any]:
        return self._load("superseding_demo_approval_request.json")

    def _snapshot(self) -> dict[str, Any]:
        return self._load("initial_top200_demo_universe_snapshot.json")

    def _smoke(self) -> dict[str, Any]:
        return self._load("engineering_smoke_final_self_check.json")

    def research_factory_summary(self) -> dict[str, Any]:
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
        return {"runs": [self.research_factory_summary()], "readOnly": True}

    def research_factory_run(self, research_run_id: str) -> dict[str, Any]:
        if research_run_id != self.RESEARCH_RUN_ID:
            raise KeyError(research_run_id)
        return self.research_factory_summary()

    def strategy_summary(self) -> dict[str, Any]:
        release = self._release()
        approval = self._approval()
        result_counts = {key: 0 for key in self.RESULT_CLASSES}
        result_counts["canEnterDemo"] = 1
        return {
            "componentStrategyCount": len(release.get("componentIds") or []),
            "portfolioCandidateCount": 1,
            "formalPassCount": int(bool(release.get("formalPass"))),
            "resultCounts": result_counts,
            "releaseReadyCount": 1,
            "approvedReleaseCount": int(bool(approval.get("approved"))),
            "armedReleaseCount": int(bool(approval.get("demoArm"))),
            "strategyOrderCount": int(approval.get("strategyOrderCount") or 0),
            "approved": bool(approval.get("approved")),
            "demoArm": bool(approval.get("demoArm")),
            "route": approval.get("route"),
            "updatedAt": release.get("generatedAt"),
            "readOnly": True,
        }

    def _current_release_projection(self) -> dict[str, Any]:
        release = self._release()
        approval = self._approval()
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
            "riskOverlayHash": release.get("riskOverlayHash"),
            "generatedAt": release.get("generatedAt"),
            "supersedesReleaseId": release.get("supersedesReleaseId"),
            "supersedesReleaseHash": release.get("supersedesReleaseHash"),
        }

    def strategy_releases(self) -> dict[str, Any]:
        old = self._load("old_release_supersession_overlay.json")
        historical = {
            "releaseId": old.get("oldReleaseId"),
            "releaseHash": old.get("oldReleaseHash"),
            "status": old.get("status") or "superseded_unapproved",
            "approved": bool(old.get("oldApproved")),
            "demoArm": bool(old.get("oldDemoArm")),
            "readOnly": True,
        }
        return {
            "releases": [self._current_release_projection(), historical],
            "activeReleaseCount": 1,
            "readOnly": True,
        }

    def strategy_release(self, release_id: str) -> dict[str, Any]:
        current = self._current_release_projection()
        if release_id == current["releaseId"]:
            return current
        for release in self.strategy_releases()["releases"]:
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
        approval = self._approval()
        smoke = self._smoke()
        reconciliation = self._load("engineering_smoke_rest_reconciliation_audit.json")
        smoke_passed = smoke.get("status") == "passed" and bool(
            smoke.get("engineeringSmokeReady")
        )
        return {
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
            "updatedAt": release.get("generatedAt"),
            "readOnly": True,
        }

    def demo_strategies(self) -> dict[str, Any]:
        release = self._current_release_projection()
        return {
            "strategies": [
                {
                    "releaseId": release["releaseId"],
                    "releaseHash": release["releaseHash"],
                    "name": release["name"],
                    "status": "waiting_approval",
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
        return {
            "positions": [],
            "openPositionCount": 0,
            "source": "strategy_position_ledger",
            "engineeringSmokeExcluded": True,
            "readOnly": True,
        }

    def demo_orders(self) -> dict[str, Any]:
        return {
            "orders": [],
            "strategyOrderCount": 0,
            "source": "strategy_order_ledger",
            "engineeringSmokeExcluded": True,
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


def build_top200_minimal_ui_projection() -> Top200MinimalUiProjection:
    configured = os.environ.get("ALPHAPILOT_TOP200_MINIMAL_UI_EVIDENCE_ROOT")
    root = Path(configured).expanduser().resolve() if configured else DEFAULT_TOP200_MINIMAL_UI_EVIDENCE_ROOT
    return Top200MinimalUiProjection(root)


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
