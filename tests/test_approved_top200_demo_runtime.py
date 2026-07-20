from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

import pytest

from alphapilot_control_console import approved_top200_demo_runtime as runtime_module
from alphapilot_control_console.approved_top200_demo_runtime import (
    build_approved_top200_demo_runtime,
    load_approved_top200_demo_runtime,
)
from alphapilot_control_console.evolution_demo_service import _contract_hash


RELEASE_ID = "provisional_research_demo_top200_policy_bound_test"
RELEASE_HASH = "provisional_demo_release_test"
RISK_OVERLAY_HASH = "risk_overlay_test"
POLICY_ID = "okx_demo_top200_liquid_usdt_swap_forward_v1"
POLICY_HASH = "top200_universe_policy_test"


def _source_contract(candidate_id: str, timeframe: str) -> dict:
    contract = {
        "schemaVersion": "alphapilot_control_console_demo_v1",
        "status": "demo_eligible",
        "releaseMode": "experimental_override",
        "livePromotionAllowed": False,
        "demoReleaseId": f"legacy_{candidate_id}",
        "releaseContentHash": f"legacy_release_hash_{candidate_id}",
        "strategyCandidateId": candidate_id,
        "executionBoundary": {
            "environment": "okx_demo_only",
            "automaticDemoExecutionAllowed": True,
            "liveExecutionAllowed": False,
            "withdrawAllowed": False,
            "rawCredentialFieldsAllowed": False,
        },
        "riskEnvelope": {
            "initialEquityUsdt": 1000.0,
            "capitalLimitUsdt": 1000.0,
            "riskPerTradePercent": 0.25,
            "maxOpenRiskPercent": 1.0,
            "maxOrderNotionalUsdt": 250.0,
            "maxConcurrentPositions": 3,
            "defaultMaxLeverage": 2,
            "maxLeverage": 2,
            "rewardRiskRatio": 2.0,
            "riskProfileId": "source-risk-profile",
            "riskProfileHash": "source-risk-profile-hash",
        },
        "strategy": {
            "familyKey": "test_family",
            "strategyContentHash": f"strategy_hash_{candidate_id}",
            "marketDefinition": {
                "exchange": "okx",
                "instrumentType": "SWAP",
                "settleCurrency": "USDT",
                "timeframe": timeframe,
                "universePolicy": {
                    "mode": "okx_usdt_linear_perpetual_full_market",
                    "screeningLimit": 100,
                },
            },
            "forwardSignalPolicy": {
                "policyType": "strategy_family_params_v1",
                "family": "test_family",
                "direction": "long",
                "parameters": {"targetRewardRiskRatio": 2.0},
            },
        },
    }
    contract["contractHash"] = _contract_hash(contract)
    return contract


def _release(contracts: list[dict]) -> dict:
    identities = [
        {
            "candidateId": contract["strategyCandidateId"],
            "sourceContractHash": contract["contractHash"],
            "sourceReleaseHash": contract["releaseContentHash"],
            "strategyDefinitionHash": contract["strategy"]["strategyContentHash"],
        }
        for contract in contracts
    ]
    return {
        "schemaVersion": "provisional_demo_release_top200_v1",
        "releaseId": RELEASE_ID,
        "releaseHash": RELEASE_HASH,
        "riskOverlayHash": RISK_OVERLAY_HASH,
        "executionIntersectionHash": "intersection_hash",
        "dynamicUniversePolicyId": POLICY_ID,
        "dynamicUniversePolicyHash": POLICY_HASH,
        "snapshotBindingMode": "policy_bound_daily_snapshot",
        "portfolioCandidateId": "three_component_portfolio",
        "componentIds": [row["candidateId"] for row in identities],
        "executionIdentity": {"componentIdentities": identities},
    }


def _approval() -> dict:
    return {
        "approved": True,
        "demoArm": False,
        "live": False,
        "withdraw": False,
        "status": "approved_not_armed",
        "releaseId": RELEASE_ID,
        "releaseHash": RELEASE_HASH,
        "riskOverlayHash": RISK_OVERLAY_HASH,
        "executionIntersectionHash": "intersection_hash",
    }


def _risk_overlay() -> dict:
    return {
        "riskOverlayHash": RISK_OVERLAY_HASH,
        "environment": "okx_demo_only",
        "riskPerTradePercent": 0.1,
        "maximumPortfolioOpenRiskPercent": 0.3,
        "maximumConcurrentPositions": 3,
        "maxLeverage": 2,
        "marginMode": "isolated",
        "feeRate": 0.0005,
        "slippageRate": 0.0002,
    }


def test_approved_portfolio_derives_exact_components_without_arming() -> None:
    source_contracts = [
        _source_contract("component-1h", "1h"),
        _source_contract("component-1d-a", "1d"),
        _source_contract("component-1d-b", "1d"),
    ]

    runtime = build_approved_top200_demo_runtime(
        release=_release(source_contracts),
        approval=_approval(),
        arm_audit=None,
        source_contracts=source_contracts,
        risk_overlay=_risk_overlay(),
        kill_switch_active=False,
    )

    assert runtime["approved"] is True
    assert runtime["armed"] is False
    assert runtime["executionEnabled"] is False
    assert runtime["blockers"] == ["exact_demo_arm_required"]
    assert {row["timeframe"] for row in runtime["schedules"]} == {"1h", "1d"}
    assert len(runtime["componentContracts"]) == 3
    for contract in runtime["componentContracts"]:
        assert contract["demoReleaseId"] == RELEASE_ID
        assert contract["releaseContentHash"] == RELEASE_HASH
        assert contract["releaseMode"] == "provisional_research_demo_portfolio_component"
        assert contract["releaseMode"] != "experimental_override"
        assert contract["portfolioRuntimeBinding"]["maximumInstrumentCount"] == 200
        assert contract["riskEnvelope"]["riskPerTradePercent"] == 0.1
        assert contract["riskEnvelope"]["maxOpenRiskPercent"] == 0.3
        assert contract["contractHash"] == _contract_hash(contract)


