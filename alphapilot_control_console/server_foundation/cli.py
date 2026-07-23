"""Command-line boundary for V63 local-first headless workers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .contracts import FoundationRole
from .lease import FoundationLeaseStore
from .manifest import FoundationManifest
from .reconciliation import StartupState
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
