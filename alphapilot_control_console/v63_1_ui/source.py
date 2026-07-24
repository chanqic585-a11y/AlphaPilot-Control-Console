from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..strategy_factory_v2.ledger import StrategyFactoryV2
from ..strategy_factory_v2.projection import DEFAULT_STATE_PATH
from ..top200_minimal_ui_projection import build_top200_minimal_ui_projection
from ..trading_terminal_projection import TradingTerminalProjection
from .service import ProjectionPageSlice


def _state_version(scope: str, payload: object) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{scope}:{digest}"


def _status(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {
        "healthy",
        "running",
        "queued",
        "waiting",
        "blocked",
        "failed",
        "passed",
        "archived",
        "stale",
        "disconnected",
        "not_run",
    }:
        return normalized
    if normalized in {"completed", "complete", "formal_complete"}:
        return "passed"
    if normalized in {"offline", "disabled"}:
        return "disconnected"
    if "block" in normalized or "fail" in normalized:
        return "blocked"
    if "run" in normalized:
        return "running"
    return "unknown"


def _page_slice(payload: dict[str, Any]) -> ProjectionPageSlice:
    next_key = payload.get("nextKey")
    if isinstance(next_key, dict):
        if {"createdAt", "recordId"} <= set(next_key):
            next_key = (
                next_key["createdAt"],
                next_key["recordId"],
            )
        else:
            raise ValueError("Projection nextKey fields are unsupported")
    elif isinstance(next_key, list):
        next_key = tuple(next_key)
    elif next_key is not None and not isinstance(next_key, tuple):
        next_key = (next_key,)
    return ProjectionPageSlice(
        items=[
            dict(item)
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ],
        has_more=bool(payload.get("hasMore")),
        next_key=next_key,
        state_version=str(payload.get("stateVersion") or "unavailable"),
    )


class V631ProjectionSource:
    """Bounded read-only data source for the V63.1 projection facade."""

    def __init__(
        self,
        *,
        top200_projection: Any,
        strategy_factory: Any | None,
        terminal_projection: Any,
    ) -> None:
        self.top200_projection = top200_projection
        self.strategy_factory = strategy_factory
        self.terminal_projection = terminal_projection

    def close(self) -> None:
        close = getattr(self.strategy_factory, "close", None)
        if callable(close):
            close()

    def object_projection(
        self,
        scope: str,
        *,
        object_id: str | None = None,
    ) -> dict[str, object]:
        if scope == "control-console":
            strategy = self.top200_projection.strategy_summary()
            research = self.top200_projection.research_factory_summary()
            as_of = strategy.get("updatedAt") or research.get("updatedAt")
            status = (
                "blocked"
                if int(strategy.get("formalPassCount") or 0) == 0
                else "passed"
            )
            return {
                "status": status,
                "asOf": as_of,
                "stateVersion": _state_version(
                    scope,
                    {
                        "strategy": strategy,
                        "research": research,
                    },
                ),
                "strategy": strategy,
                "research": research,
                "executionAuthorized": False,
                "armed": False,
            }
        if scope == "strategy-detail":
            if not object_id:
                raise ValueError("strategy_id_required")
            strategy = self.top200_projection.strategy_release(object_id)
            return {
                **strategy,
                "status": _status(strategy.get("status")),
                "asOf": strategy.get("updatedAt") or strategy.get("generatedAt"),
                "stateVersion": _state_version(scope, strategy),
                "executionAuthorized": False,
                "armed": False,
            }
        if scope == "evolution-pool":
            if self.strategy_factory is None:
                return {
                    "status": "not_run",
                    "asOf": None,
                    "stateVersion": _state_version(scope, "unavailable"),
                    "dataStatus": "strategy_factory_store_unavailable",
                    "executionAuthorized": False,
                    "armed": False,
                }
            state_version = str(self.strategy_factory.projection_state_version())
            return {
                "status": "running",
                "asOf": None,
                "stateVersion": state_version,
                "dataStatus": "available",
                "executionAuthorized": False,
                "armed": False,
            }
        if scope == "demo-fleet":
            return self._terminal_object(
                "okx_demo",
                state_version=self.terminal_projection.strategies_page(
                    "okx_demo",
                    limit=1,
                    after=None,
                )["stateVersion"],
            )
        if scope.startswith("demo-session:"):
            collection = scope.rsplit(":", 1)[-1]
            page = self._terminal_page(
                "okx_demo",
                collection,
                limit=1,
                after=None,
            )
            return self._terminal_object(
                "okx_demo",
                state_version=page["stateVersion"],
            )
        if scope.startswith("live-terminal"):
            collection = scope.split(":", 1)[1] if ":" in scope else "strategies"
            page = self._terminal_page(
                "okx_live",
                collection,
                limit=1,
                after=None,
            )
            return self._terminal_object(
                "okx_live",
                state_version=page["stateVersion"],
            )
        if scope == "runtime-health":
            demo = self.terminal_projection.summary("okx_demo")
            live = self.terminal_projection.summary("okx_live")
            status = (
                "healthy"
                if not demo.get("lastError") and not live.get("lastError")
                else "blocked"
            )
            return {
                "status": status,
                "asOf": demo.get("lastHeartbeatAt") or live.get("lastHeartbeatAt"),
                "stateVersion": _state_version(scope, {"demo": demo, "live": live}),
                "demo": demo,
                "live": live,
                "executionAuthorized": False,
                "armed": False,
            }
        if scope == "runtime-lease":
            demo = self.terminal_projection.summary("okx_demo")
            live = self.terminal_projection.summary("okx_live")
            return {
                "status": "healthy"
                if not demo.get("armed") and not live.get("armed")
                else "running",
                "asOf": demo.get("lastHeartbeatAt") or live.get("lastHeartbeatAt"),
                "stateVersion": _state_version(
                    scope,
                    {
                        "demoArmed": demo.get("armed"),
                        "liveArmed": live.get("armed"),
                        "demoDesired": demo.get("desiredEnabled"),
                        "liveDesired": live.get("desiredEnabled"),
                    },
                ),
                "demoArmed": bool(demo.get("armed")),
                "liveArmed": bool(live.get("armed")),
                "executionAuthorized": False,
            }
        raise KeyError(scope)

    def page_projection(
        self,
        scope: str,
        *,
        limit: int,
        after: tuple[Any, ...] | None,
    ) -> ProjectionPageSlice:
        if scope == "evolution-pool":
            if self.strategy_factory is None:
                metadata = self.object_projection(scope)
                return ProjectionPageSlice(
                    items=[],
                    has_more=False,
                    next_key=None,
                    state_version=str(metadata["stateVersion"]),
                )
            return _page_slice(
                self.strategy_factory.list_runs_page(
                    limit=limit,
                    after=after,
                )
            )
        if scope == "demo-fleet":
            return _page_slice(
                self.terminal_projection.strategies_page(
                    "okx_demo",
                    limit=limit,
                    after=after,
                )
            )
        if scope.startswith("demo-session:"):
            collection = scope.rsplit(":", 1)[-1]
            return _page_slice(
                self._terminal_page(
                    "okx_demo",
                    collection,
                    limit=limit,
                    after=after,
                )
            )
        if scope.startswith("live-terminal:"):
            collection = scope.split(":", 1)[1]
            return _page_slice(
                self._terminal_page(
                    "okx_live",
                    collection,
                    limit=limit,
                    after=after,
                )
            )
        raise KeyError(scope)

    def _terminal_object(
        self,
        environment: str,
        *,
        state_version: str,
    ) -> dict[str, object]:
        summary = self.terminal_projection.summary(environment)
        return {
            **summary,
            "status": _status(summary.get("runtimeStatus")),
            "asOf": summary.get("lastHeartbeatAt") or summary.get("updatedAt"),
            "stateVersion": str(state_version),
            "executionAuthorized": False,
        }

    def _terminal_page(
        self,
        environment: str,
        collection: str,
        *,
        limit: int,
        after: tuple[Any, ...] | None,
    ) -> dict[str, Any]:
        method = {
            "strategies": self.terminal_projection.strategies_page,
            "positions": self.terminal_projection.positions_page,
            "orders": self.terminal_projection.orders_page,
            "events": self.terminal_projection.events_page,
        }.get(collection)
        if method is None:
            raise ValueError("terminal_collection_invalid")
        if collection == "orders" and after is not None:
            if len(after) != 2:
                raise ValueError("order_cursor_invalid")
            normalized_after: Any = {
                "createdAt": after[0],
                "recordId": after[1],
            }
        else:
            normalized_after = after
        return method(
            environment,
            limit=limit,
            after=normalized_after,
        )


def build_v63_1_projection_source(
    *,
    strategy_factory_path: Path = DEFAULT_STATE_PATH,
) -> V631ProjectionSource:
    factory = (
        StrategyFactoryV2(strategy_factory_path)
        if Path(strategy_factory_path).is_file()
        else None
    )
    return V631ProjectionSource(
        top200_projection=build_top200_minimal_ui_projection(),
        strategy_factory=factory,
        terminal_projection=TradingTerminalProjection(),
    )
