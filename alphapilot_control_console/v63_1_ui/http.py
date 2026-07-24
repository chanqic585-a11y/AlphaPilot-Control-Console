from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, ContextManager, Mapping, Sequence
from urllib.parse import unquote

from .pagination import CursorError
from .service import StateVersionMismatch, V631ProjectionService
from .source import build_v63_1_projection_source


FEATURE_FLAG = "ALPHAPILOT_V63A_UI_ENABLED"
STALE_AFTER_SECONDS = 3
_TRUTHY = {"1", "true", "yes", "on", "enabled"}


@dataclass(frozen=True)
class V631HttpResult:
    status: int
    payload: dict[str, object]


@contextmanager
def _default_service_context():
    source = build_v63_1_projection_source()
    try:
        yield V631ProjectionService(source)
    finally:
        source.close()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _first(query: Mapping[str, Sequence[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    value = str(values[0]).strip()
    return value or None


class V631HttpRouter:
    """Feature-gated, read-only HTTP adapter for V63.1 projections."""

    def __init__(
        self,
        *,
        service_context: Callable[[], ContextManager[V631ProjectionService]]
        | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._service_context = service_context or _default_service_context
        self._environ = environ if environ is not None else os.environ

    @property
    def enabled(self) -> bool:
        return str(self._environ.get(FEATURE_FLAG, "")).strip().lower() in _TRUTHY

    def handle_get(
        self,
        path: str,
        query: Mapping[str, Sequence[str]],
    ) -> V631HttpResult | None:
        if not self.enabled or not path.startswith("/api/v63/"):
            return None
        if path == "/api/v63/events":
            return None

        limit = _first(query, "limit")
        cursor = _first(query, "cursor")
        try:
            with self._service_context() as service:
                payload = self._read_projection(
                    service,
                    path=path,
                    limit=limit,
                    cursor=cursor,
                )
        except StateVersionMismatch as error:
            conflict = error.conflict.to_dict()
            return V631HttpResult(
                status=409,
                payload={
                    **conflict,
                    "message": conflict["operatorMessageZh"],
                    "refreshRequired": conflict["refreshProjectionRequired"],
                },
            )
        except CursorError as error:
            return V631HttpResult(
                status=400,
                payload={
                    "error": error.code,
                    "message": "分页游标无效，请刷新页面后重试",
                    "refreshRequired": True,
                },
            )
        except KeyError:
            return V631HttpResult(status=404, payload={"error": "not_found"})
        except ValueError as error:
            return V631HttpResult(
                status=400,
                payload={"error": str(error) or "invalid_request"},
            )

        return V631HttpResult(status=200, payload=payload)

    def heartbeat_payload(self) -> dict[str, object]:
        return {
            "schemaVersion": V631ProjectionService.SCHEMA_VERSION,
            "event": "heartbeat",
            "generatedAt": _utc_now(),
            "monotonicNs": time.monotonic_ns(),
            "connectionStatus": "connected",
            "staleAfterSeconds": STALE_AFTER_SECONDS,
            "executionAuthorized": False,
        }

    @staticmethod
    def _read_projection(
        service: V631ProjectionService,
        *,
        path: str,
        limit: str | None,
        cursor: str | None,
    ) -> dict[str, object]:
        if path == "/api/v63/projections/control-console":
            return service.control_console()
        if path == "/api/v63/projections/evolution-pool":
            return service.evolution_pool(limit=limit, cursor=cursor)
        if path == "/api/v63/projections/demo-fleet":
            return service.demo_fleet(limit=limit, cursor=cursor)
        if path == "/api/v63/runtime/health":
            return service.runtime_health()
        if path == "/api/v63/runtime/lease":
            return service.runtime_lease()
        if path == "/api/v63/catalogs/status":
            return service.status_catalog_projection()
        if path == "/api/v63/catalogs/actions":
            return service.action_catalog_projection()
        if path == "/api/v63/navigation":
            return service.navigation_projection()

        strategy_prefix = "/api/v63/projections/strategies/"
        if path.startswith(strategy_prefix):
            strategy_id = unquote(path[len(strategy_prefix) :]).strip()
            if not strategy_id or "/" in strategy_id:
                raise ValueError("strategy_id_invalid")
            return service.strategy_detail(strategy_id)

        demo_prefix = "/api/v63/projections/demo-sessions/"
        if path.startswith(demo_prefix):
            parts = [
                unquote(value).strip()
                for value in path[len(demo_prefix) :].split("/")
            ]
            if len(parts) != 2 or not all(parts):
                raise ValueError("demo_session_route_invalid")
            return service.demo_session(
                parts[0],
                collection=parts[1],
                limit=limit,
                cursor=cursor,
            )

        live_prefix = "/api/v63/projections/live-terminal/"
        if path.startswith(live_prefix):
            collection = unquote(path[len(live_prefix) :]).strip()
            return service.live_terminal(
                collection=collection,
                limit=limit,
                cursor=cursor,
            )
        raise KeyError(path)