def test_armed_portfolio_becomes_executable_but_live_and_withdraw_stay_locked() -> None:
    source_contracts = [
        _source_contract("component-1h", "1h"),
        _source_contract("component-1d-a", "1d"),
        _source_contract("component-1d-b", "1d"),
    ]
    arm_audit = {
        "action": "arm",
        "status": "armed",
        "releaseId": RELEASE_ID,
        "releaseHash": RELEASE_HASH,
    }

    runtime = build_approved_top200_demo_runtime(
        release=_release(source_contracts),
        approval=_approval(),
        arm_audit=arm_audit,
        source_contracts=source_contracts,
        risk_overlay=_risk_overlay(),
        kill_switch_active=False,
    )

    assert runtime["armed"] is True
    assert runtime["executionEnabled"] is True
    assert runtime["blockers"] == []
    assert runtime["liveExecutionAllowed"] is False
    assert runtime["withdrawAllowed"] is False


def test_component_identity_mismatch_fails_closed() -> None:
    source_contracts = [
        _source_contract("component-1h", "1h"),
        _source_contract("component-1d-a", "1d"),
        _source_contract("component-1d-b", "1d"),
    ]
    tampered = deepcopy(source_contracts)
    tampered[0]["strategy"]["strategyContentHash"] = "tampered"

    with pytest.raises(PermissionError, match="component identity mismatch"):
        build_approved_top200_demo_runtime(
            release=_release(source_contracts),
            approval=_approval(),
            arm_audit=None,
            source_contracts=tampered,
            risk_overlay=_risk_overlay(),
            kill_switch_active=False,
        )


def test_unapproved_or_killed_portfolio_cannot_execute() -> None:
    source_contracts = [
        _source_contract("component-1h", "1h"),
        _source_contract("component-1d-a", "1d"),
        _source_contract("component-1d-b", "1d"),
    ]
    release = _release(source_contracts)
    approval = _approval()
    approval["approved"] = False

    unapproved = build_approved_top200_demo_runtime(
        release=release,
        approval=approval,
        arm_audit=None,
        source_contracts=source_contracts,
        risk_overlay=_risk_overlay(),
        kill_switch_active=False,
    )
    assert "exact_demo_release_approval_required" in unapproved["blockers"]
    assert unapproved["executionEnabled"] is False

    killed = build_approved_top200_demo_runtime(
        release=release,
        approval=_approval(),
        arm_audit={
            "action": "arm",
            "status": "armed",
            "releaseId": RELEASE_ID,
            "releaseHash": RELEASE_HASH,
        },
        source_contracts=source_contracts,
        risk_overlay=_risk_overlay(),
        kill_switch_active=True,
    )
    assert "demo_kill_switch_active" in killed["blockers"]
    assert killed["executionEnabled"] is False


def test_loader_fails_closed_when_frozen_component_source_is_missing() -> None:
    source_contracts = [
        _source_contract("component-1h", "1h"),
        _source_contract("component-1d-a", "1d"),
        _source_contract("component-1d-b", "1d"),
    ]
    release = _release(source_contracts)
    risk_overlay = _risk_overlay()

    def load_optional(path):
        if path == runtime_module.FINAL_RELEASE_PATH:
            return release
        if path == runtime_module.FINAL_RISK_OVERLAY_PATH:
            return risk_overlay
        if path == runtime_module.APPROVAL_OVERLAY_PATH:
            return _approval()
        return None

    with patch.object(runtime_module, "_load_optional", side_effect=load_optional), patch.object(
        runtime_module,
        "discover_demo_contracts",
        return_value=([], []),
    ), patch.object(runtime_module, "DemoExecutionStore") as store_type:
        store_type.return_value.get_runtime_flag.return_value = False
        runtime = load_approved_top200_demo_runtime()

    assert runtime["executionEnabled"] is False
    assert runtime["componentContracts"] == []
    assert runtime["schedules"] == []
    assert runtime["blockers"] == ["approved_top200_runtime_identity_invalid"]


def test_loader_uses_versioned_frozen_component_sources_when_runtime_store_is_empty() -> None:
    source_contracts = [
        _source_contract("component-1h", "1h"),
        _source_contract("component-1d-a", "1d"),
        _source_contract("component-1d-b", "1d"),
    ]
    release = _release(source_contracts)
    risk_overlay = _risk_overlay()

    def load_optional(path):
        if path == runtime_module.FINAL_RELEASE_PATH:
            return release
        if path == runtime_module.FINAL_RISK_OVERLAY_PATH:
            return risk_overlay
        if path == runtime_module.APPROVAL_OVERLAY_PATH:
            return _approval()
        return None

    with patch.object(runtime_module, "_load_optional", side_effect=load_optional), patch.object(
        runtime_module,
        "discover_demo_contracts",
        return_value=([], []),
    ), patch.object(
        runtime_module,
        "_load_frozen_source_contracts",
        return_value=source_contracts,
        create=True,
    ), patch.object(runtime_module, "DemoExecutionStore") as store_type:
        store_type.return_value.get_runtime_flag.return_value = False
        runtime = load_approved_top200_demo_runtime()

    assert runtime["executionEnabled"] is False
    assert runtime["blockers"] == ["exact_demo_arm_required"]
    assert len(runtime["componentContracts"]) == 3
