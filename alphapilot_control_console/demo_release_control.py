"""Exact Demo Release approval and process ARM control with append-only audit."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from .strategy_validation_hashing import canonical_bytes, stable_hash


EXACT_FIELDS = (
    "releaseId",
    "releaseHash",
    "riskOverlayHash",
    "executionIntersectionHash",
    "engineeringSmokeEvidenceHash",
    "engineeringSmokeContractHash",
    "approvalRequestHash",
)
HUMAN_OPERATOR = "human_local_operator"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(canonical_bytes(payload) + b"\n")
    temporary.replace(path)


class DemoReleaseControlStore:
    def __init__(
        self,
        *,
        database_path: Path | str,
        release_path: Path | str,
        approval_request_path: Path | str,
        engineering_smoke_path: Path | str,
        audit_dir: Path | str,
    ) -> None:
        self.release_path = Path(release_path)
        self.approval_request_path = Path(approval_request_path)
        self.engineering_smoke_path = Path(engineering_smoke_path)
        self.audit_dir = Path(audit_dir)
        target = Path(database_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS DemoReleaseApprovalActions (
              recordHash TEXT PRIMARY KEY,
              releaseId TEXT NOT NULL,
              releaseHash TEXT NOT NULL,
              riskOverlayHash TEXT NOT NULL,
              executionIntersectionHash TEXT NOT NULL,
              engineeringSmokeEvidenceHash TEXT NOT NULL,
              engineeringSmokeContractHash TEXT NOT NULL,
              approvalRequestHash TEXT NOT NULL,
              operatorIdentity TEXT NOT NULL,
              approvedAt TEXT NOT NULL,
              status TEXT NOT NULL,
              payloadJson TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_demo_release_approval
              ON DemoReleaseApprovalActions(releaseId, approvedAt);
            CREATE TABLE IF NOT EXISTS DemoReleaseArmActions (
              recordHash TEXT PRIMARY KEY,
              releaseId TEXT NOT NULL,
              releaseHash TEXT NOT NULL,
              approvalRecordHash TEXT NOT NULL,
              action TEXT NOT NULL,
              status TEXT NOT NULL,
              createdAt TEXT NOT NULL,
              previousArmRecordHash TEXT,
              payloadJson TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_demo_release_arm
              ON DemoReleaseArmActions(releaseId, createdAt);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def _expected(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        release = _load(self.release_path)
        request = _load(self.approval_request_path)
        smoke = _load(self.engineering_smoke_path)
        expected_request_hash = stable_hash(
            {key: value for key, value in request.items() if key != "requestHash"},
            "exact_release_approval_request",
        )
        if request.get("requestHash") != expected_request_hash:
            raise PermissionError("exact approval request artifact hash is invalid")
        return release, request, smoke

    def _verify_exact(self, payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        release, request, smoke = self._expected()
        expected = {
            "releaseId": release.get("releaseId"),
            "releaseHash": release.get("releaseHash"),
            "riskOverlayHash": release.get("riskOverlayHash"),
            "executionIntersectionHash": release.get("executionIntersectionHash"),
            "engineeringSmokeEvidenceHash": request.get("engineeringSmokeEvidenceHash"),
            "engineeringSmokeContractHash": request.get("engineeringSmokeContractHash"),
            "approvalRequestHash": request.get("requestHash"),
        }
        mismatches = [field for field in EXACT_FIELDS if payload.get(field) != expected[field]]
        if mismatches:
            raise PermissionError(
                "exact approval identity mismatch: " + ", ".join(mismatches)
            )
        if payload.get("operatorIdentity") != HUMAN_OPERATOR:
            raise PermissionError("exact approval requires human_local_operator")
        return release, request, smoke

    def approve(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        release, _, smoke = self._verify_exact(payload)
        if smoke.get("status") != "passed" or not smoke.get("engineeringSmokeReady"):
            raise PermissionError("engineering smoke is not ready for exact approval")
        if any(
            int(smoke.get(field) or 0) > 0
            for field in ("unknownStateCount", "orphanOrderCount", "orphanPositionCount")
        ):
            raise PermissionError("engineering smoke contains unresolved state")
        approved_at = str(payload.get("approvedAt") or "").strip()
        if not approved_at:
            raise ValueError("approvedAt is required")
        body = {field: payload[field] for field in EXACT_FIELDS}
        body.update(
            {
                "operatorIdentity": payload["operatorIdentity"],
                "approvedAt": approved_at,
                "status": "approved_not_armed",
                "approved": True,
                "demoArm": False,
                "formalPass": bool(release.get("formalPass")),
                "live": False,
                "withdraw": False,
            }
        )
        body["recordHash"] = stable_hash(body, "demo_release_approval")
        existing = self.connection.execute(
            "SELECT payloadJson FROM DemoReleaseApprovalActions WHERE recordHash = ?",
            (body["recordHash"],),
        ).fetchone()
        if existing is None:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO DemoReleaseApprovalActions(
                      recordHash, releaseId, releaseHash, riskOverlayHash,
                      executionIntersectionHash, engineeringSmokeEvidenceHash,
                      engineeringSmokeContractHash, approvalRequestHash,
                      operatorIdentity, approvedAt, status, payloadJson
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        body["recordHash"], body["releaseId"], body["releaseHash"],
                        body["riskOverlayHash"], body["executionIntersectionHash"],
                        body["engineeringSmokeEvidenceHash"],
                        body["engineeringSmokeContractHash"], body["approvalRequestHash"],
                        body["operatorIdentity"], body["approvedAt"], body["status"],
                        json.dumps(body, ensure_ascii=False, sort_keys=True),
                    ),
                )
        _atomic_write(self.audit_dir / "demo_approval_overlay.json", body)
        return body

    def approval_actions(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT payloadJson FROM DemoReleaseApprovalActions ORDER BY approvedAt, rowid"
        ).fetchall()
        return [json.loads(row["payloadJson"]) for row in rows]

    def approval_state(self) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT payloadJson FROM DemoReleaseApprovalActions ORDER BY approvedAt DESC, rowid DESC LIMIT 1"
        ).fetchone()
        return json.loads(row["payloadJson"]) if row else {"approved": False}

    @staticmethod
    def _arm_blockers(release: Mapping[str, Any], readiness: Mapping[str, Any]) -> list[str]:
        blockers: list[str] = []
        if not readiness.get("engineeringSmokeReady"):
            blockers.append("engineering_smoke_not_ready")
        if readiness.get("currentSnapshotPolicyHash") != release.get(
            "dynamicUniversePolicyHash"
        ):
            blockers.append("snapshot_policy_hash_mismatch")
        if int(readiness.get("authenticatedDemoUniverseCount") or 0) <= 0:
            blockers.append("authenticated_demo_universe_empty")
        if int(readiness.get("unknownStateCount") or 0) > 0:
            blockers.append("unknown_state_present")
        if int(readiness.get("orphanOrderCount") or 0) > 0:
            blockers.append("orphan_order_present")
        if int(readiness.get("orphanPositionCount") or 0) > 0:
            blockers.append("orphan_position_present")
        if not readiness.get("killSwitchInactive"):
            blockers.append("kill_switch_active")
        if not readiness.get("credentialsReady"):
            blockers.append("process_credentials_not_ready")
        blockers.extend(str(value) for value in readiness.get("riskBlockers") or [])
        return blockers

    def arm(
        self,
        exact_payload: Mapping[str, Any],
        *,
        readiness: Mapping[str, Any],
        runtime_arm: Callable[[], Mapping[str, Any]],
    ) -> dict[str, Any]:
        release, _, _ = self._verify_exact(exact_payload)
        approval = self.approval_state()
        if not approval.get("approved") or approval.get("releaseHash") != release.get(
            "releaseHash"
        ):
            raise PermissionError("exact release approval required before Demo ARM")
        blockers = self._arm_blockers(release, readiness)
        if blockers:
            raise PermissionError("Demo ARM blocked: " + ", ".join(blockers))
        runtime_result = dict(runtime_arm())
        if not runtime_result.get("ok"):
            raise RuntimeError("Demo runtime ARM failed")
        return self._append_arm_action(
            release=release,
            approval=approval,
            action="arm",
            status="armed",
            runtime_result=runtime_result,
        )

    def disarm(
        self,
        exact_payload: Mapping[str, Any],
        *,
        runtime_disarm: Callable[[], Mapping[str, Any]],
    ) -> dict[str, Any]:
        release, _, _ = self._verify_exact(exact_payload)
        approval = self.approval_state()
        if not approval.get("approved"):
            raise PermissionError("exact release approval required before Demo disarm")
        runtime_result = dict(runtime_disarm())
        if not runtime_result.get("ok"):
            raise RuntimeError("Demo runtime disarm failed")
        return self._append_arm_action(
            release=release,
            approval=approval,
            action="disarm",
            status="disarmed",
            runtime_result=runtime_result,
        )

    def _append_arm_action(
        self,
        *,
        release: Mapping[str, Any],
        approval: Mapping[str, Any],
        action: str,
        status: str,
        runtime_result: Mapping[str, Any],
    ) -> dict[str, Any]:
        previous = self.connection.execute(
            "SELECT recordHash FROM DemoReleaseArmActions ORDER BY createdAt DESC, rowid DESC LIMIT 1"
        ).fetchone()
        body = {
            "releaseId": release["releaseId"],
            "releaseHash": release["releaseHash"],
            "approvalRecordHash": approval["recordHash"],
            "action": action,
            "status": status,
            "createdAt": _now(),
            "previousArmRecordHash": previous["recordHash"] if previous else None,
            "runtimeResult": dict(runtime_result),
        }
        body["recordHash"] = stable_hash(body, "demo_release_arm_action")
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO DemoReleaseArmActions(
                  recordHash, releaseId, releaseHash, approvalRecordHash,
                  action, status, createdAt, previousArmRecordHash, payloadJson
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    body["recordHash"], body["releaseId"], body["releaseHash"],
                    body["approvalRecordHash"], body["action"], body["status"],
                    body["createdAt"], body["previousArmRecordHash"],
                    json.dumps(body, ensure_ascii=False, sort_keys=True),
                ),
            )
        _atomic_write(self.audit_dir / "demo_arm_audit.json", body)
        return body

    def arm_actions(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT payloadJson FROM DemoReleaseArmActions ORDER BY createdAt, rowid"
        ).fetchall()
        return [json.loads(row["payloadJson"]) for row in rows]
