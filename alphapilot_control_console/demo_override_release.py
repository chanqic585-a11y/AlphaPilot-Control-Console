"""Create audited experimental OKX Demo releases without opening live access."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .evolution_demo_service import (
    LOCAL_CONTRACT_DIR,
    _contract_hash,
    validate_demo_contract,
)
from .portfolio_risk import normalize_risk_profile
from .risk_profile_store import RISK_PROFILE_STORE_PATH, RiskProfileStore
from .state_store import append_audit


DEMO_OVERRIDE_CONFIRMATION = "仅放行到OKX DEMO"
AuditWriter = Callable[[str, dict[str, Any]], dict[str, Any]]


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value: Any, prefix: str) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _active_demo_risk_profile() -> dict[str, Any] | None:
    store = RiskProfileStore(RISK_PROFILE_STORE_PATH)
    try:
        return store.get_active_profile("okx_demo")
    finally:
        store.close()


def _direction(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized.startswith("long"):
        return "long"
    if normalized.startswith("short"):
        return "short"
    return ""


def _hard_gate_blockers(lifecycle_item: dict[str, Any]) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    metrics = _mapping(lifecycle_item.get("metrics"))
    optimization = _mapping(lifecycle_item.get("optimizationContext"))
    definition = _mapping(optimization.get("definition"))
    parameters = _mapping(optimization.get("parameters"))
    target_r = _number(
        definition.get("targetR")
        or parameters.get("targetRewardRiskRatio")
        or parameters.get("targetR")
    )
    blockers: list[str] = []
    if int(_number(metrics.get("tradeCount"))) <= 0:
        blockers.append("formal_backtest_evidence_missing")
    if target_r < 2.0:
        blockers.append("target_r_below_2r")
    if not all(
        (
            str(definition.get("family") or "").strip(),
            _direction(definition.get("direction") or lifecycle_item.get("direction")),
            str(definition.get("timeframe") or lifecycle_item.get("timeframe") or "").strip(),
            parameters,
        )
    ):
        blockers.append("strategy_definition_incomplete")
    return blockers, definition, parameters


def _risk_envelope(record: dict[str, Any]) -> dict[str, Any]:
    profile = _mapping(record.get("profile"))
    normalized = normalize_risk_profile(profile)
    return {
        **profile,
        "riskProfileId": str(record.get("riskProfileId") or ""),
        "riskProfileHash": str(record.get("contentHash") or ""),
        "initialEquityUsdt": normalized["capitalLimitUsdt"],
        "capitalLimitUsdt": normalized["capitalLimitUsdt"],
        "maxConcurrentPositions": normalized["maxConcurrentPositions"],
        "maxPositionsPerStrategy": normalized["maxPositionsPerStrategy"],
        "maxOrderNotionalUsdt": normalized["maxOrderNotionalUsdt"],
        "defaultMaxLeverage": normalized["maxLeverage"],
        "maxLeverage": normalized["maxLeverage"],
        "riskPerTradePercent": normalized["riskPerTradePercent"],
        "maxOpenRiskPercent": normalized["maxOpenRiskPercent"],
        "rewardRiskRatio": normalized["rewardRiskRatio"],
    }


def _build_strategy(
    lifecycle_item: dict[str, Any],
    definition: dict[str, Any],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    family = str(definition.get("family") or parameters.get("family") or "").strip()
    timeframe = str(definition.get("timeframe") or lifecycle_item.get("timeframe") or "").strip()
    direction = _direction(definition.get("direction") or lifecycle_item.get("direction"))
    return {
        "familyKey": family,
        "strategyContentHash": lifecycle_item.get("contentHash"),
        "marketDefinition": {
            "exchange": "okx",
            "instrumentType": "SWAP",
            "settleCurrency": "USDT",
            "timeframe": timeframe,
            "universePolicy": {
                "mode": "okx_usdt_linear_perpetual_full_market",
                "screeningLimit": 20,
                "ranking": "public_quote_volume_proxy_then_spread",
                "policyVersion": "okx_full_market_policy_v1",
            },
        },
        "forwardSignalPolicy": {
            "policyType": "strategy_family_params_v1",
            "family": family,
            "direction": direction,
            "parameters": parameters,
        },
    }


def authorize_demo_override(
    lifecycle_item: dict[str, Any],
    *,
    reason: str,
    confirmation: str,
    actor: str = "user_manual",
    contract_dir: Path = LOCAL_CONTRACT_DIR,
    risk_profile_record: dict[str, Any] | None = None,
    audit_writer: AuditWriter = append_audit,
) -> dict[str, Any]:
    """Bypass only the forward-sample gate and create no exchange order."""

    blockers: list[str] = []
    normalized_reason = str(reason or "").strip()
    if not normalized_reason:
        blockers.append("override_reason_required")
    if confirmation != DEMO_OVERRIDE_CONFIRMATION:
        blockers.append("override_confirmation_mismatch")
    gate_blockers, definition, parameters = _hard_gate_blockers(lifecycle_item)
    blockers.extend(gate_blockers)
    risk_record = risk_profile_record or _active_demo_risk_profile()
    if not risk_record or not risk_record.get("riskProfileId") or not risk_record.get("contentHash"):
        blockers.append("active_demo_risk_profile_missing")
    if blockers:
        return {
            "ok": False,
            "status": "blocked",
            "blockers": list(dict.fromkeys(blockers)),
            "created": False,
            "createsOrder": False,
            "liveExecutionAllowed": False,
        }

    strategy_id = str(lifecycle_item.get("strategyId") or "").strip()
    risk_envelope = _risk_envelope(_mapping(risk_record))
    strategy = _build_strategy(lifecycle_item, definition, parameters)
    release_seed = {
        "schemaVersion": "alphapilot_control_console_demo_v1",
        "strategyCandidateId": strategy_id,
        "strategy": strategy,
        "riskEnvelope": risk_envelope,
        "releaseMode": "experimental_override",
        "bypassedEvidence": ["local_forward_samples"],
        "reason": normalized_reason,
        "executionBoundary": {
            "environment": "okx_demo_only",
            "automaticDemoExecutionAllowed": True,
            "liveExecutionAllowed": False,
            "withdrawAllowed": False,
            "rawCredentialFieldsAllowed": False,
        },
    }
    release_content_hash = _hash(release_seed, "demo_release_content_")
    release_id = "demo_release_override_" + release_content_hash.rsplit("_", 1)[-1][:24]
    target_dir = Path(contract_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"demo_release_contract_{release_id}.json"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        validate_demo_contract(existing)
        return {
            "ok": True,
            "status": "ready",
            "created": False,
            "contract": existing,
            "contractPath": str(target),
            "createsOrder": False,
            "liveExecutionAllowed": False,
        }

    contract = {
        **release_seed,
        "demoReleaseId": release_id,
        "status": "demo_eligible",
        "releaseContentHash": release_content_hash,
        "livePromotionAllowed": False,
        "formalCandidateRegistration": {
            "strategyCandidateId": strategy_id,
            "registeredBy": "controlled_demo_override",
        },
        "overrideAudit": {
            "actor": actor,
            "reason": normalized_reason,
            "confirmationMatched": True,
            "bypassedEvidence": ["local_forward_samples"],
        },
        "createdAt": datetime.now(UTC).isoformat(),
    }
    contract["contractHash"] = _contract_hash(contract)
    validate_demo_contract(contract)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(_canonical(contract) + "\n", encoding="utf-8")
    temporary.replace(target)
    audit_writer(
        "demo_override_release_authorized",
        {
            "strategyId": strategy_id,
            "demoReleaseId": release_id,
            "reason": normalized_reason,
            "actor": actor,
            "bypassedEvidence": ["local_forward_samples"],
            "okxDemoOnly": True,
            "createsOrder": False,
            "liveExecutionAllowed": False,
            "withdrawAllowed": False,
        },
    )
    return {
        "ok": True,
        "status": "ready",
        "created": True,
        "contract": contract,
        "contractPath": str(target),
        "createsOrder": False,
        "liveExecutionAllowed": False,
    }
