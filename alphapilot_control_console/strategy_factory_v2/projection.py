from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from ..config import DATA_DIR
from .ledger import StrategyFactoryV2


DEFAULT_STATE_PATH = DATA_DIR / "strategy_factory_v2" / "strategy_factory_v2.sqlite"


class StrategyFactoryV2Projection:
    """Read-only projection of the research ledger; it never promotes or executes."""

    def __init__(self, state_path: Path = DEFAULT_STATE_PATH) -> None:
        self.state_path = Path(state_path)

    def _read_runs(self, *, limit: int = 500) -> list[dict[str, Any]]:
        factory = StrategyFactoryV2(self.state_path)
        try:
            return factory.list_runs(limit=limit)
        finally:
            factory.close()

    def summary(self) -> dict[str, Any]:
        runs = self._read_runs()
        state_counts = Counter(str(item["state"]) for item in runs)
        return {
            "schemaVersion": "strategy_factory_v2_summary_v1",
            "runCount": len(runs),
            "stateCounts": dict(sorted(state_counts.items())),
            "completedTrialCount": sum(
                int(item.get("completedTrialCount") or 0) for item in runs
            ),
            "formalCompleteCount": state_counts.get("formal_complete", 0),
            "demoReleaseDraftCount": state_counts.get("demo_release_draft", 0),
            "continuousResearchEnabled": False,
            "executionAuthorized": False,
        }

    def runs(self, *, limit: int = 100) -> dict[str, Any]:
        return {
            "schemaVersion": "strategy_factory_v2_runs_v1",
            "runs": self._read_runs(limit=limit),
            "executionAuthorized": False,
        }

    def run(self, run_id: str) -> dict[str, Any]:
        factory = StrategyFactoryV2(self.state_path)
        try:
            return factory.get_run(run_id)
        finally:
            factory.close()


def build_strategy_factory_v2_projection() -> StrategyFactoryV2Projection:
    return StrategyFactoryV2Projection()
