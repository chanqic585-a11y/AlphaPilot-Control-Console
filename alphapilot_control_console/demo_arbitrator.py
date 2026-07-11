"""Deterministic conflict and concentration arbitration for Demo signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class DemoArbitrationResult:
    selected: tuple[dict[str, Any], ...]
    rejected: tuple[dict[str, Any], ...]


def arbitrate_demo_signals(
    signals: Iterable[dict[str, Any]],
    *,
    maxPositions: int,
    coolingCandidateIds: set[str] | None = None,
    allowSameFamilyMultipleSymbols: bool = False,
) -> DemoArbitrationResult:
    if maxPositions < 1:
        raise ValueError("maxPositions must be positive")
    cooling = coolingCandidateIds or set()
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    symbol_sides: dict[str, str] = {}
    families: set[str] = set()
    correlation_groups: set[str] = set()
    ordered = sorted(signals, key=lambda item: float(item.get("score") or 0.0), reverse=True)
    for signal in ordered:
        candidate_id = str(signal.get("candidateId") or "")
        family = str(signal.get("strategyFamilyId") or "")
        symbol = str(signal.get("instId") or "")
        side = str(signal.get("side") or "")
        correlation_group = str(signal.get("correlationGroup") or "")
        reason = None
        if not candidate_id or not family or not symbol or side not in {"buy", "sell"}:
            reason = "incomplete_signal"
        elif candidate_id in cooling:
            reason = "candidate_cooldown"
        elif symbol in symbol_sides and symbol_sides[symbol] != side:
            reason = "symbol_direction_conflict"
        elif symbol in symbol_sides:
            reason = "duplicate_symbol_signal"
        elif family in families and not allowSameFamilyMultipleSymbols:
            reason = "duplicate_strategy_family"
        elif correlation_group and correlation_group in correlation_groups:
            reason = "correlated_strategy_conflict"
        elif len(selected) >= maxPositions:
            reason = "portfolio_position_limit"
        if reason:
            rejected.append({**signal, "reason": reason})
            continue
        selected.append(dict(signal))
        symbol_sides[symbol] = side
        families.add(family)
        if correlation_group:
            correlation_groups.add(correlation_group)
    return DemoArbitrationResult(tuple(selected), tuple(rejected))
