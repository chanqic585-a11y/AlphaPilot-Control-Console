"""Manual-only resume facade for the strategy-validation risk pause."""

from __future__ import annotations

from .strategy_validation_risk_store import StrategyValidationRiskStore


def resume_strategy_validation_demo(
    *, store: StrategyValidationRiskStore, reason: str, actor: str = "human_local_operator"
) -> dict:
    return store.manual_resume(reason=reason, actor=actor)
