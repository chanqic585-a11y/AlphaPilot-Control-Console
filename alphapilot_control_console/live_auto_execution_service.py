"""Automatic OKX Live Canary scans and protected order batches."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from .account_snapshot_projection import build_sanitized_account_snapshot
from .credential_runtime import live_runtime_credential_status, load_okx_live_credentials
from .demo_arbitrator import arbitrate_demo_signals
from .demo_release_scanner import scan_immutable_demo_release
from .exchange_connectors.okx_live_client import OkxLiveClient
from .execution_runtime_lease import ExecutionRuntimeLeaseStore
from .live_canary_service import (
    build_exact_live_canary_arm_readiness,
    live_runtime_gates,
    run_live_readonly_reconciliation,
)
from .live_execution_engine import LiveExecutionEngine
from .live_execution_store import LIVE_EXECUTION_STORE_PATH, LiveExecutionStore
from .live_release_service import discover_live_releases, validate_live_release_export
from .live_safety_plane import evaluate_experimental_live_floors
from .portfolio_risk import normalize_risk_profile
from .risk_profile_store import RISK_PROFILE_STORE_PATH, RiskProfileStore


def _active_live_profile(path: Path | str = RISK_PROFILE_STORE_PATH) -> dict[str, Any] | None:
    store = RiskProfileStore(path)
    try:
        return store.get_active_profile("live_canary")
    finally:
        store.close()


def build_experimental_live_auto_execution_preflight(
    *,
    bundle: Mapping[str, Any],
    approval: Mapping[str, Any] | None,
    runtime_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate frozen V59/V60 gates without arming or creating an order."""

    readiness = build_exact_live_canary_arm_readiness(
        bundle=bundle,
        approval=approval,
        runtime_state=runtime_state,
    )
    profile = dict(bundle.get("profile") or {})
    floor_blockers = evaluate_experimental_live_floors(profile, dict(runtime_state))
    blockers = [*readiness["blockers"], *floor_blockers]
    return {
        "canProceedToArm": not blockers,
        "blockers": blockers,
        "releaseHash": readiness["releaseHash"],
        "riskOverlayHash": readiness["riskOverlayHash"],
        "armStatus": "not_run",
        "orderStatus": "not_run",
        "withdrawAllowed": False,
    }


