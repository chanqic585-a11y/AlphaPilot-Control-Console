"""Local subprocess client for the Quant Engine workflow authority."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .config import DATA_DIR, get_quant_engine_path
from .strategy_optimization import (
    build_optimization_context,
    validate_optimization_parameters,
)


CONTROL_CONSOLE_VERSION = "V13.27.2"
WORKFLOW_MODULE = "alphapilot.evolution.workflow.cli"
APPROVED_WAREHOUSE_ROOT = Path(r"D:\Codex-Workspace\回测数据")
ALLOWED_COMMANDS = {
    "advance",
    "archive",
    "bootstrap",
    "cancel",
    "challenger",
    "import-optimized",
    "pause",
    "projection",
    "queue",
    "recover",
    "retry",
    "run",
    "one-click-backtest",
    "research-smoke",
}
_BACKGROUND_PROCESSES: dict[str, subprocess.Popen] = {}
_STARTUP_WORKFLOW_RECOVERY_STATUS: dict[str, Any] = {
    "status": "not_started",
    "candidateCount": 0,
    "startedCount": 0,
    "alreadyRunningCount": 0,
    "errorCount": 0,
    "errors": [],
    "checkedAt": None,
}


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
        "--warehouse-root",
        str(APPROVED_WAREHOUSE_ROOT),
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
    projection = run_workflow_cli(["projection"], quant_root=quant_root)
    for bucket in ("items", "archivedItems"):
        for item in projection.get(bucket) or []:
            if isinstance(item, dict):
                item["optimizationContext"] = build_optimization_context(item)
    return projection


def _start_created_version_backtest(
    created: dict[str, Any],
    *,
    quant_root: Path | None,
) -> dict[str, Any]:
    version_id = str(created.get("strategyVersionId") or "").strip()
    projection = build_workflow_projection(quant_root=quant_root)
    run = next(
        (
            item
            for item in projection.get("items") or []
            if isinstance(item, dict)
            and item.get("strategyVersionId") == version_id
            and item.get("stage") == "backtest"
        ),
        None,
    )
    if run is None:
        raise RuntimeError("created_strategy_backtest_run_missing")
    backtest = request_dual_layer_backtest(
        str(run.get("workflowRunId") or ""),
        quant_root=quant_root,
    )
    return {**created, "backtest": backtest}


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
                ["one-click-backtest", "--run-id", run_id],
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


def request_dual_layer_backtest(
    workflow_run_id: str,
    *,
    quant_root: Path | None = None,
) -> dict[str, Any]:
    run_id = _safe_run_id(workflow_run_id)
    worker = spawn_workflow_run(run_id, quant_root=quant_root)
    return {"workflowRunId": run_id, "worker": worker}


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
            request_dual_layer_backtest(
                str(item.get("workflowRunId") or ""),
                quant_root=quant_root,
            )
        )
    return {"requestedCount": len(requested), "runs": requested}


def get_startup_workflow_recovery_status() -> dict[str, Any]:
    return {
        **_STARTUP_WORKFLOW_RECOVERY_STATUS,
        "errors": list(_STARTUP_WORKFLOW_RECOVERY_STATUS.get("errors") or []),
    }


def resume_incomplete_workflow_runs(
    *,
    quant_root: Path | None = None,
) -> dict[str, Any]:
    """Restart interrupted backtest workers without overriding explicit pauses."""

    global _STARTUP_WORKFLOW_RECOVERY_STATUS
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        projection = build_workflow_projection(quant_root=quant_root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        _STARTUP_WORKFLOW_RECOVERY_STATUS = {
            "status": "failed",
            "candidateCount": 0,
            "startedCount": 0,
            "alreadyRunningCount": 0,
            "errorCount": 1,
            "errors": [{"workflowRunId": None, "error": str(error)[-500:]}],
            "checkedAt": checked_at,
        }
        return get_startup_workflow_recovery_status()

    candidates: list[str] = []
    seen: set[str] = set()
    for item in projection.get("items") or []:
        if not isinstance(item, dict):
            continue
        if item.get("stage") != "backtest" or item.get("status") not in {
            "queued",
            "running",
        }:
            continue
        run_id = str(item.get("workflowRunId") or "").strip()
        if not run_id or run_id in seen:
            continue
        seen.add(run_id)
        candidates.append(run_id)

    started_count = 0
    already_running_count = 0
    errors: list[dict[str, str | None]] = []
    for run_id in candidates:
        try:
            worker = spawn_workflow_run(run_id, quant_root=quant_root)
            if worker.get("started"):
                started_count += 1
            elif worker.get("alreadyRunning"):
                already_running_count += 1
        except (FileNotFoundError, RuntimeError, ValueError, OSError) as error:
            errors.append(
                {"workflowRunId": run_id, "error": str(error)[-500:]}
            )

    _STARTUP_WORKFLOW_RECOVERY_STATUS = {
        "status": "completed_with_errors" if errors else "completed",
        "candidateCount": len(candidates),
        "startedCount": started_count,
        "alreadyRunningCount": already_running_count,
        "errorCount": len(errors),
        "errors": errors,
        "checkedAt": checked_at,
    }
    return get_startup_workflow_recovery_status()


def request_workflow_action(
    action: str,
    payload: dict[str, Any],
    *,
    quant_root: Path | None = None,
) -> dict[str, Any]:
    normalized = str(action or "").strip().lower()
    if normalized in {"run-selected", "run-dual-layer"}:
        return request_dual_layer_backtest(
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
        base_parameters = payload.get("baseParameters")
        if isinstance(base_parameters, dict):
            parameters = validate_optimization_parameters(
                definition,
                base_parameters,
                parameters,
            )
        created = run_workflow_cli(
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
        if bool(payload.get("startBacktest")):
            return _start_created_version_backtest(created, quant_root=quant_root)
        return created
    if normalized == "import-optimized":
        legacy_id = str(payload.get("legacyStrategyId") or "").strip()
        display_name = str(payload.get("displayName") or "").strip()
        definition = payload.get("definition")
        base_parameters = payload.get("baseParameters")
        parameters = payload.get("parameters")
        if not legacy_id or not display_name:
            raise ValueError("legacy_optimization_identity_required")
        if not isinstance(definition, dict) or not isinstance(base_parameters, dict):
            raise ValueError("legacy_optimization_context_required")
        parameters = validate_optimization_parameters(
            definition,
            base_parameters,
            parameters,
        )
        created = run_workflow_cli(
            [
                "import-optimized",
                "--legacy-strategy-id",
                legacy_id,
                "--display-name",
                display_name,
                "--source-type",
                "legacy_stage_optimization",
                "--definition-json",
                json.dumps(definition, ensure_ascii=False, separators=(",", ":")),
                "--base-parameters-json",
                json.dumps(base_parameters, ensure_ascii=False, separators=(",", ":")),
                "--parameters-json",
                json.dumps(parameters, ensure_ascii=False, separators=(",", ":")),
            ],
            quant_root=quant_root,
        )
        if bool(payload.get("startBacktest")):
            return _start_created_version_backtest(created, quant_root=quant_root)
        return created
    raise ValueError("unsupported_workflow_action")
