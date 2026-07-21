"""Final Live ARM gate for an approved, technically ready identity."""

from __future__ import annotations

from typing import Any, Mapping


class LiveArmGate:
    """Evaluate runtime preconditions without arming or creating orders."""

    def evaluate(
        self,
        *,
        bundle: Mapping[str, Any],
        approval_gate: Mapping[str, Any],
        runtime: Mapping[str, Any],
    ) -> dict[str, Any]:
        blockers: list[str] = []
        release = dict(bundle.get("liveRelease") or {})
        technical = dict(
            bundle.get("adaptiveLearningTechnicalReadiness")
            or bundle.get("adaptiveLearningReadiness")
            or {}
        )
        if technical.get("passed") is not True:
            blockers.append("adaptive_learning_technical_readiness_not_passed")
        if approval_gate.get("passed") is not True:
            blockers.append("exact_live_release_approval_gate_not_passed")
            blockers.extend(
                str(value)
                for value in approval_gate.get("blockers") or []
                if str(value) not in blockers
            )
        if (
            release.get("executionBoundary") or {}
        ).get("mechanicalExecutionAllowedAfterExactApproval") is not True:
            blockers.append("mechanical_execution_not_allowed_after_approval")

        checks = {
            "live_runtime_credentials_missing": runtime.get("credentialsConfigured") is True,
            "live_private_read_not_ready": runtime.get("privateReadReady") is True,
            "live_reconciliation_not_confirmed": runtime.get("reconciliationMatched") is True,
            "live_open_positions_not_zero": runtime.get("zeroOpenPositions") is True
            or int(runtime.get("openPositionCount") or 0) == 0,
            "live_open_orders_not_zero": runtime.get("zeroOpenOrders") is True
            or int(runtime.get("openOrderCount") or 0) == 0,
            "live_must_be_disabled_before_arm": runtime.get("liveEnabled") is not True,
            "withdraw_must_remain_disabled": runtime.get("withdrawAllowed") is not True,
        }
        blockers.extend(name for name, passed in checks.items() if not passed)
        return {
            "schemaVersion": "live_arm_gate_v1",
            "passed": not blockers,
            "releaseHash": str(release.get("releaseHash") or ""),
            "riskOverlayHash": str(
                (bundle.get("riskOverlay") or {}).get("riskOverlayHash") or ""
            ),
            "blockers": blockers,
            "armStatus": "not_run",
            "createsOrders": False,
            "liveEnabled": False,
            "withdrawAllowed": False,
        }
