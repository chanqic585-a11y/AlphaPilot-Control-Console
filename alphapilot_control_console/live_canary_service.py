"""Fail-closed OKX Live Canary status, reconciliation, arming, and stop controls."""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from .credential_runtime import (
    live_runtime_credential_status,
    load_okx_live_credentials,
)
from .exchange_connectors.okx_live_client import OkxLiveClient
from .live_execution_store import LIVE_EXECUTION_STORE_PATH, LiveExecutionStore
from .live_release_service import build_live_release_status
from .risk_profile_store import RISK_PROFILE_STORE_PATH, RiskProfileStore


ARM_CONFIRMATION = "ARM_OKX_LIVE_CANARY"


def _flag(source: Mapping[str, str], name: str) -> bool:
    return str(source.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def live_runtime_gates(environment: Mapping[str, str] | None = None) -> dict[str, bool]:
    source = os.environ if environment is None else environment
    return {
        "masterEnabled": _flag(source, "ALPHAPILOT_OKX_LIVE_ENABLED"),
        "readEnabled": _flag(source, "ALPHAPILOT_OKX_LIVE_READ_ENABLED"),
        "canaryEnabled": _flag(source, "ALPHAPILOT_OKX_LIVE_CANARY_ENABLED"),
        "orderEnabled": _flag(source, "ALPHAPILOT_OKX_LIVE_ORDER_ENABLED"),
        "automationEnabled": _flag(source, "ALPHAPILOT_OKX_LIVE_AUTOMATION_ENABLED"),
    }


def _active_profile(path: Path | str = RISK_PROFILE_STORE_PATH) -> dict[str, Any] | None:
    store = RiskProfileStore(path)
    try:
        return store.get_active_profile("live_canary")
    finally:
        store.close()


def _release_profile_matches(releases: list[dict[str, Any]], profile: dict[str, Any] | None) -> bool:
    if not releases or profile is None:
        return False
    return any(
        row.get("release", {}).get("riskProfileId") == profile.get("riskProfileId")
        and row.get("release", {}).get("riskProfileHash") == profile.get("contentHash")
        for row in releases
    )


def build_live_canary_status(
    *,
    environment: Mapping[str, str] | None = None,
    store_path: Path | str = LIVE_EXECUTION_STORE_PATH,
    profile_path: Path | str = RISK_PROFILE_STORE_PATH,
) -> dict[str, Any]:
    source = os.environ if environment is None else environment
    gates = live_runtime_gates(source)
    credentials = live_runtime_credential_status(source)
    release_status = build_live_release_status()
    releases = list(release_status.get("releases") or [])
    profile = _active_profile(profile_path)
    store = LiveExecutionStore(store_path)
    try:
        runtime = store.runtime_state()
        records = [asdict(row) for row in store.list_records()[-20:]]
        events = store.list_events(30)
    finally:
        store.close()
    profile_match = _release_profile_matches(releases, profile)
    blockers: list[str] = []
    checks = (
        (gates["masterEnabled"], "live_master_gate_disabled"),
        (gates["readEnabled"], "live_read_gate_disabled"),
        (gates["canaryEnabled"], "live_canary_gate_disabled"),
        (gates["orderEnabled"], "live_order_gate_disabled"),
        (gates["automationEnabled"], "live_automation_gate_disabled"),
        (credentials["allConfigured"], "live_runtime_credentials_missing"),
        (bool(releases), "no_approved_live_release"),
        (profile is not None, "no_active_live_canary_risk_profile"),
        (profile_match, "live_release_risk_profile_mismatch"),
        (not runtime["killSwitchActive"], "live_kill_switch_active"),
        (not runtime["paused"], "live_entries_paused"),
        (runtime["lastReconciliationMatched"], "live_reconciliation_not_confirmed"),
    )
    for passed, reason in checks:
        if not passed:
            blockers.append(reason)
    return {
        "version": "V13.25.0",
        "source": "okx_live_canary_control_v1",
        "summary": {
            "approvedLiveReleaseCount": len(releases),
            "executionRecordCount": len(records),
            "activeRiskProfileMatched": profile_match,
            "readOnlyReady": gates["masterEnabled"] and gates["readEnabled"] and credentials["allConfigured"],
            "canaryOrderReady": not blockers,
        },
        "runtimeGates": gates,
        "credentialStatus": credentials,
        "runtime": runtime,
        "activeRiskProfile": profile,
        "liveReleases": release_status,
        "recentRecords": records,
        "recentEvents": events,
        "blockers": blockers,
        "safetyBoundary": {
            "liveAdapterPresent": True,
            "liveExecutionEnabledByDefault": False,
            "automaticSignalRunnerPresent": True,
            "automaticExecutionEnabledByDefault": False,
            "approvedLiveReleaseRequired": True,
            "activeRiskProfileHashRequired": True,
            "privateStateReconciliationRequired": True,
            "attachedProtectionRequired": True,
            "idempotencyRequired": True,
            "unknownStatePausesEntries": True,
            "killSwitchAvailable": True,
            "withdrawAllowed": False,
            "rawCredentialStorageAllowed": False,
        },
    }


def run_live_readonly_reconciliation(
    *,
    environment: Mapping[str, str] | None = None,
    store_path: Path | str = LIVE_EXECUTION_STORE_PATH,
    client: Any | None = None,
) -> dict[str, Any]:
    source = os.environ if environment is None else environment
    gates = live_runtime_gates(source)
    if not gates["masterEnabled"] or not gates["readEnabled"]:
        raise PermissionError("OKX Live read-only gates are disabled")
    live_client = client or OkxLiveClient(load_okx_live_credentials(source), site=str(source.get("ALPHAPILOT_OKX_SITE", "global")))
    config = live_client.get_account_config()
    balance = live_client.get_balance("USDT")
    positions = live_client.get_positions()
    open_orders = live_client.get_open_orders()
    responses = {"config": config, "balance": balance, "positions": positions, "openOrders": open_orders}
    endpoint_codes = {key: str(value.get("code") or "") for key, value in responses.items()}
    endpoints_ok = all(code == "0" for code in endpoint_codes.values())
    position_rows = positions.get("data") if isinstance(positions.get("data"), list) else []
    actual_positions = [row for row in position_rows if isinstance(row, dict) and abs(float(row.get("pos") or 0)) > 0]
    order_rows = open_orders.get("data") if isinstance(open_orders.get("data"), list) else []
    actual_orders = [row for row in order_rows if isinstance(row, dict)]
    store = LiveExecutionStore(store_path)
    try:
        tracked = store.list_records({"submitted", "live", "partially_filled", "filled", "unknown"})
        tracked_instruments = {row.instrumentId for row in tracked}
        tracked_client_ids = {str(row.orderPayload.get("clOrdId") or "") for row in tracked}
        untracked_positions = [row for row in actual_positions if str(row.get("instId") or "") not in tracked_instruments]
        untracked_orders = [row for row in actual_orders if str(row.get("clOrdId") or "") not in tracked_client_ids]
        matched = endpoints_ok and not untracked_positions and not untracked_orders
        store.set_runtime_flag("lastReconciliationMatched", matched)
        from datetime import UTC, datetime
        store.set_runtime_flag("lastReconciledAt", datetime.now(UTC).isoformat())
        if not matched:
            store.set_runtime_flag("paused", True)
            store.set_runtime_flag("pauseReason", "private_state_reconciliation_mismatch")
        store.append_event(None, "live_readonly_reconciliation", {
            "endpointCodes": endpoint_codes,
            "openPositionCount": len(actual_positions),
            "openOrderCount": len(actual_orders),
            "untrackedPositionCount": len(untracked_positions),
            "untrackedOrderCount": len(untracked_orders),
            "matched": matched,
        })
    finally:
        store.close()
    return {
        "ok": matched,
        "readOnly": True,
        "endpointCodes": endpoint_codes,
        "openPositionCount": len(actual_positions),
        "openOrderCount": len(actual_orders),
        "untrackedPositionCount": len(untracked_positions),
        "untrackedOrderCount": len(untracked_orders),
        "reconciliationMatched": matched,
        "accountValuesPersisted": False,
        "liveCanary": build_live_canary_status(environment=source, store_path=store_path),
    }


def arm_live_canary(
    payload: dict[str, Any],
    *,
    environment: Mapping[str, str] | None = None,
    store_path: Path | str = LIVE_EXECUTION_STORE_PATH,
) -> dict[str, Any]:
    source = os.environ if environment is None else environment
    status = build_live_canary_status(environment=source, store_path=store_path)
    gates = status["runtimeGates"]
    required = (
        gates["masterEnabled"]
        and gates["readEnabled"]
        and gates["canaryEnabled"]
        and gates["orderEnabled"]
        and gates["automationEnabled"]
    )
    if not required or not status["credentialStatus"]["allConfigured"]:
        raise PermissionError("All OKX Live Canary process gates and runtime credentials are required")
    if not status["summary"]["activeRiskProfileMatched"] or not status["liveReleases"]["releases"]:
        raise PermissionError("A matching approved LiveRelease and active RiskProfile are required")
    if status["runtime"]["lastReconciliationMatched"] is not True:
        raise PermissionError("A matching Live read-only reconciliation is required before arming")
    if str(payload.get("confirmation") or "") != ARM_CONFIRMATION or str(payload.get("actor") or "") != "user_manual":
        raise PermissionError("Exact manual Live Canary arming confirmation is required")
    store = LiveExecutionStore(store_path)
    try:
        store.set_runtime_flag("killSwitch", False)
        store.set_runtime_flag("paused", False)
        store.set_runtime_flag("pauseReason", "")
        store.append_event(None, "live_canary_armed", {"actor": "user_manual"})
    finally:
        store.close()
    return {"ok": True, "liveCanary": build_live_canary_status(environment=source, store_path=store_path)}


def build_exact_live_canary_arm_readiness(
    *,
    bundle: Mapping[str, Any],
    approval: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Read-only exact-identity gate used before a V59/V60 ARM operation exists."""

    blockers: list[str] = []
    if str(bundle.get("status") or "") != "blocked_waiting_exact_live_release_approval":
        blockers.append("experimental_live_release_readiness_invalid")
    if approval is None:
        blockers.append("exact_live_release_approval_missing")
    else:
        from .experimental_live_canary_release import validate_exact_live_canary_approval

        try:
            validate_exact_live_canary_approval(bundle, approval)
        except (PermissionError, TypeError, ValueError):
            blockers.append("exact_live_release_approval_mismatch")
    adaptive = bundle.get("adaptiveLearningReadiness") or {}
    if adaptive.get("passed") is not True:
        blockers.append("adaptive_learning_live_readiness_not_passed")
    return {
        "canArm": not blockers,
        "blockers": blockers,
        "releaseHash": str((bundle.get("liveRelease") or {}).get("releaseHash") or ""),
        "riskOverlayHash": str((bundle.get("riskOverlay") or {}).get("riskOverlayHash") or ""),
        "armStatus": "not_run",
        "withdrawAllowed": False,
    }


def activate_live_canary_kill_switch(
    payload: dict[str, Any] | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    store_path: Path | str = LIVE_EXECUTION_STORE_PATH,
    client: Any | None = None,
) -> dict[str, Any]:
    source = os.environ if environment is None else environment
    reason = str((payload or {}).get("reason") or "operator_emergency_stop")
    store = LiveExecutionStore(store_path)
    exchange_cancel_sent = False
    exchange_code = ""
    try:
        store.set_runtime_flag("killSwitch", True)
        store.set_runtime_flag("paused", True)
        store.set_runtime_flag("pauseReason", reason)
        try:
            if live_runtime_gates(source)["masterEnabled"] and live_runtime_credential_status(source)["allConfigured"]:
                live_client = client or OkxLiveClient(load_okx_live_credentials(source), site=str(source.get("ALPHAPILOT_OKX_SITE", "global")))
                response = live_client.cancel_all_after(10)
                exchange_code = str(response.get("code") or "")
                exchange_cancel_sent = exchange_code == "0"
        except Exception as error:
            exchange_code = type(error).__name__
        store.append_event(None, "live_canary_kill_switch", {
            "reason": reason,
            "exchangeCancelSent": exchange_cancel_sent,
            "exchangeCode": exchange_code,
        })
    finally:
        store.close()
    return {
        "ok": True,
        "exchangeCancelSent": exchange_cancel_sent,
        "exchangeCode": exchange_code,
        "liveCanary": build_live_canary_status(environment=source, store_path=store_path),
    }
