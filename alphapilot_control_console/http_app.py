from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import ALLOWED_STRATEGY_STATUSES, SAFETY_BOUNDARY, WEB_DIR
from .exchange_connectors.public_exchange_registry import list_public_exchange_sources, probe_public_exchanges
from .forward_review import build_forward_review, refresh_forward_review
from .importer import build_mobile_status, import_now, scan_quant_engine
from .live_readiness import build_live_readiness, create_manual_execution_ticket
from .local_sandbox_runner import run_local_sandbox
from .mobile_connection import build_mobile_connection_info
from .sandbox_auto_runner import (
    get_local_sandbox_auto_runner_status,
    run_local_sandbox_auto_runner_now,
    start_local_sandbox_auto_runner,
    stop_local_sandbox_auto_runner,
    update_local_sandbox_auto_runner_settings,
)
from .sandbox_observation_reporter import build_local_sandbox_daily_report
from .short_cycle_candidates import build_short_cycle_candidate_pool
from .simulation_bridge import build_simulation_bridge
from .simulation_replay import build_closed_sample_replay, build_closed_sample_strategy_detail
from .simulation_review import build_simulation_review, build_simulation_review_strategy
from .strategy_promotion_gate import build_strategy_promotion_gate
from .strategy_slots import list_strategy_slots
from .usable_strategy_catalog import build_usable_strategy_catalog
from .weakness_action_board import build_weakness_action_board
from .state_store import (
    ALLOWED_ARTIFACT_REVIEW_STATUSES,
    ALLOWED_PAPER_OBSERVATION_LOG_TYPES,
    ALLOWED_PAPER_OBSERVATION_TASK_STATUSES,
    add_paper_observation_log,
    list_local_sandbox_daily_reports,
    list_manual_execution_tickets,
    list_local_sandbox_runs,
    list_audit,
    list_paper_observation_logs,
    update_artifact_review,
    upsert_paper_observation_task,
    update_strategy_status,
)


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _safe_int(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


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


class ConsoleHandler(BaseHTTPRequestHandler):
    server_version = "AlphaPilotControlConsole/13.7.48"

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
        if path == "/api/health":
            self._send_json({
                "ok": True,
                "version": "V13.7.48",
                "source": "alphapilot_control_console_v13_7_48",
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/strategies":
            self._send_json({"strategies": scan_quant_engine()["strategies"]})
            return
        if path == "/api/reports":
            self._send_json({"reports": scan_quant_engine()["reports"]})
            return
        if path == "/api/mobile/status":
            self._send_json(build_mobile_status(scan_quant_engine()))
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
            payload = scan_quant_engine()
            self._send_json({
                "strategyArtifactIndex": payload["strategyArtifactIndex"],
                "safetyBoundary": SAFETY_BOUNDARY,
            })
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
            self._send_json({"tasks": tasks, "safetyBoundary": SAFETY_BOUNDARY})
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
            payload = scan_quant_engine()
            self._send_json({
                "strategyCandidateQueue": payload.get("strategyCandidateQueue") or {},
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/short-cycle-candidates":
            payload = scan_quant_engine()
            self._send_json(build_short_cycle_candidate_pool(payload))
            return
        if path == "/api/usable-strategy-catalog":
            self._send_json(build_usable_strategy_catalog())
            return
        if path == "/api/simulation-bridge":
            self._send_json(build_simulation_bridge())
            return
        if path == "/api/simulation-review":
            self._send_json(build_simulation_review())
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
            self._send_json(build_closed_sample_replay(strategy_id=strategy_id, limit=limit))
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
            self._send_json(build_weakness_action_board(limit=limit))
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
        if path.startswith("/api/closed-sample-replay/strategies/"):
            strategy_id = path.rsplit("/", 1)[-1]
            strategy = build_closed_sample_strategy_detail(strategy_id)
            if strategy is None:
                self._send_json({"error": "strategy_not_found"}, 404)
                return
            self._send_json(strategy)
            return
        if path == "/api/strategy-promotion-gate":
            payload = scan_quant_engine()
            self._send_json(build_strategy_promotion_gate(payload))
            return
        if path == "/api/research-task-board":
            payload = scan_quant_engine()
            self._send_json({
                "researchTaskBoard": payload.get("researchTaskBoard") or {},
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/strategy-learning-loop":
            payload = scan_quant_engine()
            self._send_json({
                "strategyLearningLoop": payload.get("strategyLearningLoop") or {},
                "safetyBoundary": SAFETY_BOUNDARY,
            })
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
            self._send_json({"logs": logs, "safetyBoundary": SAFETY_BOUNDARY})
            return
        if path == "/api/local-sandbox/runs":
            query = parse_qs(parsed.query or "")
            limit = _safe_int((query.get("limit") or [20])[0], 20)
            self._send_json({"runs": list_local_sandbox_runs(limit), "safetyBoundary": SAFETY_BOUNDARY})
            return
        if path == "/api/local-sandbox/daily-report":
            query = parse_qs(parsed.query or "")
            limit = _safe_int((query.get("limit") or [10])[0], 10)
            reports = list_local_sandbox_daily_reports(limit)
            self._send_json({
                "latestReport": reports[0] if reports else {},
                "reports": reports,
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/local-sandbox/auto-runner":
            self._send_json(get_local_sandbox_auto_runner_status())
            return
        if path == "/api/live-readiness":
            payload = scan_quant_engine()
            self._send_json(build_live_readiness(payload))
            return
        if path == "/api/forward-review":
            payload = scan_quant_engine()
            self._send_json(build_forward_review(payload))
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
            updated = update_artifact_review(artifact_id, review_status, note)
            latest = scan_quant_engine()
            if review_status == "paper_observation":
                artifact = _find_artifact(latest["strategyArtifactIndex"], artifact_id)
                checklist = artifact.get("paperObservationChecklist", {}) if artifact else {}
                upsert_paper_observation_task(
                    artifact_id=artifact_id,
                    task_status="active",
                    note=note,
                    target_sample_count=_safe_int(checklist.get("targetSampleCount") if isinstance(checklist, dict) else None, 50),
                    observation_days=60,
                    artifact=artifact,
                )
                latest = scan_quant_engine()
            if review_status in {"paused", "rejected"}:
                artifact = _find_artifact(latest["strategyArtifactIndex"], artifact_id)
                upsert_paper_observation_task(
                    artifact_id=artifact_id,
                    task_status="paused" if review_status == "paused" else "rejected",
                    note=note,
                    artifact=artifact,
                )
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
        self._send_json({"error": "not_found"}, 404)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def run_server(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), ConsoleHandler)
    start_local_sandbox_auto_runner()
    print(f"AlphaPilot Control Console running at http://{host}:{port}")
    print("Research control only. No Trade API, no API keys, no orders, no auto trading.")
    try:
        server.serve_forever()
    finally:
        stop_local_sandbox_auto_runner()


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
