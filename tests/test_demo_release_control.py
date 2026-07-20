from __future__ import annotations

import json
from pathlib import Path

import pytest

from alphapilot_control_console.demo_release_control import DemoReleaseControlStore
from alphapilot_control_console.strategy_validation_hashing import stable_hash


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(root: Path) -> tuple[dict, dict, dict]:
    release = {
        "schemaVersion": "provisional_research_demo_v1",
        "releaseId": "release-1",
        "releaseHash": "release-hash-1",
        "riskOverlayHash": "risk-hash-1",
        "executionIntersectionHash": "intersection-hash-1",
        "dynamicUniversePolicyHash": "policy-hash-1",
        "route": "blocked_waiting_exact_release_approval",
        "approvalRequired": True,
        "approved": False,
        "demoArm": False,
        "formalPass": False,
        "cleanHistoricalOosPass": False,
        "livePromotionEligible": False,
        "automaticLivePromotionAllowed": False,
        "snapshotBindingMode": "policy_bound_daily_snapshot",
    }
    request = {
        "schemaVersion": "provisional_demo_exact_release_approval_request_v1",
        "releaseId": release["releaseId"],
        "releaseHash": release["releaseHash"],
        "riskOverlayHash": release["riskOverlayHash"],
        "executionIntersectionHash": release["executionIntersectionHash"],
        "engineeringSmokeEvidenceHash": "smoke-evidence-hash-1",
        "engineeringSmokeContractHash": "smoke-contract-hash-1",
        "approvalRequestHash": "not-used",
        "requestHash": "",
        "requestType": "exact_provisional_research_demo_release_approval",
        "approvalGranted": False,
        "approved": False,
        "demoArm": False,
        "route": "blocked_waiting_exact_release_approval",
        "status": "blocked_waiting_exact_release_approval",
        "generatedAt": "2026-07-21T00:00:00Z",
    }
    request["requestHash"] = stable_hash(
        {key: value for key, value in request.items() if key != "requestHash"},
        "exact_release_approval_request",
    )
    smoke = {
        "status": "passed",
        "engineeringSmokeReady": True,
        "unknownStateCount": 0,
        "orphanOrderCount": 0,
        "orphanPositionCount": 0,
    }
    _write(root / "release.json", release)
    _write(root / "request.json", request)
    _write(root / "smoke.json", smoke)
    return release, request, smoke


def _approval_payload(release: dict, request: dict) -> dict:
    return {
        "releaseId": release["releaseId"],
        "releaseHash": release["releaseHash"],
        "riskOverlayHash": release["riskOverlayHash"],
        "executionIntersectionHash": release["executionIntersectionHash"],
        "engineeringSmokeEvidenceHash": request["engineeringSmokeEvidenceHash"],
        "engineeringSmokeContractHash": request["engineeringSmokeContractHash"],
        "approvalRequestHash": request["requestHash"],
        "operatorIdentity": "human_local_operator",
        "approvedAt": "2026-07-21T01:00:00Z",
    }


def _store(root: Path) -> DemoReleaseControlStore:
    return DemoReleaseControlStore(
        database_path=root / "control.sqlite",
        release_path=root / "release.json",
        approval_request_path=root / "request.json",
        engineering_smoke_path=root / "smoke.json",
        audit_dir=root / "audit",
    )


@pytest.mark.parametrize(
    "field",
    [
        "releaseId",
        "releaseHash",
        "riskOverlayHash",
        "executionIntersectionHash",
        "engineeringSmokeEvidenceHash",
        "engineeringSmokeContractHash",
        "approvalRequestHash",
    ],
)
def test_approval_rejects_every_exact_identity_mismatch(tmp_path: Path, field: str) -> None:
    release, request, _ = _fixture(tmp_path)
    store = _store(tmp_path)
    payload = _approval_payload(release, request)
    payload[field] = "wrong"

    with pytest.raises(PermissionError, match="exact approval identity mismatch"):
        store.approve(payload)

    assert store.approval_actions() == []
    store.close()


def test_approval_is_append_only_idempotent_and_never_arms(tmp_path: Path) -> None:
    release, request, _ = _fixture(tmp_path)
    store = _store(tmp_path)
    payload = _approval_payload(release, request)

    first = store.approve(payload)
    second = store.approve(payload)

    assert first["status"] == "approved_not_armed"
    assert first["approved"] is True
    assert first["demoArm"] is False
    assert second["recordHash"] == first["recordHash"]
    assert len(store.approval_actions()) == 1
    assert store.arm_actions() == []
    overlay = json.loads((tmp_path / "audit" / "demo_approval_overlay.json").read_text())
    assert overlay["approved"] is True
    assert overlay["demoArm"] is False
    store.close()


def _ready(release: dict) -> dict:
    return {
        "engineeringSmokeReady": True,
        "currentSnapshotPolicyHash": release["dynamicUniversePolicyHash"],
        "authenticatedDemoUniverseCount": 82,
        "unknownStateCount": 0,
        "orphanOrderCount": 0,
        "orphanPositionCount": 0,
        "killSwitchInactive": True,
        "credentialsReady": True,
        "riskBlockers": [],
    }


def test_arm_requires_approval_and_all_runtime_gates(tmp_path: Path) -> None:
    release, request, _ = _fixture(tmp_path)
    store = _store(tmp_path)
    exact = _approval_payload(release, request)

    with pytest.raises(PermissionError, match="exact release approval required"):
        store.arm(exact, readiness=_ready(release), runtime_arm=lambda: {"ok": True})

    store.approve(exact)
    for field, value in (
        ("credentialsReady", False),
        ("authenticatedDemoUniverseCount", 0),
        ("killSwitchInactive", False),
        ("unknownStateCount", 1),
    ):
        readiness = _ready(release)
        readiness[field] = value
        with pytest.raises(PermissionError, match="Demo ARM blocked"):
            store.arm(exact, readiness=readiness, runtime_arm=lambda: {"ok": True})

    stale = _ready(release)
    stale["currentSnapshotPolicyHash"] = "stale-policy"
    with pytest.raises(PermissionError, match="Demo ARM blocked"):
        store.arm(exact, readiness=stale, runtime_arm=lambda: {"ok": True})
    store.close()


def test_approved_release_can_arm_and_disarm_as_separate_append_only_actions(
    tmp_path: Path,
) -> None:
    release, request, _ = _fixture(tmp_path)
    store = _store(tmp_path)
    exact = _approval_payload(release, request)
    store.approve(exact)
    calls: list[str] = []

    armed = store.arm(
        exact,
        readiness=_ready(release),
        runtime_arm=lambda: calls.append("arm") or {"ok": True, "armedForCurrentProcess": True},
    )
    disarmed = store.disarm(
        exact,
        runtime_disarm=lambda: calls.append("disarm") or {"ok": True, "armedForCurrentProcess": False},
    )

    assert calls == ["arm", "disarm"]
    assert armed["status"] == "armed"
    assert disarmed["status"] == "disarmed"
    assert [row["action"] for row in store.arm_actions()] == ["arm", "disarm"]
    audit = json.loads((tmp_path / "audit" / "demo_arm_audit.json").read_text())
    assert audit["status"] == "disarmed"
    assert audit["approvalRecordHash"] == store.approval_state()["recordHash"]
    store.close()
