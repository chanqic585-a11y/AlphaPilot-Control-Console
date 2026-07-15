"""Explicit, isolated OKX Demo engineering-smoke lifecycle."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .config import DATA_DIR
from .demo_engineering_smoke_contract import validate_demo_engineering_smoke_contract
from .demo_engineering_smoke_store import DemoEngineeringSmokeRecord, DemoEngineeringSmokeStore
from .demo_execution_engine import DemoExecutionEngine
from .demo_execution_store import DemoExecutionStore


DEMO_ENGINEERING_SMOKE_STORE_PATH = DATA_DIR / "demo_engineering_smoke.sqlite"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _first(response: dict[str, Any]) -> dict[str, Any]:
    rows = response.get("data") if isinstance(response.get("data"), list) else []
    return rows[0] if rows and isinstance(rows[0], dict) else {}


def _response_projection(response: dict[str, Any]) -> dict[str, Any]:
    allowed_top = {"code", "msg"}
    allowed_row = {
        "ordId", "clOrdId", "sCode", "sMsg", "state", "accFillSz",
        "instId", "pos", "posSide", "avgPx", "lever", "upl",
    }
    projection: dict[str, Any] = {
        key: response.get(key)
        for key in allowed_top
        if key in response
    }
    rows = response.get("data") if isinstance(response.get("data"), list) else []
    projection["data"] = [
        {key: row.get(key) for key in allowed_row if key in row}
        for row in rows
        if isinstance(row, dict)
    ]
    return projection


def _matching_positions(response: dict[str, Any], instrument_id: str) -> list[dict[str, Any]]:
    if str(response.get("code")) != "0":
        raise RuntimeError("Demo position query failed")
    rows = response.get("data") if isinstance(response.get("data"), list) else []
    matches: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or str(row.get("instId") or "") != instrument_id:
            continue
        try:
            position = float(row.get("pos") or 0)
        except (TypeError, ValueError):
            raise RuntimeError("Demo position quantity is malformed") from None
        if abs(position) > 0:
            matches.append(dict(row))
    return matches


def _close_payload(*, record: DemoEngineeringSmokeRecord, position: dict[str, Any]) -> dict[str, Any]:
    quantity = float(position.get("pos") or 0)
    pos_side = str(position.get("posSide") or "net").lower()
    side = "sell" if quantity > 0 else "buy"
    if pos_side == "long":
        side = "sell"
    elif pos_side == "short":
        side = "buy"
    close_id = "apsmclose" + hashlib.sha256(
        f"{record.runId}:{record.attemptCount}".encode("utf-8")
    ).hexdigest()[:20]
    payload: dict[str, Any] = {
        "instId": record.instrumentId,
        "side": side,
        "posSide": pos_side if pos_side in {"long", "short"} else "net",
        "tdMode": str(record.orderPayload.get("tdMode") or "isolated"),
        "ordType": "market",
        "sz": format(abs(quantity), ".15g"),
        "clOrdId": close_id,
        "reduceOnly": True,
        "tag": "alphapilot",
    }
    return payload


def _adapter_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "alphapilot_control_console_demo_v1",
        "demoReleaseId": contract["releaseId"],
        "status": "demo_eligible",
        "releaseContentHash": contract["releaseHash"],
        "riskEnvelope": {
            "initialEquityUsdt": 1000.0,
            "capitalLimitUsdt": 1000.0,
            "maxOrderNotionalUsdt": 10.0,
            "maxConcurrentPositions": 1,
            "defaultMaxLeverage": 1,
            "hardMaxLeverage": 1,
        },
        "executionBoundary": {
            "environment": "okx_demo_only",
            "automaticDemoExecutionAllowed": True,
            "liveExecutionAllowed": False,
            "withdrawAllowed": False,
        },
    }


def _result(record: DemoEngineeringSmokeRecord, *, minimum_size: str = "") -> dict[str, Any]:
    return {
        "runId": record.runId,
        "releaseId": record.releaseId,
        "releaseHash": record.releaseHash,
        "instrumentId": record.instrumentId,
        "minimumOrderSize": minimum_size or str(record.orderPayload.get("sz") or ""),
        "status": record.status,
        "attemptCount": record.attemptCount,
        "duplicateAttemptCount": record.duplicateAttemptCount,
        "orderAttemptCount": record.attemptCount,
        "exchangeOrderId": record.exchangeOrderId,
        "orderStatus": record.orderStatus,
        "positionStatus": record.positionStatus,
        "exitStatus": record.exitStatus,
        "reconciliationStatus": record.reconciliationStatus,
        "errorCode": record.errorCode,
        "errorMessage": record.errorMessage,
        "strategyQualification": False,
        "promotionEligible": False,
        "forwardPerformanceEligible": False,
        "evidenceClass": "demo_engineering_smoke",
        "updatedAt": record.updatedAt,
    }


def run_demo_engineering_smoke(
    *,
    client: Any,
    contract: dict[str, Any],
    universe: dict[str, Any],
    deterministicTrigger: bool,
    storePath: Path | str = DEMO_ENGINEERING_SMOKE_STORE_PATH,
    executionEngineFactory: Callable[..., DemoExecutionEngine] = DemoExecutionEngine,
    orderStatusChecks: int = 3,
) -> dict[str, Any]:
    validate_demo_engineering_smoke_contract(contract)
    if deterministicTrigger is not True:
        raise PermissionError("Engineering smoke requires an explicit deterministic trigger")
    if universe.get("status") != "usable" or universe.get("environment", "demo") != "demo":
        raise RuntimeError("Authenticated Demo instrument universe is not usable")
    eligible = [str(value) for value in (universe.get("eligibleInstrumentIds") or []) if str(value)]
    if not eligible:
        raise RuntimeError("Authenticated/public Demo instrument intersection is empty")
    instrument_id = str(universe.get("selectedInstrumentId") or eligible[0])
    if instrument_id not in eligible:
        raise ValueError("Selected engineering smoke instrument is unavailable in Demo intersection")
    constraints = universe.get("instrumentConstraints") if isinstance(universe.get("instrumentConstraints"), dict) else {}
    instrument_constraints = constraints.get(instrument_id) if isinstance(constraints.get(instrument_id), dict) else {}
    minimum_size = str(instrument_constraints.get("minSz") or "").strip()
    try:
        if float(minimum_size) <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Demo engineering smoke requires a positive exchange minSz") from None

    idempotency_key = hashlib.sha256(
        _canonical({
            "releaseHash": contract["releaseHash"],
            "publicManifestHash": universe.get("publicManifestHash"),
            "authenticatedInstrumentHash": universe.get("authenticatedInstrumentHash"),
            "instrumentId": instrument_id,
        }).encode("utf-8")
    ).hexdigest()
    opening_payload = {
        "instId": instrument_id,
        "side": "buy",
        "posSide": "net",
        "tdMode": "isolated",
        "ordType": "market",
        "sz": minimum_size,
    }
    store = DemoEngineeringSmokeStore(storePath)
    execution_store: DemoExecutionStore | None = None
    try:
        created = store.create_or_get_run(
            idempotencyKey=idempotency_key,
            releaseId=str(contract["releaseId"]),
            releaseHash=str(contract["releaseHash"]),
            instrumentId=instrument_id,
            orderPayload=opening_payload,
        )
        record = created.record
        if record.status == "completed":
            return _result(record, minimum_size=minimum_size)
        maximum_attempts = int(contract["maximumAttempts"])
        if record.attemptCount >= maximum_attempts:
            record = store.update_run(
                record.runId,
                status="failed",
                errorCode="retry_exhausted",
                errorMessage="Maximum bounded engineering smoke attempts reached",
            )
            return _result(record, minimum_size=minimum_size)
        record = store.increment_attempt(record.runId, maximumAttempts=maximum_attempts)
        store.append_event(record.runId, "order_attempt_started", {
            "attempt": record.attemptCount,
            "instrumentId": instrument_id,
            "minimumOrderSize": minimum_size,
        })
        try:
            leverage_response = client.set_leverage(
                instrumentId=instrument_id,
                leverage=1,
                marginMode="isolated",
                positionSide=None,
            )
            if str(leverage_response.get("code")) != "0":
                raise RuntimeError("Demo leverage setup failed")
            execution_store = DemoExecutionStore(storePath)
            engine = executionEngineFactory(client=client, store=execution_store)
            if execution_store.get_runtime_flag("paused", False):
                engine.resume()
            signal = {
                "candidateId": f"engineering-smoke-{record.runId}-a{record.attemptCount}",
                "signalTime": _now(),
                "strategyFamilyId": "engineering_smoke",
                **opening_payload,
                "notionalUsdt": 1.0,
                "leverage": 1,
                "riskPercent": 0.01,
            }
            execution_record = engine.execute(
                contract=_adapter_contract(contract),
                signal=signal,
                portfolio={
                    "availableEquityUsdt": 1000.0,
                    "dataFresh": True,
                    "liquidityPassed": True,
                },
            )
            if execution_record.status == "rejected":
                order = _first(execution_record.exchangeResponse)
                record = store.update_run(
                    record.runId,
                    status="failed",
                    orderStatus="rejected",
                    exchangeProjection=_response_projection(execution_record.exchangeResponse),
                    errorCode=str(order.get("sCode") or execution_record.exchangeResponse.get("code") or "order_rejected"),
                    errorMessage=str(order.get("sMsg") or execution_record.exchangeResponse.get("msg") or "Demo order rejected")[:240],
                )
                return _result(record, minimum_size=minimum_size)
            record = store.update_run(
                record.runId,
                status="order_submitted",
                exchangeOrderId=execution_record.exchangeOrderId,
                orderStatus=execution_record.status,
                exchangeProjection=_response_projection(execution_record.exchangeResponse),
            )
            reconciled = execution_record
            for _ in range(max(1, int(orderStatusChecks))):
                if reconciled.status in {"filled", "canceled", "rejected", "mmp_canceled"}:
                    break
                reconciled = engine.reconcile(execution_record.recordId)
            record = store.update_run(
                record.runId,
                orderStatus=reconciled.status,
                exchangeOrderId=reconciled.exchangeOrderId,
                exchangeProjection=_response_projection(reconciled.exchangeResponse),
            )
            if reconciled.status != "filled":
                cancel_response = client.cancel_order(
                    instId=instrument_id,
                    ordId=reconciled.exchangeOrderId,
                    clOrdId=str(reconciled.orderPayload.get("clOrdId") or "") or None,
                )
                positions_response = client.get_positions(instrumentId=instrument_id)
                orphan = bool(_matching_positions(positions_response, instrument_id))
                cancel_ok = str(cancel_response.get("code")) == "0"
                record = store.update_run(
                    record.runId,
                    status="failed",
                    positionStatus="orphan" if orphan else "flat",
                    exitStatus="canceled" if cancel_ok else "cancel_failed",
                    reconciliationStatus="mismatch" if orphan else "passed",
                    exchangeProjection={
                        "cancel": _response_projection(cancel_response),
                        "positions": _response_projection(positions_response),
                    },
                    errorCode="order_status_timeout",
                    errorMessage="Demo order did not reach a filled terminal state within bounded checks",
                )
                return _result(record, minimum_size=minimum_size)

            positions_response = client.get_positions(instrumentId=instrument_id)
            positions = _matching_positions(positions_response, instrument_id)
            if not positions:
                record = store.update_run(
                    record.runId,
                    status="failed",
                    positionStatus="missing_after_fill",
                    exitStatus="not_started",
                    reconciliationStatus="mismatch",
                    exchangeProjection={"positions": _response_projection(positions_response)},
                    errorCode="filled_position_missing",
                    errorMessage="Filled Demo order has no readable matching position",
                )
                return _result(record, minimum_size=minimum_size)

            record = store.update_run(record.runId, status="closing", positionStatus="open")
            close_payload = _close_payload(record=record, position=positions[0])
            close_response = client.place_order(close_payload)
            close_order = _first(close_response)
            close_accepted = str(close_response.get("code")) == "0" and str(close_order.get("sCode", "0")) == "0"
            close_status = "rejected"
            if close_accepted:
                close_query = client.get_order(
                    instId=instrument_id,
                    ordId=str(close_order.get("ordId") or "") or None,
                    clOrdId=str(close_payload["clOrdId"]),
                )
                close_status = str(_first(close_query).get("state") or "unknown")
            final_positions_response = client.get_positions(instrumentId=instrument_id)
            final_positions = _matching_positions(final_positions_response, instrument_id)
            orphan = bool(final_positions)
            passed = close_accepted and close_status == "filled" and not orphan
            record = store.update_run(
                record.runId,
                status="completed" if passed else "failed",
                positionStatus="orphan" if orphan else "flat",
                exitStatus=close_status,
                reconciliationStatus="passed" if passed else "mismatch",
                exchangeProjection={
                    "openPositions": _response_projection(positions_response),
                    "close": _response_projection(close_response),
                    "finalPositions": _response_projection(final_positions_response),
                },
                errorCode=None if passed else "reconciliation_mismatch",
                errorMessage=None if passed else "Demo position remained open or close state was not filled",
            )
            store.append_event(record.runId, "reconciliation_completed", {
                "passed": passed,
                "positionStatus": record.positionStatus,
                "exitStatus": record.exitStatus,
            })
            return _result(record, minimum_size=minimum_size)
        except Exception as error:
            record = store.update_run(
                record.runId,
                status="failed",
                errorCode=type(error).__name__,
                errorMessage="Demo engineering smoke failed before safe reconciliation",
            )
            store.append_event(record.runId, "engineering_smoke_failed", {"errorType": type(error).__name__})
            return _result(record, minimum_size=minimum_size)
    finally:
        if execution_store is not None:
            execution_store.close()
        store.close()


def reconcile_demo_engineering_smoke(
    *,
    client: Any,
    storePath: Path | str = DEMO_ENGINEERING_SMOKE_STORE_PATH,
) -> dict[str, Any]:
    store = DemoEngineeringSmokeStore(storePath)
    try:
        for record in store.list_runs():
            if record.status == "completed" and record.positionStatus == "flat":
                continue
            try:
                positions_response = client.get_positions(instrumentId=record.instrumentId)
                positions = _matching_positions(positions_response, record.instrumentId)
                store.update_run(
                    record.runId,
                    positionStatus="orphan" if positions else "flat",
                    reconciliationStatus="mismatch" if positions else "passed",
                    exchangeProjection={"positions": _response_projection(positions_response)},
                )
            except Exception as error:
                store.update_run(
                    record.runId,
                    reconciliationStatus="failed",
                    errorCode=type(error).__name__,
                    errorMessage="Demo engineering smoke reconciliation failed",
                )
        return _status_from_store(store)
    finally:
        store.close()


def _status_from_store(store: DemoEngineeringSmokeStore) -> dict[str, Any]:
    summary = store.build_summary()
    records = store.list_runs()
    summary["orphanCount"] = sum(record.positionStatus == "orphan" for record in records)
    summary["reconciliationPassedCount"] = sum(
        record.reconciliationStatus == "passed" for record in records
    )
    return {
        "status": "usable" if not summary["orphanCount"] else "blocked",
        "environment": "demo",
        "demoPurpose": "engineering_smoke",
        "evidenceClass": "demo_engineering_smoke",
        "strategyQualification": False,
        "promotionEligible": False,
        "forwardPerformanceEligible": False,
        "summary": summary,
        "runs": [_result(record) for record in records[-10:]],
        "blockers": ["orphan_demo_position"] if summary["orphanCount"] else [],
        "nextAction": (
            "Reconcile or close the isolated Demo smoke position."
            if summary["orphanCount"]
            else "Run an explicit engineering smoke only when connectivity proof is required."
        ),
    }


def build_demo_engineering_smoke_status(
    *,
    storePath: Path | str = DEMO_ENGINEERING_SMOKE_STORE_PATH,
) -> dict[str, Any]:
    store = DemoEngineeringSmokeStore(storePath)
    try:
        return _status_from_store(store)
    finally:
        store.close()
