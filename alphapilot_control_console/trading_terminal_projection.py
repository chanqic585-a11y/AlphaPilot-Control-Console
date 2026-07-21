"""Read-only Demo and Live terminal projection backed by runtime ledgers."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .execution_control import ACTION_STORE_PATH
from .live_execution_store import LIVE_EXECUTION_STORE_PATH
from .risk_profile_store import RISK_PROFILE_STORE_PATH
from .strategy_execution_policy_store import STRATEGY_EXECUTION_POLICY_STORE_PATH


DEMO_EXECUTION_STORE_PATH = DATA_DIR / "evolution_demo_execution.sqlite"


def _connect_read_only(path: Path) -> sqlite3.Connection | None:
    target = Path(path)
    if not target.is_file():
        return None
    connection = sqlite3.connect(f"{target.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone() is not None


def _json(value: Any, fallback: Any) -> Any:
    try:
        return json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError):
        return fallback


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if mapping.get(key) not in (None, ""):
            return mapping[key]
    return None


class TradingTerminalProjection:
    def __init__(
        self,
        *,
        runtime_store_path: Path | str = ACTION_STORE_PATH,
        demo_execution_store_path: Path | str = DEMO_EXECUTION_STORE_PATH,
        live_execution_store_path: Path | str = LIVE_EXECUTION_STORE_PATH,
        risk_profile_store_path: Path | str = RISK_PROFILE_STORE_PATH,
        strategy_policy_store_path: Path | str = STRATEGY_EXECUTION_POLICY_STORE_PATH,
    ) -> None:
        self.runtime_store_path = Path(runtime_store_path)
        self.demo_execution_store_path = Path(demo_execution_store_path)
        self.live_execution_store_path = Path(live_execution_store_path)
        self.risk_profile_store_path = Path(risk_profile_store_path)
        self.strategy_policy_store_path = Path(strategy_policy_store_path)

    @staticmethod
    def _normalize_environment(environment: str) -> str:
        if environment not in {"okx_demo", "okx_live"}:
            raise ValueError("Unsupported terminal environment")
        return environment

    def _runtime(self, environment: str) -> dict[str, Any]:
        environment = self._normalize_environment(environment)
        connection = _connect_read_only(self.runtime_store_path)
        if connection is None:
            return {
                "environment": environment,
                "desiredEnabled": False,
                "armed": False,
                "status": "offline",
                "lastHeartbeatAt": None,
                "nextEvaluationAt": None,
                "pauseReason": "runtime_store_unavailable",
                "lastError": None,
                "updatedAt": None,
            }
        try:
            if not _table_exists(connection, "AutoExecutionRuntime"):
                return {
                    "environment": environment,
                    "desiredEnabled": False,
                    "armed": False,
                    "status": "offline",
                    "lastHeartbeatAt": None,
                    "nextEvaluationAt": None,
                    "pauseReason": "runtime_table_unavailable",
                    "lastError": None,
                    "updatedAt": None,
                }
            row = connection.execute(
                "SELECT * FROM AutoExecutionRuntime WHERE environment = ?",
                (environment,),
            ).fetchone()
            if row is None:
                return {
                    "environment": environment,
                    "desiredEnabled": False,
                    "armed": False,
                    "status": "disabled",
                    "lastHeartbeatAt": None,
                    "nextEvaluationAt": None,
                    "pauseReason": None,
                    "lastError": None,
                    "updatedAt": None,
                }
            desired = bool(row["desiredEnabled"])
            armed_process_id = str(row["armedProcessId"] or "")
            return {
                "environment": environment,
                "desiredEnabled": desired,
                "armed": bool(
                    desired and armed_process_id == str(os.getpid())
                ),
                "status": row["status"],
                "lastHeartbeatAt": row["lastHeartbeatAt"],
                "nextEvaluationAt": row["nextEvaluationAt"],
                "pauseReason": row["pauseReason"],
                "lastError": row["lastError"],
                "updatedAt": row["updatedAt"],
            }
        finally:
            connection.close()

    def _latest_heartbeat(self, environment: str) -> dict[str, Any] | None:
        connection = _connect_read_only(self.runtime_store_path)
        if connection is None:
            return None
        try:
            if not _table_exists(connection, "AutoExecutionEvents"):
                return None
            row = connection.execute(
                """
                SELECT eventId, payloadJson, createdAt FROM AutoExecutionEvents
                WHERE environment = ? AND eventType = 'heartbeat_completed'
                ORDER BY eventId DESC LIMIT 1
                """,
                (environment,),
            ).fetchone()
            if row is None:
                return None
            payload = _json(row["payloadJson"], {})
            return {
                "eventId": int(row["eventId"]),
                "createdAt": row["createdAt"],
                "payload": payload if isinstance(payload, dict) else {},
            }
        finally:
            connection.close()

    def _execution_connection(self, environment: str) -> sqlite3.Connection | None:
        path = (
            self.demo_execution_store_path
            if environment == "okx_demo"
            else self.live_execution_store_path
        )
        return _connect_read_only(path)

    def _runtime_flag(self, environment: str, key: str) -> Any:
        connection = self._execution_connection(environment)
        if connection is None:
            return None
        table = "DemoRuntimeState" if environment == "okx_demo" else "LiveRuntimeState"
        try:
            if not _table_exists(connection, table):
                return None
            row = connection.execute(
                f"SELECT valueJson FROM {table} WHERE stateKey = ?",
                (key,),
            ).fetchone()
            return _json(row["valueJson"], None) if row else None
        finally:
            connection.close()

    def _account_snapshot(self, environment: str) -> dict[str, Any] | None:
        for key in ("lastPortfolioSnapshot", "lastAccountSnapshot"):
            snapshot = self._runtime_flag(environment, key)
            if isinstance(snapshot, dict):
                return snapshot
        return None

    def _records(self, environment: str) -> list[dict[str, Any]]:
        connection = self._execution_connection(environment)
        if connection is None:
            return []
        table = "DemoExecutionRecords" if environment == "okx_demo" else "LiveExecutionRecords"
        try:
            if not _table_exists(connection, table):
                return []
            rows = connection.execute(
                f"SELECT * FROM {table} ORDER BY createdAt, recordId"
            ).fetchall()
            records: list[dict[str, Any]] = []
            for row in rows:
                signal = _json(row["signalJson"], {})
                order = _json(row["orderPayloadJson"], {})
                signal = signal if isinstance(signal, dict) else {}
                order = order if isinstance(order, dict) else {}
                release_id = (
                    row["demoReleaseId"]
                    if environment == "okx_demo"
                    else row["liveReleaseId"]
                )
                strategy_id = _first(
                    signal,
                    "strategyId",
                    "strategyCandidateId",
                    "candidateId",
                )
                if environment == "okx_live":
                    strategy_id = strategy_id or row["strategyCandidateId"]
                records.append(
                    {
                        "recordId": row["recordId"],
                        "releaseId": release_id,
                        "strategyId": strategy_id or release_id,
                        "instrumentId": _first(signal, "instrumentId", "instId")
                        or _first(order, "instId", "instrumentId"),
                        "side": _first(signal, "side", "direction") or order.get("side"),
                        "status": row["status"],
                        "exchangeOrderId": row["exchangeOrderId"],
                        "orderType": _first(order, "ordType", "orderType"),
                        "quantity": _first(order, "sz", "quantity", "size"),
                        "price": _first(order, "px", "price"),
                        "createdAt": row["createdAt"],
                        "updatedAt": row["updatedAt"],
                    }
                )
            return records
        finally:
            connection.close()

    def _latest_scan(self, environment: str) -> dict[str, Any]:
        event = self._latest_heartbeat(environment)
        payload = event["payload"] if event else {}
        audit = payload.get("evaluationAudit")
        audit = audit if isinstance(audit, dict) else {}
        funnel = audit.get("funnel")
        funnel = funnel if isinstance(funnel, dict) else {}
        return {
            "eventId": event.get("eventId") if event else None,
            "completedAt": event.get("createdAt") if event else None,
            "state": audit.get("state"),
            "evaluatedReleaseCount": int(payload.get("evaluatedReleaseCount") or 0),
            "marketInstrumentCount": int(funnel.get("marketInstrumentCount") or 0),
            "liquidityEligibleInstrumentCount": int(
                funnel.get("liquidityEligibleInstrumentCount") or 0
            ),
            "deepScreenCount": int(
                funnel.get("componentInstrumentEvaluationCount") or 0
            ),
            "matchedSignalCount": int(funnel.get("matchedSignalCount") or 0),
            "orderAttemptCount": int(funnel.get("orderAttemptCount") or 0),
            "filledOrderCount": int(funnel.get("filledOrderCount") or 0),
            "openPositionCount": int(funnel.get("openPositionCount") or 0),
            "releaseAudits": list(audit.get("releaseAudits") or []),
            "stageDurationsMs": dict(audit.get("stageDurationsMs") or {}),
        }

    def summary(self, environment: str) -> dict[str, Any]:
        environment = self._normalize_environment(environment)
        runtime = self._runtime(environment)
        snapshot = self._account_snapshot(environment)
        records = self._records(environment)
        scan = self._latest_scan(environment)
        issues: list[dict[str, str]] = []
        if runtime["lastError"]:
            issues.append({
                "severity": "error",
                "code": "runtime_error",
                "message": str(runtime["lastError"]),
            })
        if runtime["desiredEnabled"] and not runtime["armed"]:
            issues.append({
                "severity": "warning",
                "code": "process_arm_required",
                "message": "当前进程尚未 ARM，需要操作员在安全启动器中确认。",
            })
        if snapshot is None:
            account_status = "unavailable_process_credentials_required"
            equity = available_balance = today_pnl = floating_pnl = open_position_count = None
            issues.append({
                "severity": "info",
                "code": "account_snapshot_unavailable",
                "message": "账户快照不可用；需要当前进程凭据完成只读同步。",
            })
        else:
            account_status = str(snapshot.get("status") or "available")
            equity = _first(snapshot, "accountEquityUsdt", "availableEquityUsdt")
            available_balance = _first(
                snapshot,
                "availableBalanceUsdt",
                "availableEquityUsdt",
            )
            today_pnl = snapshot.get("todayRealizedPnlUsdt")
            floating_pnl = snapshot.get("floatingPnlUsdt")
            positions = snapshot.get("positions")
            open_position_count = len(positions) if isinstance(positions, list) else int(
                snapshot.get("openPositionCount") or 0
            )
        strategy_ids = {
            str(item.get("strategyId") or item.get("releaseId"))
            for item in scan["releaseAudits"]
            if isinstance(item, dict) and (item.get("strategyId") or item.get("releaseId"))
        }
        return {
            "environment": environment,
            "runtimeStatus": runtime["status"],
            "desiredEnabled": runtime["desiredEnabled"],
            "armed": runtime["armed"],
            "lastHeartbeatAt": runtime["lastHeartbeatAt"],
            "nextEvaluationAt": runtime["nextEvaluationAt"],
            "lastError": runtime["lastError"],
            "accountDataStatus": account_status,
            "equity": equity,
            "availableBalance": available_balance,
            "todayPnl": today_pnl,
            "floatingPnl": floating_pnl,
            "openPositionCount": open_position_count,
            "runningStrategyCount": len(strategy_ids) if runtime["armed"] else 0,
            "strategyOrderCount": len(records),
            "scanFunnel": {key: value for key, value in scan.items() if key != "releaseAudits"},
            "issues": issues,
            "updatedAt": snapshot.get("updatedAt") if snapshot else runtime["updatedAt"],
            "source": "runtime_and_execution_ledgers",
            "readOnly": True,
        }

    def strategies(self, environment: str) -> dict[str, Any]:
        environment = self._normalize_environment(environment)
        runtime = self._runtime(environment)
        scan = self._latest_scan(environment)
        records = self._records(environment)
        snapshot = self._account_snapshot(environment) or {}
        positions = snapshot.get("positions") if isinstance(snapshot.get("positions"), list) else []
        rows: list[dict[str, Any]] = []
        audits_by_identity: dict[tuple[str, str], dict[str, Any]] = {}
        for item in scan["releaseAudits"]:
            if not isinstance(item, dict):
                continue
            identity = (
                str(item.get("strategyId") or item.get("releaseId") or ""),
                str(item.get("releaseId") or ""),
            )
            existing = audits_by_identity.get(identity)
            if existing is None:
                audits_by_identity[identity] = dict(item)
                continue
            for field in (
                "marketInstrumentCount",
                "liquidityEligibleCount",
                "deepScreenRequired",
                "deepScreenCompleted",
                "matchedSignalCount",
            ):
                existing[field] = max(int(existing.get(field) or 0), int(item.get(field) or 0))
            for field in ("name", "displayName", "timeframe"):
                if not existing.get(field) and item.get(field):
                    existing[field] = item[field]
        audits = list(audits_by_identity.values())
        for audit in audits:
            strategy_id = str(audit.get("strategyId") or audit.get("releaseId") or "")
            release_id = str(audit.get("releaseId") or "")
            strategy_records = [item for item in records if item["strategyId"] == strategy_id or item["releaseId"] == release_id]
            strategy_positions = [item for item in positions if isinstance(item, dict) and item.get("strategyId") == strategy_id]
            timeframe = audit.get("timeframe")
            display_name = str(audit.get("displayName") or audit.get("name") or strategy_id or release_id)
            rows.append({
                "strategyId": strategy_id,
                "releaseId": release_id,
                "name": display_name,
                "displayName": display_name,
                "timeframe": timeframe,
                "timeframes": [timeframe] if timeframe else [],
                "status": "running" if runtime["armed"] else "not_armed",
                "latestScanAt": scan["completedAt"],
                "scanInstrumentCount": int(audit.get("marketInstrumentCount") or 0),
                "latestScan": {
                    "marketInstrumentCount": int(audit.get("marketInstrumentCount") or 0),
                    "liquidityEligibleCount": int(audit.get("liquidityEligibleCount") or 0),
                    "deepScreenRequired": int(audit.get("deepScreenRequired") or 0),
                    "deepScreenCompleted": int(audit.get("deepScreenCompleted") or 0),
                    "matchedSignalCount": int(audit.get("matchedSignalCount") or 0),
                },
                "orderCount": len(strategy_records),
                "openPositionCount": len(strategy_positions),
                "todayPnl": None,
                "floatingPnl": sum(
                    float(item.get("unrealizedPnlUsdt") or item.get("floatingPnlUsdt") or 0)
                    for item in strategy_positions
                ),
            })
        if not rows:
            identities = sorted({(item["strategyId"], item["releaseId"]) for item in records})
            rows = [
                {
                    "strategyId": strategy_id,
                    "releaseId": release_id,
                    "name": strategy_id or release_id,
                    "displayName": strategy_id or release_id,
                    "timeframe": None,
                    "timeframes": [],
                    "status": "running" if runtime["armed"] else "not_armed",
                    "latestScanAt": scan["completedAt"],
                    "scanInstrumentCount": 0,
                    "latestScan": None,
                    "orderCount": len([item for item in records if item["strategyId"] == strategy_id]),
                    "openPositionCount": 0,
                    "todayPnl": None,
                    "floatingPnl": None,
                }
                for strategy_id, release_id in identities
            ]
        return {"environment": environment, "strategies": rows, "readOnly": True}

    def positions(self, environment: str) -> dict[str, Any]:
        environment = self._normalize_environment(environment)
        snapshot = self._account_snapshot(environment)
        if snapshot is None:
            return {
                "environment": environment,
                "positions": [],
                "openPositionCount": None,
                "dataStatus": "unavailable_process_credentials_required",
                "readOnly": True,
            }
        positions = snapshot.get("positions")
        positions = [dict(item) for item in positions if isinstance(item, dict)] if isinstance(positions, list) else []
        return {
            "environment": environment,
            "positions": positions,
            "openPositionCount": len(positions),
            "dataStatus": str(snapshot.get("status") or "available"),
            "updatedAt": snapshot.get("updatedAt"),
            "readOnly": True,
        }

    def orders(self, environment: str) -> dict[str, Any]:
        environment = self._normalize_environment(environment)
        records = self._records(environment)
        return {
            "environment": environment,
            "orders": records,
            "strategyOrderCount": len(records),
            "source": "execution_ledger",
            "rawExchangePayloadExcluded": True,
            "readOnly": True,
        }
