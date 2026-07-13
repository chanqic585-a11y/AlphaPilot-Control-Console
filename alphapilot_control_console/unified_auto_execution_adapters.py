"""Environment adapters for the shared automatic execution controller."""

from __future__ import annotations

from typing import Any

from .auto_execution_schedule import TIMEFRAME_SECONDS
from .evolution_demo_service import (
    activate_evolution_demo_kill_switch,
    build_evolution_demo_status,
    discover_demo_contracts,
    pause_evolution_demo_runtime,
    reconcile_evolution_demo_runtime,
    run_evolution_demo_batch_cycle,
)
from .exchange_demo_simulation import build_exchange_demo_simulation
from .demo_market_runtime_registry import get_demo_market_runtime_status
from .demo_evaluation_audit import build_demo_evaluation_audit
from .live_auto_execution_service import (
    pause_live_auto_execution_runtime,
    reconcile_live_auto_execution_runtime,
    run_live_auto_execution_batch,
)
from .live_canary_service import activate_live_canary_kill_switch, build_live_canary_status
from .live_release_service import discover_live_releases
from .unified_auto_execution_controller import ReleaseSchedule


class OkxDemoAutoExecutionAdapter:
    environment = "okx_demo"

    def list_releases(self) -> list[ReleaseSchedule]:
        contracts, _ = discover_demo_contracts()
        releases: list[ReleaseSchedule] = []
        for contract in contracts:
            strategy = contract.get("strategy") if isinstance(contract.get("strategy"), dict) else {}
            market = (
                strategy.get("marketDefinition")
                if isinstance(strategy.get("marketDefinition"), dict)
                else {}
            )
            timeframe = str(market.get("timeframe") or "")
            if timeframe not in TIMEFRAME_SECONDS:
                continue
            releases.append(
                ReleaseSchedule(
                    releaseId=str(contract.get("demoReleaseId") or ""),
                    strategyId=str(contract.get("strategyCandidateId") or ""),
                    timeframe=timeframe,
                )
            )
        return [release for release in releases if release.releaseId and release.strategyId]

    def preflight(self) -> dict[str, Any]:
        runtime = build_evolution_demo_status()
        exchange = build_exchange_demo_simulation()
        market_runtime = get_demo_market_runtime_status()
        blockers = [str(value) for value in runtime.get("blockers", []) if str(value)]
        readonly = exchange.get("readonlySummary") if isinstance(exchange.get("readonlySummary"), dict) else {}
        public_market = (
            market_runtime.get("runtime")
            if isinstance(market_runtime.get("runtime"), dict)
            else {}
        )
        if str(readonly.get("status") or "") != "passed":
            blockers.append("okx_demo_readonly_preflight_required")
        if public_market.get("warm") is not True:
            blockers.append("demo_market_runtime_not_warm")
        return {
            "ok": bool(runtime.get("summary", {}).get("ready")) and not blockers,
            "blockers": blockers,
            "runtime": runtime,
            "readonlySummary": readonly,
            "marketRuntimeStatus": market_runtime,
        }

    def reconcile(self) -> dict[str, Any]:
        return reconcile_evolution_demo_runtime()

    def run_batch(
        self,
        releases: list[ReleaseSchedule],
        candle_keys: dict[str, str],
        close_event: Any | None = None,
    ) -> dict[str, Any]:
        del candle_keys
        result = run_evolution_demo_batch_cycle(
            [release.releaseId for release in releases],
            close_event=close_event,
        )
        return {
            **result,
            "evaluationAudit": build_demo_evaluation_audit(result, releases=releases),
        }

    def pause(self, reason: str) -> None:
        pause_evolution_demo_runtime(reason)

    def emergency_stop(self, reason: str) -> dict[str, Any]:
        return activate_evolution_demo_kill_switch(reason)


class OkxLiveAutoExecutionAdapter:
    environment = "okx_live"

    def list_releases(self) -> list[ReleaseSchedule]:
        exports, _ = discover_live_releases()
        releases: list[ReleaseSchedule] = []
        for export in exports:
            release = export.get("release") if isinstance(export.get("release"), dict) else {}
            strategy = release.get("strategy") if isinstance(release.get("strategy"), dict) else {}
            market = strategy.get("marketDefinition") if isinstance(strategy.get("marketDefinition"), dict) else {}
            timeframe = str(market.get("timeframe") or "")
            if timeframe not in TIMEFRAME_SECONDS:
                continue
            releases.append(
                ReleaseSchedule(
                    releaseId=str(export.get("liveReleaseId") or ""),
                    strategyId=str(release.get("strategyCandidateId") or ""),
                    timeframe=timeframe,
                )
            )
        return [release for release in releases if release.releaseId and release.strategyId]

    def preflight(self) -> dict[str, Any]:
        status = build_live_canary_status()
        blockers = [str(value) for value in status.get("blockers", []) if str(value)]
        gates = status.get("runtimeGates") if isinstance(status.get("runtimeGates"), dict) else {}
        if not gates.get("automationEnabled") and "live_automation_gate_disabled" not in blockers:
            blockers.append("live_automation_gate_disabled")
        return {
            "ok": bool(status.get("summary", {}).get("canaryOrderReady")) and not blockers,
            "blockers": blockers,
            "liveCanary": status,
        }

    def reconcile(self) -> dict[str, Any]:
        return reconcile_live_auto_execution_runtime()

    def run_batch(
        self,
        releases: list[ReleaseSchedule],
        candle_keys: dict[str, str],
        close_event: Any | None = None,
    ) -> dict[str, Any]:
        del candle_keys, close_event
        return run_live_auto_execution_batch([release.releaseId for release in releases])

    def pause(self, reason: str) -> None:
        pause_live_auto_execution_runtime(reason)

    def emergency_stop(self, reason: str) -> dict[str, Any]:
        return activate_live_canary_kill_switch({"reason": reason})
