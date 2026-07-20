"""Redacted V37A execution-control projection and bounded action facade."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from .config import DATA_DIR
from .unified_auto_execution_store import UnifiedAutoExecutionStore


SCHEMA_VERSION = "execution-control.v1"
ACTION_STORE_PATH = DATA_DIR / "unified_auto_execution.sqlite"
_SENSITIVE_KEY_PARTS = (
    "apikey",
    "secretkey",
    "passphrase",
    "credential",
    "password",
    "signature",
    "rawpayload",
    "exchangepayload",
)
_ACTION_LABELS = {
    "start_demo_with_process_credentials": "使用进程内 Demo 凭据启动",
    "prepare_immutable_demo_release": "准备不可变 Demo Release",
    "arm_current_demo_process": "ARM 当前 Demo 进程",
    "resolve_runtime_error": "检查并处理运行错误",
    "reconcile_demo_state": "复核 Demo 订单与持仓",
    "reset_demo_kill_switch": "复核后解除 Demo 紧急停止",
    "keep_live_off": "保持实盘关闭",
    "complete_live_readiness": "完成实盘只读与安全门槛",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _integer(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _key_is_sensitive(key: Any) -> bool:
    compact = str(key).replace("_", "").replace("-", "").lower()
    return any(token in compact for token in _SENSITIVE_KEY_PARTS)


def _redact(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return None
    if isinstance(value, Mapping):
        return {
            str(key): _redact(child, depth=depth + 1)
            for key, child in value.items()
            if not _key_is_sensitive(key)
        }
    if isinstance(value, (list, tuple)):
        return [_redact(child, depth=depth + 1) for child in list(value)[:200]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _hashes(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    hashes: list[str] = []
    for value in values:
        if isinstance(value, str) and value:
            hashes.append(value)
        elif isinstance(value, Mapping):
            candidate = str(
                value.get("liveReleaseHash")
                or value.get("demoReleaseHash")
                or value.get("contentHash")
                or value.get("releaseHash")
                or ""
            )
            if candidate:
                hashes.append(candidate)
    return sorted(set(hashes))


def _release_hashes(source: Mapping[str, Any], *, live: bool) -> list[str]:
    explicit = _hashes(source.get("releaseHashes"))
    if explicit:
        return explicit
    if live:
        return _hashes(_mapping(source.get("liveReleases")).get("releases"))
    hashes: list[str] = []
    for queue in _mapping(source.get("queues")).values():
        if not isinstance(queue, list):
            continue
        for row in queue:
            if isinstance(row, Mapping):
                hashes.extend(
                    _hashes(
                        [
                            row.get("releaseHash"),
                            row.get("contentHash"),
                            _mapping(row.get("release")).get("contentHash"),
                        ]
                    )
                )
    return sorted(set(hashes))


def _automatic_runtime(automatic: Mapping[str, Any], identity: str) -> dict[str, Any]:
    return _mapping(_mapping(automatic.get("environments")).get(identity))


def _market_feed_summary(source: Mapping[str, Any], runtime: Mapping[str, Any]) -> dict[str, Any]:
    feed = _mapping(source.get("marketFeed")) or _mapping(runtime.get("marketFeed"))
    if not feed:
        feed = _mapping(_mapping(runtime.get("lastHeartbeatResult")).get("marketFeed"))
    status = str(feed.get("status") or "unknown")
    summary = {
        "status": status,
        "source": feed.get("source"),
        "lastUpdatedAt": feed.get("lastUpdatedAt") or feed.get("updatedAt"),
        "stale": bool(feed.get("stale")) if "stale" in feed else status in {"stale", "degraded"},
    }
    return {key: value for key, value in summary.items() if value is not None}


def _demo_credential_ready(demo: Mapping[str, Any]) -> bool:
    runtime = _mapping(demo.get("runtime"))
    status = _mapping(runtime.get("credentialStatus"))
    return bool(
        runtime.get("credentialsConfigured")
        or status.get("allConfigured")
        or _mapping(demo.get("summary")).get("credentialsConfigured")
    )


def _live_credential_ready(live: Mapping[str, Any]) -> bool:
    return bool(_mapping(live.get("credentialStatus")).get("allConfigured"))


def _workflow_items(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for queue in _mapping(source.get("queues")).values():
        if isinstance(queue, list):
            items.extend(_mapping(row) for row in queue if isinstance(row, Mapping))
    return items


def _demo_open_positions(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    explicit = source.get("positions")
    rows = list(explicit) if isinstance(explicit, list) else [
        position
        for item in _workflow_items(source)
        for position in list(item.get("positions") or [])
        if isinstance(position, Mapping)
    ]
    closed = {"cancelled", "canceled", "closed", "exited", "flat", "not_started", "rejected"}
    return [dict(row) for row in rows if str(row.get("status") or "").lower() not in closed]


def _demo_open_order_count(source: Mapping[str, Any]) -> int:
    explicit = _mapping(source.get("summary")).get("openOrderCount")
    if explicit is not None:
        return _integer(explicit)
    open_states = {"live", "open", "order_submitted", "partially_filled", "submitted"}
    return sum(
        str(_mapping(item.get("position")).get("status") or "").lower() in open_states
        for item in _workflow_items(source)
    )


def _latest_live_reconciliation(source: Mapping[str, Any]) -> dict[str, Any]:
    for event in list(source.get("recentEvents") or []):
        row = _mapping(event)
        if row.get("eventType") == "live_readonly_reconciliation":
            return row
    return {}


def _reconciliation_summary(source: Mapping[str, Any], *, live: bool) -> dict[str, Any]:
    runtime = _mapping(source.get("runtime"))
    reconciliation = _mapping(runtime.get("reconciliation"))
    if live:
        event = _latest_live_reconciliation(source)
        payload = _mapping(event.get("payload"))
        matched_value = payload.get("matched", runtime.get("lastReconciliationMatched"))
        matched = bool(matched_value)
        return {
            "matched": matched,
            "status": "matched" if matched else "not_confirmed",
            "lastCheckedAt": event.get("createdAt") or runtime.get("lastReconciledAt"),
            "unknownOrderCount": _integer(payload.get("untrackedOrderCount")),
            "unknownPositionCount": _integer(payload.get("untrackedPositionCount")),
        }
    if not reconciliation:
        rows = [_mapping(item.get("reconciliation")) for item in _workflow_items(source)]
        statuses = [str(row.get("status") or "").lower() for row in rows]
        failed = {"failed", "mismatch", "unhealthy"}
        healthy = {"healthy", "matched", "passed", "reconciled"}
        matched_value = False if any(status in failed for status in statuses) else (
            True if any(status in healthy for status in statuses) else None
        )
        timestamps = sorted(str(row.get("updatedAt")) for row in rows if row.get("updatedAt"))
        return {
            "matched": matched_value,
            "status": "mismatch" if matched_value is False else (
                "matched" if matched_value is True else "not_started"
            ),
            "lastCheckedAt": timestamps[-1] if timestamps else None,
            "unknownOrderCount": 0,
            "unknownPositionCount": 0,
        }
    matched_value = reconciliation.get("matched")
    matched = bool(matched_value) if matched_value is not None else None
    return {
        "matched": matched,
        "status": reconciliation.get("status") or ("matched" if matched else "not_started"),
        "lastCheckedAt": reconciliation.get("lastCheckedAt"),
        "unknownOrderCount": _integer(reconciliation.get("unknownOrderCount")),
        "unknownPositionCount": _integer(reconciliation.get("unknownPositionCount")),
    }


def _demo_blockers(
    runtime: Mapping[str, Any],
    demo: Mapping[str, Any],
    *,
    credential_ready: bool,
    release_hashes: list[str],
) -> list[str]:
    blockers: list[str] = []
    if not credential_ready:
        blockers.append("demo_credentials_missing")
    if _integer(runtime.get("releaseCount")) == 0 and not release_hashes:
        blockers.append("immutable_release_missing")
    if bool(runtime.get("desiredEnabled")) and not bool(runtime.get("armedForCurrentProcess")):
        blockers.append("process_arm_required")
    if runtime.get("lastError"):
        blockers.append("runtime_error")
    reconciliation = _reconciliation_summary(demo, live=False)
    if (
        reconciliation["matched"] is False
        or reconciliation["unknownOrderCount"]
        or reconciliation["unknownPositionCount"]
    ):
        blockers.append("reconciliation_unhealthy")
    kill_switch = _mapping(_mapping(demo.get("runtime")).get("killSwitch"))
    if kill_switch.get("active"):
        blockers.append("kill_switch_active")
    return _dedupe(blockers)


def _next_actions(blockers: list[str], *, live: bool) -> list[dict[str, str]]:
    mapping = {
        "demo_credentials_missing": "start_demo_with_process_credentials",
        "immutable_release_missing": "prepare_immutable_demo_release",
        "process_arm_required": "arm_current_demo_process",
        "runtime_error": "resolve_runtime_error",
        "reconciliation_unhealthy": "reconcile_demo_state",
        "kill_switch_active": "reset_demo_kill_switch",
        "live_default_off": "keep_live_off",
    }
    codes = _dedupe([mapping.get(blocker, "complete_live_readiness" if live else "") for blocker in blockers])
    return [{"code": code, "labelZh": _ACTION_LABELS[code]} for code in codes]


def build_execution_control_status(
    *,
    automatic_execution: Mapping[str, Any],
    demo_workflow: Mapping[str, Any],
    live_canary: Mapping[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    automatic = _mapping(automatic_execution)
    demo = _mapping(demo_workflow)
    live = _mapping(live_canary)
    demo_runtime = _automatic_runtime(automatic, "okx_demo")
    live_runtime = _automatic_runtime(automatic, "okx_live")
    demo_hashes = _release_hashes(demo, live=False)
    live_hashes = _release_hashes(live, live=True)
    demo_credentials = _demo_credential_ready(demo)
    live_credentials = _live_credential_ready(live)
    demo_blockers = _demo_blockers(
        demo_runtime,
        demo,
        credential_ready=demo_credentials,
        release_hashes=demo_hashes,
    )
    live_blockers = [str(value) for value in list(live.get("blockers") or []) if str(value)]
    if not bool(live_runtime.get("desiredEnabled")):
        live_blockers.insert(0, "live_default_off")
    live_blockers = _dedupe(live_blockers)
    demo_summary = _mapping(demo.get("summary"))
    live_summary = _mapping(live.get("summary"))
    live_state = _mapping(live.get("runtime"))
    demo_positions = _demo_open_positions(demo)
    live_reconciliation = _reconciliation_summary(live, live=True)
    live_reconciliation_event = _mapping(_latest_live_reconciliation(live).get("payload"))
    mismatch_blockers = [
        {"environment": environment, "code": code}
        for environment, codes in (("demo", demo_blockers), ("live", live_blockers))
        for code in codes
        if "mismatch" in code.lower() or "hash" in code.lower()
    ]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at or _now_iso(),
        "researchTrack": {
            "status": "isolated",
            "executionEvidenceEligible": False,
            "messageZh": "研究结果与执行工程证据保持隔离。",
        },
        "environments": {
            "demo": {
                "runtimeIdentity": "okx_demo",
                "status": demo_runtime.get("status") or "unavailable",
                "runnerOnline": bool(automatic.get("running")),
                "desiredEnabled": bool(demo_runtime.get("desiredEnabled")),
                "armedForCurrentProcess": bool(demo_runtime.get("armedForCurrentProcess")),
                "credentialReady": demo_credentials,
                "releaseCount": _integer(demo_runtime.get("releaseCount")) or len(demo_hashes),
                "lastHeartbeatAt": demo_runtime.get("lastHeartbeatAt"),
                "nextEvaluationAt": demo_runtime.get("nextEvaluationAt"),
                "lastError": demo_runtime.get("lastError"),
                "marketFeed": _market_feed_summary(demo, demo_runtime),
                "orders": {"openCount": _demo_open_order_count(demo)},
                "positions": {
                    "openCount": _integer(demo_summary.get("openPositionCount")) or len(demo_positions),
                    "items": _redact(demo_positions),
                },
                "reconciliation": _reconciliation_summary(demo, live=False),
                "risk": _redact(_mapping(_mapping(demo.get("runtime")).get("risk"))),
                "killSwitch": _redact(_mapping(_mapping(demo.get("runtime")).get("killSwitch"))),
                "blockerCodes": demo_blockers,
                "nextActions": _next_actions(demo_blockers, live=False),
            },
            "live": {
                "runtimeIdentity": "okx_live",
                "status": live_runtime.get("status") or "disabled",
                "runnerOnline": bool(automatic.get("running")),
                "desiredEnabled": bool(live_runtime.get("desiredEnabled")),
                "armedForCurrentProcess": bool(live_runtime.get("armedForCurrentProcess")),
                "credentialReady": live_credentials,
                "releaseCount": _integer(live_runtime.get("releaseCount")) or len(live_hashes),
                "lastHeartbeatAt": live_runtime.get("lastHeartbeatAt"),
                "nextEvaluationAt": live_runtime.get("nextEvaluationAt"),
                "lastError": live_runtime.get("lastError"),
                "marketFeed": _market_feed_summary(live, live_runtime),
                "orders": {
                    "recordCount": _integer(live_summary.get("executionRecordCount")),
                    "openCount": _integer(live_reconciliation_event.get("openOrderCount")),
                },
                "positions": {
                    "openCount": _integer(live_reconciliation_event.get("openPositionCount")),
                    "items": [],
                },
                "reconciliation": live_reconciliation,
                "risk": _redact(_mapping(live.get("activeRiskProfile"))),
                "killSwitch": {
                    "active": bool(live_state.get("killSwitchActive")),
                    "paused": bool(live_state.get("paused")),
                },
                "blockerCodes": live_blockers,
                "nextActions": _next_actions(live_blockers, live=True),
            },
        },
        "crossTrack": {
            "demoReleaseHashes": demo_hashes,
            "liveReleaseHashes": live_hashes,
            "sharedReleaseHashes": sorted(set(demo_hashes) & set(live_hashes)),
            "mismatchBlockers": mismatch_blockers,
            "runtimeIdentityIsolated": True,
        },
        "safetyBoundary": {
            "demoLiveConfigurationShared": False,
            "credentialsPersisted": False,
            "withdrawAllowed": False,
            "liveDefaultOff": True,
            "immutableReleaseRequired": True,
            "approvalArmRiskBypassAllowed": False,
        },
    }


class ExecutionControlActionFacade:
    """Idempotent, environment-bounded wrapper over existing runtime actions."""

    _ALLOWED = {
        "okx_demo": {"start", "pause", "stop", "emergency_stop"},
        "okx_live": {"pause", "stop", "emergency_stop"},
    }

    def __init__(
        self,
        *,
        store: UnifiedAutoExecutionStore,
        action_runner: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.store = store
        self.action_runner = action_runner

    @staticmethod
    def _semantic_payload(body: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "environment": str(body.get("environment") or ""),
            "action": str(body.get("action") or ""),
            "actor": str(body.get("actor") or "console_operator")[:80],
            "reason": str(body.get("reason") or "")[:240],
            "confirmationHash": str(body.get("confirmationHash") or "")[:128],
        }

    def execute(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        body = _mapping(payload)
        request_id = str(body.get("requestId") or "").strip()[:128]
        environment = str(body.get("environment") or "")
        action = str(body.get("action") or "")
        if not request_id:
            return {"ok": False, "status": "rejected", "blockers": ["request_id_required"]}
        if environment not in self._ALLOWED:
            return {"ok": False, "status": "rejected", "blockers": ["unsupported_execution_environment"]}
        if environment == "okx_live" and action == "start":
            return {"ok": False, "status": "rejected", "blockers": ["live_start_not_available_in_v37a"]}
        if environment == "okx_live" and action == "arm":
            return {
                "ok": False,
                "status": "rejected",
                "blockers": ["live_arm_requires_existing_manual_path"],
            }
        if action not in self._ALLOWED[environment]:
            return {"ok": False, "status": "rejected", "blockers": ["unsupported_execution_action"]}
        semantic = self._semantic_payload(body)
        payload_hash = hashlib.sha256(
            json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        claim = self.store.claim_action_request(
            request_id=request_id,
            environment=environment,
            action=action,
            payload_hash=payload_hash,
        )
        if claim["state"] == "conflict":
            return {
                "ok": False,
                "status": "conflict",
                "requestId": request_id,
                "blockers": ["idempotency_key_payload_mismatch"],
            }
        if claim["state"] == "in_progress":
            return {
                "ok": False,
                "status": "in_progress",
                "requestId": request_id,
                "blockers": ["action_request_in_progress"],
            }
        if claim["state"] == "replay":
            return {**_mapping(claim.get("result")), "requestId": request_id, "idempotentReplay": True}
        try:
            result = _mapping(self.action_runner({**semantic, "requestId": request_id}))
        except TimeoutError:
            result = {"ok": False, "blockers": ["action_dispatch_timeout"]}
        except Exception:
            result = {"ok": False, "blockers": ["action_dispatch_failed"]}
        safe_result = _redact(result)
        response = {
            **_mapping(safe_result),
            "requestId": request_id,
            "status": "completed" if bool(result.get("ok")) else "failed",
            "idempotentReplay": False,
        }
        self.store.complete_action_request(request_id, response)
        return response


def get_execution_control_status() -> dict[str, Any]:
    from .demo_workflow_service import build_demo_workflow_status
    from .live_canary_service import build_live_canary_status
    from .unified_auto_execution_runner import get_unified_auto_execution_status

    return build_execution_control_status(
        automatic_execution=get_unified_auto_execution_status(),
        demo_workflow=build_demo_workflow_status(),
        live_canary=build_live_canary_status(),
    )


def run_execution_control_action(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    from .unified_auto_execution_runner import run_unified_auto_execution_action

    store = UnifiedAutoExecutionStore(Path(ACTION_STORE_PATH))
    try:
        return ExecutionControlActionFacade(
            store=store,
            action_runner=run_unified_auto_execution_action,
        ).execute(payload)
    finally:
        store.close()
