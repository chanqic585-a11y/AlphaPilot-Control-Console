"""Project the exact approved TOP200 portfolio into executable Demo components."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import DATA_DIR
from .demo_execution_store import DemoExecutionStore
from .dynamic_top200_universe import MAXIMUM_INSTRUMENT_COUNT
from .evolution_demo_service import (
    STORE_PATH,
    _contract_hash,
    discover_demo_contracts,
)


RELEASE_ROOT = DATA_DIR / "v54_v60" / "release"
CONTROL_AUDIT_ROOT = DATA_DIR / "v54_v60" / "control" / "audit"
FINAL_RELEASE_PATH = RELEASE_ROOT / "final_superseding_provisional_release.json"
FINAL_RISK_OVERLAY_PATH = RELEASE_ROOT / "final_portfolio_risk_overlay.json"
FROZEN_SOURCE_COMPONENT_ROOT = RELEASE_ROOT / "source_component_contracts"
APPROVAL_OVERLAY_PATH = CONTROL_AUDIT_ROOT / "demo_approval_overlay.json"
ARM_AUDIT_PATH = CONTROL_AUDIT_ROOT / "demo_arm_audit.json"
PORTFOLIO_COMPONENT_MODE = "provisional_research_demo_portfolio_component"


def _load_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _load_frozen_source_contracts() -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    if not FROZEN_SOURCE_COMPONENT_ROOT.exists():
        return contracts
    for path in sorted(FROZEN_SOURCE_COMPONENT_ROOT.glob("*.json")):
        payload = _load_optional(path)
        if payload is not None:
            contracts.append(payload)
    return contracts


def _exact_identity_matches(
    release: Mapping[str, Any],
    control: Mapping[str, Any],
) -> bool:
    return all(
        control.get(field) == release.get(field)
        for field in (
            "releaseId",
            "releaseHash",
            "riskOverlayHash",
            "executionIntersectionHash",
        )
    )


def _effective_risk_envelope(
    source: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> dict[str, Any]:
    effective = deepcopy(dict(source))
    effective["environment"] = "okx_demo"
    effective["marginMode"] = str(overlay.get("marginMode") or "isolated")
    effective["riskPerTradePercent"] = float(overlay["riskPerTradePercent"])
    effective["maxOpenRiskPercent"] = float(
        overlay["maximumPortfolioOpenRiskPercent"]
    )
    effective["maxConcurrentPositions"] = int(
        overlay["maximumConcurrentPositions"]
    )
    effective["maxLeverage"] = min(
        int(effective.get("maxLeverage") or overlay["maxLeverage"]),
        int(overlay["maxLeverage"]),
    )
    effective["defaultMaxLeverage"] = min(
        int(effective.get("defaultMaxLeverage") or effective["maxLeverage"]),
        effective["maxLeverage"],
    )
    effective["feeRate"] = float(overlay.get("feeRate") or 0.0)
    effective["slippageRate"] = float(overlay.get("slippageRate") or 0.0)
    effective["approvedRiskOverlayHash"] = str(overlay["riskOverlayHash"])
    effective["initialStopMayWiden"] = False
    effective["noAdding"] = True
    effective["noAveraging"] = True
    effective["noMartingale"] = True
    return effective


def _component_identities(release: Mapping[str, Any]) -> list[dict[str, Any]]:
    execution_identity = (
        release.get("executionIdentity")
        if isinstance(release.get("executionIdentity"), Mapping)
        else {}
    )
    rows = execution_identity.get("componentIdentities")
    if not isinstance(rows, list) or not rows:
        raise PermissionError("approved portfolio component identities are missing")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _derive_component_contract(
    *,
    release: Mapping[str, Any],
    identity: Mapping[str, Any],
    source: Mapping[str, Any],
    risk_overlay: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_id = str(identity.get("candidateId") or "")
    strategy = source.get("strategy") if isinstance(source.get("strategy"), Mapping) else {}
    actual = {
        "candidateId": source.get("strategyCandidateId"),
        "sourceContractHash": source.get("contractHash"),
        "sourceReleaseHash": source.get("releaseContentHash"),
        "strategyDefinitionHash": strategy.get("strategyContentHash"),
    }
    expected = {
        key: identity.get(key)
        for key in (
            "candidateId",
            "sourceContractHash",
            "sourceReleaseHash",
            "strategyDefinitionHash",
        )
    }
    if actual != expected:
        raise PermissionError(f"component identity mismatch: {candidate_id}")

    derived = deepcopy(dict(source))
    for field in (
        "bypassedEvidence",
        "formalCandidateRegistration",
        "overrideAudit",
        "reason",
        "successorMetadata",
        "supersedesDemoReleaseId",
    ):
        derived.pop(field, None)
    derived.update(
        {
            "status": "demo_active",
            "releaseMode": PORTFOLIO_COMPONENT_MODE,
            "livePromotionAllowed": False,
            "demoReleaseId": str(release["releaseId"]),
            "releaseContentHash": str(release["releaseHash"]),
            "riskEnvelope": _effective_risk_envelope(
                source.get("riskEnvelope")
                if isinstance(source.get("riskEnvelope"), Mapping)
                else {},
                risk_overlay,
            ),
            "portfolioComponentLineage": {
                **expected,
                "sourceDemoReleaseId": source.get("demoReleaseId"),
                "sourceReleaseMode": source.get("releaseMode"),
            },
            "portfolioRuntimeBinding": {
                "portfolioCandidateId": release.get("portfolioCandidateId"),
                "portfolioReleaseId": release.get("releaseId"),
                "portfolioReleaseHash": release.get("releaseHash"),
                "riskOverlayHash": release.get("riskOverlayHash"),
                "executionIntersectionHash": release.get("executionIntersectionHash"),
                "snapshotBindingMode": release.get("snapshotBindingMode"),
                "maximumInstrumentCount": MAXIMUM_INSTRUMENT_COUNT,
                "universePolicy": {
                    "policyId": release.get("dynamicUniversePolicyId"),
                    "policyHash": release.get("dynamicUniversePolicyHash"),
                    "mode": "daily_frozen_top200",
                    "maximumInstrumentCount": MAXIMUM_INSTRUMENT_COUNT,
                },
            },
        }
    )
    derived["contractHash"] = _contract_hash(derived)
    return derived


def build_approved_top200_demo_runtime(
    *,
    release: Mapping[str, Any],
    approval: Mapping[str, Any] | None,
    arm_audit: Mapping[str, Any] | None,
    source_contracts: Iterable[Mapping[str, Any]],
    risk_overlay: Mapping[str, Any],
    kill_switch_active: bool,
) -> dict[str, Any]:
    """Build a fail-closed runtime projection without mutating frozen artifacts."""

    if risk_overlay.get("riskOverlayHash") != release.get("riskOverlayHash"):
        raise PermissionError("approved risk overlay identity mismatch")
    if str(release.get("snapshotBindingMode") or "") != "policy_bound_daily_snapshot":
        raise PermissionError("approved TOP200 snapshot binding is invalid")
    identities = _component_identities(release)
    expected_ids = [str(value) for value in release.get("componentIds") or []]
    identity_ids = [str(row.get("candidateId") or "") for row in identities]
    if identity_ids != expected_ids:
        raise PermissionError("approved component order or identity is invalid")

    sources_by_hash = {
        str(contract.get("contractHash") or ""): contract
        for contract in source_contracts
        if str(contract.get("contractHash") or "")
    }
    components: list[dict[str, Any]] = []
    for identity in identities:
        source_hash = str(identity.get("sourceContractHash") or "")
        source = sources_by_hash.get(source_hash)
        if source is None:
            raise PermissionError(
                f"component identity mismatch: {identity.get('candidateId') or '--'}"
            )
        components.append(
            _derive_component_contract(
                release=release,
                identity=identity,
                source=source,
                risk_overlay=risk_overlay,
            )
        )

    approved = bool(
        approval
        and approval.get("approved") is True
        and _exact_identity_matches(release, approval)
        and approval.get("live") is False
        and approval.get("withdraw") is False
    )
    armed = bool(
        approved
        and arm_audit
        and arm_audit.get("action") == "arm"
        and arm_audit.get("status") == "armed"
        and arm_audit.get("releaseId") == release.get("releaseId")
        and arm_audit.get("releaseHash") == release.get("releaseHash")
    )
    blockers: list[str] = []
    if not approved:
        blockers.append("exact_demo_release_approval_required")
    if approved and not armed:
        blockers.append("exact_demo_arm_required")
    if kill_switch_active:
        blockers.append("demo_kill_switch_active")

    timeframes = sorted(
        {
            str(
                ((contract.get("strategy") or {}).get("marketDefinition") or {}).get(
                    "timeframe"
                )
                or ""
            )
            for contract in components
        }
        - {""}
    )
    schedules = [
        {
            "releaseId": str(release["releaseId"]),
            "strategyId": f"{release.get('portfolioCandidateId')}:{timeframe}",
            "timeframe": timeframe,
        }
        for timeframe in timeframes
    ]
    execution_enabled = approved and armed and not kill_switch_active
    return {
        "releaseId": release.get("releaseId"),
        "releaseHash": release.get("releaseHash"),
        "approved": approved,
        "armed": armed,
        "demoArmEligible": approved and not kill_switch_active,
        "executionEnabled": execution_enabled,
        "notKilled": not kill_switch_active,
        "liveExecutionAllowed": False,
        "withdrawAllowed": False,
        "blockers": blockers,
        "componentContracts": components,
        "schedules": schedules,
    }


def load_approved_top200_demo_runtime() -> dict[str, Any]:
    release = _load_optional(FINAL_RELEASE_PATH)
    risk_overlay = _load_optional(FINAL_RISK_OVERLAY_PATH)
    if release is None or risk_overlay is None:
        return {
            "approved": False,
            "armed": False,
            "executionEnabled": False,
            "componentContracts": [],
            "schedules": [],
            "blockers": ["approved_top200_release_artifacts_missing"],
        }
    approval = _load_optional(APPROVAL_OVERLAY_PATH)
    arm_audit = _load_optional(ARM_AUDIT_PATH)
    contracts, _ = discover_demo_contracts(include_legacy_diagnostic=True)
    source_contracts_by_hash = {
        str(contract.get("contractHash") or ""): contract
        for contract in _load_frozen_source_contracts()
        if str(contract.get("contractHash") or "")
    }
    source_contracts_by_hash.update(
        {
            str(contract.get("contractHash") or ""): contract
            for contract in contracts
            if str(contract.get("contractHash") or "")
        }
    )
    store = DemoExecutionStore(STORE_PATH)
    try:
        kill_switch_active = bool(store.get_runtime_flag("killSwitch", False))
    finally:
        store.close()
    try:
        return build_approved_top200_demo_runtime(
            release=release,
            approval=approval,
            arm_audit=arm_audit,
            source_contracts=source_contracts_by_hash.values(),
            risk_overlay=risk_overlay,
            kill_switch_active=kill_switch_active,
        )
    except (PermissionError, TypeError, ValueError):
        return {
            "releaseId": release.get("releaseId"),
            "releaseHash": release.get("releaseHash"),
            "approved": bool(approval and approval.get("approved") is True),
            "armed": False,
            "executionEnabled": False,
            "notKilled": not kill_switch_active,
            "liveExecutionAllowed": False,
            "withdrawAllowed": False,
            "componentContracts": [],
            "schedules": [],
            "blockers": ["approved_top200_runtime_identity_invalid"],
        }
