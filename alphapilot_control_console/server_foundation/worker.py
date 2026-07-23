"""Headless worker primitive shared by all six V63 roles."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .checkpoint import (
    CheckpointIdentityMismatch,
    FoundationCheckpointStore,
)
from .contracts import FoundationRole
from .identity import build_runtime_identity
from .lease import FoundationLeaseClaim, FoundationLeaseStore
from .manifest import FoundationManifest
from .reconciliation import StartupState, assert_startup_reconciled
from .shadow import NoOrderShadowPolicy


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return normalized.astimezone(UTC).isoformat()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


class FoundationWorker:
    def __init__(
        self,
        *,
        manifest: FoundationManifest,
        role: FoundationRole,
        lease_store: FoundationLeaseStore,
        now_factory: Callable[[], datetime] = _utc_now,
        process_id: int | None = None,
    ) -> None:
        self.manifest = manifest
        self.role = FoundationRole(role)
        self.lease_store = lease_store
        self._now = now_factory
        self.process_id = int(process_id if process_id is not None else os.getpid())
        self.policy = NoOrderShadowPolicy()
        self.claim: FoundationLeaseClaim | None = None
        self.started_at: str | None = None
        self.cycle_count = 0
        self.resumed_from_checkpoint = False
        self.resumed_checkpoint_fencing_token: int | None = None
        self.checkpoint_resume_disposition = "started_without_checkpoint"
        self.superseded_checkpoint_path: str | None = None
        self.checkpoints = FoundationCheckpointStore(
            manifest.stateRoot / "checkpoints"
        )

    @property
    def role_root(self) -> Path:
        return self.manifest.stateRoot / "roles" / self.role.value

    def run_once(self, startup_state: StartupState) -> dict[str, Any]:
        reconciliation = assert_startup_reconciled(startup_state)
        now = self._now().astimezone(UTC)
        if self.claim is None:
            self.started_at = _iso(now)
            self.claim = self.lease_store.acquire(
                environment=self.manifest.environment,
                role=self.role,
                owner_id=f"{self.manifest.deploymentId}:{self.role.value}:{self.process_id}",
                ttl_seconds=30,
            )
            try:
                checkpoint = self.checkpoints.load_for_resume(
                    role=self.role,
                    expected_manifest_hash=self.manifest.manifestHash,
                    expected_config_hash=self.manifest.configHash,
                    current_fencing_token=self.claim.fencingToken,
                )
            except FileNotFoundError:
                pass
            except CheckpointIdentityMismatch as exc:
                if not exc.is_supersedable_runtime_identity_change:
                    self.close()
                    raise
                try:
                    archived = self.checkpoints.archive_superseded(
                        role=self.role
                    )
                except Exception:
                    self.close()
                    raise
                self.checkpoint_resume_disposition = (
                    "started_fresh_new_identity"
                )
                self.superseded_checkpoint_path = str(archived)
            else:
                progress = checkpoint.get("progress", {})
                resumed_cycle_count = int(progress.get("cycleCount", 0))
                if resumed_cycle_count < 0:
                    raise ValueError("checkpoint_cycle_count_must_be_nonnegative")
                self.cycle_count = resumed_cycle_count
                self.resumed_from_checkpoint = True
                self.resumed_checkpoint_fencing_token = int(
                    checkpoint["fencingToken"]
                )
                self.checkpoint_resume_disposition = (
                    "resumed_same_identity"
                )
        else:
            self.claim = self.lease_store.heartbeat(
                self.claim,
                ttl_seconds=30,
            )
        assert self.started_at is not None
        self.cycle_count += 1
        identity = build_runtime_identity(
            manifest=self.manifest,
            role=self.role,
            process_id=self.process_id,
            started_at=self.started_at,
            lease_id=self.claim.leaseId,
            fencing_token=self.claim.fencingToken,
        )
        identity_path = self.role_root / "runtime_identity.json"
        health_path = self.role_root / "health.json"
        _write_json_atomic(identity_path, identity.to_dict())
        checkpoint = self.checkpoints.write(
            role=self.role,
            manifest_hash=self.manifest.manifestHash,
            config_hash=self.manifest.configHash,
            fencing_token=self.claim.fencingToken,
            progress={
                "status": "healthy_shadow_no_order",
                "lastHeartbeatAt": _iso(now),
                "cycleCount": self.cycle_count,
            },
        )
        health = {
            "schemaVersion": "alphapilot_v63_worker_health_v1",
            "status": "healthy_shadow_no_order",
            "role": self.role.value,
            "processId": self.process_id,
            "startedAt": self.started_at,
            "lastHeartbeatAt": _iso(now),
            "identityHash": identity.identityHash,
            "manifestHash": self.manifest.manifestHash,
            "configHash": self.manifest.configHash,
            "leaseId": self.claim.leaseId,
            "fencingToken": self.claim.fencingToken,
            "reconciliation": reconciliation.to_dict(),
            "orderCapabilityEnabled": False,
            "demoArmAllowed": False,
            "liveArmAllowed": False,
            "withdrawAllowed": False,
            "cycleCount": self.cycle_count,
            "resumedFromCheckpoint": self.resumed_from_checkpoint,
            "resumedCheckpointFencingToken": (
                self.resumed_checkpoint_fencing_token
            ),
            "checkpointResumeDisposition": (
                self.checkpoint_resume_disposition
            ),
            "supersededCheckpointPath": self.superseded_checkpoint_path,
            "healthPath": str(health_path),
            "identityPath": str(identity_path),
            "checkpointPath": str(self.checkpoints.path_for(self.role)),
        }
        _write_json_atomic(health_path, health)
        return health

    def run_forever(
        self,
        startup_state: StartupState,
        *,
        heartbeat_seconds: float = 5.0,
    ) -> None:
        stop_request = self.role_root / "stop.request"
        if stop_request.exists():
            stop_request.unlink()
        while not stop_request.exists():
            self.run_once(startup_state)
            time.sleep(max(0.1, float(heartbeat_seconds)))
        self.close()

    def close(self) -> None:
        if self.claim is None:
            return
        role_root = self.role_root
        health_path = role_root / "health.json"
        stopped_at = _iso(self._now().astimezone(UTC))
        try:
            self.lease_store.release(self.claim)
        except PermissionError:
            pass
        finally:
            self.claim = None
        if health_path.is_file():
            try:
                health = json.loads(health_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                health = {
                    "schemaVersion": "alphapilot_v63_worker_health_v1",
                    "role": self.role.value,
                }
            health.update(
                {
                    "status": "stopped",
                    "stoppedAt": stopped_at,
                    "lastHeartbeatAt": stopped_at,
                    "orderCapabilityEnabled": False,
                    "demoArmAllowed": False,
                    "liveArmAllowed": False,
                    "withdrawAllowed": False,
                }
            )
            _write_json_atomic(health_path, health)
