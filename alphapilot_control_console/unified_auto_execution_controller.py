"""Shared fail-closed orchestration for isolated Demo and Live adapters."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from .auto_execution_schedule import closed_candle_key, next_candle_close
from .unified_auto_execution_store import UnifiedAutoExecutionStore


@dataclass(frozen=True)
class ReleaseSchedule:
    releaseId: str
    strategyId: str
    timeframe: str


class ExecutionEnvironmentAdapter(Protocol):
    environment: str

    def preflight(self) -> dict[str, Any]: ...

    def reconcile(self) -> dict[str, Any]: ...

    def list_releases(self) -> list[ReleaseSchedule]: ...

    def run_batch(
        self,
        releases: list[ReleaseSchedule],
        candle_keys: dict[str, str],
        close_event: Any | None = None,
    ) -> dict[str, Any]: ...

    def pause(self, reason: str) -> None: ...

    def emergency_stop(self, reason: str) -> dict[str, Any]: ...


class UnifiedAutoExecutionController:
    def __init__(
        self,
        *,
        store: UnifiedAutoExecutionStore,
        adapters: dict[str, ExecutionEnvironmentAdapter],
        process_id: str | None = None,
    ):
        self.store = store
        self.adapters = dict(adapters)
        self.process_id = str(process_id if process_id is not None else os.getpid())
        for environment, adapter in self.adapters.items():
            if environment != adapter.environment:
                raise ValueError("Automatic execution adapter environment mismatch")

    def _adapter(self, environment: str) -> ExecutionEnvironmentAdapter:
        try:
            return self.adapters[environment]
        except KeyError as error:
            raise ValueError(f"No automatic execution adapter for {environment!r}") from error

    def start(self, environment: str) -> dict[str, Any]:
        self._adapter(environment)
        self.store.set_desired_enabled(environment, True)
        self.store.append_event(environment, "start_requested", {"processId": self.process_id})
        return self.status(environment)

    def arm(self, environment: str) -> dict[str, Any]:
        self._adapter(environment)
        self.store.record_arm(environment, process_id=self.process_id)
        return self.status(environment)

    def pause(self, environment: str, reason: str = "operator_pause") -> dict[str, Any]:
        adapter = self._adapter(environment)
        adapter.pause(reason)
        self.store.update_runtime(
            environment,
            status="paused",
            pauseReason=reason,
            lastError=None,
        )
        self.store.append_event(environment, "paused", {"reason": reason})
        return self.status(environment)

    def stop(self, environment: str, reason: str = "operator_stop") -> dict[str, Any]:
        self._adapter(environment)
        self.store.disarm(environment, reason=reason)
        self.store.set_desired_enabled(environment, False)
        self.store.append_event(environment, "stopped", {"reason": reason})
        return self.status(environment)

    def emergency_stop(self, environment: str, reason: str) -> dict[str, Any]:
        adapter = self._adapter(environment)
        exchange = adapter.emergency_stop(reason)
        self.store.disarm(environment, reason=reason)
        self.store.set_desired_enabled(environment, False)
        self.store.append_event(
            environment,
            "emergency_stop",
            {"reason": reason, "adapterOk": bool(exchange.get("ok"))},
        )
        return {"ok": bool(exchange.get("ok")), "adapter": exchange, "runtime": self.status(environment)}

    def status(self, environment: str) -> dict[str, Any]:
        adapter = self._adapter(environment)
        runtime = self.store.runtime(environment, current_process_id=self.process_id)
        releases = adapter.list_releases()
        recent_events = self.store.list_events(environment, 20)
        last_evaluation = next(
            (
                event["payload"].get("evaluationAudit")
                for event in recent_events
                if event.get("eventType") in {"heartbeat_completed", "heartbeat_blocked"}
                and isinstance(event.get("payload"), dict)
                and isinstance(event["payload"].get("evaluationAudit"), dict)
            ),
            {},
        )
        return {
            **runtime,
            "releaseCount": len(releases),
            "releases": [
                {
                    "releaseId": release.releaseId,
                    "strategyId": release.strategyId,
                    "timeframe": release.timeframe,
                    "lastClosedCandle": self.store.checkpoint(
                        environment,
                        release.releaseId,
                        release.timeframe,
                    ),
                }
                for release in releases
            ],
            "recentEvents": recent_events,
            "lastEvaluation": dict(last_evaluation),
        }

    def heartbeat(
        self,
        environment: str,
        *,
        now: datetime | None = None,
        close_event: Any | None = None,
    ) -> dict[str, Any]:
        adapter = self._adapter(environment)
        heartbeat_at = (now or datetime.now(UTC)).astimezone(UTC)
        heartbeat_iso = heartbeat_at.isoformat()
        runtime = self.store.runtime(environment, current_process_id=self.process_id)
        if not runtime["desiredEnabled"]:
            self.store.update_runtime(
                environment,
                status="disabled",
                lastHeartbeatAt=heartbeat_iso,
                nextEvaluationAt=None,
            )
            return self._heartbeat_result(environment, "disabled", 0)
        if not runtime["armedForCurrentProcess"]:
            self.store.update_runtime(
                environment,
                status="disarmed",
                lastHeartbeatAt=heartbeat_iso,
                nextEvaluationAt=None,
                pauseReason="process_arm_required",
            )
            return self._heartbeat_result(
                environment,
                "disarmed",
                0,
                blockers=["process_arm_required"],
            )

        try:
            preflight = adapter.preflight()
            if not preflight.get("ok"):
                return self._handle_failure(environment, adapter, preflight, heartbeat_iso)
            reconciliation = adapter.reconcile()
            if not reconciliation.get("ok"):
                return self._handle_failure(environment, adapter, reconciliation, heartbeat_iso)

            releases = adapter.list_releases()
            if environment == "okx_demo" and close_event is None:
                next_times = [
                    next_candle_close(heartbeat_at, release.timeframe)
                    for release in releases
                ]
                next_evaluation = min(next_times).isoformat() if next_times else None
                self.store.update_runtime(
                    environment,
                    status="waiting",
                    lastHeartbeatAt=heartbeat_iso,
                    nextEvaluationAt=next_evaluation,
                    pauseReason=None,
                    lastError=None,
                )
                return self._heartbeat_result(environment, "waiting", 0)
            due: list[ReleaseSchedule] = []
            candle_keys: dict[str, str] = {}
            next_times: list[datetime] = []
            event_timeframe = str(
                close_event.get("timeframe")
                if isinstance(close_event, dict)
                else getattr(close_event, "timeframe", "")
            ) if close_event is not None else ""
            event_sequence = str(
                close_event.get("sequenceId")
                if isinstance(close_event, dict)
                else getattr(close_event, "sequenceId", "")
            ) if close_event is not None else ""
            if close_event is not None and (not event_timeframe or not event_sequence):
                return self._handle_failure(
                    environment,
                    adapter,
                    {"blockers": ["confirmed_close_event_invalid"]},
                    heartbeat_iso,
                )
            for release in releases:
                next_times.append(next_candle_close(heartbeat_at, release.timeframe))
                if close_event is not None and release.timeframe != event_timeframe:
                    continue
                candle_key = event_sequence if close_event is not None else closed_candle_key(
                    heartbeat_at,
                    release.timeframe,
                )
                if self.store.checkpoint(
                    environment,
                    release.releaseId,
                    release.timeframe,
                ) != candle_key:
                    due.append(release)
                    candle_keys[release.releaseId] = candle_key

            next_evaluation = min(next_times).isoformat() if next_times else None
            if not due:
                self.store.update_runtime(
                    environment,
                    status="waiting",
                    lastHeartbeatAt=heartbeat_iso,
                    nextEvaluationAt=next_evaluation,
                    pauseReason=None,
                    lastError=None,
                )
                return self._heartbeat_result(environment, "waiting", 0)

            batch = adapter.run_batch(due, candle_keys, close_event)
            if not batch.get("ok"):
                return self._handle_failure(environment, adapter, batch, heartbeat_iso)
            for release in due:
                self.store.save_checkpoint(
                    environment,
                    release.releaseId,
                    release.timeframe,
                    candle_keys[release.releaseId],
                )
            self.store.update_runtime(
                environment,
                status="running",
                lastHeartbeatAt=heartbeat_iso,
                nextEvaluationAt=next_evaluation,
                pauseReason=None,
                lastError=None,
            )
            evaluation_audit = dict(batch.get("evaluationAudit") or {})
            if evaluation_audit:
                evaluation_audit.update({
                    "processId": self.process_id,
                    "closeSequenceId": event_sequence or None,
                })
                batch = {**batch, "evaluationAudit": evaluation_audit}
            self.store.append_event(
                environment,
                "heartbeat_completed",
                {
                    "evaluatedReleaseCount": len(due),
                    "createdOrderCount": int(batch.get("createdOrderCount") or 0),
                    "matchedSignalCount": int(batch.get("matchedSignalCount") or 0),
                    "closeSequenceId": event_sequence or None,
                    "closeReceivedAt": (
                        close_event.get("receivedAt")
                        if isinstance(close_event, dict)
                        else getattr(close_event, "receivedAt", None)
                    ) if close_event is not None else None,
                    "latencyMetrics": dict(batch.get("latencyMetrics") or {}),
                    "expiredSignalCount": len(batch.get("expiredSignals") or []),
                    "conditionalLateEntryCount": len(batch.get("conditionalLateEntries") or []),
                    "evaluationAudit": evaluation_audit,
                },
            )
            return self._heartbeat_result(
                environment,
                "running",
                len(due),
                batch=batch,
            )
        except Exception as error:
            reason = f"controller_exception:{type(error).__name__}"
            adapter.pause(reason)
            self.store.update_runtime(
                environment,
                status="paused",
                lastHeartbeatAt=heartbeat_iso,
                pauseReason=reason,
                lastError=type(error).__name__,
            )
            self.store.append_event(environment, "heartbeat_failed", {"reason": reason})
            return self._heartbeat_result(environment, "paused", 0, blockers=[reason])

    def _handle_failure(
        self,
        environment: str,
        adapter: ExecutionEnvironmentAdapter,
        result: dict[str, Any],
        heartbeat_iso: str,
    ) -> dict[str, Any]:
        if environment == "okx_demo" and result.get("transient") is True:
            return self._degrade_from_failure(environment, result, heartbeat_iso)
        return self._pause_from_failure(environment, adapter, result, heartbeat_iso)

    def _degrade_from_failure(
        self,
        environment: str,
        result: dict[str, Any],
        heartbeat_iso: str,
    ) -> dict[str, Any]:
        blockers = [str(value) for value in result.get("blockers", []) if str(value)]
        reason = blockers[0] if blockers else "transient_demo_transport_failure"
        evaluation_audit = (
            dict(result.get("evaluationAudit") or {})
            if isinstance(result.get("evaluationAudit"), dict)
            else {}
        )
        self.store.update_runtime(
            environment,
            status="degraded",
            lastHeartbeatAt=heartbeat_iso,
            pauseReason=None,
            lastError=reason,
        )
        self.store.append_event(
            environment,
            "heartbeat_degraded",
            {
                "blockers": blockers or [reason],
                "retryMode": "next_heartbeat",
                "evaluationAudit": evaluation_audit,
            },
        )
        return self._heartbeat_result(
            environment,
            "degraded",
            int(evaluation_audit.get("evaluatedReleaseCount") or 0),
            blockers=blockers or [reason],
            batch={"evaluationAudit": evaluation_audit} if evaluation_audit else None,
        )

    def _pause_from_failure(
        self,
        environment: str,
        adapter: ExecutionEnvironmentAdapter,
        result: dict[str, Any],
        heartbeat_iso: str,
    ) -> dict[str, Any]:
        blockers = [str(value) for value in result.get("blockers", []) if str(value)]
        reason = blockers[0] if blockers else "automatic_execution_gate_failed"
        adapter.pause(reason)
        self.store.update_runtime(
            environment,
            status="paused",
            lastHeartbeatAt=heartbeat_iso,
            pauseReason=reason,
            lastError=None,
        )
        evaluation_audit = (
            dict(result.get("evaluationAudit") or {})
            if isinstance(result.get("evaluationAudit"), dict)
            else {}
        )
        self.store.append_event(
            environment,
            "heartbeat_blocked",
            {
                "blockers": blockers or [reason],
                "evaluationAudit": evaluation_audit,
            },
        )
        return self._heartbeat_result(
            environment,
            "paused",
            int(evaluation_audit.get("evaluatedReleaseCount") or 0),
            blockers=blockers or [reason],
            batch={"evaluationAudit": evaluation_audit} if evaluation_audit else None,
        )

    def _heartbeat_result(
        self,
        environment: str,
        status: str,
        evaluated_release_count: int,
        *,
        blockers: list[str] | None = None,
        batch: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            **self.status(environment),
            "status": status,
            "evaluatedReleaseCount": int(evaluated_release_count),
            "blockers": list(blockers or []),
            "batch": dict(batch or {}),
        }
