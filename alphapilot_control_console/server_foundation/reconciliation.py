"""Fail-closed startup reconciliation for all V63 worker roles."""

from __future__ import annotations

from dataclasses import dataclass


class StartupReconciliationBlocked(PermissionError):
    """Raised when a headless worker cannot prove a safe startup state."""


@dataclass(frozen=True)
class StartupState:
    demoArmed: bool
    liveArmed: bool
    openOrderCount: int
    unknownOrderCount: int
    openPositionCount: int
    withdrawEnabled: bool


@dataclass(frozen=True)
class StartupReconciliationDecision:
    passed: bool
    reasonCodes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": "alphapilot_v63_startup_reconciliation_v1",
            "passed": self.passed,
            "reasonCodes": list(self.reasonCodes),
        }


def evaluate_startup_state(
    state: StartupState,
) -> StartupReconciliationDecision:
    reasons: list[str] = []
    if state.demoArmed:
        reasons.append("demoArmed_true")
    if state.liveArmed:
        reasons.append("liveArmed_true")
    if state.openOrderCount != 0:
        reasons.append("openOrderCount_nonzero")
    if state.unknownOrderCount != 0:
        reasons.append("unknownOrderCount_nonzero")
    if state.openPositionCount != 0:
        reasons.append("openPositionCount_nonzero")
    if state.withdrawEnabled:
        reasons.append("withdrawEnabled_true")
    return StartupReconciliationDecision(
        passed=not reasons,
        reasonCodes=tuple(reasons),
    )


def assert_startup_reconciled(
    state: StartupState,
) -> StartupReconciliationDecision:
    decision = evaluate_startup_state(state)
    if not decision.passed:
        raise StartupReconciliationBlocked(
            "startup_reconciliation_blocked:" + ",".join(decision.reasonCodes)
        )
    return decision
