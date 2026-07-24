from __future__ import annotations

from pathlib import Path

from alphapilot_control_console.strategy_factory_v2 import StrategyFactoryV2


def _hypothesis(index: int) -> dict[str, object]:
    return {
        "hypothesisId": f"hypothesis_{index:04d}",
        "familyId": "cursor_pagination_fixture",
        "familyFingerprint": "cursor_pagination_fixture_v1",
        "mechanism": "Bounded fixture for read-only projection pagination.",
        "falsifiableHypothesis": "The fixture is never used for execution.",
        "invalidationConditions": ["fixture_only"],
        "timeframe": "1h",
        "direction": "both",
        "requiredData": ["ohlcv"],
        "exitPolicy": {"policyId": "fixture_exit_v1", "version": 1},
        "sourceArtifactHashes": ["fixture:cursor-pagination"],
    }


def test_strategy_factory_runs_use_stable_keyset_pages(tmp_path: Path) -> None:
    factory = StrategyFactoryV2(tmp_path / "factory.sqlite")
    try:
        for index in range(125):
            factory.create_run(
                run_id=f"run_{index:04d}",
                campaign_id=f"campaign_{index:04d}",
                hypothesis_draft=_hypothesis(index),
            )

        first = factory.list_runs_page(limit=50)
        second = factory.list_runs_page(limit=50, after=first["nextKey"])
        third = factory.list_runs_page(limit=50, after=second["nextKey"])

        assert len(first["items"]) == 50
        assert first["hasMore"] is True
        assert len(second["items"]) == 50
        assert second["hasMore"] is True
        assert len(third["items"]) == 25
        assert third["hasMore"] is False
        assert third["nextKey"] is None

        run_ids = [
            item["runId"]
            for page in (first, second, third)
            for item in page["items"]
        ]
        assert len(run_ids) == 125
        assert len(set(run_ids)) == 125
        assert first["stateVersion"] == second["stateVersion"] == third["stateVersion"]
    finally:
        factory.close()


def test_strategy_factory_page_state_version_changes_with_ledger_state(tmp_path: Path) -> None:
    factory = StrategyFactoryV2(tmp_path / "factory.sqlite")
    try:
        factory.create_run(
            run_id="run_before",
            campaign_id="campaign_before",
            hypothesis_draft=_hypothesis(1),
        )
        before = factory.list_runs_page(limit=10)

        factory.create_run(
            run_id="run_after",
            campaign_id="campaign_after",
            hypothesis_draft=_hypothesis(2),
        )
        after = factory.list_runs_page(limit=10)

        assert before["stateVersion"] != after["stateVersion"]
    finally:
        factory.close()
