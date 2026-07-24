from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from .contracts import (
    ActionKind,
    DataFreshness,
    NextActionProjection,
    ProjectionConflict,
    StatusPresentationCatalog,
)
from .pagination import (
    CursorError,
    CursorPage,
    decode_cursor,
    encode_cursor,
    normalize_page_size,
)


@dataclass(frozen=True)
class ProjectionPageSlice:
    items: list[dict[str, object]]
    has_more: bool
    next_key: tuple[Any, ...] | None
    state_version: str


class ProjectionSource(Protocol):
    def object_projection(
        self,
        scope: str,
        *,
        object_id: str | None = None,
    ) -> dict[str, object]: ...

    def page_projection(
        self,
        scope: str,
        *,
        limit: int,
        after: tuple[Any, ...] | None,
    ) -> ProjectionPageSlice: ...


class StateVersionMismatch(RuntimeError):
    def __init__(self, conflict: ProjectionConflict) -> None:
        super().__init__(conflict.error)
        self.conflict = conflict


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class V631ProjectionService:
    """Read-only V63.1 projection facade.

    The facade never reads an unbounded collection. Each collection source must
    implement keyset pagination and may return at most ``limit + 1`` rows.
    """

    SCHEMA_VERSION = "alphapilot_v63_1_projection_v1"

    def __init__(self, source: ProjectionSource) -> None:
        self.source = source
        self.status_catalog = StatusPresentationCatalog.default()

    def control_console(self) -> dict[str, object]:
        return self._object("control-console")

    def strategy_detail(self, strategy_id: str) -> dict[str, object]:
        return self._object("strategy-detail", object_id=strategy_id)

    def evolution_pool(
        self,
        *,
        limit: int | str | None = None,
        cursor: str | None = None,
    ) -> dict[str, object]:
        return self._collection("evolution-pool", limit=limit, cursor=cursor)

    def demo_fleet(
        self,
        *,
        limit: int | str | None = None,
        cursor: str | None = None,
    ) -> dict[str, object]:
        return self._collection("demo-fleet", limit=limit, cursor=cursor)

    def demo_session(
        self,
        session_id: str,
        *,
        collection: str,
        limit: int | str | None = None,
        cursor: str | None = None,
    ) -> dict[str, object]:
        normalized = collection.strip().lower()
        if normalized not in {"positions", "orders", "events"}:
            raise ValueError("demo_session_collection_invalid")
        return self._collection(
            f"demo-session:{session_id}:{normalized}",
            limit=limit,
            cursor=cursor,
        )

    def live_terminal(
        self,
        *,
        collection: str,
        limit: int | str | None = None,
        cursor: str | None = None,
    ) -> dict[str, object]:
        normalized = collection.strip().lower()
        if normalized not in {"strategies", "positions", "orders", "events"}:
            raise ValueError("live_terminal_collection_invalid")
        return self._collection(
            f"live-terminal:{normalized}",
            limit=limit,
            cursor=cursor,
        )

    def runtime_health(self) -> dict[str, object]:
        return self._object("runtime-health")

    def runtime_lease(self) -> dict[str, object]:
        return self._object("runtime-lease")

    def status_catalog_projection(self) -> dict[str, object]:
        catalog = self.status_catalog.to_dict()
        return {
            "schemaVersion": self.SCHEMA_VERSION,
            "scope": "status-catalog",
            "generatedAt": _utc_now(),
            "stateVersion": "status-presentation-v1",
            "collection": CursorPage(
                items=list(catalog.values()),
                pageSize=len(catalog),
                nextCursor=None,
                hasMore=False,
                stateVersion="status-presentation-v1",
            ).to_dict(),
            "executionAuthorized": False,
        }

    def action_catalog_projection(self) -> dict[str, object]:
        actions = [
            self._navigate_action(
                "open_control_console",
                "打开总览控制台",
                "/v63a/control",
                primary=True,
            ).to_dict(),
            self._navigate_action(
                "open_evolution_pool",
                "查看进化孵化舱",
                "/v63a/evolution",
            ).to_dict(),
        ]
        return {
            "schemaVersion": self.SCHEMA_VERSION,
            "scope": "action-catalog",
            "generatedAt": _utc_now(),
            "stateVersion": "v63-1-read-only-actions-v1",
            "collection": CursorPage(
                items=actions,
                pageSize=len(actions),
                nextCursor=None,
                hasMore=False,
                stateVersion="v63-1-read-only-actions-v1",
            ).to_dict(),
            "executionAuthorized": False,
        }

    def navigation_projection(self) -> dict[str, object]:
        rows = [
            {"route": "/v63a/control", "labelZh": "总览仪表盘"},
            {"route": "/v63a/evolution", "labelZh": "进化与孵化舱"},
            {"route": "/v63a/demo", "labelZh": "Demo 舰队"},
            {"route": "/v63a/live", "labelZh": "实盘终端"},
        ]
        return {
            "schemaVersion": self.SCHEMA_VERSION,
            "scope": "navigation",
            "generatedAt": _utc_now(),
            "stateVersion": "v63-1-navigation-v1",
            "collection": CursorPage(
                items=rows,
                pageSize=len(rows),
                nextCursor=None,
                hasMore=False,
                stateVersion="v63-1-navigation-v1",
            ).to_dict(),
            "executionAuthorized": False,
        }

    def _object(
        self,
        scope: str,
        *,
        object_id: str | None = None,
    ) -> dict[str, object]:
        payload = dict(self.source.object_projection(scope, object_id=object_id))
        state_version = str(payload.get("stateVersion") or "unavailable")
        status = str(payload.get("status") or "unknown")
        as_of = payload.get("asOf")
        freshness = DataFreshness.from_timestamp(
            str(as_of) if as_of else None,
            stale_after_seconds=3,
        )
        payload.update(
            {
                "schemaVersion": self.SCHEMA_VERSION,
                "scope": scope,
                "generatedAt": _utc_now(),
                "stateVersion": state_version,
                "statusPresentation": self.status_catalog.present(status).to_dict(),
                "freshness": freshness.to_dict(),
                "nextActions": CursorPage(
                    items=[
                        self._navigate_action(
                            "refresh_projection",
                            "刷新当前状态",
                            None,
                            primary=True,
                        ).to_dict()
                    ],
                    pageSize=1,
                    nextCursor=None,
                    hasMore=False,
                    stateVersion=state_version,
                ).to_dict(),
                "executionAuthorized": False,
            }
        )
        return payload

    def _collection(
        self,
        scope: str,
        *,
        limit: int | str | None,
        cursor: str | None,
    ) -> dict[str, object]:
        page_size = normalize_page_size(limit)
        metadata = self.source.object_projection(scope)
        actual_state_version = str(metadata.get("stateVersion") or "unavailable")
        after: tuple[Any, ...] | None = None
        if cursor:
            decoded = decode_cursor(cursor, scope=scope)
            expected_state_version = str(decoded.get("stateVersion") or "")
            if expected_state_version != actual_state_version:
                raise StateVersionMismatch(
                    ProjectionConflict(
                        expectedStateVersion=expected_state_version,
                        actualStateVersion=actual_state_version,
                    )
                )
            after = tuple(decoded["last"])

        source_page = self.source.page_projection(
            scope,
            limit=page_size,
            after=after,
        )
        if source_page.state_version != actual_state_version:
            raise StateVersionMismatch(
                ProjectionConflict(
                    expectedStateVersion=actual_state_version,
                    actualStateVersion=source_page.state_version,
                )
            )
        next_cursor = None
        if source_page.has_more:
            if source_page.next_key is None:
                raise CursorError("cursor_next_key_missing")
            next_cursor = encode_cursor(
                scope=scope,
                state_version=actual_state_version,
                last=source_page.next_key,
            )

        payload = dict(metadata)
        payload.update(
            {
                "schemaVersion": self.SCHEMA_VERSION,
                "scope": scope,
                "generatedAt": _utc_now(),
                "stateVersion": actual_state_version,
                "collection": CursorPage(
                    items=source_page.items,
                    pageSize=page_size,
                    nextCursor=next_cursor,
                    hasMore=source_page.has_more,
                    stateVersion=actual_state_version,
                ).to_dict(),
                "executionAuthorized": False,
            }
        )
        return payload

    @staticmethod
    def _navigate_action(
        action_id: str,
        label_zh: str,
        href: str | None,
        *,
        primary: bool = False,
    ) -> NextActionProjection:
        return NextActionProjection(
            actionId=action_id,
            labelZh=label_zh,
            actionKind=ActionKind.NAVIGATE,
            enabled=True,
            primary=primary,
            href=href,
        )
