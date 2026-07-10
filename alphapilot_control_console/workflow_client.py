"""Local subprocess client for the Quant Engine workflow authority."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

from .config import DATA_DIR, get_quant_engine_path


CONTROL_CONSOLE_VERSION = "V13.27.1"
WORKFLOW_MODULE = "alphapilot.evolution.workflow.cli"
ALLOWED_COMMANDS = {
    "advance",
    "archive",
    "bootstrap",
    "cancel",
    "challenger",
    "pause",
    "projection",
    "queue",
    "recover",
    "retry",
    "run",
}
_BACKGROUND_PROCESSES: dict[str, subprocess.Popen] = {}


def _safe_run_id(value: str) -> str:
    run_id = str(value or "").strip()
    if not run_id or not re.fullmatch(r"[A-Za-z0-9_.:-]+", run_id):
        raise ValueError("invalid_workflow_run_id")
    return run_id


def _quant_python(quant_root: Path) -> Path:
    candidates = [
        quant_root / ".venv" / "Scripts" / "python.exe",
        quant_root / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Quant Engine Python environment is missing: {quant_root}")


def build_workflow_command(
    arguments: Sequence[str],
    *,
    quant_root: Path | None = None,
) -> list[str]:
    root = (quant_root or get_quant_engine_path()).resolve()
    if not arguments or str(arguments[0]) not in ALLOWED_COMMANDS:
        raise ValueError("unsupported_workflow_command")
    return [
        str(_quant_python(root)),
        "-m",
        WORKFLOW_MODULE,
        "--registry",
        str(root / "data" / "evolution_registry.sqlite"),
        "--output-root",
        str(root / "data" / "workflow" / "backtests"),
        *[str(value) for value in arguments],
    ]


def run_workflow_cli(
    arguments: Sequence[str],
    *,
    quant_root: Path | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    root = (quant_root or get_quant_engine_path()).resolve()
    completed = subprocess.run(
        build_workflow_command(arguments, quant_root=root),
        cwd=root,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    output = (completed.stdout or "").strip()
    if completed.returncode != 0:
        message = (completed.stderr or output or "workflow_command_failed")[-2000:]
        raise RuntimeError(message)
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as error:
        raise RuntimeError("workflow_command_returned_invalid_json") from error
    if not isinstance(payload, dict):
        raise RuntimeError("workflow_command_returned_non_object")
    return payload


def build_workflow_projection(
    *,
    quant_root: Path | None = None,
) -> dict[str, Any]:
    return run_workflow_cli(["projection"], quant_root=quant_root)


def spawn_workflow_run(
    workflow_run_id: str,
    *,
    quant_root: Path | None = None,
) -> dict[str, Any]:
    run_id = _safe_run_id(workflow_run_id)
    existing = _BACKGROUND_PROCESSES.get(run_id)
    if existing is not None and existing.poll() is None:
        return {
            "started": False,
            "alreadyRunning": True,
            "workflowRunId": run_id,
            "processId": existing.pid,
        }
    root = (quant_root or get_quant_engine_path()).resolve()
    log_root = DATA_DIR / "workflow_jobs"
    log_root.mkdir(parents=True, exist_ok=True)
    log_path = log_root / f"{run_id}.log"
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with log_path.open("a", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            build_workflow_command(
                ["run", "--run-id", run_id],
                quant_root=root,
            ),
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
    _BACKGROUND_PROCESSES[run_id] = process
    return {
        "started": True,
        "alreadyRunning": False,
        "workflowRunId": run_id,
        "processId": process.pid,
        "logPath": str(log_path),
    }


def request_backtest_run(
    workflow_run_id: str,
    *,
    quant_root: Path | None = None,
) -> dict[str, Any]:
    run_id = _safe_run_id(workflow_run_id)
    queued = run_workflow_cli(
        ["queue", "--run-id", run_id],
        quant_root=quant_root,
    )
    worker = spawn_workflow_run(run_id, quant_root=quant_root)
    return {"workflowRunId": run_id, "queued": queued, "worker": worker}


def request_all_awaiting_backtests(
    *,
    quant_root: Path | None = None,
) -> dict[str, Any]:
    projection = build_workflow_projection(quant_root=quant_root)
    requested = []
    for item in projection.get("items") or []:
        if not isinstance(item, dict):
            continue
        if item.get("stage") != "backtest" or item.get("status") != "awaiting":
            continue
        requested.append(
            request_backtest_run(
                str(item.get("workflowRunId") or ""),
                quant_root=quant_root,
            )
        )
    return {"requestedCount": len(requested), "runs": requested}


def request_workflow_action(
    action: str,
    payload: dict[str, Any],
    *,
    quant_root: Path | None = None,
) -> dict[str, Any]:
    normalized = str(action or "").strip().lower()
    if normalized == "run-selected":
        return request_backtest_run(
            str(payload.get("workflowRunId") or ""),
            quant_root=quant_root,
        )
    if normalized == "run-all-awaiting":
        return request_all_awaiting_backtests(quant_root=quant_root)
    if normalized in {"pause", "cancel"}:
        run_id = _safe_run_id(str(payload.get("workflowRunId") or ""))
        return run_workflow_cli(
            [normalized, "--run-id", run_id],
            quant_root=quant_root,
        )
    if normalized == "retry":
        run_id = _safe_run_id(str(payload.get("workflowRunId") or ""))
        retry = run_workflow_cli(
            ["retry", "--run-id", run_id],
            quant_root=quant_root,
        )
        retry_run_id = _safe_run_id(str(retry.get("workflowRunId") or ""))
        return {
            "retry": retry,
            "worker": spawn_workflow_run(retry_run_id, quant_root=quant_root),
        }
    if normalized == "archive":
        version_id = str(payload.get("strategyVersionId") or "").strip()
        if not version_id:
            raise ValueError("strategy_version_id_required")
        return run_workflow_cli(
            ["archive", "--strategy-version-id", version_id],
            quant_root=quant_root,
        )
    if normalized == "advance":
        version_id = str(payload.get("strategyVersionId") or "").strip()
        if not version_id:
            raise ValueError("strategy_version_id_required")
        return run_workflow_cli(
            ["advance", "--strategy-version-id", version_id],
            quant_root=quant_root,
        )
    if normalized == "challenger":
        parent_id = str(payload.get("parentStrategyVersionId") or "").strip()
        display_name = str(payload.get("displayName") or "").strip()
        definition = payload.get("definition")
        parameters = payload.get("parameters")
        if not parent_id or not display_name:
            raise ValueError("challenger_identity_required")
        if not isinstance(definition, dict) or not isinstance(parameters, dict):
            raise ValueError("challenger_definition_and_parameters_required")
        return run_workflow_cli(
            [
                "challenger",
                "--parent-version-id",
                parent_id,
                "--display-name",
                display_name,
                "--definition-json",
                json.dumps(definition, ensure_ascii=False, separators=(",", ":")),
                "--parameters-json",
                json.dumps(parameters, ensure_ascii=False, separators=(",", ":")),
            ],
            quant_root=quant_root,
        )
    raise ValueError("unsupported_workflow_action")
