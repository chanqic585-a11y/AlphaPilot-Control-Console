"""Loopback HTTP-facing helpers for strategy-validation approval actions."""

from __future__ import annotations

from typing import Any

from .strategy_validation_approval_store import StrategyValidationApprovalStore


def approve_strategy_validation_release(
    payload: dict[str, Any], store: StrategyValidationApprovalStore
) -> dict[str, Any]:
    return store.approve(
        releaseId=str(payload.get("releaseId") or ""),
        releaseHash=str(payload.get("releaseHash") or ""),
        riskConfigHash=str(payload.get("riskConfigHash") or ""),
        reason=str(payload.get("reason") or ""),
        actor="human_local_operator",
    )

def revoke_strategy_validation_release(
    payload: dict[str, Any], store: StrategyValidationApprovalStore
) -> dict[str, Any]:
    return store.revoke(
        releaseId=str(payload.get("releaseId") or ""),
        releaseHash=str(payload.get("releaseHash") or ""),
        riskConfigHash=str(payload.get("riskConfigHash") or ""),
        reason=str(payload.get("reason") or ""),
        actor="human_local_operator",
    )
