from __future__ import annotations

import argparse
import ipaddress
import json
import mimetypes
import os
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import ALLOWED_STRATEGY_STATUSES, SAFETY_BOUNDARY, WEB_DIR
from .credential_runtime import load_okx_demo_credentials
from .auto_execution_engine import build_auto_execution_engine, run_auto_execution_engine
from .auto_execution_learning import build_auto_execution_learning
from .auto_execution_lifecycle import build_auto_execution_lifecycle_monitor
from .auto_execution_lifecycle_advancer import advance_auto_execution_lifecycle
from .auto_execution_review import build_auto_execution_review
from .exchange_connectors.public_exchange_registry import list_public_exchange_sources, probe_public_exchanges
from .exchange_demo_simulation import (
    build_exchange_demo_simulation,
    query_exchange_demo_order_status,
    run_exchange_demo_emergency_drill,
    run_exchange_demo_readonly_check,
    scan_exchange_demo_candidates,
    submit_exchange_demo_order,
)
from .evolution_demo_service import (
    activate_evolution_demo_kill_switch,
    build_evolution_demo_status,
    run_evolution_demo_cycle,
)
from .demo_workflow_service import build_demo_workflow_status, run_demo_workflow_action
from .demo_market_runtime_registry import start_demo_market_runtime, stop_demo_market_runtime
from .demo_instrument_universe import load_or_refresh_demo_instrument_universe
from .demo_release_service import (
    approve_final_demo_release,
    arm_final_demo_release,
    disarm_final_demo_release,
)
from .demo_engineering_smoke_contract import (
    DEFAULT_CONTRACT_DIR as DEMO_ENGINEERING_SMOKE_CONTRACT_DIR,
    build_demo_engineering_smoke_contract,
    validate_demo_engineering_smoke_contract,
)
from .demo_engineering_smoke_service import (
    build_demo_engineering_smoke_status,
    reconcile_demo_engineering_smoke,
    run_demo_engineering_smoke,
)
from .demo_credential_bootstrap import (
    bootstrap_demo_credentials,
    maybe_open_demo_credential_prompt,
)
from .demo_startup_arm import (
    arm_okx_demo_runtime_on_startup,
    start_okx_demo_runtime_startup_recovery,
)
from .exchange_connectors.okx_demo_client import OkxDemoClient
from .execution_outcome_export import (
    build_execution_outcome_status,
    write_execution_outcome_export,
)
from .execution_control import (
    get_execution_control_status,
    run_execution_control_action,
)
from .forward_review import build_forward_review, refresh_forward_review
from .importer import build_mobile_status, import_now, scan_quant_engine
from .live_readiness import build_live_readiness, create_manual_execution_ticket
from .live_candidate_service import (
    approve_live_candidate,
    build_live_candidate_status,
    revoke_live_candidate,
)
from .live_safety_plane import activate_live_kill_switch, build_live_safety_status
from .live_canary_service import (
    activate_live_canary_kill_switch,
    build_live_canary_status,
    run_live_readonly_reconciliation,
)
from .local_demo_launcher import LOCAL_DEMO_LAUNCHER
from .windows_demo_credential_vault import DEMO_CREDENTIAL_VAULT, DemoCredentialVaultError
from .local_sandbox_concentration_review import build_local_sandbox_concentration_review
from .local_sandbox_quality_center import build_local_sandbox_quality_center
from .local_sandbox_result_review import build_local_sandbox_result_review
from .local_simulation_retirement import (
    RETIRED_LOCAL_SIMULATION_POST_ROUTES,
    legacy_read_projection,
    retired_write_response,
)
from .shadow_observation_store import DEFAULT_SHADOW_PATH, ShadowObservationStore
from .mobile_connection import build_mobile_connection_info
from .no_key_pre_live import (
    build_no_key_pre_live_workbench,
    create_no_key_observation_ticket,
    scan_no_key_pre_live_candidates,
)
from .pre_live_preparation_pack import (
    build_pre_live_preparation_pack,
    create_pre_live_rehearsal,
    simulate_pre_live_order_lifecycle,
)
from .risk_profile_service import (
    activate_risk_profile_version,
    create_risk_profile_version,
    rollback_risk_profile_version,
)
from .risk_profile_store import build_risk_profile_status
from .sandbox_auto_runner import (
    get_local_sandbox_auto_runner_status,
)
from .sandbox_observation_reporter import build_local_sandbox_daily_report
from .short_cycle_candidates import build_short_cycle_candidate_pool
from .candidate_promotion_gate import build_candidate_promotion_gate_v2
from .research_action_executor import build_research_action_executor
from .research_execution_pipeline import build_research_execution_pipeline
from .simulation_bridge import build_simulation_bridge
from .simulation_command_center import build_simulation_command_center
from .simulation_replay import build_closed_sample_replay, build_closed_sample_strategy_detail
from .simulation_review import build_simulation_review, build_simulation_review_strategy
from .strategy_promotion_gate import build_strategy_promotion_gate
from .strategy_asset_playbook import build_strategy_asset_playbook
from .strategy_lifecycle_projection import build_strategy_lifecycle_projection
from .strategy_stage_service import (
    build_strategy_stage_board,
    promote_strategies_to_demo_trial,
    return_strategies_to_local_sandbox,
)
from .strategy_slots import list_strategy_slots
from .testnet_design_boundary import build_testnet_design_boundary
from .testnet_audit import build_testnet_audit_pack
from .testnet_drill import build_testnet_drill
from .testnet_permission_check import build_testnet_permission_check
from .testnet_readiness_pack import build_testnet_readiness_pack
from .testnet_small_order_simulation import (
    build_testnet_small_order_simulation,
    create_testnet_small_order_simulation,
)
from .top200_minimal_ui_projection import build_top200_minimal_ui_projection
from .usable_strategy_catalog import build_usable_strategy_catalog
from .weakness_action_board import build_weakness_action_board
from .workflow_client import (
    build_workflow_projection as build_quant_workflow_projection,
    get_startup_workflow_recovery_status,
    request_workflow_action,
    resume_incomplete_workflow_runs,
)
from .backtest_screening_projection import build_backtest_screening_projection
from .strategy_validation_hashing import reject_sensitive_fields
from .strategy_validation_status import (
    build_strategy_validation_status,
    import_strategy_validation_campaign,
    resume_strategy_validation_risk,
    run_strategy_validation_approval_action,
    run_strategy_validation_runtime_action,
)
from .strategy_lab_projection import build_strategy_lab_projection
from .state_store import (
    ALLOWED_ARTIFACT_REVIEW_STATUSES,
    ALLOWED_PAPER_OBSERVATION_LOG_TYPES,
    ALLOWED_PAPER_OBSERVATION_TASK_STATUSES,
    ALLOWED_WEAKNESS_ACTION_STATUSES,
    add_paper_observation_log,
    append_audit,
    list_local_sandbox_daily_reports,
    list_manual_execution_tickets,
    list_local_sandbox_runs,
    list_audit,
    list_paper_observation_logs,
    list_weakness_action_tasks,
    update_artifact_review,
    upsert_paper_observation_task,
    update_strategy_status,
    update_weakness_action_task,
)
from .unified_auto_execution_runner import (
    get_unified_auto_execution_status,
    run_unified_auto_execution_action,
    start_unified_auto_execution_runner,
    stop_unified_auto_execution_runner,
    wake_unified_auto_execution_runner,
)
from .workflow_validation_demo import run_workflow_validation_demo_fixture


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


