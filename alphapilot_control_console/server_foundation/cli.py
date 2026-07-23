"""Command-line boundary for V63 local-first headless workers."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .contracts import FOUNDATION_ROLES, FoundationRole
from .lease import FoundationLeaseStore
from .manifest import FoundationManifest
from .reconciliation import StartupState
from .resource_budget import validate_resource_budget
from .sqlite_backup import (
    RestoreGuard,
    create_online_backup,
    restore_online_backup,
)
from .supervisor import FoundationSupervisor
from .worker import FoundationWorker


def _load_startup_state(path: Path) -> StartupState:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != "alphapilot_v63_startup_state_v1":
        raise ValueError("unsupported_foundation_startup_state_schema")
    return StartupState(
        demoArmed=bool(payload.get("demoArmed")),
        liveArmed=bool(payload.get("liveArmed")),
        openOrderCount=int(payload.get("openOrderCount", -1)),
        unknownOrderCount=int(payload.get("unknownOrderCount", -1)),
        openPositionCount=int(payload.get("openPositionCount", -1)),
        withdrawEnabled=bool(payload.get("withdrawEnabled")),
    )


def _run_worker(args: argparse.Namespace) -> int:
    manifest = FoundationManifest.load(Path(args.manifest))
    lease_store = FoundationLeaseStore(
        manifest.stateRoot / "foundation_leases.sqlite"
    )
    worker = FoundationWorker(
        manifest=manifest,
        role=FoundationRole(args.role),
        lease_store=lease_store,
    )
    try:
        worker.run_forever(
            _load_startup_state(Path(args.startup_state)),
            heartbeat_seconds=float(args.heartbeat_seconds),
        )
        return 0
    finally:
        worker.close()
        lease_store.close()


def _roles(value: str) -> tuple[FoundationRole, ...]:
    normalized = str(value).strip().lower()
    if normalized == "all":
        return FOUNDATION_ROLES
    return tuple(
        FoundationRole(item.strip())
        for item in normalized.split(",")
        if item.strip()
    )


def _supervisor(args: argparse.Namespace) -> FoundationSupervisor:
    return FoundationSupervisor(
        manifest_path=Path(args.manifest),
        python_executable=Path(args.python_executable),
        repository_root=Path(args.repository_root),
        source_environment=os.environ,
    )


def _print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _start(args: argparse.Namespace) -> int:
    result = _supervisor(args).start(
        roles=_roles(args.roles),
        startup_state=_load_startup_state(Path(args.startup_state)),
        startup_timeout_seconds=float(args.timeout_seconds),
        heartbeat_seconds=float(args.heartbeat_seconds),
    )
    _print_json(result)
    return 0


def _stop(args: argparse.Namespace) -> int:
    result = _supervisor(args).stop(
        roles=_roles(args.roles),
        timeout_seconds=float(args.timeout_seconds),
    )
    _print_json(result)
    return 0


def _health(args: argparse.Namespace) -> int:
    result = _supervisor(args).health(
        roles=_roles(args.roles),
        maximum_age_seconds=float(args.maximum_age_seconds),
    )
    _print_json(result)
    return 0 if result["healthy"] else 2


def _status(args: argparse.Namespace) -> int:
    result = _supervisor(args).status(
        roles=_roles(args.roles),
        maximum_age_seconds=float(args.maximum_age_seconds),
    )
    _print_json(result)
    return 0 if result["status"] == "running_shadow_no_order" else 2


def _validate(args: argparse.Namespace) -> int:
    manifest = FoundationManifest.load(Path(args.manifest))
    resource_budget = validate_resource_budget(manifest)
    payload = {
        "schemaVersion": "alphapilot_v63_foundation_validation_v1",
        "passed": (
            resource_budget.passed
            and manifest.mode.value == "shadow_no_order"
            and not manifest.orderCapabilityEnabled
            and len(manifest.roles) == len(FOUNDATION_ROLES)
        ),
        "deploymentId": manifest.deploymentId,
        "environment": manifest.environment,
        "mode": manifest.mode.value,
        "roleCount": len(manifest.roles),
        "repositoryCommit": manifest.repositoryCommit,
        "repositoryTag": manifest.repositoryTag,
        "manifestHash": manifest.manifestHash,
        "configHash": manifest.configHash,
        "stateRoot": str(manifest.stateRoot),
        "orderCapabilityEnabled": manifest.orderCapabilityEnabled,
        "demoArmAllowed": False,
        "liveArmAllowed": False,
        "withdrawAllowed": False,
        "resourceBudget": resource_budget.to_dict(),
    }
    _print_json(payload)
    return 0 if payload["passed"] else 2


def _backup(args: argparse.Namespace) -> int:
    receipt = create_online_backup(
        Path(args.source),
        Path(args.destination),
    )
    if args.receipt:
        receipt_path = Path(args.receipt)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    _print_json(receipt)
    return 0


def _restore(args: argparse.Namespace) -> int:
    guard_payload = json.loads(Path(args.guard).read_text(encoding="utf-8"))
    guard = RestoreGuard(
        allRolesStopped=bool(guard_payload.get("allRolesStopped")),
        demoArmed=bool(guard_payload.get("demoArmed")),
        liveArmed=bool(guard_payload.get("liveArmed")),
        activeLeaseCount=int(guard_payload.get("activeLeaseCount", -1)),
    )
    receipt = restore_online_backup(
        Path(args.source),
        Path(args.destination),
        guard=guard,
    )
    if args.receipt:
        receipt_path = Path(args.receipt)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    _print_json(receipt)
    return 0


def _add_supervisor_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--roles", default="all")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AlphaPilot V63 local-first server foundation",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    worker = subcommands.add_parser("worker", help="run one headless role")
    worker.add_argument("--manifest", required=True)
    worker.add_argument(
        "--role",
        required=True,
        choices=[role.value for role in FoundationRole],
    )
    worker.add_argument("--startup-state", required=True)
    worker.add_argument("--heartbeat-seconds", type=float, default=5.0)
    worker.set_defaults(handler=_run_worker)

    start = subcommands.add_parser("start", help="start headless roles")
    _add_supervisor_arguments(start)
    start.add_argument("--startup-state", required=True)
    start.add_argument("--heartbeat-seconds", type=float, default=5.0)
    start.add_argument("--timeout-seconds", type=float, default=30.0)
    start.set_defaults(handler=_start)

    stop = subcommands.add_parser("stop", help="cooperatively stop headless roles")
    _add_supervisor_arguments(stop)
    stop.add_argument("--timeout-seconds", type=float, default=30.0)
    stop.set_defaults(handler=_stop)

    health = subcommands.add_parser("health", help="read role health")
    _add_supervisor_arguments(health)
    health.add_argument("--maximum-age-seconds", type=float, default=15.0)
    health.set_defaults(handler=_health)

    status = subcommands.add_parser("status", help="read role and lease status")
    _add_supervisor_arguments(status)
    status.add_argument("--maximum-age-seconds", type=float, default=15.0)
    status.set_defaults(handler=_status)

    validate = subcommands.add_parser(
        "validate",
        help="validate one materialized no-order deployment manifest",
    )
    validate.add_argument("--manifest", required=True)
    validate.set_defaults(handler=_validate)

    backup = subcommands.add_parser("backup", help="online-backup one SQLite file")
    backup.add_argument("--source", required=True)
    backup.add_argument("--destination", required=True)
    backup.add_argument("--receipt")
    backup.set_defaults(handler=_backup)

    restore = subcommands.add_parser(
        "restore",
        help="restore one SQLite backup through a fail-closed guard",
    )
    restore.add_argument("--source", required=True)
    restore.add_argument("--destination", required=True)
    restore.add_argument("--guard", required=True)
    restore.add_argument("--receipt")
    restore.set_defaults(handler=_restore)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
