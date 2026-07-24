from __future__ import annotations

import unittest
from datetime import datetime, timezone

from alphapilot_control_console.v63_1_ui.contracts import (
    ActionKind,
    DataFreshness,
    NextActionProjection,
    ProjectionConflict,
    StatusPresentationCatalog,
    validate_primary_action_uniqueness,
)
from alphapilot_control_console.v63_1_ui.pagination import (
    CursorError,
    paginate_items,
)


class V631ProjectionContractTests(unittest.TestCase):
    def test_status_catalog_uses_chinese_operator_labels(self) -> None:
        catalog = StatusPresentationCatalog.default()

        running = catalog.present("running")
        blocked = catalog.present("blocked")
        unknown = catalog.present("unexpected_machine_code")

        self.assertEqual(running.labelZh, "运行中")
        self.assertEqual(blocked.labelZh, "已阻塞")
        self.assertEqual(unknown.labelZh, "状态未知")
        self.assertNotIn("unexpected_machine_code", unknown.labelZh)

    def test_page_allows_only_one_primary_action(self) -> None:
        actions = [
            NextActionProjection(
                actionId="open-current-pilot",
                labelZh="查看当前 Pilot",
                actionKind=ActionKind.NAVIGATE,
                enabled=True,
                primary=True,
            ),
            NextActionProjection(
                actionId="export-evidence",
                labelZh="导出研究证据",
                actionKind=ActionKind.RESEARCH_COMMAND,
                enabled=True,
                primary=False,
                expectedStateVersionRequired=True,
            ),
        ]
        validate_primary_action_uniqueness(actions)

        actions[1] = NextActionProjection(
            actionId="export-evidence",
            labelZh="导出研究证据",
            actionKind=ActionKind.RESEARCH_COMMAND,
            enabled=True,
            primary=True,
            expectedStateVersionRequired=True,
        )
        with self.assertRaises(ValueError):
            validate_primary_action_uniqueness(actions)

    def test_forbidden_execution_action_cannot_be_enabled(self) -> None:
        with self.assertRaises(ValueError):
            NextActionProjection(
                actionId="demo-arm",
                labelZh="启动 Demo",
                actionKind=ActionKind.FORBIDDEN_EXECUTION,
                enabled=True,
                primary=True,
            )

    def test_stale_data_cannot_present_strictly_matched(self) -> None:
        freshness = DataFreshness.from_timestamp(
            "2026-07-24T00:00:00Z",
            stale_after_seconds=3,
            now=datetime(2026, 7, 24, 0, 0, 4, tzinfo=timezone.utc),
        )
        self.assertTrue(freshness.isStale)
        self.assertEqual(freshness.status, "stale")
        self.assertEqual(freshness.labelZh, "数据陈旧")
        self.assertFalse(freshness.allowsStrictMatch)

    def test_state_version_conflict_is_a_structured_409_contract(self) -> None:
        conflict = ProjectionConflict(
            expectedStateVersion="state-v2",
            actualStateVersion="state-v3",
        )

        self.assertEqual(conflict.httpStatus, 409)
        self.assertEqual(conflict.error, "state_version_mismatch")
        self.assertTrue(conflict.refreshProjectionRequired)
        self.assertEqual(
            conflict.operatorMessageZh,
            "底层状态已变更，请基于最新状态操作",
        )

    def test_cursor_pagination_is_bounded_and_has_no_duplicates(self) -> None:
        items = [
            {"candidateId": f"candidate-{index:04d}", "sequence": index}
            for index in range(3_000, 0, -1)
        ]
        seen: list[str] = []
        cursor: str | None = None

        while True:
            page = paginate_items(
                items,
                limit=97,
                cursor=cursor,
                scope="evolution-pool",
                state_version="state-v1",
                key=lambda item: (item["sequence"], item["candidateId"]),
            )
            self.assertLessEqual(len(page.items), 97)
            seen.extend(item["candidateId"] for item in page.items)
            self.assertEqual(page.hasMore, page.nextCursor is not None)
            if not page.hasMore:
                break
            cursor = page.nextCursor

        self.assertEqual(len(seen), 3_000)
        self.assertEqual(len(set(seen)), 3_000)

    def test_cursor_is_bound_to_scope_and_state_version(self) -> None:
        items = [
            {"candidateId": f"candidate-{index}", "sequence": index}
            for index in range(20, 0, -1)
        ]
        first = paginate_items(
            items,
            limit=5,
            cursor=None,
            scope="evolution-pool",
            state_version="state-v1",
            key=lambda item: (item["sequence"], item["candidateId"]),
        )
        self.assertIsNotNone(first.nextCursor)

        with self.assertRaises(CursorError) as scope_error:
            paginate_items(
                items,
                limit=5,
                cursor=first.nextCursor,
                scope="demo-fleet",
                state_version="state-v1",
                key=lambda item: (item["sequence"], item["candidateId"]),
            )
        self.assertEqual(scope_error.exception.code, "cursor_scope_mismatch")

        with self.assertRaises(CursorError) as version_error:
            paginate_items(
                items,
                limit=5,
                cursor=first.nextCursor,
                scope="evolution-pool",
                state_version="state-v2",
                key=lambda item: (item["sequence"], item["candidateId"]),
            )
        self.assertEqual(version_error.exception.code, "cursor_state_version_mismatch")

    def test_cursor_rejects_payload_tampering(self) -> None:
        first = paginate_items(
            [{"candidateId": str(index), "sequence": index} for index in range(20)],
            limit=5,
            cursor=None,
            scope="evolution-pool",
            state_version="state-v1",
            key=lambda item: (item["sequence"], item["candidateId"]),
        )
        self.assertIsNotNone(first.nextCursor)

        tampered = str(first.nextCursor)
        replacement = "A" if tampered[-1] != "A" else "B"
        tampered = f"{tampered[:-1]}{replacement}"

        with self.assertRaises(CursorError) as raised:
            paginate_items(
                [{"candidateId": str(index), "sequence": index} for index in range(20)],
                limit=5,
                cursor=tampered,
                scope="evolution-pool",
                state_version="state-v1",
                key=lambda item: (item["sequence"], item["candidateId"]),
            )
        self.assertEqual(raised.exception.code, "cursor_invalid")

    def test_page_size_is_clamped_to_contract_maximum(self) -> None:
        page = paginate_items(
            [{"candidateId": str(index), "sequence": index} for index in range(500)],
            limit=10_000,
            cursor=None,
            scope="evolution-pool",
            state_version="state-v1",
            key=lambda item: (item["sequence"], item["candidateId"]),
        )
        self.assertEqual(page.pageSize, 200)
        self.assertEqual(len(page.items), 200)


if __name__ == "__main__":
    unittest.main()
