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
        blockers = [str(value) for value in runtime.get("blockers", []) if str(value)]
        readonly = exchange.get("readonlySummary") if isinstance(exchange.get("readonlySummary"), dict) else {}
        if str(readonly.get("status") or "") != "passed":
            blockers.append("okx_demo_readonly_preflight_required")
        return {
            "ok": bool(runtime.get("summary", {}).get("ready")) and not blockers,
            "blockers": blockers,
            "runtime": runtime,
            "readonlySummary": readonly,
        }

    def reconcile(self) -> dict[str, Any]:
        return reconcile_evolution_demo_runtime()

    def run_batch(
        self,
        releases: list[ReleaseSchedule],
        candle_keys: dict[str, str],
    ) -> dict[str, Any]:
        del candle_keys
        return run_evolution_demo_batch_cycle([release.releaseId for release in releases])

    def pause(self, reason: str) -> None:
        pause_evolution_demo_runtime(reason)

    def emergency_stop(self, reason: str) -> dict[str, Any]:
        return activate_evolution_demo_kill_switch(reason)
