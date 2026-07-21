"""Exact approval gate that runs only after technical readiness passes."""

from __future__ import annotations

from typing import Any, Mapping


class ExactLiveReleaseApprovalGate:
    """Validate an actionable request against exact immutable identities."""

    def evaluate(
        self,
        *,
        bundle: Mapping[str, Any],
        approval: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        blockers: list[str] = []
        technical = dict(
            bundle.get("adaptiveLearningTechnicalReadiness")
            or bundle.get("adaptiveLearningReadiness")
            or {}
        )
        release = dict(bundle.get("liveRelease") or {})
        risk = dict(bundle.get("riskOverlay") or {})
        request = dict(bundle.get("approvalRequest") or {})
        profile = dict(bundle.get("profile") or risk.get("profile") or {})

        if technical.get("passed") is not True:
            blockers.append("adaptive_learning_technical_readiness_not_passed")
        if request.get("approvalRequestActionable") is not True:
            blockers.append("approval_request_not_actionable")
        if (
            release.get("executionBoundary") or {}
        ).get("mechanicalExecutionAllowedAfterExactApproval") is not True:
            blockers.append("mechanical_execution_not_allowed_after_approval")
        if approval is None:
            blockers.append("exact_live_release_approval_missing")
        else:
            checks = {
                "actor": str(approval.get("actor") or "") == "user_manual",
                "confirmation": str(approval.get("confirmation") or "")
                == str(request.get("requiredConfirmation") or ""),
                "releaseHash": str(approval.get("releaseHash") or "")
                == str(release.get("releaseHash") or ""),
                "riskOverlayHash": str(approval.get("riskOverlayHash") or "")
                == str(risk.get("riskOverlayHash") or ""),
                "maximumAcceptedLossUSDT": float(
                    approval.get("maximumAcceptedLossUSDT") or -1
                )
                == float(profile.get("maximumAcceptedLossUSDT") or -2),
            }
            blockers.extend(
                f"exact_live_release_approval_mismatch:{key}"
                for key, passed in checks.items()
                if not passed
            )
        return {
            "schemaVersion": "exact_live_release_approval_gate_v1",
            "passed": not blockers,
            "approvalRequestActionable": request.get("approvalRequestActionable") is True,
            "releaseHash": str(release.get("releaseHash") or ""),
            "riskOverlayHash": str(risk.get("riskOverlayHash") or ""),
            "blockers": blockers,
            "createsOrders": False,
            "armsRuntime": False,
        }
