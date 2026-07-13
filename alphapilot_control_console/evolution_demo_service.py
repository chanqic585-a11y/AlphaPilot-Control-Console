"""Bridge immutable Quant Engine Demo releases into the local Console runtime."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DATA_DIR, get_quant_engine_path
from .credential_runtime import load_okx_demo_credentials, runtime_credential_status
from .demo_arbitrator import arbitrate_demo_signals
from .demo_market_scan_service import save_demo_release_scan
from .demo_execution_engine import DemoExecutionEngine
from .demo_execution_store import DemoExecutionStore
from .demo_entry_latency_policy import evaluate_demo_entry_latency
from .demo_market_runtime_registry import get_demo_market_runtime
from .demo_release_scanner import scan_immutable_demo_release
from .demo_runtime_guard import evaluate_demo_runtime_guard
from .demo_strategy_runtime_settings import (
    effective_symbol_limit,
    get_demo_strategy_runtime_settings,
)
from .exchange_connectors.okx_demo_client import OkxDemoClient
from .execution_outcome_store import ExecutionOutcomeStore
from .portfolio_risk import normalize_risk_profile
from .risk_profile_store import RISK_PROFILE_STORE_PATH, RiskProfileStore


STORE_PATH = DATA_DIR / "evolution_demo_execution.sqlite"
LOCAL_CONTRACT_DIR = DATA_DIR / "demo_release_contracts"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _close_event_value(close_event: Any, key: str) -> Any:
    if isinstance(close_event, dict):
        return close_event.get(key)
    return getattr(close_event, key, None)


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _contract_hash(contract: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in contract.items() if key != "contractHash"}
    digest = hashlib.sha256(_canonical(unsigned).encode("utf-8")).hexdigest()
    return f"console_contract_{digest}"


def validate_demo_contract(contract: dict[str, Any]) -> None:
    if contract.get("schemaVersion") != "alphapilot_control_console_demo_v1":
        raise ValueError("Unsupported Demo release contract")
    if contract.get("status") not in {"demo_eligible", "demo_active"}:
        raise ValueError("Demo release is not eligible")
    expected = str(contract.get("contractHash") or "")
    if not expected or expected != _contract_hash(contract):
        raise ValueError("Demo release contract checksum mismatch")
    boundary = contract.get("executionBoundary") if isinstance(contract.get("executionBoundary"), dict) else {}
    if boundary.get("environment") != "okx_demo_only":
        raise PermissionError("Demo release environment is invalid")
    if boundary.get("automaticDemoExecutionAllowed") is not True:
        raise PermissionError("Demo release does not allow automatic Demo execution")
    if boundary.get("liveExecutionAllowed") is not False or boundary.get("withdrawAllowed") is not False:
        raise PermissionError("Live or withdraw capability is forbidden")
    if boundary.get("rawCredentialFieldsAllowed") is not False:
        raise PermissionError("Raw credential fields must be forbidden")
    if contract.get("releaseMode") == "experimental_override" and contract.get("livePromotionAllowed") is not False:
        raise PermissionError("Experimental Demo override promotion must remain disabled")
    if not contract.get("demoReleaseId") or not contract.get("strategyCandidateId"):
        raise ValueError("Demo release identity is incomplete")
    if not contract.get("releaseContentHash"):
        raise ValueError("Demo release content hash is missing")
    limits = contract.get("riskEnvelope") if isinstance(contract.get("riskEnvelope"), dict) else {}
    normalized = normalize_risk_profile(limits)
    if float(normalized["rewardRiskRatio"]) < 2.0:
        raise ValueError("Demo RiskProfile reward/risk is below 2R")
    profile_id = str(limits.get("riskProfileId") or "")
    profile_hash = str(limits.get("riskProfileHash") or "")
    if bool(profile_id) != bool(profile_hash):
        raise ValueError("Demo RiskProfile identity is incomplete")
    if not profile_id:
        legacy_required = {
            "initialEquityUsdt": 1000.0,
            "riskPerTradePercent": 0.25,
            "maxOpenRiskPercent": 1.0,
            "maxOrderNotionalUsdt": 250.0,
            "maxConcurrentPositions": 3,
        }
        for key, expected_value in legacy_required.items():
            if float(limits.get(key) or 0) != expected_value:
                raise ValueError(f"Legacy Demo risk envelope mismatch: {key}")


def _portfolio_from_demo_account(
    client: OkxDemoClient,
    store: DemoExecutionStore,
    risk_profile: dict[str, Any],
) -> dict[str, Any]:
    balance = client.get_balance("USDT")
    positions = client.get_positions(instrumentType="SWAP")
    if str(balance.get("code")) != "0" or str(positions.get("code")) != "0":
        raise RuntimeError("OKX Demo private read failed before execution")
    balance_rows = balance.get("data") if isinstance(balance.get("data"), list) else []
    balance_row = balance_rows[0] if balance_rows and isinstance(balance_rows[0], dict) else {}
    details = balance_row.get("details") if isinstance(balance_row.get("details"), list) else []
    usdt = next(
        (item for item in details if isinstance(item, dict) and str(item.get("ccy")) == "USDT"),
        {},
    )
    available = float(usdt.get("availEq") or usdt.get("availBal") or balance_row.get("availEq") or 0)
    position_rows = positions.get("data") if isinstance(positions.get("data"), list) else []
    open_positions = [
        item
        for item in position_rows
        if isinstance(item, dict) and abs(float(item.get("pos") or 0)) > 0
    ]
    limits = normalize_risk_profile(risk_profile)
    attributed_records = store.list_records(
        {"prepared", "submitted", "live", "partially_filled", "filled", "unknown"}
    )
    positions_by_strategy: dict[str, int] = {}
    positions_by_symbol: dict[str, int] = {}
    risk_by_strategy: dict[str, float] = {}
    risk_by_symbol: dict[str, float] = {}
    risk_by_direction: dict[str, float] = {}
    risk_by_correlation: dict[str, float] = {}
    for record in attributed_records:
        signal = record.signal
        strategy = str(signal.get("strategyCandidateId") or signal.get("candidateId") or "unknown")
        symbol = str(signal.get("instId") or "unknown")
        direction = "long" if str(signal.get("side") or "").lower() == "buy" else "short"
        correlation = str(signal.get("correlationGroup") or "")
        risk = float(signal.get("riskPercent") or 0)
        positions_by_strategy[strategy] = positions_by_strategy.get(strategy, 0) + 1
        positions_by_symbol[symbol] = positions_by_symbol.get(symbol, 0) + 1
        risk_by_strategy[strategy] = risk_by_strategy.get(strategy, 0.0) + risk
        risk_by_symbol[symbol] = risk_by_symbol.get(symbol, 0.0) + risk
        risk_by_direction[direction] = risk_by_direction.get(direction, 0.0) + risk
        if correlation:
            risk_by_correlation[correlation] = risk_by_correlation.get(correlation, 0.0) + risk
    risk_per_trade = float(limits["riskPerTradePercent"])
    return {
        "availableEquityUsdt": available,
        "openPositionCount": max(len(open_positions), len(attributed_records)),
        "openRiskPercent": sum(risk_by_strategy.values()) or len(open_positions) * risk_per_trade,
        "activeStrategyIds": sorted(positions_by_strategy),
        "positionsByStrategy": positions_by_strategy,
        "positionsBySymbol": positions_by_symbol,
        "openRiskByStrategy": risk_by_strategy,
        "openRiskBySymbol": risk_by_symbol,
        "openRiskByDirection": risk_by_direction,
        "openRiskByCorrelationGroup": risk_by_correlation,
        "dailyLossPercent": float(store.get_runtime_flag("dailyLossPercent", 0.0) or 0.0),
        "drawdownPercent": float(store.get_runtime_flag("drawdownPercent", 0.0) or 0.0),
        "closedOutcomeCount": int(store.get_runtime_flag("closedOutcomeCount", 0) or 0),
        "rollingProfitFactor": float(store.get_runtime_flag("rollingProfitFactor", 0.0) or 0.0),
        "consecutiveLosses": int(store.get_runtime_flag("consecutiveLosses", 0) or 0),
        "observedSlippageBps": float(store.get_runtime_flag("observedSlippageBps", 0.0) or 0.0),
        "assumedSlippageBps": float(store.get_runtime_flag("assumedSlippageBps", 2.0) or 2.0),
        "reconciliationMatched": True,
        "privateReadOnlyBeforeOrder": True,
    }


def _contract_paths() -> list[Path]:
    quant_reports = get_quant_engine_path() / "reports"
    paths: list[Path] = []
    for directory in (LOCAL_CONTRACT_DIR, quant_reports):
        if directory.exists():
            paths.extend(directory.glob("demo_release_contract_*.json"))
    return sorted(set(path.resolve() for path in paths))


def discover_demo_contracts() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    contracts: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in _contract_paths():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Contract JSON must be an object")
            validate_demo_contract(payload)
            release_id = str(payload["demoReleaseId"])
            if release_id not in seen:
                seen.add(release_id)
                contracts.append(payload)
        except (OSError, json.JSONDecodeError, ValueError, PermissionError) as error:
            rejected.append({"file": str(path), "reason": type(error).__name__})
    return contracts, rejected


def _record_payload(record: Any) -> dict[str, Any]:
    payload = asdict(record)
    payload.pop("exchangeResponse", None)
    return payload


def _outcome_payload(outcome: Any) -> dict[str, Any]:
    payload = asdict(outcome) if is_dataclass(outcome) else dict(vars(outcome))
    payload.pop("exchangeResponse", None)
    return payload


def build_evolution_demo_status() -> dict[str, Any]:
    contracts, rejected = discover_demo_contracts()
    store = DemoExecutionStore(STORE_PATH)
    try:
        records = store.list_records()
        paused = bool(store.get_runtime_flag("paused", False))
        kill_switch = bool(store.get_runtime_flag("killSwitch", False))
    finally:
        store.close()
    outcome_store = ExecutionOutcomeStore()
    try:
        outcomes = [
            outcome
            for outcome in outcome_store.list_outcomes()
            if outcome.environment == "okx_demo"
        ]
    finally:
        outcome_store.close()
    realized_net_pnl = sum(
        float(((outcome.outcome or {}).get("trade") or {}).get("netPnl") or 0.0)
        for outcome in outcomes
    )
    credential_status = runtime_credential_status()
    risk_store = RiskProfileStore(RISK_PROFILE_STORE_PATH)
    try:
        active_risk_profile = risk_store.get_active_profile("okx_demo")
    finally:
        risk_store.close()
    private_enabled = _enabled("ALPHAPILOT_OKX_DEMO_ENABLED")
    order_enabled = _enabled("ALPHAPILOT_OKX_DEMO_ORDER_ENABLED")
    automation_enabled = _enabled("ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED")
    blockers: list[str] = []
    if not contracts:
        blockers.append("no_eligible_demo_release")
    if not private_enabled:
        blockers.append("okx_demo_private_connection_disabled")
    if not order_enabled:
        blockers.append("okx_demo_order_gate_disabled")
    if not automation_enabled:
        blockers.append("okx_demo_automation_gate_disabled")
    if not credential_status["allConfigured"]:
        blockers.append("okx_demo_credentials_missing")
    if paused:
        blockers.append("demo_runtime_paused")
    if kill_switch:
        blockers.append("demo_kill_switch_active")
    contract_profile_hashes = {
        str((contract.get("riskEnvelope") or {}).get("riskProfileHash") or "")
        for contract in contracts
        if isinstance(contract.get("riskEnvelope"), dict)
    }
    if contracts and active_risk_profile and contract_profile_hashes != {""} and (
        active_risk_profile["contentHash"] not in contract_profile_hashes
    ):
        blockers.append("active_demo_risk_profile_release_mismatch")
    active_limits = normalize_risk_profile(
        active_risk_profile["profile"] if active_risk_profile else None
    )
    return {
        "version": "V13.20.0",
        "source": "immutable_release_demo_bridge_v13_20",
        "summary": {
            "eligibleReleaseCount": len(contracts),
            "rejectedContractCount": len(rejected),
            "executionRecordCount": len(records),
            "activeRecordCount": sum(record.status not in {"filled", "canceled", "rejected", "mmp_canceled"} for record in records),
            "closedOutcomeCount": len(outcomes),
            "realizedNetPnl": realized_net_pnl,
            "paused": paused,
            "killSwitch": kill_switch,
            "ready": not blockers,
            "initialEquityUsdt": active_limits["capitalLimitUsdt"],
            "maxOrderNotionalUsdt": active_limits["maxOrderNotionalUsdt"],
        },
        "stages": [
            {"stageId": "research", "label": "Research", "status": "available", "description": "离线因子、OOS 和成本检验"},
            {"stageId": "shadow", "label": "Shadow", "status": "available", "description": "公共实时行情闭合观察"},
            {"stageId": "okx_demo", "label": "OKX Demo", "status": "ready" if not blockers else "blocked", "description": "不可变 release 自动机械执行"},
            {"stageId": "live", "label": "Live Locked", "status": "locked", "description": "必须另行人工批准 release"},
        ],
        "contracts": [
            {
                "demoReleaseId": contract.get("demoReleaseId"),
                "strategyCandidateId": contract.get("strategyCandidateId"),
                "status": contract.get("status"),
                "contractHash": contract.get("contractHash"),
                "releaseMode": contract.get("releaseMode") or "formal_evidence",
                "livePromotionAllowed": bool(contract.get("livePromotionAllowed", False)),
                "marketDefinition": (
                    (contract.get("strategy") or {}).get("marketDefinition")
                    if isinstance(contract.get("strategy"), dict)
                    else {}
                ),
            }
            for contract in contracts
        ],
        "activeRiskProfile": active_risk_profile,
        "recentRecords": [_record_payload(record) for record in records[-10:]],
        "recentOutcomes": [_outcome_payload(outcome) for outcome in outcomes[-50:]],
        "rejectedContracts": rejected,
        "credentialStatus": credential_status,
        "runtimeGates": {
            "privateEnabled": private_enabled,
            "orderEnabled": order_enabled,
            "automationEnabled": automation_enabled,
            "rawCredentialsStored": False,
        },
        "blockers": blockers,
        "safetyBoundary": {
            "okxDemoOnly": True,
            "automaticDemoExecutionAllowed": True,
            "liveExecutionAllowed": False,
            "withdrawAllowed": False,
            "rawCredentialStorageAllowed": False,
        },
    }


def _increment_demo_portfolio(portfolio: dict[str, Any], signal: dict[str, Any]) -> None:
    strategy_id = str(signal.get("strategyCandidateId") or signal.get("candidateId") or "unknown")
    symbol = str(signal.get("instId") or "unknown")
    direction = "long" if str(signal.get("side") or "").lower() == "buy" else "short"
    correlation = str(signal.get("correlationGroup") or "")
    risk = float(signal.get("riskPercent") or 0.0)
    portfolio["openPositionCount"] = int(portfolio.get("openPositionCount") or 0) + 1
    portfolio["openRiskPercent"] = float(portfolio.get("openRiskPercent") or 0.0) + risk
    active = set(str(value) for value in (portfolio.get("activeStrategyIds") or []))
    active.add(strategy_id)
    portfolio["activeStrategyIds"] = sorted(active)
    for key, identity in (
        ("positionsByStrategy", strategy_id),
        ("positionsBySymbol", symbol),
    ):
        values = dict(portfolio.get(key) or {})
        values[identity] = int(values.get(identity, 0)) + 1
        portfolio[key] = values
    for key, identity in (
        ("openRiskByStrategy", strategy_id),
        ("openRiskBySymbol", symbol),
        ("openRiskByDirection", direction),
    ):
        values = dict(portfolio.get(key) or {})
        values[identity] = float(values.get(identity, 0.0)) + risk
        portfolio[key] = values
    if correlation:
        values = dict(portfolio.get("openRiskByCorrelationGroup") or {})
        values[correlation] = float(values.get(correlation, 0.0)) + risk
        portfolio["openRiskByCorrelationGroup"] = values


def run_evolution_demo_batch_cycle(
    release_ids: list[str],
    *,
    close_event: Any | None = None,
) -> dict[str, Any]:
    status = build_evolution_demo_status()
    if status["blockers"]:
        return {"ok": False, "blockers": status["blockers"], "status": status}
    contracts, _ = discover_demo_contracts()
    requested = [str(value) for value in release_ids if str(value)]
    selected_contracts = [
        contract
        for release_id in requested
        for contract in contracts
        if str(contract.get("demoReleaseId") or "") == release_id
    ]
    found_ids = {str(contract.get("demoReleaseId") or "") for contract in selected_contracts}
    missing = [release_id for release_id in requested if release_id not in found_ids]
    if not selected_contracts or missing:
        return {
            "ok": False,
            "blockers": ["demo_release_not_found"],
            "missingReleaseIds": missing or requested,
            "status": status,
        }

    close_received_at = _close_event_value(close_event, "receivedAt")
    close_sequence_id = str(_close_event_value(close_event, "sequenceId") or "")
    close_timeframe = str(_close_event_value(close_event, "timeframe") or "")
    if not close_received_at or not close_sequence_id or not close_timeframe:
        return {
            "ok": False,
            "blockers": ["confirmed_close_event_required"],
            "status": status,
        }
    selected_timeframes = {
        str(((contract.get("strategy") or {}).get("marketDefinition") or {}).get("timeframe") or "")
        for contract in selected_contracts
    }
    if selected_timeframes != {close_timeframe}:
        return {
            "ok": False,
            "blockers": ["confirmed_close_timeframe_mismatch"],
            "status": status,
        }
    market_runtime = get_demo_market_runtime()
    market_runtime_status = market_runtime.status()
    if not market_runtime_status.get("warm"):
        return {
            "ok": False,
            "blockers": ["demo_market_runtime_not_warm"],
            "marketRuntimeStatus": market_runtime_status,
            "status": status,
        }
    try:
        frozen_market = market_runtime.freeze_for_timeframe(
            close_timeframe,
            received_at=_utc_now(),
        )
    except RuntimeError:
        return {
            "ok": False,
            "blockers": ["demo_market_runtime_not_warm"],
            "marketRuntimeStatus": market_runtime.status(),
            "status": status,
        }

    scans: dict[str, dict[str, Any]] = {}
    all_signals: list[dict[str, Any]] = []
    scan_rejections: list[dict[str, Any]] = []
    for contract in selected_contracts:
        release_id = str(contract.get("demoReleaseId") or "")
        scan = scan_immutable_demo_release(
            contract,
            snapshot_loader=frozen_market.load_snapshot,
            metadata_loader=frozen_market.load_metadata,
            universe_loader=frozen_market.load_universe,
        )
        scans[release_id] = scan
        if scan.get("blockers"):
            return {
                "ok": False,
                "blockers": [
                    f"{release_id}:{reason}"
                    for reason in scan.get("blockers", [])
                ],
                "scans": scans,
                "status": status,
            }
        strategy_id = str(contract.get("strategyCandidateId") or "")
        if strategy_id:
            try:
                save_demo_release_scan(strategy_id, scan)
            except (OSError, ValueError):
                return {
                    "ok": False,
                    "blockers": ["demo_market_scan_persistence_failed"],
                    "scans": scans,
                    "status": build_evolution_demo_status(),
                }
        signals = scan.get("signals") if isinstance(scan.get("signals"), list) else []
        for signal in signals:
            if isinstance(signal, dict):
                all_signals.append({
                    **signal,
                    "demoReleaseId": signal.get("demoReleaseId") or release_id,
                    "strategyCandidateId": signal.get("strategyCandidateId") or strategy_id,
                })
        scan_rejections.extend(
            {**row, "demoReleaseId": release_id}
            for row in scan.get("rejections", [])
            if isinstance(row, dict)
        )

    first_contract = selected_contracts[0]
    store = DemoExecutionStore(STORE_PATH)
    try:
        client = OkxDemoClient(load_okx_demo_credentials())
        engine = DemoExecutionEngine(client=client, store=store)
        recovered = engine.recover_open_records()
        try:
            portfolio = _portfolio_from_demo_account(
                client,
                store,
                first_contract.get("riskEnvelope")
                if isinstance(first_contract.get("riskEnvelope"), dict)
                else {},
            )
        except RuntimeError as error:
            engine.pause("demo_private_read_failed")
            return {
                "ok": False,
                "blockers": [str(error)],
                "scans": scans,
                "status": build_evolution_demo_status(),
            }
        portfolio["dataFresh"] = all(bool(item.get("dataFresh")) for item in all_signals)
        portfolio["liquidityPassed"] = all(bool(item.get("liquidityPassed")) for item in all_signals)
        guard = evaluate_demo_runtime_guard(
            portfolio,
            recovered_statuses=[record.status for record in recovered],
            checksums_match=True,
        )
        if guard.pauseRequired:
            engine.pause(";".join(guard.reasonCodes))
            return {
                "ok": False,
                "blockers": list(guard.reasonCodes),
                "scans": scans,
                "status": build_evolution_demo_status(),
            }
        base_result = {
            "scannedReleaseCount": len(selected_contracts),
            "matchedSignalCount": len(all_signals),
            "scans": scans,
            "recovered": [_record_payload(record) for record in recovered],
            "closeReceivedAt": str(close_received_at),
            "closeSequenceId": close_sequence_id,
            "marketRuntimeStatus": market_runtime_status,
            "latencyMetrics": {"selected": [], "expiredCount": 0},
            "expiredSignals": [],
            "conditionalLateEntries": [],
        }
        if not all_signals:
            return {
                "ok": True,
                **base_result,
                "createdOrderCount": 0,
                "created": [],
                "rejectedSignals": scan_rejections,
                "status": build_evolution_demo_status(),
            }

        envelopes = [
            contract.get("riskEnvelope")
            for contract in selected_contracts
            if isinstance(contract.get("riskEnvelope"), dict)
        ]
        max_positions = min(
            int(envelope.get("maxConcurrentPositions") or 3)
            for envelope in envelopes
        ) if envelopes else 3
        current_positions = int(portfolio.get("openPositionCount") or 0)
        available_slots = max_positions - current_positions
        if available_slots <= 0:
            return {
                "ok": True,
                **base_result,
                "createdOrderCount": 0,
                "created": [],
                "rejectedSignals": [
                    {**item, "reason": "portfolio_position_limit"}
                    for item in all_signals
                    if isinstance(item, dict)
                ],
                "status": status,
            }

        contract_by_release = {
            str(contract.get("demoReleaseId") or ""): contract
            for contract in selected_contracts
        }
        contract_by_strategy = {
            str(contract.get("strategyCandidateId") or ""): contract
            for contract in selected_contracts
        }
        preliminarily_selected: list[dict[str, Any]] = []
        arbitration_rejections: list[dict[str, Any]] = list(scan_rejections)
        symbol_limits: dict[str, dict[str, Any]] = {}
        for contract in selected_contracts:
            strategy_id = str(contract.get("strategyCandidateId") or "")
            strategy_signals = [
                signal
                for signal in all_signals
                if str(signal.get("strategyCandidateId") or "") == strategy_id
            ]
            if not strategy_signals:
                continue
            limits = contract.get("riskEnvelope") if isinstance(contract.get("riskEnvelope"), dict) else {}
            current_strategy_positions = int(
                (portfolio.get("positionsByStrategy") or {}).get(strategy_id, 0)
                if isinstance(portfolio.get("positionsByStrategy"), dict)
                else 0
            )
            max_positions_per_strategy = int(limits.get("maxPositionsPerStrategy") or max_positions)
            settings = get_demo_strategy_runtime_settings(strategy_id)
            requested_slots = max(
                0,
                int(settings.get("maxConcurrentSymbols") or 1) - current_strategy_positions,
            )
            profile_slots = max(0, max_positions_per_strategy - current_strategy_positions)
            risk_per_trade = float(limits.get("riskPerTradePercent") or 0.25)
            remaining_risk = max(
                0.0,
                float(limits.get("maxOpenRiskPercent") or 1.0)
                - float(portfolio.get("openRiskPercent") or 0.0),
            )
            risk_slots = int(remaining_risk // risk_per_trade) if risk_per_trade > 0 else 0
            symbol_limit = effective_symbol_limit(
                requested=requested_slots,
                portfolio_limit=profile_slots,
                remaining_slots=available_slots,
                risk_slots=risk_slots,
                matched_count=len(strategy_signals),
            )
            symbol_limits[strategy_id] = symbol_limit
            if int(symbol_limit["effective"]) <= 0:
                arbitration_rejections.extend(
                    {**signal, "reason": "strategy_symbol_limit_reached"}
                    for signal in strategy_signals
                )
                continue
            per_strategy = arbitrate_demo_signals(
                strategy_signals,
                maxPositions=int(symbol_limit["effective"]),
                allowSameFamilyMultipleSymbols=True,
            )
            preliminarily_selected.extend(per_strategy.selected)
            arbitration_rejections.extend(per_strategy.rejected)

        if len(selected_contracts) == 1:
            globally_selected = tuple(preliminarily_selected)
        elif preliminarily_selected:
            global_arbitration = arbitrate_demo_signals(
                preliminarily_selected,
                maxPositions=available_slots,
                allowSameFamilyMultipleSymbols=True,
            )
            globally_selected = global_arbitration.selected
            arbitration_rejections.extend(global_arbitration.rejected)
        else:
            globally_selected = ()

        created: list[Any] = []
        execution_rejections: list[dict[str, Any]] = []
        selected_latency: list[dict[str, Any]] = []
        expired_signals: list[dict[str, Any]] = []
        conditional_late_entries: list[dict[str, Any]] = []
        rolling_portfolio = dict(portfolio)
        for signal in globally_selected:
            contract = contract_by_release.get(str(signal.get("demoReleaseId") or ""))
            if contract is None:
                contract = contract_by_strategy.get(str(signal.get("strategyCandidateId") or ""))
            if contract is None:
                execution_rejections.append({
                    "candidateId": signal.get("candidateId"),
                    "instId": signal.get("instId"),
                    "reason": "signal_release_binding_missing",
                })
                continue
            ready_at = _utc_now()
            quote = market_runtime.quote(str(signal.get("instId") or ""))
            limits = contract.get("riskEnvelope") if isinstance(contract.get("riskEnvelope"), dict) else {}
            decision = evaluate_demo_entry_latency(
                signal,
                quote,
                close_received_at=close_received_at,
                order_ready_at=ready_at,
                fee_rate=float(limits.get("feeRate") or 0.0005),
                slippage_rate=float(limits.get("slippageRate") or 0.0002),
            )
            decision_payload = asdict(decision)
            timing_payload = {
                "candidateId": signal.get("candidateId"),
                "instId": signal.get("instId"),
                **decision_payload,
                "closeReceivedAt": str(close_received_at),
                "orderReadyAt": ready_at.isoformat(),
            }
            if not decision.passed:
                rejected = {
                    "candidateId": signal.get("candidateId"),
                    "instId": signal.get("instId"),
                    "reason": decision.reasonCode or "entry_latency_gate_failed",
                    "latency": timing_payload,
                }
                execution_rejections.append(rejected)
                if decision.reasonCode == "signal_expired":
                    expired_signals.append(rejected)
                continue
            selected_latency.append(timing_payload)
            if decision.latencyClass == "conditional":
                conditional_late_entries.append(timing_payload)
            executable_signal = {
                **signal,
                "latencyAudit": timing_payload,
            }
            try:
                record = engine.execute(
                    contract=contract,
                    signal=executable_signal,
                    portfolio=rolling_portfolio,
                )
                created.append(record)
                _increment_demo_portfolio(rolling_portfolio, executable_signal)
            except (RuntimeError, ValueError) as error:
                execution_rejections.append({
                    "candidateId": signal.get("candidateId"),
                    "instId": signal.get("instId"),
                    "reason": str(error),
                })
                if store.get_runtime_flag("paused", False):
                    break
        paused = bool(store.get_runtime_flag("paused", False))
        return {
            "ok": not paused,
            **base_result,
            "createdOrderCount": len(created),
            "created": [_record_payload(record) for record in created],
            "rejectedSignals": [*arbitration_rejections, *execution_rejections],
            "symbolLimits": symbol_limits,
            "latencyMetrics": {
                "selected": selected_latency,
                "expiredCount": len(expired_signals),
            },
            "expiredSignals": expired_signals,
            "conditionalLateEntries": conditional_late_entries,
            "marketRuntimeStatus": market_runtime.status(),
            "status": build_evolution_demo_status(),
        }
    finally:
        store.close()


def run_evolution_demo_cycle(payload: dict[str, Any]) -> dict[str, Any]:
    release_id = str(payload.get("demoReleaseId") or "")
    external_count = len(payload.get("signals", [])) if isinstance(payload.get("signals"), list) else 0
    result = run_evolution_demo_batch_cycle(
        [release_id],
        close_event=payload.get("closeEvent"),
    )
    scans = result.get("scans") if isinstance(result.get("scans"), dict) else {}
    symbol_limits = result.get("symbolLimits") if isinstance(result.get("symbolLimits"), dict) else {}
    contracts, _ = discover_demo_contracts()
    contract = next(
        (row for row in contracts if str(row.get("demoReleaseId") or "") == release_id),
        {},
    )
    strategy_id = str(contract.get("strategyCandidateId") or "")
    return {
        **result,
        "externalSignalsIgnored": external_count,
        "scan": scans.get(release_id, {}),
        "symbolLimit": symbol_limits.get(strategy_id),
    }


def reconcile_evolution_demo_runtime() -> dict[str, Any]:
    """Reconcile existing Demo orders and positions without creating entries."""
    status = build_evolution_demo_status()
    if status["blockers"]:
        return {"ok": False, "blockers": status["blockers"], "status": status}
    contracts, _ = discover_demo_contracts()
    if not contracts:
        return {"ok": False, "blockers": ["no_eligible_demo_release"], "status": status}

    store = DemoExecutionStore(STORE_PATH)
    try:
        client = OkxDemoClient(load_okx_demo_credentials())
        engine = DemoExecutionEngine(client=client, store=store)
        recovered = engine.recover_open_records()
        try:
            portfolio = _portfolio_from_demo_account(
                client,
                store,
                contracts[0].get("riskEnvelope")
                if isinstance(contracts[0].get("riskEnvelope"), dict)
                else {},
            )
        except RuntimeError as error:
            engine.pause("demo_private_read_failed")
            return {
                "ok": False,
                "blockers": [str(error)],
                "recoveredCount": len(recovered),
                "status": build_evolution_demo_status(),
            }
        guard = evaluate_demo_runtime_guard(
            portfolio,
            recovered_statuses=[record.status for record in recovered],
            checksums_match=True,
        )
        if guard.pauseRequired:
            engine.pause(";".join(guard.reasonCodes))
            return {
                "ok": False,
                "blockers": list(guard.reasonCodes),
                "recoveredCount": len(recovered),
                "openPositionCount": int(portfolio.get("openPositionCount") or 0),
                "status": build_evolution_demo_status(),
            }
        return {
            "ok": True,
            "blockers": [],
            "recoveredCount": len(recovered),
            "openPositionCount": int(portfolio.get("openPositionCount") or 0),
            "status": build_evolution_demo_status(),
        }
    finally:
        store.close()


def pause_evolution_demo_runtime(reason: str) -> None:
    store = DemoExecutionStore(STORE_PATH)
    try:
        store.set_runtime_flag("paused", True)
        store.set_runtime_flag("pauseReason", reason or "automatic_execution_paused")
        store.append_event(None, "demo_paused", {"reason": reason or "automatic_execution_paused"})
    finally:
        store.close()


def resume_evolution_demo_runtime(store_path: Path | str = STORE_PATH) -> None:
    store = DemoExecutionStore(store_path)
    try:
        if store.get_runtime_flag("killSwitch", False):
            raise RuntimeError(
                "Demo kill switch must be cleared by a separate reviewed operation"
            )
        store.set_runtime_flag("paused", False)
        store.set_runtime_flag("pauseReason", None)
        store.append_event(None, "demo_resumed", {})
    finally:
        store.close()


def activate_evolution_demo_kill_switch(reason: str) -> dict[str, Any]:
    if not _enabled("ALPHAPILOT_OKX_DEMO_ENABLED"):
        return {"ok": False, "blockers": ["okx_demo_private_connection_disabled"]}
    store = DemoExecutionStore(STORE_PATH)
    try:
        engine = DemoExecutionEngine(client=OkxDemoClient(load_okx_demo_credentials()), store=store)
        response = engine.activate_kill_switch(reason or "console_request")
        return {"ok": True, "response": response, "status": build_evolution_demo_status()}
    finally:
        store.close()
