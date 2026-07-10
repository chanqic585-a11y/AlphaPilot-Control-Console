"""Bridge immutable Quant Engine Demo releases into the local Console runtime."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import DATA_DIR, get_quant_engine_path
from .credential_runtime import load_okx_demo_credentials, runtime_credential_status
from .demo_arbitrator import arbitrate_demo_signals
from .demo_execution_engine import DemoExecutionEngine
from .demo_execution_store import DemoExecutionStore
from .demo_release_scanner import scan_immutable_demo_release
from .demo_runtime_guard import evaluate_demo_runtime_guard
from .exchange_connectors.okx_demo_client import OkxDemoClient


STORE_PATH = DATA_DIR / "evolution_demo_execution.sqlite"
LOCAL_CONTRACT_DIR = DATA_DIR / "demo_release_contracts"


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
    if not contract.get("demoReleaseId") or not contract.get("strategyCandidateId"):
        raise ValueError("Demo release identity is incomplete")
    if not contract.get("releaseContentHash"):
        raise ValueError("Demo release content hash is missing")
    limits = contract.get("riskEnvelope") if isinstance(contract.get("riskEnvelope"), dict) else {}
    required_limits = {
        "initialEquityUsdt": 1000.0,
        "riskPerTradePercent": 0.25,
        "maxOpenRiskPercent": 1.0,
        "maxOrderNotionalUsdt": 250.0,
        "maxConcurrentPositions": 3,
    }
    for key, expected_value in required_limits.items():
        if float(limits.get(key) or 0) != expected_value:
            raise ValueError(f"Demo risk envelope mismatch: {key}")


def _portfolio_from_demo_account(client: OkxDemoClient, store: DemoExecutionStore) -> dict[str, Any]:
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
    risk_per_trade = 0.25
    return {
        "availableEquityUsdt": available,
        "openPositionCount": len(open_positions),
        "openRiskPercent": len(open_positions) * risk_per_trade,
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


def build_evolution_demo_status() -> dict[str, Any]:
    contracts, rejected = discover_demo_contracts()
    store = DemoExecutionStore(STORE_PATH)
    try:
        records = store.list_records()
        paused = bool(store.get_runtime_flag("paused", False))
        kill_switch = bool(store.get_runtime_flag("killSwitch", False))
    finally:
        store.close()
    credential_status = runtime_credential_status()
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
    return {
        "version": "V13.20.0",
        "source": "immutable_release_demo_bridge_v13_20",
        "summary": {
            "eligibleReleaseCount": len(contracts),
            "rejectedContractCount": len(rejected),
            "executionRecordCount": len(records),
            "activeRecordCount": sum(record.status not in {"filled", "canceled", "rejected", "mmp_canceled"} for record in records),
            "paused": paused,
            "killSwitch": kill_switch,
            "ready": not blockers,
            "initialEquityUsdt": 1000.0,
            "maxOrderNotionalUsdt": 250.0,
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
            }
            for contract in contracts
        ],
        "recentRecords": [_record_payload(record) for record in records[-10:]],
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


def run_evolution_demo_cycle(payload: dict[str, Any]) -> dict[str, Any]:
    status = build_evolution_demo_status()
    if status["blockers"]:
        return {"ok": False, "blockers": status["blockers"], "status": status}
    contracts, _ = discover_demo_contracts()
    release_id = str(payload.get("demoReleaseId") or "")
    contract = next((item for item in contracts if item.get("demoReleaseId") == release_id), None)
    if contract is None:
        return {"ok": False, "blockers": ["demo_release_not_found"], "status": status}
    externally_supplied_signal_count = len(payload.get("signals", [])) if isinstance(payload.get("signals"), list) else 0
    scan = scan_immutable_demo_release(contract)
    if scan.get("blockers"):
        return {
            "ok": False,
            "blockers": list(scan["blockers"]),
            "externalSignalsIgnored": externally_supplied_signal_count,
            "scan": scan,
            "status": status,
        }
    signals = scan.get("signals") if isinstance(scan.get("signals"), list) else []
    store = DemoExecutionStore(STORE_PATH)
    try:
        client = OkxDemoClient(load_okx_demo_credentials())
        engine = DemoExecutionEngine(client=client, store=store)
        recovered = engine.recover_open_records()
        try:
            portfolio = _portfolio_from_demo_account(client, store)
        except RuntimeError as error:
            engine.pause("demo_private_read_failed")
            return {
                "ok": False,
                "blockers": [str(error)],
                "externalSignalsIgnored": externally_supplied_signal_count,
                "scan": scan,
                "status": build_evolution_demo_status(),
            }
        portfolio["dataFresh"] = all(bool(item.get("dataFresh")) for item in signals)
        portfolio["liquidityPassed"] = all(bool(item.get("liquidityPassed")) for item in signals)
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
                "externalSignalsIgnored": externally_supplied_signal_count,
                "scan": scan,
                "status": build_evolution_demo_status(),
            }
        if not signals:
            return {
                "ok": True,
                "created": [],
                "recovered": [_record_payload(record) for record in recovered],
                "rejectedSignals": list(scan.get("rejections") or []),
                "externalSignalsIgnored": externally_supplied_signal_count,
                "scan": scan,
                "status": build_evolution_demo_status(),
            }
        limits = contract.get("riskEnvelope") if isinstance(contract.get("riskEnvelope"), dict) else {}
        max_positions = int(limits.get("maxConcurrentPositions") or 3)
        current_positions = int(portfolio.get("openPositionCount") or 0)
        available_slots = max_positions - current_positions
        if available_slots <= 0:
            return {
                "ok": False,
                "blockers": ["max_concurrent_positions"],
                "rejectedSignals": [
                    {**item, "reason": "portfolio_position_limit"}
                    for item in signals
                    if isinstance(item, dict)
                ],
                "externalSignalsIgnored": externally_supplied_signal_count,
                "scan": scan,
                "status": status,
            }
        arbitration = arbitrate_demo_signals(
            [item for item in signals if isinstance(item, dict)],
            maxPositions=available_slots,
        )
        created = []
        execution_rejections = []
        rolling_portfolio = dict(portfolio)
        for signal in arbitration.selected:
            try:
                record = engine.execute(contract=contract, signal=signal, portfolio=rolling_portfolio)
                created.append(record)
                rolling_portfolio["openPositionCount"] = int(rolling_portfolio.get("openPositionCount") or 0) + 1
                rolling_portfolio["openRiskPercent"] = float(rolling_portfolio.get("openRiskPercent") or 0) + float(signal.get("riskPercent") or 0)
            except (RuntimeError, ValueError) as error:
                execution_rejections.append({
                    "candidateId": signal.get("candidateId"),
                    "instId": signal.get("instId"),
                    "reason": str(error),
                })
                if store.get_runtime_flag("paused", False):
                    break
        return {
            "ok": bool(created) and not store.get_runtime_flag("paused", False),
            "created": [_record_payload(record) for record in created],
            "recovered": [_record_payload(record) for record in recovered],
            "rejectedSignals": [*arbitration.rejected, *execution_rejections],
            "externalSignalsIgnored": externally_supplied_signal_count,
            "scan": scan,
            "status": build_evolution_demo_status(),
        }
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