_RESPONSE_CACHE: dict[str, tuple[float, object]] = {}
_DEMO_ENGINEERING_SMOKE_LOCK = threading.Lock()


def _is_fresh_query(query: dict[str, list[str]]) -> bool:
    value = (query.get("fresh") or [""])[0].lower()
    return value in {"1", "true", "yes"}


def _request_is_loopback(client_host: str) -> bool:
    try:
        return ipaddress.ip_address(str(client_host).split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def _cached_payload(key: str, ttl_seconds: float, builder, *, fresh: bool = False) -> object:
    now = time.monotonic()
    if not fresh:
        cached = _RESPONSE_CACHE.get(key)
        if cached and now - cached[0] <= ttl_seconds:
            return cached[1]
    payload = builder()
    _RESPONSE_CACHE[key] = (now, payload)
    return payload


def _safe_int(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _build_demo_instrument_universe_status(*, fresh: bool) -> dict:
    try:
        credentials = load_okx_demo_credentials()
    except (RuntimeError, ValueError):
        return {
            "status": "blocked",
            "environment": "demo",
            "eligibleInstrumentIds": [],
            "blockers": ["okx_demo_credentials_missing"],
            "rawPrivatePayloadStored": False,
        }
    return load_or_refresh_demo_instrument_universe(
        OkxDemoClient(credentials),
        fresh=fresh,
    )


def _load_demo_engineering_smoke_contract() -> dict:
    paths = sorted(DEMO_ENGINEERING_SMOKE_CONTRACT_DIR.glob("*.json"))
    if paths:
        contract = json.loads(paths[-1].read_text(encoding="utf-8"))
        validate_demo_engineering_smoke_contract(contract)
        return contract
    return build_demo_engineering_smoke_contract(
        createdAt=datetime.now(UTC).replace(microsecond=0).isoformat(),
    )


def _find_artifact(index: dict, artifact_id: str) -> dict | None:
    for key in ("artifacts", "topArtifacts"):
        rows = index.get(key)
        if not isinstance(rows, list):
            continue
        for item in rows:
            if isinstance(item, dict) and item.get("artifactId") == artifact_id:
                return item
    return None


def _find_task_pack_task(payload: dict, task_id: str) -> dict | None:
    learning = payload.get("strategyLearningLoop") if isinstance(payload.get("strategyLearningLoop"), dict) else {}
    pack = learning.get("paperObservationTaskPack") if isinstance(learning.get("paperObservationTaskPack"), dict) else {}
    tasks = pack.get("paperObservationTasks") if isinstance(pack.get("paperObservationTasks"), list) else []
    for item in tasks:
        if not isinstance(item, dict) or item.get("taskId") != task_id:
            continue
        return {
            "artifactId": item.get("taskId"),
            "strategyId": item.get("strategyId"),
            "title": item.get("title") or item.get("candidateId") or task_id,
            "displayName": item.get("title") or item.get("candidateId") or task_id,
            "version": item.get("version") or learning.get("version") or "V13.7.43",
            "sourceFile": item.get("sourceReport"),
            "readinessTier": item.get("status") or "planned_paper_observation",
            "metrics": item.get("historicalMetrics") if isinstance(item.get("historicalMetrics"), dict) else {},
        }
    return None


_TOP200_MINIMAL_UI_EXACT_ROUTES = {
    "/api/research-factory/summary",
    "/api/research-factory/runs",
    "/api/strategy/summary",
    "/api/strategy/releases",
    "/api/demo/summary",
    "/api/demo/strategies",
    "/api/demo/positions",
    "/api/demo/orders",
    "/api/demo/universe",
    "/api/demo/reconciliation",
}


def _is_top200_minimal_ui_route(path: str) -> bool:
    return (
        path in _TOP200_MINIMAL_UI_EXACT_ROUTES
        or path.startswith("/api/research-factory/runs/")
        or path.startswith("/api/strategy/releases/")
    )


def _build_top200_minimal_ui_payload(path: str) -> dict:
    projection = build_top200_minimal_ui_projection()
    if path == "/api/research-factory/summary":
        return projection.research_factory_summary()
    if path == "/api/research-factory/runs":
        return projection.research_factory_runs()
    if path.startswith("/api/research-factory/runs/"):
        return projection.research_factory_run(path.rsplit("/", 1)[-1])
    if path == "/api/strategy/summary":
        return projection.strategy_summary()
    if path == "/api/strategy/releases":
        return projection.strategy_releases()
    if path.startswith("/api/strategy/releases/"):
        suffix = path.removeprefix("/api/strategy/releases/")
        if suffix.endswith("/forward-validation"):
            return projection.forward_validation(
                suffix.removesuffix("/forward-validation").rstrip("/")
            )
        return projection.strategy_release(suffix)
    if path == "/api/demo/summary":
        return projection.demo_summary()
    if path == "/api/demo/strategies":
        return projection.demo_strategies()
    if path == "/api/demo/positions":
        return projection.demo_positions()
    if path == "/api/demo/orders":
        return projection.demo_orders()
    if path == "/api/demo/universe":
        return projection.demo_universe()
    if path == "/api/demo/reconciliation":
        return projection.demo_reconciliation()
    raise KeyError(path)


class ConsoleHandler(BaseHTTPRequestHandler):
    server_version = "AlphaPilotControlConsole/13.27.1.6"

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "not_found"}, 404)
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query or "")
        fresh = _is_fresh_query(query)
        if path == "/api/health":
            self._send_json(build_health_payload())
            return
        if _is_top200_minimal_ui_route(path):
            try:
                self._send_json(_build_top200_minimal_ui_payload(path))
            except KeyError:
                self._send_json({"ok": False, "error": "top200_projection_not_found"}, 404)
            except (OSError, RuntimeError, ValueError):
                self._send_json(
                    {
                        "ok": False,
                        "error": "top200_projection_unavailable",
                        "message": "TOP200 projection evidence is unavailable.",
                    },
                    503,
                )
            return
        if path == "/api/backtest-screening":
            campaign_id = str((query.get("campaignId") or [""])[0] or "").strip()
            if not campaign_id:
                self._send_json({"ok": False, "error": "campaign_id_required"}, 400)
                return
            try:
                self._send_json(build_backtest_screening_projection(campaign_id))
            except FileNotFoundError as error:
                self._send_json({"ok": False, "error": "campaign_not_found", "message": str(error)}, 404)
            except ValueError as error:
                self._send_json({"ok": False, "error": "campaign_evidence_invalid", "message": str(error)}, 409)
            return
        if path == "/api/strategy-validation/status":
            campaign_id = str((query.get("campaignId") or [""])[0] or "").strip() or None
            self._send_json(build_strategy_validation_status(campaign_id=campaign_id))
            return
        if path == "/api/strategy-lab":
            self._send_json(_cached_payload(
                "strategy-lab",
                30,
                build_strategy_lab_projection,
                fresh=fresh,
            ))
            return
        if path == "/api/shadow-observation":
            release_id = str((query.get("releaseId") or [""])[0] or "").strip() or None
            try:
                limit = int((query.get("limit") or ["100"])[0])
            except (TypeError, ValueError):
                limit = 100
            store = ShadowObservationStore(DEFAULT_SHADOW_PATH)
            try:
                payload = store.query(release_id=release_id, limit=limit)
            finally:
                store.close()
            self._send_json({**payload, "readOnly": True, "diagnosticOnly": True})
            return
        if path == "/api/local-control/okx-demo-credential-vault":
            if not _request_is_loopback(str(self.client_address[0])):
                self._send_json({"ok": False, "error": "local_host_required"}, 403)
                return
            self._send_json(DEMO_CREDENTIAL_VAULT.metadata())
            return
        if path == "/api/workflow":
            try:
                workflow = _cached_payload(
                    "quant-workflow",
                    2,
                    build_quant_workflow_projection,
                    fresh=fresh,
                )
            except (FileNotFoundError, RuntimeError, ValueError) as error:
                self._send_json(
                    {
                        "version": "V13.27.9",
                        "source": "quant_workflow_unavailable",
                        "loadError": str(error),
                        "summary": {},
                        "items": [],
                        "archivedItems": [],
                        "safetyBoundary": SAFETY_BOUNDARY,
                    },
                    503,
                )
                return
            self._send_json(workflow)
            return
        if path == "/api/strategies":
            self._send_json(_cached_payload(
                "strategies",
                20,
                lambda: {"strategies": scan_quant_engine()["strategies"]},
                fresh=fresh,
            ))
            return
        if path == "/api/reports":
            self._send_json(_cached_payload(
                "reports",
                20,
                lambda: {"reports": scan_quant_engine()["reports"]},
                fresh=fresh,
            ))
            return
        if path == "/api/mobile/status":
            self._send_json(_cached_payload(
                "mobile-status",
                15,
                lambda: {
                    **build_mobile_status(scan_quant_engine()),
                    "automaticExecution": get_unified_auto_execution_status(),
                },
                fresh=fresh,
            ))
            return
        if path == "/api/auto-execution/runtime":
            self._send_json(get_unified_auto_execution_status())
            return
        if path == "/api/execution-control/status":
            self._send_json(_cached_payload(
                "execution-control-status",
                1,
                get_execution_control_status,
                fresh=fresh,
            ))
            return
        if path == "/api/execution-control/workflow-validation-demo":
            self._send_json(run_workflow_validation_demo_fixture())
            return
        if path == "/api/runtime":
            payload = scan_quant_engine()
            self._send_json({
                "runtimeStatus": payload["runtimeStatus"],
                "signalTape": payload["signalTape"],
                "paperObservationLedger": payload["paperObservationLedger"],
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/strategy-artifacts":
            self._send_json(_cached_payload(
                "strategy-artifacts",
                30,
                lambda: {
                    "strategyArtifactIndex": scan_quant_engine()["strategyArtifactIndex"],
                    "safetyBoundary": SAFETY_BOUNDARY,
                },
                fresh=fresh,
            ))
            return
        if path == "/api/paper-observation-tasks":
            payload = scan_quant_engine()
            index = payload["strategyArtifactIndex"]
            tasks = []
            artifacts = index.get("artifacts") if isinstance(index.get("artifacts"), list) else []
            for item in artifacts:
                task = item.get("paperObservationTask") if isinstance(item.get("paperObservationTask"), dict) else None
                if task and (task.get("taskStatus") != "planned" or item.get("reviewStatus") == "paper_observation"):
                    tasks.append({
                        **task,
                        "title": item.get("displayName") or item.get("title"),
                        "originalTitle": item.get("title"),
                        "displaySubtitle": item.get("displaySubtitle"),
                        "strategyId": item.get("strategyId"),
                        "version": item.get("version"),
                        "metrics": item.get("metrics") if isinstance(item.get("metrics"), dict) else {},
                    })
            self._send_json(legacy_read_projection({"tasks": tasks, "safetyBoundary": SAFETY_BOUNDARY}))
            return
        if path == "/api/forward-validation":
            payload = build_mobile_status(scan_quant_engine())
            self._send_json({
                "forwardValidation": payload.get("forwardValidation"),
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/ml-coverage":
            payload = scan_quant_engine()
            index = payload.get("strategyArtifactIndex") if isinstance(payload.get("strategyArtifactIndex"), dict) else {}
            summary = index.get("summary") if isinstance(index.get("summary"), dict) else {}
            self._send_json({
                "mlCoverage": summary.get("mlCoverage") if isinstance(summary.get("mlCoverage"), dict) else {},
                "strategyArtifactIndex": index,
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/candidate-queue":
            self._send_json(_cached_payload(
                "candidate-queue",
                30,
                lambda: {
                    "strategyCandidateQueue": scan_quant_engine().get("strategyCandidateQueue") or {},
                    "safetyBoundary": SAFETY_BOUNDARY,
                },
                fresh=fresh,
            ))
            return
        if path == "/api/short-cycle-candidates":
            self._send_json(_cached_payload(
                "short-cycle-candidates",
                30,
                lambda: build_short_cycle_candidate_pool(scan_quant_engine()),
                fresh=fresh,
            ))
            return
        if path == "/api/usable-strategy-catalog":
            self._send_json(_cached_payload(
                "usable-strategy-catalog",
                30,
                build_usable_strategy_catalog,
                fresh=fresh,
            ))
            return
        if path == "/api/strategy-lifecycle":
            self._send_json(_cached_payload(
                "strategy-lifecycle",
                15,
                build_strategy_lifecycle_projection,
                fresh=fresh,
            ))
            return
        if path == "/api/simulation-bridge":
            self._send_json(_cached_payload(
                "simulation-bridge",
                30,
                build_simulation_bridge,
                fresh=fresh,
            ))
            return
        if path == "/api/simulation-review":
            self._send_json(_cached_payload(
                "simulation-review",
                30,
                build_simulation_review,
                fresh=fresh,
            ))
            return
        if path == "/api/simulation-review/strategies":
            review = build_simulation_review()
            self._send_json({
                "version": review["version"],
                "source": review["source"],
                "strategies": review["queue"],
                "thresholds": review["thresholds"],
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/simulation-review/queue":
            review = build_simulation_review()
            self._send_json({
                "version": review["version"],
                "source": review["source"],
                "queue": review["queue"],
                "summary": review["summary"],
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path.startswith("/api/simulation-review/strategies/"):
            strategy_id = path.rsplit("/", 1)[-1]
            strategy = build_simulation_review_strategy(strategy_id)
            if strategy is None:
                self._send_json({"error": "strategy_not_found"}, 404)
                return
            self._send_json(strategy)
            return
        if path == "/api/closed-sample-replay":
            query = parse_qs(parsed.query or "")
            strategy_id = str((query.get("strategyId") or [""])[0]).strip() or None
            limit = _safe_int((query.get("limit") or [80])[0], 80)
            self._send_json(_cached_payload(
                f"closed-sample-replay:{strategy_id or 'all'}:{limit}",
                30,
                lambda: build_closed_sample_replay(strategy_id=strategy_id, limit=limit),
                fresh=fresh,
            ))
            return
        if path == "/api/closed-sample-replay/strategies":
            payload = build_closed_sample_replay()
            self._send_json({
                "version": payload["version"],
                "source": payload["source"],
                "strategies": payload["strategies"],
                "summary": payload["summary"],
                "sampleSchema": payload["sampleSchema"],
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/closed-sample-replay/samples":
            query = parse_qs(parsed.query or "")
            limit = _safe_int((query.get("limit") or [100])[0], 100)
            payload = build_closed_sample_replay(limit=limit)
            self._send_json({
                "version": payload["version"],
                "source": payload["source"],
                "samples": payload["samples"],
                "sampleSchema": payload["sampleSchema"],
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/weakness-action-board":
            query = parse_qs(parsed.query or "")
            limit = _safe_int((query.get("limit") or [200])[0], 200)
            self._send_json(_cached_payload(
                f"weakness-action-board:{limit}",
                30,
                lambda: build_weakness_action_board(limit=limit),
                fresh=fresh,
            ))
            return
        if path == "/api/weakness-action-board/actions":
            payload = build_weakness_action_board()
            self._send_json({
                "version": payload["version"],
                "source": payload["source"],
                "summary": payload["summary"],
                "actions": payload["actions"],
                "dryRunApproved": False,
                "liveTradingApproved": False,
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/weakness-action-board/tasks":
            self._send_json({
                "version": "V13.8.1",
                "source": "alphapilot_control_console_v13_8_1",
                "tasks": list_weakness_action_tasks(),
                "allowedStatuses": sorted(ALLOWED_WEAKNESS_ACTION_STATUSES),
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/research-action-executor":
            self._send_json(_cached_payload(
                "research-action-executor",
                30,
                lambda: build_research_action_executor(apply_updates=False),
                fresh=fresh,
            ))
            return
        if path == "/api/candidate-promotion-gate":
            self._send_json(_cached_payload(
                "candidate-promotion-gate",
                30,
                build_candidate_promotion_gate_v2,
                fresh=fresh,
            ))
            return
        if path == "/api/simulation-command-center":
            self._send_json(_cached_payload(
                "simulation-command-center",
                30,
                build_simulation_command_center,
                fresh=fresh,
            ))
            return
        if path == "/api/testnet-readiness-pack":
            self._send_json(_cached_payload("testnet-readiness-pack", 30, build_testnet_readiness_pack, fresh=fresh))
            return
        if path == "/api/testnet-design-boundary":
            self._send_json(_cached_payload("testnet-design-boundary", 60, build_testnet_design_boundary, fresh=fresh))
            return
        if path == "/api/pre-live-preparation-pack":
            self._send_json(_cached_payload("pre-live-preparation-pack", 30, build_pre_live_preparation_pack, fresh=fresh))
            return
        if path == "/api/testnet-drill":
            self._send_json(_cached_payload("testnet-drill", 60, build_testnet_drill, fresh=fresh))
            return
        if path == "/api/testnet-audit-pack":
            self._send_json(_cached_payload("testnet-audit-pack", 60, build_testnet_audit_pack, fresh=fresh))
            return
        if path == "/api/testnet-permission-check":
            self._send_json(_cached_payload("testnet-permission-check", 30, build_testnet_permission_check, fresh=fresh))
            return
        if path == "/api/testnet-small-order-simulation":
            self._send_json(_cached_payload("testnet-small-order-simulation", 30, build_testnet_small_order_simulation, fresh=fresh))
            return
        if path == "/api/exchange-demo/simulation":
            self._send_json(_cached_payload("exchange-demo-simulation", 15, build_exchange_demo_simulation, fresh=fresh))
            return
        if path == "/api/demo-workflow":
            self._send_json(_cached_payload(
                "demo-workflow",
                5,
                lambda: {
                    **build_demo_workflow_status(),
                    "automaticExecution": get_unified_auto_execution_status().get("environments", {}).get("okx_demo", {}),
                },
                fresh=fresh,
            ))
            return
        if path == "/api/evolution-demo":
            self._send_json(_cached_payload("evolution-demo", 5, build_evolution_demo_status, fresh=fresh))
            return
        if path == "/api/demo-instrument-universe":
            if not _request_is_loopback(str(self.client_address[0])):
                self._send_json({"ok": False, "error": "local_host_required"}, 403)
                return
            projection = _build_demo_instrument_universe_status(fresh=fresh)
            self._send_json(projection, 200 if projection.get("status") == "usable" else 503)
            return
        if path == "/api/demo-engineering-smoke":
            if not _request_is_loopback(str(self.client_address[0])):
                self._send_json({"ok": False, "error": "local_host_required"}, 403)
                return
            self._send_json(build_demo_engineering_smoke_status())
            return
        if path == "/api/live-candidates":
            self._send_json(_cached_payload("live-candidates", 5, build_live_candidate_status, fresh=fresh))
            return
        if path == "/api/live-safety":
            self._send_json(_cached_payload("live-safety", 5, build_live_safety_status, fresh=fresh))
            return
        if path == "/api/live-canary":
            self._send_json(_cached_payload(
                "live-canary",
                5,
                lambda: {
                    **build_live_canary_status(),
                    "automaticExecution": get_unified_auto_execution_status().get("environments", {}).get("okx_live", {}),
                },
                fresh=fresh,
            ))
            return
        if path == "/api/execution-outcomes":
            self._send_json(_cached_payload(
                "execution-outcomes",
                5,
                build_execution_outcome_status,
                fresh=fresh,
            ))
            return
        if path == "/api/risk-profiles":
            self._send_json(_cached_payload("risk-profiles", 5, build_risk_profile_status, fresh=fresh))
            return
        if path == "/api/no-key-pre-live":
            self._send_json(_cached_payload("no-key-pre-live", 15, build_no_key_pre_live_workbench, fresh=fresh))
            return
        if path == "/api/auto-execution-engine":
            self._send_json(_cached_payload("auto-execution-engine", 15, build_auto_execution_engine, fresh=fresh))
            return
        if path == "/api/auto-execution-lifecycle":
            self._send_json(_cached_payload(
                "auto-execution-lifecycle",
                10,
                build_auto_execution_lifecycle_monitor,
                fresh=fresh,
            ))
            return
        if path == "/api/auto-execution-review":
            self._send_json(_cached_payload(
                "auto-execution-review",
                10,
                build_auto_execution_review,
                fresh=fresh,
            ))
            return
        if path == "/api/auto-execution-learning":
            self._send_json(_cached_payload(
                "auto-execution-learning",
                10,
                build_auto_execution_learning,
                fresh=fresh,
            ))
            return
        if path == "/api/research-execution-pipeline":
            self._send_json(_cached_payload(
                "research-execution-pipeline",
                30,
                lambda: build_research_execution_pipeline(apply_updates=False),
                fresh=fresh,
            ))
            return
        if path.startswith("/api/closed-sample-replay/strategies/"):
            strategy_id = path.rsplit("/", 1)[-1]
            strategy = build_closed_sample_strategy_detail(strategy_id)
            if strategy is None:
                self._send_json({"error": "strategy_not_found"}, 404)
                return
            self._send_json(strategy)
            return
        if path == "/api/strategy-promotion-gate":
            self._send_json(_cached_payload(
                "strategy-promotion-gate",
                30,
                lambda: build_strategy_promotion_gate(scan_quant_engine()),
                fresh=fresh,
            ))
            return
        if path == "/api/strategy-asset-playbook":
            self._send_json(_cached_payload(
                "strategy-asset-playbook",
                60,
                build_strategy_asset_playbook,
                fresh=fresh,
            ))
            return
        if path == "/api/research-task-board":
            self._send_json(_cached_payload(
                "research-task-board",
                30,
                lambda: {
                    "researchTaskBoard": scan_quant_engine().get("researchTaskBoard") or {},
                    "safetyBoundary": SAFETY_BOUNDARY,
                },
                fresh=fresh,
            ))
            return
        if path == "/api/strategy-learning-loop":
            self._send_json(_cached_payload(
                "strategy-learning-loop",
                60,
                lambda: {
                    "strategyLearningLoop": scan_quant_engine().get("strategyLearningLoop") or {},
                    "safetyBoundary": SAFETY_BOUNDARY,
                },
                fresh=fresh,
            ))
            return
        if path == "/api/paper-observation-logs":
            query = parse_qs(parsed.query or "")
            artifact_id = str((query.get("artifactId") or [""])[0]).strip()
            logs = list_paper_observation_logs(artifact_id or None)
            if isinstance(logs, dict):
                flattened: list[dict] = []
                for rows in logs.values():
                    flattened.extend(row for row in rows if isinstance(row, dict))
                logs = sorted(flattened, key=lambda item: str(item.get("createdAt") or ""), reverse=True)[:200]
            self._send_json(legacy_read_projection({"logs": logs, "safetyBoundary": SAFETY_BOUNDARY}))
            return
        if path == "/api/local-sandbox/runs":
            query = parse_qs(parsed.query or "")
            limit = _safe_int((query.get("limit") or [20])[0], 20)
            self._send_json(legacy_read_projection({
                "runs": list_local_sandbox_runs(limit),
                "safetyBoundary": SAFETY_BOUNDARY,
            }))
            return
        if path == "/api/local-sandbox/daily-report":
            query = parse_qs(parsed.query or "")
            limit = _safe_int((query.get("limit") or [10])[0], 10)
            reports = list_local_sandbox_daily_reports(limit)
            self._send_json(legacy_read_projection({
                "latestReport": reports[0] if reports else {},
                "reports": reports,
                "safetyBoundary": SAFETY_BOUNDARY,
            }))
            return
        if path == "/api/local-sandbox/auto-runner":
            self._send_json(get_local_sandbox_auto_runner_status())
            return
        if path == "/api/strategy-stage-board":
            self._send_json(build_strategy_stage_board())
            return
        if path == "/api/local-sandbox/quality-center":
            self._send_json(legacy_read_projection(_cached_payload(
                "local-sandbox-quality-center",
                45,
                build_local_sandbox_quality_center,
                fresh=fresh,
            )))
            return
        if path == "/api/local-sandbox/concentration-review":
            self._send_json(legacy_read_projection(_cached_payload(
                "local-sandbox-concentration-review",
                45,
                build_local_sandbox_concentration_review,
                fresh=fresh,
            )))
            return
        if path == "/api/local-sandbox/result-review":
            self._send_json(legacy_read_projection(_cached_payload(
                "local-sandbox-result-review",
                45,
                build_local_sandbox_result_review,
                fresh=fresh,
            )))
            return
        if path == "/api/live-readiness":
            self._send_json(_cached_payload(
                "live-readiness",
                30,
                lambda: build_live_readiness(scan_quant_engine()),
                fresh=fresh,
            ))
            return
        if path == "/api/forward-review":
            self._send_json(_cached_payload(
                "forward-review",
                30,
                lambda: build_forward_review(scan_quant_engine()),
                fresh=fresh,
            ))
            return
        if path == "/api/manual-execution-tickets":
            query = parse_qs(parsed.query or "")
            limit = _safe_int((query.get("limit") or [20])[0], 20)
            self._send_json({
                "tickets": list_manual_execution_tickets(limit),
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/mobile/connection-info":
            self._send_json(build_mobile_connection_info(str(self.server.server_address[0]), int(self.server.server_address[1])))
            return
        if path == "/api/audit":
            self._send_json({"events": list_audit()})
            return
        if path == "/api/exchanges":
            self._send_json(list_public_exchange_sources())
            return
        if path == "/api/strategy-slots":
            self._send_json(list_strategy_slots())
            return
        if path in {"/", "/index.html"}:
            self._send_static(WEB_DIR / "index.html")
            return
        static_path = (WEB_DIR / path.lstrip("/")).resolve()
        if WEB_DIR.resolve() in static_path.parents:
            self._send_static(static_path)
            return
        self._send_json({"error": "not_found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        release_control_action: str | None = None
        release_control_id = ""
        if parsed.path.startswith("/api/strategy/releases/") and parsed.path.endswith(
            "/approve"
        ):
            release_control_action = "approve"
            release_control_id = parsed.path.removeprefix(
                "/api/strategy/releases/"
            ).removesuffix("/approve").strip("/")
        elif parsed.path.startswith("/api/demo/releases/"):
            suffix = parsed.path.removeprefix("/api/demo/releases/").strip("/")
            if suffix.endswith("/arm"):
                release_control_action = "arm"
                release_control_id = suffix.removesuffix("/arm").strip("/")
            elif suffix.endswith("/disarm"):
                release_control_action = "disarm"
                release_control_id = suffix.removesuffix("/disarm").strip("/")
        if release_control_action is not None:
            payload = self._read_body_json()
            if not _request_is_loopback(str(self.client_address[0])):
                self._send_json({"ok": False, "error": "local_host_required"}, 403)
                return
            try:
                reject_sensitive_fields(payload)
                if not release_control_id:
                    raise ValueError("releaseId is required in the route")
                if release_control_action == "approve":
                    result = approve_final_demo_release(release_control_id, payload)
                elif release_control_action == "arm":
                    result = arm_final_demo_release(release_control_id, payload)
                else:
                    result = disarm_final_demo_release(release_control_id, payload)
            except (KeyError, PermissionError, RuntimeError, ValueError, OSError) as error:
                self._send_json(
                    {
                        "ok": False,
                        "error": type(error).__name__,
                        "message": str(error),
                    },
                    409,
                )
                return
            _RESPONSE_CACHE.clear()
            self._send_json(result)
            return
        strategy_validation_routes = {
            "/api/strategy-validation-releases/import",
            "/api/strategy-validation-releases/approve",
            "/api/strategy-validation-releases/revoke",
            "/api/strategy-validation-runtime/arm",
            "/api/strategy-validation-runtime/disarm",
            "/api/strategy-validation-risk/resume",
        }
        if parsed.path in strategy_validation_routes:
            payload = self._read_body_json()
            if not _request_is_loopback(str(self.client_address[0])):
                self._send_json({"ok": False, "error": "local_host_required"}, 403)
                return
            try:
                reject_sensitive_fields(payload)
            except ValueError as error:
                self._send_json({"ok": False, "error": "sensitive_field_forbidden", "message": str(error)}, 400)
                return
            try:
                if parsed.path.endswith("/import"):
                    result = import_strategy_validation_campaign(payload)
                elif parsed.path.endswith("/approve"):
                    result = run_strategy_validation_approval_action("approve", payload)
                elif parsed.path.endswith("/revoke"):
                    result = run_strategy_validation_approval_action("revoke", payload)
                elif parsed.path.endswith("/arm"):
                    result = run_strategy_validation_runtime_action("arm", payload)
                elif parsed.path.endswith("/disarm"):
                    result = run_strategy_validation_runtime_action("disarm", payload)
                else:
                    result = resume_strategy_validation_risk(payload)
            except FileNotFoundError as error:
                self._send_json({"ok": False, "error": "campaign_not_found", "message": str(error)}, 404)
                return
            except (KeyError, PermissionError, RuntimeError, ValueError) as error:
                self._send_json({"ok": False, "error": type(error).__name__, "message": str(error)}, 409)
                return
            self._send_json(result)
            return
        if parsed.path in RETIRED_LOCAL_SIMULATION_POST_ROUTES:
            self._read_body_json()
            self._send_json(retired_write_response(), 410)
            return
        if parsed.path in {
            "/api/demo-engineering-smoke/run",
            "/api/demo-engineering-smoke/reconcile",
        }:
            payload = self._read_body_json()
            if not _request_is_loopback(str(self.client_address[0])):
                self._send_json({"ok": False, "error": "local_host_required"}, 403)
                return
            is_run = parsed.path.endswith("/run")
            expected_confirmation = (
                "RUN_DEMO_ENGINEERING_SMOKE"
                if is_run
                else "RECONCILE_DEMO_ENGINEERING_SMOKE"
            )
            if payload.get("confirmation") != expected_confirmation:
                self._send_json({"ok": False, "error": "explicit_confirmation_required"}, 409)
                return
            if not _DEMO_ENGINEERING_SMOKE_LOCK.acquire(blocking=False):
                self._send_json({"ok": False, "error": "engineering_smoke_already_running"}, 409)
                return
            try:
                try:
                    credentials = load_okx_demo_credentials()
                except (RuntimeError, ValueError):
                    self._send_json({"ok": False, "error": "okx_demo_credentials_missing"}, 409)
                    return
                universe = _build_demo_instrument_universe_status(fresh=True)
                if universe.get("status") != "usable" or not universe.get("eligibleInstrumentIds"):
                    self._send_json({
                        "ok": False,
                        "error": "demo_instrument_universe_blocked",
                        "blockers": universe.get("blockers") or [],
                    }, 409)
                    return
                client = OkxDemoClient(credentials)
                if is_run:
                    result = run_demo_engineering_smoke(
                        client=client,
                        contract=_load_demo_engineering_smoke_contract(),
                        universe=universe,
                        deterministicTrigger=True,
                    )
                    self._send_json({
                        "ok": result.get("status") == "completed",
                        "engineeringSmoke": result,
                    })
                    return
                result = reconcile_demo_engineering_smoke(client=client)
                self._send_json({
                    "ok": result.get("status") == "usable",
                    "engineeringSmoke": result,
                })
                return
            except (KeyError, PermissionError, RuntimeError, ValueError) as error:
                self._send_json({
                    "ok": False,
                    "error": type(error).__name__,
                    "message": str(error),
                }, 409)
                return
            finally:
                _DEMO_ENGINEERING_SMOKE_LOCK.release()
        if parsed.path == "/api/local-control/delete-okx-demo-credential-vault":
            payload = self._read_body_json()
            if not _request_is_loopback(str(self.client_address[0])):
                self._send_json({"ok": False, "error": "local_host_required"}, 403)
                return
            if payload.get("confirmation") != "DELETE_OKX_DEMO_CREDENTIAL":
                self._send_json({"ok": False, "error": "confirmation_required"}, 409)
                return
            try:
                deleted = DEMO_CREDENTIAL_VAULT.delete()
                metadata = DEMO_CREDENTIAL_VAULT.metadata()
            except DemoCredentialVaultError as error:
                self._send_json({"ok": False, "error": error.category}, 409)
                return
            append_audit("demo_vault_deleted", {"processId": os.getpid(), "deleted": deleted})
            self._send_json({"ok": True, "status": "deleted", "metadata": metadata})
            return
        if parsed.path == "/api/local-control/open-okx-demo-launcher":
            self._read_body_json()
            result = LOCAL_DEMO_LAUNCHER.open(
                str(self.client_address[0]),
                current_pid=os.getpid(),
                port=int(self.server.server_address[1]),
                mobile=str(self.server.server_address[0]) in {"0.0.0.0", "::"},
            )
            status = 202
            if not result.get("ok"):
                status = {
                    "local_host_required": 403,
                    "launcher_already_open": 409,
                    "invalid_launcher_context": 409,
                    "launcher_script_missing": 500,
                    "launcher_start_failed": 500,
                }.get(str(result.get("error") or ""), 500)
            self._send_json(result, status)
            return
        if parsed.path == "/api/workflow/action":
            payload = self._read_body_json()
            action = str(payload.get("action") or "")
            try:
                result = request_workflow_action(action, payload)
                _RESPONSE_CACHE.pop("quant-workflow", None)
                workflow = build_quant_workflow_projection()
            except (FileNotFoundError, RuntimeError, ValueError) as error:
                self._send_json(
                    {
                        "ok": False,
                        "error": type(error).__name__,
                        "message": str(error),
                        "safetyBoundary": SAFETY_BOUNDARY,
                    },
                    409,
                )
                return
            self._send_json(
                {
                    "ok": True,
                    "action": action,
                    "result": result,
                    "workflow": workflow,
                    "safetyBoundary": SAFETY_BOUNDARY,
                }
            )
            return
        if parsed.path == "/api/import":
            self._send_json(import_now())
            return
        if parsed.path == "/api/forward-review/refresh":
            self._read_body_json()
            self._send_json(refresh_forward_review())
            return
        if parsed.path == "/api/strategy-status":
            payload = self._read_body_json()
            strategy_id = str(payload.get("strategyId") or "").strip()
            status = str(payload.get("status") or "").strip()
            note = str(payload.get("note") or "").strip()
            if not strategy_id:
                self._send_json({"error": "strategyId_required"}, 400)
                return
            if status not in ALLOWED_STRATEGY_STATUSES:
                self._send_json({"error": "unsupported_status", "allowed": sorted(ALLOWED_STRATEGY_STATUSES)}, 400)
                return
            updated = update_strategy_status(strategy_id, status, note)
            self._send_json({"updated": updated, "safetyBoundary": SAFETY_BOUNDARY})
            return
        if parsed.path == "/api/strategy-artifact-review":
            payload = self._read_body_json()
            artifact_id = str(payload.get("artifactId") or "").strip()
            review_status = str(payload.get("reviewStatus") or "").strip()
            note = str(payload.get("note") or "").strip()
            if not artifact_id:
                self._send_json({"error": "artifactId_required"}, 400)
                return
            if review_status not in ALLOWED_ARTIFACT_REVIEW_STATUSES:
                self._send_json({
                    "error": "unsupported_review_status",
                    "allowed": sorted(ALLOWED_ARTIFACT_REVIEW_STATUSES),
                }, 400)
                return
            if review_status == "paper_observation":
                self._send_json(retired_write_response(), 410)
                return
            updated = update_artifact_review(artifact_id, review_status, note)
            latest = scan_quant_engine()
            self._send_json({
                "updated": updated,
                "strategyArtifactIndex": latest["strategyArtifactIndex"],
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if parsed.path == "/api/paper-observation-task":
            payload = self._read_body_json()
            artifact_id = str(payload.get("artifactId") or "").strip()
            task_status = str(payload.get("taskStatus") or "").strip()
            note = str(payload.get("note") or "").strip()
            if not artifact_id:
                self._send_json({"error": "artifactId_required"}, 400)
                return
            if task_status not in ALLOWED_PAPER_OBSERVATION_TASK_STATUSES:
                self._send_json({
                    "error": "unsupported_task_status",
                    "allowed": sorted(ALLOWED_PAPER_OBSERVATION_TASK_STATUSES),
                }, 400)
                return
            latest = scan_quant_engine()
            artifact = _find_artifact(latest["strategyArtifactIndex"], artifact_id) or _find_task_pack_task(latest, artifact_id)
            updated = upsert_paper_observation_task(
                artifact_id=artifact_id,
                task_status=task_status,
                note=note,
                target_sample_count=_safe_int(payload.get("targetSampleCount"), 50),
                observation_days=_safe_int(payload.get("observationDays"), 60),
                artifact=artifact,
            )
            latest = scan_quant_engine()
            self._send_json({
                "updated": updated,
                "strategyArtifactIndex": latest["strategyArtifactIndex"],
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if parsed.path == "/api/paper-observation-log":
            payload = self._read_body_json()
            artifact_id = str(payload.get("artifactId") or "").strip()
            log_type = str(payload.get("logType") or "no_signal").strip()
            note = str(payload.get("note") or "").strip()
            outcome = str(payload.get("outcome") or "").strip()
            if not artifact_id:
                self._send_json({"error": "artifactId_required"}, 400)
                return
            if log_type not in ALLOWED_PAPER_OBSERVATION_LOG_TYPES:
                self._send_json({
                    "error": "unsupported_log_type",
                    "allowed": sorted(ALLOWED_PAPER_OBSERVATION_LOG_TYPES),
                }, 400)
                return
            latest = scan_quant_engine()
            artifact = _find_artifact(latest["strategyArtifactIndex"], artifact_id) or _find_task_pack_task(latest, artifact_id)
            updated = add_paper_observation_log(
                artifact_id=artifact_id,
                log_type=log_type,
                note=note,
                signal_observed=bool(payload.get("signalObserved")) if "signalObserved" in payload else None,
                rule_matched=bool(payload.get("ruleMatched")) if "ruleMatched" in payload else None,
                outcome=outcome,
                artifact=artifact,
            )
            latest = scan_quant_engine()
            self._send_json({
                "updated": updated,
                "strategyArtifactIndex": latest["strategyArtifactIndex"],
                "strategyLearningLoop": latest.get("strategyLearningLoop") or {},
                "paperObservationTasks": build_mobile_status(latest).get("paperObservationTasks"),
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if parsed.path == "/api/weakness-action-task":
            payload = self._read_body_json()
            action_id = str(payload.get("actionId") or "").strip()
            task_status = str(payload.get("taskStatus") or "").strip()
            note = str(payload.get("note") or "").strip()
            owner = str(payload.get("owner") or "local_research").strip() or "local_research"
            if not action_id:
                self._send_json({"error": "actionId_required"}, 400)
                return
            if task_status not in ALLOWED_WEAKNESS_ACTION_STATUSES:
                self._send_json({
                    "error": "unsupported_task_status",
                    "allowed": sorted(ALLOWED_WEAKNESS_ACTION_STATUSES),
                }, 400)
                return
            updated = update_weakness_action_task(action_id, task_status, note, owner)
            self._send_json({
                "updated": updated,
                "weaknessActionBoard": build_weakness_action_board(),
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if parsed.path == "/api/research-action-executor/run":
            payload = self._read_body_json()
            apply_updates = bool(payload.get("applyUpdates", True))
            self._send_json(build_research_action_executor(apply_updates=apply_updates))
            return
        if parsed.path == "/api/research-execution-pipeline/run":
            payload = self._read_body_json()
            apply_updates = bool(payload.get("applyUpdates", True))
            self._send_json(build_research_execution_pipeline(apply_updates=apply_updates))
            return
        if parsed.path == "/api/local-sandbox/run":
            payload = self._read_body_json()
            run = run_local_sandbox(payload)
            latest = scan_quant_engine()
            daily_report = build_local_sandbox_daily_report(latest.get("strategyLearningLoop") or {})
            self._send_json({
                "localSandboxRun": run,
                "localSandboxDailyReport": daily_report,
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if parsed.path == "/api/local-sandbox/build-daily-report":
            self._read_body_json()
            latest = scan_quant_engine()
            report = build_local_sandbox_daily_report(latest.get("strategyLearningLoop") or {})
            self._send_json({
                "localSandboxDailyReport": report,
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if parsed.path == "/api/local-sandbox/auto-runner":
            payload = self._read_body_json()
            self._send_json(update_local_sandbox_auto_runner_settings(payload))
            return
        if parsed.path == "/api/local-sandbox/auto-runner/run-now":
            self._read_body_json()
            self._send_json(run_local_sandbox_auto_runner_now())
            return
        if parsed.path == "/api/strategy-stage/promote-demo":
            payload = self._read_body_json()
            strategy_ids = payload.get("strategyIds")
            self._send_json(promote_strategies_to_demo_trial(
                strategy_ids if isinstance(strategy_ids, list) else None,
                reason=str(payload.get("reason") or "manual_demo_trial_promotion"),
            ))
            return
        if parsed.path == "/api/strategy-stage/return-sandbox":
            payload = self._read_body_json()
            strategy_ids = payload.get("strategyIds")
            if not isinstance(strategy_ids, list) or not strategy_ids:
                self._send_json({"error": "strategy_ids_required"}, 400)
                return
            self._send_json(return_strategies_to_local_sandbox(
                strategy_ids,
                reason=str(payload.get("reason") or "manual_return_to_sandbox"),
            ))
            return
        if parsed.path == "/api/exchanges/probe-public":
            payload = self._read_body_json()
            exchanges = payload.get("exchanges")
            if not isinstance(exchanges, list):
                exchanges = None
            symbol = str(payload.get("symbol") or "").strip() or "BTC/USDT:USDT"
            timeframe = str(payload.get("timeframe") or "").strip() or "1h"
            limit = _safe_int(payload.get("limit") or 2, 2)
            self._send_json(probe_public_exchanges(exchanges=exchanges, symbol=symbol, timeframe=timeframe, limit=limit))
            return
        if parsed.path == "/api/manual-execution-ticket":
            payload = self._read_body_json()
            latest = scan_quant_engine()
            try:
                ticket = create_manual_execution_ticket(payload, latest)
            except ValueError as error:
                self._send_json({"error": str(error)}, 400)
                return
            except PermissionError as error:
                self._send_json({
                    "error": str(error),
                    "liveReadiness": build_live_readiness(latest),
                    "safetyBoundary": SAFETY_BOUNDARY,
                }, 409)
                return
            self._send_json({
                "ticket": ticket,
                "liveReadiness": build_live_readiness(latest),
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if parsed.path == "/api/pre-live-order-lifecycle/simulate":
            payload = self._read_body_json()
            self._send_json(simulate_pre_live_order_lifecycle(payload))
            return
        if parsed.path == "/api/pre-live-order-lifecycle/rehearse":
            payload = self._read_body_json()
            self._send_json(create_pre_live_rehearsal(payload))
            return
        if parsed.path == "/api/testnet-small-order-simulation/rehearse":
            payload = self._read_body_json()
            self._send_json(create_testnet_small_order_simulation(payload))
            return
        if parsed.path == "/api/exchange-demo/read-only-check":
            self._send_json(run_exchange_demo_readonly_check())
            return
        if parsed.path == "/api/exchange-demo/scan-candidates":
            payload = self._read_body_json()
            self._send_json(scan_exchange_demo_candidates(payload))
            return
        if parsed.path == "/api/demo-workflow/action":
            payload = self._read_body_json()
            _RESPONSE_CACHE.clear()
            self._send_json(run_demo_workflow_action(payload))
            return
        if parsed.path == "/api/auto-execution/action":
            payload = self._read_body_json()
            _RESPONSE_CACHE.clear()
            try:
                result = run_unified_auto_execution_action(payload)
            except (KeyError, RuntimeError, ValueError, PermissionError) as error:
                self._send_json({"ok": False, "error": type(error).__name__, "message": str(error)}, 409)
                return
            self._send_json(result, 200 if result.get("ok") else 409)
            return
        if parsed.path == "/api/execution-control/action":
            payload = self._read_body_json()
            _RESPONSE_CACHE.clear()
            result = run_execution_control_action(payload)
            status_code = 200 if result.get("ok") else (409 if result.get("status") == "conflict" else 422)
            self._send_json(result, status_code)
            return
        if parsed.path == "/api/no-key-pre-live/scan":
            payload = self._read_body_json()
            self._send_json(scan_no_key_pre_live_candidates(payload))
            return
        if parsed.path == "/api/no-key-pre-live/create-ticket":
            payload = self._read_body_json()
            self._send_json(create_no_key_observation_ticket(payload))
            return
        if parsed.path == "/api/auto-execution-engine/run":
            payload = self._read_body_json()
            self._send_json(run_auto_execution_engine(payload))
            return
        if parsed.path == "/api/auto-execution-lifecycle/advance":
            payload = self._read_body_json()
            lifecycle_advance = advance_auto_execution_lifecycle(payload)
            _RESPONSE_CACHE.clear()
            self._send_json({
                "ok": True,
                "lifecycleAdvance": lifecycle_advance,
                "autoExecutionEngine": build_auto_execution_engine(),
                "autoExecutionLifecycle": build_auto_execution_lifecycle_monitor(),
                "autoExecutionReview": build_auto_execution_review(),
                "autoExecutionLearning": build_auto_execution_learning(),
                "safetyBoundary": lifecycle_advance.get("safetyBoundary") or SAFETY_BOUNDARY,
            })
            return
        if parsed.path == "/api/exchange-demo/order":
            payload = self._read_body_json()
            self._send_json(submit_exchange_demo_order(payload))
            return
        if parsed.path == "/api/exchange-demo/order-status":
            payload = self._read_body_json()
            self._send_json(query_exchange_demo_order_status(payload))
            return
        if parsed.path == "/api/exchange-demo/emergency-stop":
            payload = self._read_body_json()
            self._send_json(run_exchange_demo_emergency_drill(payload))
            return
        if parsed.path == "/api/evolution-demo/run":
            payload = self._read_body_json()
            _RESPONSE_CACHE.clear()
            self._send_json(run_evolution_demo_cycle(payload))
            return
        if parsed.path == "/api/evolution-demo/kill-switch":
            payload = self._read_body_json()
            _RESPONSE_CACHE.clear()
            self._send_json(activate_evolution_demo_kill_switch(str(payload.get("reason") or "console_request")))
            return
        if parsed.path == "/api/live-candidates/approve":
            payload = self._read_body_json()
            try:
                result = approve_live_candidate(payload)
            except (ValueError, PermissionError) as error:
                self._send_json({"ok": False, "error": type(error).__name__, "message": str(error)}, 409)
                return
            _RESPONSE_CACHE.clear()
            self._send_json(result)
            return
        if parsed.path == "/api/live-candidates/revoke":
            payload = self._read_body_json()
            try:
                result = revoke_live_candidate(payload)
            except (ValueError, PermissionError) as error:
                self._send_json({"ok": False, "error": type(error).__name__, "message": str(error)}, 409)
                return
            _RESPONSE_CACHE.clear()
            self._send_json(result)
            return
        if parsed.path == "/api/live-safety/kill-switch":
            payload = self._read_body_json()
            _RESPONSE_CACHE.clear()
            self._send_json(activate_live_kill_switch(str(payload.get("reason") or "operator_request")))
            return
        if parsed.path in {
            "/api/live-canary/reconcile",
            "/api/live-canary/arm",
            "/api/live-canary/kill-switch",
        }:
            payload = self._read_body_json()
            try:
                if parsed.path.endswith("/reconcile"):
                    result = run_live_readonly_reconciliation()
                elif parsed.path.endswith("/arm"):
                    automatic = run_unified_auto_execution_action({
                        **payload,
                        "environment": "okx_live",
                        "action": "arm",
                    })
                    if not automatic.get("ok"):
                        self._send_json(automatic, 409)
                        return
                    arm_result = automatic.get("armResult") if isinstance(automatic.get("armResult"), dict) else {}
                    result = {
                        **arm_result,
                        "ok": True,
                        "automaticExecution": automatic.get("runtime") or {},
                    }
                else:
                    result = activate_live_canary_kill_switch(payload)
            except (KeyError, RuntimeError, ValueError, PermissionError) as error:
                self._send_json({"ok": False, "error": type(error).__name__, "message": str(error)}, 409)
                return
            _RESPONSE_CACHE.clear()
            self._send_json(result)
            return
        if parsed.path == "/api/execution-outcomes/export":
            try:
                result = write_execution_outcome_export()
            except (OSError, RuntimeError, ValueError) as error:
                self._send_json({"ok": False, "error": type(error).__name__, "message": str(error)}, 409)
                return
            _RESPONSE_CACHE.clear()
            self._send_json({"ok": True, "executionOutcomes": result})
            return
        if parsed.path in {
            "/api/risk-profiles/create",
            "/api/risk-profiles/activate",
            "/api/risk-profiles/rollback",
        }:
            payload = self._read_body_json()
            try:
                if parsed.path.endswith("/create"):
                    result = create_risk_profile_version(payload)
                elif parsed.path.endswith("/activate"):
                    result = activate_risk_profile_version(payload)
                else:
                    result = rollback_risk_profile_version(payload)
            except (KeyError, ValueError, PermissionError) as error:
                self._send_json({"ok": False, "error": type(error).__name__, "message": str(error)}, 409)
                return
            _RESPONSE_CACHE.clear()
            self._send_json(result)
            return
        self._send_json({"error": "not_found"}, 404)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def build_health_payload() -> dict[str, object]:
    return {
        "ok": True,
        "version": "V13.27.9",
        "source": "alphapilot_control_console_v13_27_9",
        "workflowRecovery": get_startup_workflow_recovery_status(),
        "safetyBoundary": SAFETY_BOUNDARY,
    }


def run_server(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), ConsoleHandler)
    credential_bootstrap = bootstrap_demo_credentials()
    resume_incomplete_workflow_runs()
    market_runtime = start_demo_market_runtime(
        close_listener=wake_unified_auto_execution_runner,
    )
    if market_runtime.get("blockers") and not market_runtime.get("disabled"):
        print(
            "OKX public market runtime is not ready; Demo automatic execution remains disabled: "
            + ",".join(str(value) for value in market_runtime.get("blockers", []))
        )
    start_unified_auto_execution_runner()
    startup_arm = arm_okx_demo_runtime_on_startup()
    if startup_arm.get("status") == "blocked":
        print(f"OKX Demo startup ARM was blocked: {startup_arm.get('blocker') or 'startup_arm_failed'}")
    startup_recovery = start_okx_demo_runtime_startup_recovery(
        initial_result=startup_arm,
        credential_ready=bool(credential_bootstrap.get("ok")),
    )
    if startup_recovery.get("status") == "scheduled":
        print("OKX Demo public market warmup will continue in the background before ARM.")
    maybe_open_demo_credential_prompt(
        credential_bootstrap,
        get_unified_auto_execution_status(),
        host=host,
        port=port,
    )
    print(f"AlphaPilot Control Console running at http://{host}:{port}")
    print("Research, OKX Demo, and gated Live Canary control. Credentials are process-only; Withdraw is absent.")
    try:
        server.serve_forever()
    finally:
        stop_unified_auto_execution_runner()
        stop_demo_market_runtime()


def smoke() -> None:
    payload = scan_quant_engine()
    assert payload["safetyBoundary"]["tradeApiAllowed"] is False
    assert payload["safetyBoundary"]["orderCreationAllowed"] is False
    assert isinstance(payload["strategies"], list)
    print(json.dumps({
        "ok": True,
        "strategyCount": len(payload["strategies"]),
        "reportCount": len(payload["reports"]),
        "artifactCount": len(payload.get("strategyArtifactIndex", {}).get("artifacts", []))
        if isinstance(payload.get("strategyArtifactIndex"), dict)
        else 0,
        "mobileBridgeReady": True,
    }, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        smoke()
        return
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