def scan_live_release(
    export: dict[str, Any],
    active_profile: dict[str, Any],
    *,
    loaders: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_live_release_export(export)
    release = export.get("release") if isinstance(export.get("release"), dict) else {}
    strategy = release.get("strategy") if isinstance(release.get("strategy"), dict) else {}
    if not strategy:
        return {"signals": [], "rejections": [], "blockers": ["live_release_strategy_definition_missing"]}
    strategy_id = str(release.get("strategyCandidateId") or "")
    if not strategy_id:
        return {"signals": [], "rejections": [], "blockers": ["live_release_strategy_identity_missing"]}
    limits = normalize_risk_profile(
        active_profile.get("profile") if isinstance(active_profile.get("profile"), dict) else {}
    )
    demo_contract = {
        "demoReleaseId": str(export.get("liveReleaseId") or ""),
        "strategyCandidateId": strategy_id,
        "strategy": strategy,
        "riskEnvelope": {
            **limits,
            "initialEquityUsdt": limits["capitalLimitUsdt"],
            "defaultMaxLeverage": limits["maxLeverage"],
        },
    }
    loader_options = dict(loaders or {})
    scan = scan_immutable_demo_release(demo_contract, **loader_options)
    mapped: list[dict[str, Any]] = []
    for raw in scan.get("signals", []) if isinstance(scan.get("signals"), list) else []:
        if not isinstance(raw, dict):
            continue
        signal = dict(raw)
        signal["liveSignalId"] = str(signal.get("candidateId") or "")
        signal["candidateId"] = strategy_id
        signal["strategyId"] = strategy_id
        signal["strategyCandidateId"] = strategy_id
        signal["liveReleaseId"] = str(export.get("liveReleaseId") or "")
        signal["source"] = "immutable_live_release_scanner_v13_27_2"
        signal.pop("demoReleaseId", None)
        mapped.append(signal)
    return {**scan, "signals": mapped}


def _tracked_signal(store: LiveExecutionStore, export: dict[str, Any], signal: dict[str, Any]) -> bool:
    release_id = str(export.get("liveReleaseId") or "")
    return any(
        record.liveReleaseId == release_id
        and record.strategyCandidateId == str(signal.get("candidateId") or "")
        and record.instrumentId == str(signal.get("instId") or "")
        and str(record.signal.get("signalTime") or "") == str(signal.get("signalTime") or "")
        and str(record.signal.get("side") or "") == str(signal.get("side") or "")
        for record in store.list_records()
    )


def _portfolio_snapshot(
    client: Any,
    store: LiveExecutionStore,
    active_profile: dict[str, Any],
    signals: list[dict[str, Any]],
) -> dict[str, Any]:
    balance = client.get_balance("USDT")
    positions = client.get_positions()
    open_orders = client.get_open_orders()
    if any(str(response.get("code") or "") != "0" for response in (balance, positions, open_orders)):
        raise RuntimeError("live_private_state_endpoint_failed")
    active_records = store.list_records({"prepared", "submitted", "live", "partially_filled", "filled", "unknown"})
    strategy_ids_by_instrument: dict[str, list[str]] = {}
    for record in active_records:
        if record.instrumentId and record.strategyCandidateId:
            strategy_ids_by_instrument.setdefault(record.instrumentId, []).append(record.strategyCandidateId)
    for signal in signals:
        instrument_id = str(signal.get("instId") or "")
        strategy_id = str(signal.get("candidateId") or signal.get("strategyCandidateId") or "")
        if instrument_id and strategy_id:
            strategy_ids_by_instrument.setdefault(instrument_id, []).append(strategy_id)
    account_snapshot = build_sanitized_account_snapshot(
        balance_response=balance,
        positions_response=positions,
        strategy_ids_by_instrument=strategy_ids_by_instrument,
    )
    store.set_runtime_flag("lastPortfolioSnapshot", account_snapshot)
    available = float(account_snapshot["availableEquityUsdt"])
    actual_positions = list(account_snapshot["positions"])
    positions_by_strategy: dict[str, int] = {}
    positions_by_symbol: dict[str, int] = {}
    risk_by_strategy: dict[str, float] = {}
    risk_by_symbol: dict[str, float] = {}
    risk_by_direction: dict[str, float] = {}
    risk_by_correlation: dict[str, float] = {}
    for record in active_records:
        strategy_id = record.strategyCandidateId
        symbol = record.instrumentId
        direction = "long" if str(record.signal.get("side") or "").lower() == "buy" else "short"
        correlation = str(record.signal.get("correlationGroup") or "")
        risk = float(record.signal.get("riskPercent") or 0)
        positions_by_strategy[strategy_id] = positions_by_strategy.get(strategy_id, 0) + 1
        positions_by_symbol[symbol] = positions_by_symbol.get(symbol, 0) + 1
        risk_by_strategy[strategy_id] = risk_by_strategy.get(strategy_id, 0.0) + risk
        risk_by_symbol[symbol] = risk_by_symbol.get(symbol, 0.0) + risk
        risk_by_direction[direction] = risk_by_direction.get(direction, 0.0) + risk
        if correlation:
            risk_by_correlation[correlation] = risk_by_correlation.get(correlation, 0.0) + risk
    profile = normalize_risk_profile(active_profile.get("profile") if isinstance(active_profile.get("profile"), dict) else {})
    return {
        "availableEquityUsdt": min(available, float(profile["capitalLimitUsdt"])),
        "openPositionCount": len(actual_positions),
        "openRiskPercent": sum(risk_by_strategy.values()),
        "activeStrategyIds": sorted(positions_by_strategy),
        "positionsByStrategy": positions_by_strategy,
        "positionsBySymbol": positions_by_symbol,
        "openRiskByStrategy": risk_by_strategy,
        "openRiskBySymbol": risk_by_symbol,
        "openRiskByDirection": risk_by_direction,
        "openRiskByCorrelationGroup": risk_by_correlation,
        "dailyLossPercent": float(store.get_runtime_flag("dailyLossPercent", 0.0) or 0.0),
        "drawdownPercent": float(store.get_runtime_flag("drawdownPercent", 0.0) or 0.0),
        "canaryLossUsdt": float(store.get_runtime_flag("canaryLossUsdt", 0.0) or 0.0),
        "cooldownActive": bool(store.get_runtime_flag("cooldownActive", False)),
        "dataFresh": all(bool(signal.get("dataFresh")) for signal in signals),
        "liquidityPassed": all(bool(signal.get("liquidityPassed")) for signal in signals),
        "reconciliationMatched": bool(store.get_runtime_flag("lastReconciliationMatched", False)),
    }


def run_live_auto_execution_batch(
    release_ids: list[str],
    *,
    client: Any | None = None,
    store_path: Path | str = LIVE_EXECUTION_STORE_PATH,
    profile_path: Path | str = RISK_PROFILE_STORE_PATH,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    source = os.environ if environment is None else environment
    gates = live_runtime_gates(source)
    required_gates = ("masterEnabled", "readEnabled", "canaryEnabled", "orderEnabled", "automationEnabled")
    blockers = [f"live_{key}_gate_disabled" for key in required_gates if not gates.get(key)]
    if not live_runtime_credential_status(source)["allConfigured"]:
        blockers.append("live_runtime_credentials_missing")
    if blockers:
        return {"ok": False, "blockers": blockers, "createdOrderCount": 0}

    releases, _ = discover_live_releases()
    requested = [str(value) for value in release_ids if str(value)]
    selected = [row for release_id in requested for row in releases if str(row.get("liveReleaseId") or "") == release_id]
    found = {str(row.get("liveReleaseId") or "") for row in selected}
    missing = [release_id for release_id in requested if release_id not in found]
    if not selected or missing:
        return {"ok": False, "blockers": ["live_release_not_found"], "missingReleaseIds": missing or requested, "createdOrderCount": 0}
    active_profile = _active_live_profile(profile_path)
    if active_profile is None:
        return {"ok": False, "blockers": ["no_active_live_canary_risk_profile"], "createdOrderCount": 0}

    scans: dict[str, dict[str, Any]] = {}
    all_signals: list[dict[str, Any]] = []
    rejection_rows: list[dict[str, Any]] = []
    export_by_release: dict[str, dict[str, Any]] = {}
    export_by_strategy: dict[str, dict[str, Any]] = {}
    for export in selected:
        validate_live_release_export(export)
        release = export.get("release") if isinstance(export.get("release"), dict) else {}
        if (
            release.get("riskProfileId") != active_profile.get("riskProfileId")
            or release.get("riskProfileHash") != active_profile.get("contentHash")
        ):
            return {"ok": False, "blockers": ["live_release_risk_profile_mismatch"], "createdOrderCount": 0}
        release_id = str(export.get("liveReleaseId") or "")
        strategy_id = str(release.get("strategyCandidateId") or "")
        scan = scan_live_release(export, active_profile)
        scans[release_id] = scan
        if scan.get("blockers"):
            return {"ok": False, "blockers": list(scan.get("blockers") or []), "scans": scans, "createdOrderCount": 0}
        export_by_release[release_id] = export
        export_by_strategy[strategy_id] = export
        all_signals.extend(row for row in scan.get("signals", []) if isinstance(row, dict))
        rejection_rows.extend(row for row in scan.get("rejections", []) if isinstance(row, dict))

    store = LiveExecutionStore(store_path)
    try:
        runtime = store.runtime_state()
        if runtime["killSwitchActive"] or runtime["paused"] or not runtime["lastReconciliationMatched"]:
            runtime_blockers = []
            if runtime["killSwitchActive"]:
                runtime_blockers.append("live_kill_switch_active")
            if runtime["paused"]:
                runtime_blockers.append("live_entries_paused")
            if not runtime["lastReconciliationMatched"]:
                runtime_blockers.append("live_reconciliation_not_confirmed")
            return {"ok": False, "blockers": runtime_blockers, "scans": scans, "createdOrderCount": 0}
        fresh_signals: list[dict[str, Any]] = []
        for signal in all_signals:
            export = export_by_release.get(str(signal.get("liveReleaseId") or ""))
            if export is not None and _tracked_signal(store, export, signal):
                rejection_rows.append({**signal, "reason": "idempotent_signal_already_tracked"})
            else:
                fresh_signals.append(signal)
        if not fresh_signals:
            return {
                "ok": True,
                "blockers": [],
                "scannedReleaseCount": len(selected),
                "matchedSignalCount": len(all_signals),
                "createdOrderCount": 0,
                "created": [],
                "rejectedSignals": rejection_rows,
                "scans": scans,
            }
        lease_store = ExecutionRuntimeLeaseStore(store_path)
        try:
            try:
                lease_claim = lease_store.acquire(
                    environment="okx_live",
                    owner_id=f"live-strategy-runtime:{os.getpid()}",
                    ttl_seconds=300,
                )
            except PermissionError:
                return {
                    "ok": False,
                    "blockers": ["execution_runtime_lease_unavailable"],
                    "createdOrderCount": 0,
                    "scans": scans,
                }
            try:
                live_client = client or OkxLiveClient(
                    load_okx_live_credentials(source),
                    site=str(source.get("ALPHAPILOT_OKX_SITE", "global")),
                )
                portfolio = _portfolio_snapshot(live_client, store, active_profile, fresh_signals)
                limits = normalize_risk_profile(active_profile.get("profile") if isinstance(active_profile.get("profile"), dict) else {})
                available_slots = max(0, int(limits["maxConcurrentPositions"]) - int(portfolio["openPositionCount"]))
                # One fresh Live entry per heartbeat keeps private-state reconciliation strict.
                arbitration = arbitrate_demo_signals(
                    fresh_signals,
                    maxPositions=min(1, available_slots),
                    allowSameFamilyMultipleSymbols=True,
                )
                engine = LiveExecutionEngine(
                    client=live_client,
                    store=store,
                    authorityAssertion=lambda: lease_store.assert_authority(lease_claim),
                )
                created = []
                for signal in arbitration.selected:
                    export = export_by_release.get(str(signal.get("liveReleaseId") or ""))
                    if export is None:
                        export = export_by_strategy.get(str(signal.get("candidateId") or ""))
                    if export is None:
                        engine.pause("live_signal_release_binding_missing")
                        return {"ok": False, "blockers": ["live_signal_release_binding_missing"], "createdOrderCount": 0, "scans": scans}
                    try:
                        created.append(engine.execute(contract=export, activeProfile=active_profile, signal=signal, portfolio=portfolio))
                    except (PermissionError, RuntimeError, ValueError) as error:
                        engine.pause(f"live_batch_execution_failed:{type(error).__name__}")
                        return {
                            "ok": False,
                            "blockers": [str(error)],
                            "createdOrderCount": len(created),
                            "scans": scans,
                        }
                return {
                    "ok": True,
                    "blockers": [],
                    "scannedReleaseCount": len(selected),
                    "matchedSignalCount": len(all_signals),
                    "createdOrderCount": len(created),
                    "created": [{"recordId": record.recordId, "status": record.status} for record in created],
                    "rejectedSignals": [*rejection_rows, *arbitration.rejected],
                    "scans": scans,
                }
            finally:
                try:
                    lease_store.release(lease_claim)
                except PermissionError:
                    pass
        finally:
            lease_store.close()
    finally:
        store.close()


def reconcile_live_auto_execution_runtime(
    *,
    client: Any | None = None,
    store_path: Path | str = LIVE_EXECUTION_STORE_PATH,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    source = os.environ if environment is None else environment
    live_client = client or OkxLiveClient(
        load_okx_live_credentials(source),
        site=str(source.get("ALPHAPILOT_OKX_SITE", "global")),
    )
    store = LiveExecutionStore(store_path)
    try:
        recovered = LiveExecutionEngine(client=live_client, store=store).recover_open_records()
    finally:
        store.close()
    readonly = run_live_readonly_reconciliation(
        environment=source,
        store_path=store_path,
        client=live_client,
    )
    return {
        "ok": bool(readonly.get("ok")),
        "blockers": [] if readonly.get("ok") else ["live_reconciliation_failed"],
        "recoveredCount": len(recovered),
        "reconciliation": readonly,
    }


def pause_live_auto_execution_runtime(
    reason: str,
    *,
    store_path: Path | str = LIVE_EXECUTION_STORE_PATH,
) -> None:
    store = LiveExecutionStore(store_path)
    try:
        store.set_runtime_flag("paused", True)
        store.set_runtime_flag("pauseReason", reason or "automatic_execution_paused")
        store.append_event(None, "live_paused", {"reason": reason or "automatic_execution_paused"})
    finally:
        store.close()
