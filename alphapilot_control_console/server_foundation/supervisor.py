"""Process supervisor for the six-role V63 local-first foundation."""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import FoundationRole
from .manifest import FoundationManifest
from .reconciliation import StartupState, assert_startup_reconciled
from .secret_isolation import sanitized_environment_for_role


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _startup_state_payload(state: StartupState) -> dict[str, object]:
    return {
        "demoArmed": state.demoArmed,
        "liveArmed": state.liveArmed,
        "openOrderCount": state.openOrderCount,
        "unknownOrderCount": state.unknownOrderCount,
        "openPositionCount": state.openPositionCount,
        "withdrawEnabled": state.withdrawEnabled,
    }


def _parse_time(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)


class FoundationSupervisor:
    """Starts and observes isolated V63 role processes.

    The supervisor only supports the frozen ``shadow_no_order`` mode. It does
    not contain an order, ARM, or private exchange credential path.
    """

    def __init__(
        self,
        *,
        manifest_path: Path | str,
        python_executable: Path | str,
        repository_root: Path | str,
        source_environment: Mapping[str, str],
    ) -> None:
        self.manifest_path = Path(manifest_path).resolve()
        self.manifest = FoundationManifest.load(self.manifest_path)
        self.python_executable = Path(python_executable).resolve()
        self.repository_root = Path(repository_root).resolve()
        self.source_environment = dict(source_environment)
        self._processes: dict[FoundationRole, subprocess.Popen[bytes]] = {}
        self._log_handles: dict[FoundationRole, Any] = {}
        if not self.python_executable.is_file():
            raise FileNotFoundError(
                f"foundation_python_not_found:{self.python_executable}"
            )
        if not self.repository_root.is_dir():
            raise FileNotFoundError(
                f"foundation_repository_root_not_found:{self.repository_root}"
            )

    @property
    def startup_state_path(self) -> Path:
        return self.manifest.stateRoot / "startup_state.json"

    def start(
        self,
        *,
        roles: Sequence[FoundationRole],
        startup_state: StartupState,
        startup_timeout_seconds: float = 30,
        heartbeat_seconds: float = 5,
    ) -> dict[str, object]:
        assert_startup_reconciled(startup_state)
        selected = self._normalize_roles(roles)
        _write_json_atomic(
            self.startup_state_path,
            {
                "schemaVersion": "alphapilot_v63_startup_state_v1",
                **_startup_state_payload(startup_state),
            },
        )
        started: list[FoundationRole] = []
        try:
            for role in selected:
                role_root = self.manifest.stateRoot / "roles" / role.value
                role_root.mkdir(parents=True, exist_ok=True)
                stop_request = role_root / "stop.request"
                if stop_request.exists():
                    stop_request.unlink()
                for stale_name in ("health.json", "runtime_identity.json"):
                    stale = role_root / stale_name
                    if stale.exists():
                        stale.unlink()

                environment = sanitized_environment_for_role(
                    role,
                    self.source_environment,
                )
                environment["PYTHONPATH"] = str(self.repository_root)
                environment["ALPHAPILOT_V63_ROLE"] = role.value
                environment["ALPHAPILOT_V63_MODE"] = "shadow_no_order"
                environment["ALPHAPILOT_V63_MANIFEST"] = str(self.manifest_path)
                log_handle = (role_root / "worker.log").open("ab")
                process = subprocess.Popen(
                    [
                        str(self.python_executable),
                        "-m",
                        "alphapilot_control_console.server_foundation.cli",
                        "worker",
                        "--manifest",
                        str(self.manifest_path),
                        "--role",
                        role.value,
                        "--startup-state",
                        str(self.startup_state_path),
                        "--heartbeat-seconds",
                        str(max(0.1, float(heartbeat_seconds))),
                    ],
                    cwd=str(self.repository_root),
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                self._processes[role] = process
                self._log_handles[role] = log_handle
                started.append(role)

            deadline = time.monotonic() + max(1.0, float(startup_timeout_seconds))
            while time.monotonic() < deadline:
                exited = [
                    role.value
                    for role in started
                    if self._processes[role].poll() is not None
                ]
                if exited:
                    raise RuntimeError(
                        "foundation_worker_exited_during_startup:"
                        + ",".join(exited)
                    )
                projection = self.health(
                    roles=selected,
                    maximum_age_seconds=max(
                        2.0,
                        float(heartbeat_seconds) * 4,
                    ),
                )
                if projection["healthy"]:
                    return {
                        "schemaVersion": "alphapilot_v63_supervisor_start_v1",
                        "status": "started_shadow_no_order",
                        "deploymentId": self.manifest.deploymentId,
                        "environment": self.manifest.environment,
                        "manifestHash": self.manifest.manifestHash,
                        "configHash": self.manifest.configHash,
                        "startedRoles": [role.value for role in selected],
                        "orderCapabilityEnabled": False,
                        "demoArmAllowed": False,
                        "liveArmAllowed": False,
                        "withdrawAllowed": False,
                    }
                time.sleep(0.1)
            raise TimeoutError("foundation_worker_startup_timeout")
        except Exception:
            if started:
                self.stop(roles=tuple(started), timeout_seconds=5)
            raise

    def health(
        self,
        *,
        roles: Sequence[FoundationRole],
        maximum_age_seconds: float = 15,
    ) -> dict[str, object]:
        selected = self._normalize_roles(roles)
        now = datetime.now(UTC)
        projections: list[dict[str, object]] = []
        for role in selected:
            path = self.manifest.stateRoot / "roles" / role.value / "health.json"
            if not path.is_file():
                projections.append(
                    {
                        "role": role.value,
                        "healthy": False,
                        "status": "health_missing",
                        "orderCapabilityEnabled": False,
                    }
                )
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                heartbeat = _parse_time(payload.get("lastHeartbeatAt"))
                age_seconds = max(0.0, (now - heartbeat).total_seconds())
                healthy = (
                    payload.get("status") == "healthy_shadow_no_order"
                    and payload.get("manifestHash") == self.manifest.manifestHash
                    and payload.get("configHash") == self.manifest.configHash
                    and payload.get("orderCapabilityEnabled") is False
                    and age_seconds <= float(maximum_age_seconds)
                )
                projections.append(
                    {
                        **payload,
                        "healthy": healthy,
                        "ageSeconds": round(age_seconds, 3),
                    }
                )
            except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
                projections.append(
                    {
                        "role": role.value,
                        "healthy": False,
                        "status": "health_invalid",
                        "errorType": type(exc).__name__,
                        "orderCapabilityEnabled": False,
                    }
                )
        healthy_count = sum(bool(item["healthy"]) for item in projections)
        return {
            "schemaVersion": "alphapilot_v63_supervisor_health_v1",
            "healthy": healthy_count == len(selected),
            "healthyRoleCount": healthy_count,
            "expectedRoleCount": len(selected),
            "manifestHash": self.manifest.manifestHash,
            "configHash": self.manifest.configHash,
            "orderCapabilityEnabled": False,
            "roles": projections,
        }

    def stop(
        self,
        *,
        roles: Sequence[FoundationRole],
        timeout_seconds: float = 30,
    ) -> dict[str, object]:
        selected = self._normalize_roles(roles)
        for role in selected:
            role_root = self.manifest.stateRoot / "roles" / role.value
            role_root.mkdir(parents=True, exist_ok=True)
            (role_root / "stop.request").write_text(
                "cooperative_stop_requested\n",
                encoding="ascii",
            )
        deadline = time.monotonic() + max(1.0, float(timeout_seconds))
        pending = set(selected)
        while pending and time.monotonic() < deadline:
            completed: list[FoundationRole] = []
            for role in pending:
                process = self._processes.get(role)
                if process is not None:
                    if process.poll() is not None:
                        completed.append(role)
                    continue
                health_path = (
                    self.manifest.stateRoot / "roles" / role.value / "health.json"
                )
                if health_path.is_file():
                    try:
                        health = json.loads(health_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        continue
                    if health.get("status") == "stopped":
                        completed.append(role)
            for role in completed:
                pending.discard(role)
            if pending:
                time.sleep(0.1)

        for role in selected:
            handle = self._log_handles.pop(role, None)
            if handle is not None:
                handle.close()
            self._processes.pop(role, None)
        if pending:
            raise TimeoutError(
                "foundation_worker_stop_timeout:"
                + ",".join(sorted(role.value for role in pending))
            )
        return {
            "schemaVersion": "alphapilot_v63_supervisor_stop_v1",
            "status": "stopped",
            "stoppedRoles": [role.value for role in selected],
            "orderCapabilityEnabled": False,
        }

    def _normalize_roles(
        self,
        roles: Sequence[FoundationRole],
    ) -> tuple[FoundationRole, ...]:
        normalized = tuple(FoundationRole(role) for role in roles)
        if not normalized:
            raise ValueError("at_least_one_foundation_role_required")
        if len(set(normalized)) != len(normalized):
            raise ValueError("duplicate_foundation_roles_requested")
        disabled = [
            role.value
            for role in normalized
            if not self.manifest.role(role).enabled
        ]
        if disabled:
            raise PermissionError(
                "foundation_roles_disabled:" + ",".join(disabled)
            )
        return normalized
