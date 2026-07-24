from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from alphapilot_control_console.v63_1_ui.service import (
    ProjectionPageSlice,
    StateVersionMismatch,
    V631ProjectionService,
)


@dataclass
class _Call:
    scope: str
    limit: int
    after: tuple[Any, ...] | None


class _FakeSource:
    def __init__(self, *, state_version: str = "state-v1") -> None:
        self.state_version = state_version
        self.calls: list[_Call] = []
        self.items = [
            {
                "candidateId": f"candidate-{index:04d}",
                "createdAt": f"2026-07-24T00:{index // 60:02d}:{index % 60:02d}Z",
                "status": "archived" if index % 2 else "running",
            }
            for index in range(3_000)
        ]

    def object_projection(
        self,
        scope: str,
        *,
        object_id: str | None = None,
    ) -> dict[str, object]:
        return {
            "scope": scope,
            "objectId": object_id,
            "stateVersion": self.state_version,
            "status": "healthy",
        }

    def page_projection(
        self,
        scope: str,
        *,
        limit: int,
        after: tuple[Any, ...] | None,
    ) -> ProjectionPageSlice:
        self.calls.append(_Call(scope=scope, limit=limit, after=after))
        ordered = sorted(
            self.items,
            key=lambda item: (item["createdAt"], item["candidateId"]),
            reverse=True,
        )
        if after is not None:
            ordered = [
                item
                for item in ordered
                if (item["createdAt"], item["candidateId"]) < after
            ]
        selected = ordered[: limit + 1]
        page_items = selected[:limit]
        return ProjectionPageSlice(
            items=page_items,
            has_more=len(selected) > limit,
            next_key=(
                (page_items[-1]["createdAt"], page_items[-1]["candidateId"])
                if len(selected) > limit and page_items
                else None
            ),
            state_version=self.state_version,
        )


class V631ProjectionServiceTests(unittest.TestCase):
    def test_evolution_pool_uses_bounded_cursor_pages_for_large_collections(self) -> None:
        source = _FakeSource()
        service = V631ProjectionService(source)

        first = service.evolution_pool(limit=50)
        second = service.evolution_pool(
            limit=50,
            cursor=str(first["collection"]["nextCursor"]),
        )

        self.assertEqual(len(first["collection"]["items"]), 50)
        self.assertTrue(first["collection"]["hasMore"])
        self.assertEqual(len(second["collection"]["items"]), 50)
        self.assertTrue(second["collection"]["hasMore"])
        self.assertLessEqual(max(call.limit for call in source.calls), 50)
        self.assertEqual(source.calls[0].after, None)
        self.assertIsNotNone(source.calls[1].after)
        self.assertNotEqual(
            first["collection"]["items"][0]["candidateId"],
            second["collection"]["items"][0]["candidateId"],
        )

    def test_cursor_is_rejected_after_underlying_state_version_changes(self) -> None:
        source = _FakeSource()
        service = V631ProjectionService(source)
        first = service.evolution_pool(limit=25)
        cursor = str(first["collection"]["nextCursor"])
        source.state_version = "state-v2"

        with self.assertRaises(StateVersionMismatch) as raised:
            service.evolution_pool(limit=25, cursor=cursor)

        conflict = raised.exception.conflict.to_dict()
        self.assertEqual(conflict["httpStatus"], 409)
        self.assertTrue(conflict["refreshProjectionRequired"])
        self.assertEqual(
            conflict["operatorMessageZh"],
            "底层状态已变更，请基于最新状态操作",
        )

    def test_all_operational_list_projections_share_the_cursor_envelope(self) -> None:
        source = _FakeSource()
        service = V631ProjectionService(source)

        projections = (
            service.evolution_pool(limit=20),
            service.demo_fleet(limit=20),
            service.demo_session("session-1", collection="orders", limit=20),
            service.live_terminal(collection="positions", limit=20),
        )

        for projection in projections:
            with self.subTest(scope=projection["scope"]):
                collection = projection["collection"]
                self.assertEqual(collection["pageSize"], 20)
                self.assertIn("nextCursor", collection)
                self.assertIn("hasMore", collection)
                self.assertEqual(collection["stateVersion"], "state-v1")

    def test_projection_actions_never_expose_demo_live_or_order_commands(self) -> None:
        source = _FakeSource()
        service = V631ProjectionService(source)

        for projection in (
            service.control_console(),
            service.strategy_detail("strategy-1"),
            service.evolution_pool(limit=10),
            service.demo_fleet(limit=10),
            service.live_terminal(collection="positions", limit=10),
        ):
            serialized = str(projection).lower()
            self.assertNotIn("demo_arm", serialized)
            self.assertNotIn("live_arm", serialized)
            self.assertNotIn("place_order", serialized)
            self.assertNotIn("withdraw", serialized)
            self.assertFalse(projection["executionAuthorized"])


if __name__ == "__main__":
    unittest.main()
