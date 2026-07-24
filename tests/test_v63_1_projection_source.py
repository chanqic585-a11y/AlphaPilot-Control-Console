from __future__ import annotations

import unittest
from typing import Any

from alphapilot_control_console.v63_1_ui.service import ProjectionPageSlice
from alphapilot_control_console.v63_1_ui.source import V631ProjectionSource


class _FakeTop200:
    def strategy_summary(self) -> dict[str, Any]:
        return {
            "status": "completed",
            "updatedAt": "2026-07-24T01:00:00Z",
            "currentPilot": {"campaignId": "pilot-1"},
        }

    def research_factory_summary(self) -> dict[str, Any]:
        return {
            "status": "completed",
            "updatedAt": "2026-07-24T01:00:00Z",
            "candidateResults": {"eligibleForDemo": 1},
        }

    def strategy_release(self, strategy_id: str) -> dict[str, Any]:
        return {
            "releaseId": strategy_id,
            "displayName": "测试策略",
            "status": "formal_complete",
            "updatedAt": "2026-07-24T01:00:00Z",
        }


class _FakeFactory:
    def __init__(self) -> None:
        self.calls: list[tuple[int, tuple[Any, ...] | None]] = []

    def projection_state_version(self) -> str:
        return "factory-v1"

    def get_run(self, run_id: str) -> dict[str, Any]:
        return {
            "runId": run_id,
            "state": "development_complete",
            "updatedAt": "2026-07-24T01:00:00Z",
        }

    def list_runs_page(
        self,
        *,
        limit: int,
        after: tuple[Any, ...] | None,
    ) -> dict[str, Any]:
        self.calls.append((limit, after))
        items = [
            {
                "runId": f"run-{index}",
                "state": "archived",
                "createdAt": f"2026-07-24T00:00:0{index}Z",
            }
            for index in range(limit)
        ]
        return {
            "items": items,
            "hasMore": True,
            "nextKey": (items[-1]["createdAt"], items[-1]["runId"]),
            "stateVersion": "factory-v1",
        }


class _FakeTerminal:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int, object]] = []

    def summary(self, environment: str) -> dict[str, Any]:
        return {
            "runtimeStatus": "waiting",
            "desiredEnabled": False,
            "armed": False,
            "lastHeartbeatAt": "2026-07-24T01:00:00Z",
            "updatedAt": "2026-07-24T01:00:00Z",
            "environment": environment,
            "strategyOrderCount": 0,
            "openPositionCount": 0,
        }

    def _page(
        self,
        name: str,
        environment: str,
        *,
        limit: int,
        after: object,
    ) -> dict[str, Any]:
        self.calls.append((name, environment, limit, after))
        return {
            "items": [{"id": f"{name}-1"}],
            "hasMore": False,
            "nextKey": None,
            "stateVersion": f"{environment}-v1",
        }

    def strategies_page(self, environment: str, *, limit: int, after: object) -> dict[str, Any]:
        return self._page("strategies", environment, limit=limit, after=after)

    def positions_page(self, environment: str, *, limit: int, after: object) -> dict[str, Any]:
        return self._page("positions", environment, limit=limit, after=after)

    def orders_page(self, environment: str, *, limit: int, after: object) -> dict[str, Any]:
        return self._page("orders", environment, limit=limit, after=after)

    def events_page(self, environment: str, *, limit: int, after: object) -> dict[str, Any]:
        return self._page("events", environment, limit=limit, after=after)


class V631ProjectionSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = _FakeFactory()
        self.terminal = _FakeTerminal()
        self.source = V631ProjectionSource(
            top200_projection=_FakeTop200(),
            strategy_factory=self.factory,
            terminal_projection=self.terminal,
        )

    def test_evolution_pool_delegates_to_factory_keyset_page(self) -> None:
        metadata = self.source.object_projection("evolution-pool")
        page = self.source.page_projection(
            "evolution-pool",
            limit=25,
            after=("2026-07-24T00:00:25Z", "run-25"),
        )

        self.assertEqual(metadata["stateVersion"], "factory-v1")
        self.assertIsInstance(page, ProjectionPageSlice)
        self.assertEqual(len(page.items), 25)
        self.assertEqual(
            self.factory.calls,
            [(25, ("2026-07-24T00:00:25Z", "run-25"))],
        )

    def test_demo_and_live_lists_use_only_bounded_terminal_pages(self) -> None:
        scopes = (
            "demo-fleet",
            "demo-session:session-1:positions",
            "demo-session:session-1:orders",
            "demo-session:session-1:events",
            "live-terminal:strategies",
            "live-terminal:positions",
            "live-terminal:orders",
            "live-terminal:events",
        )

        for scope in scopes:
            with self.subTest(scope=scope):
                page = self.source.page_projection(scope, limit=20, after=None)
                self.assertLessEqual(len(page.items), 20)

        self.assertTrue(all(call[2] == 20 for call in self.terminal.calls))
        self.assertNotIn("unbounded", {call[0] for call in self.terminal.calls})

    def test_object_projection_never_claims_arm_or_execution_authority(self) -> None:
        for scope in ("control-console", "demo-fleet", "live-terminal:orders"):
            with self.subTest(scope=scope):
                projection = self.source.object_projection(scope)
                self.assertFalse(projection["executionAuthorized"])
                self.assertFalse(projection.get("armed", False))

    def test_current_pilot_candidate_resolves_without_a_release(self) -> None:
        class _PilotOnlyTop200(_FakeTop200):
            def strategy_summary(self) -> dict[str, Any]:
                summary = super().strategy_summary()
                summary["currentPilot"] = {
                    "authority": "current_v62_4_acceptance_pilot",
                    "campaignId": "pilot-1",
                    "status": "formal_completed_not_passed",
                    "formalReadyCandidateIds": ["candidate-ready"],
                    "formalBlockedCandidateIds": ["candidate-blocked"],
                    "sourceHashes": {"campaignSummary": "sha256:abc"},
                }
                return summary

            def strategy_release(self, strategy_id: str) -> dict[str, Any]:
                raise KeyError(strategy_id)

        source = V631ProjectionSource(
            top200_projection=_PilotOnlyTop200(),
            strategy_factory=self.factory,
            terminal_projection=self.terminal,
        )

        projection = source.object_projection(
            "strategy-detail",
            object_id="candidate-ready",
        )

        self.assertEqual(projection["candidateId"], "candidate-ready")
        self.assertEqual(projection["campaignId"], "pilot-1")
        self.assertEqual(projection["formalRole"], "formal_ready")
        self.assertEqual(
            projection["sourceAuthority"],
            "current_v62_4_acceptance_pilot",
        )
        self.assertFalse(projection["metricsAvailable"])
        self.assertFalse(projection["executionAuthorized"])


if __name__ == "__main__":
    unittest.main()
