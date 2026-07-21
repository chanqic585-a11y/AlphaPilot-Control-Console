"""Immutable V59/V60 experimental Live Canary readiness identities."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping


PROFILE_SCHEMA = "alphapilot_live_experiment_profile_v1"
RELEASE_SCHEMA = "alphapilot_experimental_live_canary_release_v1"
APPROVAL_SCHEMA = "alphapilot_exact_live_canary_approval_request_v1"
REQUIRED_PROFILE_FIELDS = (
    "allocatedCapitalUSDT",
    "maximumAcceptedLossUSDT",
    "riskPerTradePercent",
    "riskPerTradeUSDT",
    "maximumPortfolioOpenRiskPercent",
    "maximumPortfolioOpenRiskUSDT",
    "maximumConcurrentPositions",
    "maximumInstrumentRisk",
    "maximumLeverage",
    "marginMode",
    "dailyLossLimit",
    "programLossLimit",
    "hardKillLossLimit",
    "scanTopN",
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _stable_hash(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _number(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Live Experiment Profile field is invalid: {field}") from error
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"Live Experiment Profile field must be positive: {field}")
    return result


def _integer(value: Any, field: str) -> int:
    result = _number(value, field)
    if not result.is_integer():
        raise ValueError(f"Live Experiment Profile field must be an integer: {field}")
    return int(result)


def build_live_experiment_profile(
    values: Mapping[str, Any],
    *,
    version: int,
) -> dict[str, Any]:
    """Validate a UI-supplied profile and bind every effective value to a hash."""

    missing = [field for field in REQUIRED_PROFILE_FIELDS if values.get(field) in (None, "")]
    if missing:
        raise ValueError("Live Experiment Profile fields are required: " + ",".join(missing))
    if int(version) <= 0:
        raise ValueError("Live Experiment Profile version must be positive")

    profile = {
        "schemaVersion": PROFILE_SCHEMA,
        "version": int(version),
        "allocatedCapitalUSDT": _number(values["allocatedCapitalUSDT"], "allocatedCapitalUSDT"),
        "maximumAcceptedLossUSDT": _number(
            values["maximumAcceptedLossUSDT"], "maximumAcceptedLossUSDT"
        ),
        "riskPerTradePercent": _number(values["riskPerTradePercent"], "riskPerTradePercent"),
        "riskPerTradeUSDT": _number(values["riskPerTradeUSDT"], "riskPerTradeUSDT"),
        "maximumPortfolioOpenRiskPercent": _number(
            values["maximumPortfolioOpenRiskPercent"], "maximumPortfolioOpenRiskPercent"
        ),
        "maximumPortfolioOpenRiskUSDT": _number(
            values["maximumPortfolioOpenRiskUSDT"], "maximumPortfolioOpenRiskUSDT"
        ),
        "maximumConcurrentPositions": _integer(
            values["maximumConcurrentPositions"], "maximumConcurrentPositions"
        ),
        "maximumInstrumentRisk": _number(values["maximumInstrumentRisk"], "maximumInstrumentRisk"),
        "maximumLeverage": _integer(values["maximumLeverage"], "maximumLeverage"),
        "marginMode": str(values["marginMode"]).strip().lower(),
        "dailyLossLimit": _number(values["dailyLossLimit"], "dailyLossLimit"),
        "programLossLimit": _number(values["programLossLimit"], "programLossLimit"),
        "hardKillLossLimit": _number(values["hardKillLossLimit"], "hardKillLossLimit"),
        "scanTopN": _integer(values["scanTopN"], "scanTopN"),
        "lossLimitUnit": "USDT",
        "maximumSignalAgeSeconds": 20.0,
        "unknownOrderStateFailsClosed": True,
        "withdrawAllowed": False,
        "transferAllowed": False,
    }

    capital = profile["allocatedCapitalUSDT"]
    accepted = profile["maximumAcceptedLossUSDT"]
    daily = profile["dailyLossLimit"]
    program = profile["programLossLimit"]
    hard_kill = profile["hardKillLossLimit"]
    if not (daily <= program <= hard_kill <= accepted <= capital):
        raise ValueError(
            "Live Experiment Profile loss limits must satisfy daily <= program <= hardKill "
            "<= maximumAcceptedLoss <= allocatedCapital"
        )
    if profile["marginMode"] != "isolated":
        raise ValueError("Live Experiment Profile margin mode must be isolated")
    if profile["maximumLeverage"] > 5:
        raise ValueError("Live Experiment Profile leverage exceeds the immutable 5x ceiling")
    if profile["scanTopN"] > 200:
        raise ValueError("Live Experiment Profile scanTopN exceeds 200")
    if profile["maximumInstrumentRisk"] > profile["maximumPortfolioOpenRiskPercent"]:
        raise ValueError("Live Experiment Profile instrument risk exceeds portfolio risk")
    if profile["riskPerTradePercent"] > profile["maximumPortfolioOpenRiskPercent"]:
        raise ValueError("Live Experiment Profile per-trade percent exceeds portfolio risk")
    if profile["riskPerTradeUSDT"] > profile["maximumPortfolioOpenRiskUSDT"]:
        raise ValueError("Live Experiment Profile per-trade USDT risk exceeds portfolio risk")
    if profile["maximumPortfolioOpenRiskUSDT"] > capital:
        raise ValueError("Live Experiment Profile open risk exceeds allocated capital")

    profile["profileHash"] = _stable_hash(
        "live_experiment_profile_",
        profile,
    )
    profile["profileId"] = "live_experiment_profile_v" + str(profile["version"])
    return profile


def _source_identity(source: Mapping[str, Any]) -> dict[str, Any]:
    release_id = str(source.get("releaseId") or source.get("demoReleaseId") or "").strip()
    release_hash = str(source.get("releaseHash") or source.get("demoReleaseHash") or "").strip()
    risk_hash = str(source.get("riskOverlayHash") or "").strip()
    if not release_id or not release_hash or not risk_hash:
        raise ValueError("Source Demo Release identity is incomplete")
    return {
        "releaseId": release_id,
        "releaseHash": release_hash,
        "riskOverlayHash": risk_hash,
        "observerSidecarHash": str(source.get("observerSidecarHash") or "not_bound"),
        "componentIds": list(source.get("componentIds") or source.get("componentCandidateIds") or []),
        "componentDefinitionHashes": list(source.get("componentDefinitionHashes") or []),
    }


def _validate_smoke_result(smoke: Mapping[str, Any]) -> dict[str, Any]:
    final_open_positions = smoke.get("finalOpenPositionCount")
    final_open_orders = smoke.get("finalOpenOrderCount")
    checks = {
        "status": smoke.get("status") == "completed_canceled_and_reconciled",
        "singleOrderAttempt": int(smoke.get("orderAttemptCount") or 0) == 1,
        "cancelConfirmed": smoke.get("cancelConfirmed") is True,
        "zeroOpenPositions": int(final_open_positions if final_open_positions is not None else -1) == 0,
        "zeroOpenOrders": int(final_open_orders if final_open_orders is not None else -1) == 0,
        "reconciliationMatched": smoke.get("finalReconciliationMatched") is True,
        "noCredentialPersistence": smoke.get("rawCredentialsPersisted") is False,
        "noPrivateValuePersistence": smoke.get("privateAccountValuesPersisted") is False,
        "withdrawDisabled": smoke.get("withdrawAllowed") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("V58 Live engineering smoke evidence is incomplete: " + ",".join(failed))
    return {
        "contractHash": str(smoke.get("contractHash") or ""),
        "status": str(smoke.get("status")),
        "checks": checks,
    }


def _validate_adaptive_binding(
    observer_binding: Mapping[str, Any],
    readiness: Mapping[str, Any],
    source: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    sidecar_hash = str(observer_binding.get("sidecarBindingHash") or "").strip()
    model_hash = str(observer_binding.get("modelHash") or "").strip()
    model_policy_hash = str(observer_binding.get("modelPolicyHash") or "").strip()
    if not sidecar_hash or not model_hash or not model_policy_hash:
        raise ValueError("Adaptive observer binding identity is incomplete")
    if str(observer_binding.get("releaseHash") or "") != str(source["releaseHash"]):
        raise ValueError("Adaptive observer binding does not match the source Demo Release")
    if str(observer_binding.get("releaseId") or "") != str(source["releaseId"]):
        raise ValueError("Adaptive observer binding Release ID does not match")
    adaptive_core = {
        "schemaVersion": str(readiness.get("schemaVersion") or "adaptive_learning_live_readiness_v1"),
        "passed": readiness.get("passed") is True,
        "status": str(readiness.get("status") or "unknown"),
        "modelMode": str(readiness.get("modelMode") or ""),
        "blockers": sorted(str(value) for value in readiness.get("blockers") or []),
    }
    return (
        {
            "sidecarBindingHash": sidecar_hash,
            "modelHash": model_hash,
            "modelPolicyHash": model_policy_hash,
        },
        {
            **adaptive_core,
            "readinessHash": _stable_hash("adaptive_live_readiness_", adaptive_core),
        },
    )


def build_experimental_live_canary_bundle(
    *,
    profile_input: Mapping[str, Any],
    source_demo_release: Mapping[str, Any],
    smoke_result: Mapping[str, Any],
    observer_binding: Mapping[str, Any],
    adaptive_learning_readiness: Mapping[str, Any],
    generated_at: str,
    profile_version: int = 1,
) -> dict[str, Any]:
    profile = build_live_experiment_profile(profile_input, version=profile_version)
    source = _source_identity(source_demo_release)
    smoke = _validate_smoke_result(smoke_result)
    observer, adaptive = _validate_adaptive_binding(
        observer_binding,
        adaptive_learning_readiness,
        source,
    )
    source["observerSidecarHash"] = observer["sidecarBindingHash"]

    environment_core = {
        "schemaVersion": "alphapilot_experimental_live_environment_v1",
        "environment": "okx_live",
        "site": "global",
        "credentialMode": "process_only",
        "simulationHeaderAllowed": False,
        "withdrawAllowed": False,
        "transferAllowed": False,
    }
    environment = {
        **environment_core,
        "environmentHash": _stable_hash("live_environment_", environment_core),
    }
    universe_core = {
        "schemaVersion": "alphapilot_live_dynamic_universe_policy_v1",
        "market": "OKX_USDT_SWAP",
        "scanTopN": profile["scanTopN"],
        "selection": "dynamic_public_market_liquidity_rank",
        "requiresIndependentRuntimeSnapshot": True,
        "snapshotStatus": "not_run",
        "liquidityGateRequired": True,
        "depthGateRequired": True,
    }
    universe = {
        **universe_core,
        "universePolicyHash": _stable_hash("live_universe_policy_", universe_core),
    }
    risk_core = {
        "schemaVersion": "alphapilot_experimental_live_risk_overlay_v1",
        "profileId": profile["profileId"],
        "profileHash": profile["profileHash"],
        "profile": profile,
        "lossControlNotice": (
            "Loss controls are targets and cannot guarantee final realized loss in fast markets."
        ),
        "riskIncreaseRequiresNewHashAndExactApproval": True,
    }
    risk_overlay = {
        **risk_core,
        "riskOverlayHash": _stable_hash("live_risk_overlay_", risk_core),
    }
    release_core = {
        "schemaVersion": RELEASE_SCHEMA,
        "releasePurpose": "operator_approved_live_canary",
        "formalPass": False,
        "productionQualified": False,
        "automaticPromotion": False,
        "sourceDemoRelease": source,
        "riskOverlayHash": risk_overlay["riskOverlayHash"],
        "environmentHash": environment["environmentHash"],
        "universePolicyHash": universe["universePolicyHash"],
        "observerSidecarHash": observer["sidecarBindingHash"],
        "modelHash": observer["modelHash"],
        "modelPolicyHash": observer["modelPolicyHash"],
        "adaptiveLearningReadinessHash": adaptive["readinessHash"],
        "adaptiveLearningReadinessPassed": adaptive["passed"],
        "executionBoundary": {
            "environment": "okx_live_canary_only",
            "mechanicalExecutionAllowedAfterExactApproval": True,
            "manualOrderApprovalRequiredAfterArm": False,
            "withdrawAllowed": False,
            "transferAllowed": False,
            "exactReleaseAndRiskApprovalRequired": True,
        },
        "requiredEvidence": {
            "demoExecutionIntegrity": "passed",
            "livePrivateRead": "passed_via_v58_private_preflight",
            "liveEngineeringSmoke": smoke["status"],
            "liveRiskProfile": "complete",
            "adaptiveLearningLiveReadiness": adaptive["status"],
        },
    }
    release_hash = _stable_hash("experimental_live_release_", release_core)
    live_release = {
        **release_core,
        "releaseId": "experimental_live_canary_" + release_hash[-24:],
        "releaseHash": release_hash,
        "generatedAt": str(generated_at),
        "status": "blocked_waiting_exact_live_release_approval",
    }
    required_confirmation = (
        "APPROVE_EXPERIMENTAL_LIVE_CANARY "
        f"{release_hash} {risk_overlay['riskOverlayHash']} "
        f"MAX_LOSS_USDT {profile['maximumAcceptedLossUSDT']:g}"
    )
    approval_core = {
        "schemaVersion": APPROVAL_SCHEMA,
        "environment": "LIVE",
        "releaseId": live_release["releaseId"],
        "releaseHash": release_hash,
        "riskOverlayHash": risk_overlay["riskOverlayHash"],
        "maximumAcceptedLossUSDT": profile["maximumAcceptedLossUSDT"],
        "allocatedCapitalUSDT": profile["allocatedCapitalUSDT"],
        "riskPerTradePercent": profile["riskPerTradePercent"],
        "riskPerTradeUSDT": profile["riskPerTradeUSDT"],
        "maximumPortfolioOpenRiskPercent": profile["maximumPortfolioOpenRiskPercent"],
        "maximumPortfolioOpenRiskUSDT": profile["maximumPortfolioOpenRiskUSDT"],
        "maximumConcurrentPositions": profile["maximumConcurrentPositions"],
        "maximumLeverage": profile["maximumLeverage"],
        "withdrawAllowed": False,
        "requiredConfirmation": required_confirmation,
        "status": "blocked_waiting_exact_live_release_approval",
    }
    approval_request = {
        **approval_core,
        "approvalRequestHash": _stable_hash("live_approval_request_", approval_core),
        "generatedAt": str(generated_at),
    }
    not_run = {"schemaVersion": "alphapilot_live_execution_ledger_v1", "status": "not_run", "records": []}
    return {
        "schemaVersion": "alphapilot_v59_v60_live_canary_readiness_bundle_v1",
        "generatedAt": str(generated_at),
        "status": "blocked_waiting_exact_live_release_approval",
        "profile": profile,
        "riskOverlay": risk_overlay,
        "environment": environment,
        "universePolicy": universe,
        "liveRelease": live_release,
        "approvalRequest": approval_request,
        "privateReadEvidence": {
            "schemaVersion": "alphapilot_v58_private_preflight_derivation_v1",
            "status": "passed_via_v58_private_preflight",
            "smokeContractHash": smoke["contractHash"],
            "basis": "V58 smoke could not submit until account, balance, positions, orders, and leverage reads passed.",
            "privateAccountValuesPersisted": False,
        },
        "smokeEvidence": smoke,
        "observerBinding": observer,
        "adaptiveLearningReadiness": adaptive,
        "executionState": {
            "approvalStatus": "not_run",
            "armStatus": "not_run",
            "strategyOrderStatus": "not_run",
            "liveEnabled": False,
            "withdrawAllowed": False,
        },
        "orderLedger": dict(not_run),
        "fillLedger": dict(not_run),
        "positionLedger": dict(not_run),
    }


def validate_exact_live_canary_approval(
    bundle: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> dict[str, Any]:
    release = dict(bundle.get("liveRelease") or {})
    risk = dict(bundle.get("riskOverlay") or {})
    request = dict(bundle.get("approvalRequest") or {})
    profile = dict(bundle.get("profile") or {})
    checks = (
        str(approval.get("actor") or "") == "user_manual",
        str(approval.get("confirmation") or "") == str(request.get("requiredConfirmation") or ""),
        str(approval.get("releaseHash") or "") == str(release.get("releaseHash") or ""),
        str(approval.get("riskOverlayHash") or "") == str(risk.get("riskOverlayHash") or ""),
        float(approval.get("maximumAcceptedLossUSDT") or -1)
        == float(profile.get("maximumAcceptedLossUSDT") or -2),
    )
    if not all(checks):
        raise PermissionError("Exact Live Release, Risk Overlay, and maximum accepted loss approval is required")
    core = {
        "schemaVersion": "alphapilot_exact_live_canary_approval_v1",
        "actor": "user_manual",
        "releaseHash": release["releaseHash"],
        "riskOverlayHash": risk["riskOverlayHash"],
        "maximumAcceptedLossUSDT": profile["maximumAcceptedLossUSDT"],
        "approvalRequestHash": request["approvalRequestHash"],
    }
    return {
        **core,
        "approvalHash": _stable_hash("live_exact_approval_", core),
        "status": "approved_exact_live_canary_identity",
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_experimental_live_canary_bundle(
    output_dir: Path | str,
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    output = Path(output_dir)
    artifacts = {
        "live_experiment_profile.json": bundle["profile"],
        "experimental_live_risk_overlay.json": bundle["riskOverlay"],
        "experimental_live_environment.json": bundle["environment"],
        "experimental_live_universe_policy.json": bundle["universePolicy"],
        "experimental_live_release.json": bundle["liveRelease"],
        "exact_live_approval_request.json": bundle["approvalRequest"],
        "live_private_read_evidence.json": bundle["privateReadEvidence"],
        "live_engineering_smoke_binding.json": bundle["smokeEvidence"],
        "observer_sidecar_binding.json": bundle["observerBinding"],
        "adaptive_learning_live_readiness.json": bundle["adaptiveLearningReadiness"],
        "live_execution_state.json": bundle["executionState"],
        "live_order_ledger.json": bundle["orderLedger"],
        "live_fill_ledger.json": bundle["fillLedger"],
        "live_position_ledger.json": bundle["positionLedger"],
    }
    rows: list[dict[str, Any]] = []
    for name, payload in artifacts.items():
        path = output / name
        _write_json(path, payload)
        rows.append(
            {
                "path": name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "sizeBytes": path.stat().st_size,
            }
        )
    manifest = {
        "schemaVersion": "alphapilot_v59_v60_live_canary_artifact_manifest_v1",
        "status": str(bundle.get("status") or "unknown"),
        "artifactCount": len(rows),
        "artifacts": rows,
        "rawCredentialsPersisted": False,
        "privateAccountValuesPersisted": False,
        "withdrawAllowed": False,
    }
    _write_json(output / "artifact_manifest.json", manifest)
    return manifest
