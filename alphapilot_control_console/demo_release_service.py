"""Application service for the exact TOP200 Demo Release approval boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .config import DATA_DIR
from .credential_runtime import runtime_credential_status
from .demo_release_control import DemoReleaseControlStore
from .evolution_demo_service import build_evolution_demo_status
from .unified_auto_execution_runner import (
    arm_approved_demo_runtime,
    disarm_approved_demo_runtime,
)


RELEASE_ROOT = DATA_DIR / "v54_v60" / "release"
CONTROL_ROOT = DATA_DIR / "v54_v60" / "control"
CONTROL_AUDIT_ROOT = CONTROL_ROOT / "audit"
FINAL_RELEASE_PATH = RELEASE_ROOT / "final_superseding_provisional_release.json"
FINAL_APPROVAL_REQUEST_PATH = RELEASE_ROOT / "final_demo_approval_request.json"
ENGINEERING_SMOKE_PATH = (
    DATA_DIR / "top200_minimal_ui" / "engineering_smoke_final_self_check.json"
)
TOP200_SNAPSHOT_PATH = (
    DATA_DIR / "top200_minimal_ui" / "initial_top200_demo_universe_snapshot.json"
)
TOP200_READINESS_PATH = (
    DATA_DIR / "top200_minimal_ui" / "top200_universe_readiness_audit.json"
)
CONTROL_DATABASE_PATH = CONTROL_ROOT / "demo_release_control.sqlite"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _store() -> DemoReleaseControlStore:
    return DemoReleaseControlStore(
        database_path=CONTROL_DATABASE_PATH,
        release_path=FINAL_RELEASE_PATH,
        approval_request_path=FINAL_APPROVAL_REQUEST_PATH,
        engineering_smoke_path=ENGINEERING_SMOKE_PATH,
        audit_dir=CONTROL_AUDIT_ROOT,
    )


def _verify_route_release_id(release_id: str) -> dict[str, Any]:
    release = _load(FINAL_RELEASE_PATH)
    if release_id != release.get("releaseId"):
        raise PermissionError("route releaseId does not match the final Demo Release")
    return release


def approve_final_demo_release(
    release_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    _verify_route_release_id(release_id)
    store = _store()
    try:
        approval = store.approve(payload)
    finally:
        store.close()
    return {"ok": True, **approval}


def _runtime_readiness(release: Mapping[str, Any]) -> dict[str, Any]:
    smoke = _load(ENGINEERING_SMOKE_PATH)
    snapshot = _load(TOP200_SNAPSHOT_PATH)
    universe = _load(TOP200_READINESS_PATH)
    runtime = build_evolution_demo_status()
    summary = runtime.get("summary") if isinstance(runtime.get("summary"), dict) else {}
    known = {
        "okx_demo_credentials_missing",
        "demo_kill_switch_active",
        "no_eligible_demo_release",
    }
    runtime_blockers = [
        str(value)
        for value in runtime.get("blockers") or []
        if str(value) and str(value) not in known
    ]
    return {
        "engineeringSmokeReady": bool(smoke.get("engineeringSmokeReady"))
        and smoke.get("status") == "passed",
        "currentSnapshotPolicyHash": snapshot.get("policyHash"),
        "authenticatedDemoUniverseCount": int(
            universe.get("authenticatedInstrumentCount") or 0
        ),
        "unknownStateCount": int(smoke.get("unknownStateCount") or 0),
        "orphanOrderCount": int(smoke.get("orphanOrderCount") or 0),
        "orphanPositionCount": int(smoke.get("orphanPositionCount") or 0),
        "killSwitchInactive": not bool(summary.get("killSwitch")),
        "credentialsReady": bool(runtime_credential_status().get("allConfigured")),
        "riskBlockers": runtime_blockers,
        "releasePolicyHash": release.get("dynamicUniversePolicyHash"),
    }


def arm_final_demo_release(
    release_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    release = _verify_route_release_id(release_id)
    store = _store()
    try:
        arm = store.arm(
            payload,
            readiness=_runtime_readiness(release),
            runtime_arm=arm_approved_demo_runtime,
        )
    finally:
        store.close()
    return {"ok": True, "approved": True, "demoArm": True, **arm}


def disarm_final_demo_release(
    release_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    _verify_route_release_id(release_id)
    store = _store()
    try:
        arm = store.disarm(
            payload,
            runtime_disarm=disarm_approved_demo_runtime,
        )
    finally:
        store.close()
    return {"ok": True, "approved": True, "demoArm": False, **arm}
