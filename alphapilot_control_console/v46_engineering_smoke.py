"""Exact, one-shot V46 OKX Demo engineering smoke with isolated evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import time
from datetime import UTC, datetime
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any, Callable, Mapping

from .credential_runtime import load_okx_demo_credentials
from .demo_credential_bootstrap import bootstrap_demo_credentials
from .exchange_connectors.okx_demo_client import OkxDemoClient
from .exchange_connectors.okx_demo_private_ws import OkxDemoPrivateWsRuntime


_CONTRACT_FILE = "engineering_smoke_contract.json"
_CHECKPOINT_FILE = ".engineering_smoke_checkpoint.json"
_INSTRUMENT_FIELDS = (
    "instId",
    "instType",
    "settleCcy",
    "state",
    "tickSz",
    "lotSz",
    "minSz",
    "ctVal",
    "ctType",
)
_SENSITIVE_PARTS = (
    "apikey",
    "secretkey",
    "passphrase",
    "password",
    "credential",
    "accesstoken",
    "okaccesssign",
)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(_canonical(dict(payload)) + "\n")


def _reject_sensitive(value: Any, path: str = "engineeringSmoke") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            compact = str(key).replace("_", "").replace("-", "").lower()
            if any(part in compact for part in _SENSITIVE_PARTS):
                raise ValueError(f"Sensitive field is forbidden: {path}.{key}")
            _reject_sensitive(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{path}[{index}]")


def _contract_unsigned(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in contract.items() if key != "contractHash"}


def validate_v46_engineering_smoke_contract(contract: Mapping[str, Any]) -> None:
    _reject_sensitive(contract)
    if contract.get("schemaVersion") != "alphapilot_v46_engineering_smoke_contract_v1":
        raise ValueError("Unsupported V46 engineering smoke contract schema")
    exact = {
        "requestType": "engineering_smoke_only",
        "environment": "okx_demo_only",
        "instrumentId": "BTC-USDT-SWAP",
        "maximumConcurrentPositions": 1,
        "maximumOpenPositions": 1,
        "maximumOrderCount": 3,
        "noAdding": True,
        "noAveraging": True,
        "noMartingale": True,
        "strategyQualification": False,
        "formalPass": False,
        "forwardEvidenceEligible": False,
        "livePromotionEligible": False,
        "strategyReleaseApprovalAccepted": False,
        "demoArm": False,
        "liveExecutionAllowed": False,
        "withdrawAllowed": False,
    }
    for field, expected in exact.items():
        if contract.get(field) != expected:
            raise PermissionError(f"Invalid V46 engineering smoke boundary: {field}")
    instrument = contract.get("instrument")
    if not isinstance(instrument, Mapping) or set(instrument) != set(_INSTRUMENT_FIELDS):
        raise ValueError("V46 smoke requires exact BTC-USDT-SWAP metadata")
    if str(instrument.get("instId")) != "BTC-USDT-SWAP":
        raise ValueError("V46 smoke instrument mismatch")
    if str(instrument.get("state")) != "live":
        raise ValueError("V46 smoke instrument is not live")
    if str(instrument.get("instType")) != "SWAP" or str(instrument.get("settleCcy")) != "USDT":
        raise ValueError("V46 smoke requires a USDT SWAP")
    if contract.get("maximumOrderSize") != instrument.get("minSz"):
        raise ValueError("V46 smoke size must equal the exchange minimum")
    if contract.get("positionMode") != "net_mode":
        raise ValueError("V46 smoke is frozen to the observed net position mode")
    required_hashes = (
        "releaseId",
        "releaseHash",
        "riskOverlayHash",
        "executionIntersectionHash",
        "approvedRequestEvidenceHash",
        "approvalDocumentSha256",
    )
    if any(not str(contract.get(field) or "").strip() for field in required_hashes):
        raise ValueError("V46 smoke identity binding is incomplete")
    expected_hash = _sha256_bytes(_canonical(_contract_unsigned(contract)).encode("utf-8"))
    if contract.get("contractHash") != f"engineering_smoke_contract_{expected_hash}":
        raise ValueError("V46 engineering smoke contract checksum mismatch")


def build_v46_engineering_smoke_contract(
    *,
    release: Mapping[str, Any],
    risk_overlay: Mapping[str, Any],
    universe: Mapping[str, Any],
    smoke_request: Mapping[str, Any],
    approval_document_text: str,
    generated_at: str,
    instrument: Mapping[str, Any],
    account_mode: str,
    position_mode: str,
) -> dict[str, Any]:
    release_id = str(release.get("releaseId") or "")
    release_hash = str(release.get("releaseHash") or "")
    risk_hash = str(release.get("riskOverlayHash") or "")
    intersection_hash = str(release.get("executionIntersectionHash") or "")
    request_hash = str(smoke_request.get("evidenceHash") or "")
    identity_bindings = {
        release_id,
        release_hash,
        risk_hash,
        intersection_hash,
        request_hash,
        "engineering_smoke_only",
    }
    boundary_bindings = {
        "strategyQualification=false",
        "formalPass=false",
        "forwardEvidenceEligible=false",
        "livePromotionEligible=false",
    }
    approval_compact = re.sub(r"\s+", "", approval_document_text)
    missing_from_approval = [
        value
        for value in identity_bindings
        if value not in approval_document_text
    ] + [
        value
        for value in boundary_bindings
        if value not in approval_compact
    ]
    if missing_from_approval:
        raise PermissionError("Explicit V46 engineering smoke approval does not bind the exact request")
    if smoke_request.get("requestType") != "engineering_smoke_only":
        raise PermissionError("Approval request is not engineering-smoke only")
    if smoke_request.get("releaseId") != release_id or smoke_request.get("releaseHash") != release_hash:
        raise PermissionError("Engineering smoke request does not match the release")
    if smoke_request.get("riskOverlayHash") != risk_hash:
        raise PermissionError("Engineering smoke request does not match the risk overlay")
    if risk_overlay.get("riskOverlayHash") != risk_hash:
        raise PermissionError("Risk overlay hash mismatch")
    if universe.get("executionIntersectionHash") != intersection_hash:
        raise PermissionError("Execution intersection hash mismatch")
    execution_instruments = list(
        universe.get("executionInstruments")
        or universe.get("executionIntersection")
        or []
    )
    if "BTC-USDT-SWAP" not in execution_instruments:
        raise PermissionError("BTC-USDT-SWAP is outside the frozen execution intersection")
    if any(bool(release.get(field)) for field in ("approved", "demoArm", "formalPass", "livePromotionEligible")):
        raise PermissionError("Release state is incompatible with an isolated pre-approval smoke")
    for field in ("noAdding", "noAveraging", "noMartingale"):
        if risk_overlay.get(field) is not True:
            raise PermissionError(f"Risk overlay does not preserve {field}")
    if risk_overlay.get("environment") != "okx_demo_only":
        raise PermissionError("Risk overlay is not frozen to OKX Demo only")
    if risk_overlay.get("liveExecutionAllowed") is True or risk_overlay.get("withdrawAllowed") is True:
        raise PermissionError("Risk overlay crosses the approved Demo boundary")

    exact_instrument = {field: str(instrument.get(field) or "").strip() for field in _INSTRUMENT_FIELDS}
    unsigned = {
        "schemaVersion": "alphapilot_v46_engineering_smoke_contract_v1",
        "generatedAt": str(generated_at),
        "requestType": "engineering_smoke_only",
        "releaseId": release_id,
        "releaseHash": release_hash,
        "riskOverlayHash": risk_hash,
        "executionIntersectionHash": intersection_hash,
        "approvedRequestEvidenceHash": request_hash,
        "approvalDocumentSha256": _sha256_bytes(approval_document_text.encode("utf-8")),
        "environment": "okx_demo_only",
        "xSimulatedTrading": "1",
        "instrumentId": "BTC-USDT-SWAP",
        "instrument": exact_instrument,
        "accountMode": str(account_mode),
        "positionMode": str(position_mode),
        "marginMode": "isolated",
        "maximumOrderSize": exact_instrument["minSz"],
        "maximumConcurrentPositions": 1,
        "maximumOpenPositions": 1,
        "maximumOrderCount": 3,
        "pathA": "post_only_submit_query_cancel_final_canceled",
        "pathB": "minimum_fill_position_reduce_only_close_final_flat",
        "noAdding": True,
        "noAveraging": True,
        "noMartingale": True,
        "strategyQualification": False,
        "formalPass": False,
        "forwardEvidenceEligible": False,
        "livePromotionEligible": False,
        "strategyReleaseApprovalAccepted": False,
        "demoArm": False,
        "liveExecutionAllowed": False,
        "withdrawAllowed": False,
    }
    digest = _sha256_bytes(_canonical(unsigned).encode("utf-8"))
    contract = {**unsigned, "contractHash": f"engineering_smoke_contract_{digest}"}
    validate_v46_engineering_smoke_contract(contract)
    return contract


def _rows(response: Mapping[str, Any], endpoint: str) -> list[dict[str, Any]]:
    if str(response.get("code") or "") != "0":
        raise RuntimeError(f"okx_demo_request_failed:{endpoint}:{response.get('code')}")
    rows = response.get("data")
    if not isinstance(rows, list):
        raise RuntimeError(f"okx_demo_response_invalid:{endpoint}")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _accepted(response: Mapping[str, Any], endpoint: str) -> dict[str, Any]:
    rows = _rows(response, endpoint)
    if not rows:
        raise RuntimeError(f"okx_demo_response_empty:{endpoint}")
    row = rows[0]
    if str(row.get("sCode") or "0") != "0":
        raise RuntimeError(f"okx_demo_order_rejected:{endpoint}:{row.get('sCode')}")
    return row


_RESPONSE_FIELDS = {
    "ordId",
    "clOrdId",
    "state",
    "accFillSz",
    "fillSz",
    "fillPx",
    "avgPx",
    "instId",
    "pos",
    "posSide",
    "side",
    "sCode",
    "sMsg",
}


def _project_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {field: row.get(field) for field in sorted(_RESPONSE_FIELDS) if field in row}
        for row in rows
    ]


def _nonzero_positions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        try:
            quantity = Decimal(str(row.get("pos") or "0"))
        except Exception as error:
            raise RuntimeError("okx_demo_position_quantity_invalid") from error
        if quantity != 0:
            result.append(row)
    return result


def _private_state(client: Any) -> dict[str, Any]:
    return {
        "positions": _rows(client.get_positions(instrumentType="SWAP"), "positions"),
        "pendingOrders": _rows(client.get_open_orders(), "pending_orders"),
        "recentFills": _rows(client.get_fills(limit=100), "recent_fills"),
    }


def _preflight(client: Any, contract: Mapping[str, Any], *, allow_expected_position: bool) -> tuple[dict[str, Any], list[str]]:
    time_sync = client.synchronize_server_time()
    config_rows = _rows(client.get_account_config(), "account_config")
    instrument_rows = _rows(client.get_account_instruments(instrumentType="SWAP"), "account_instruments")
    _rows(client.get_balance(currency="USDT"), "balance")
    state = _private_state(client)
    config = config_rows[0] if config_rows else {}
    instrument = next(
        (row for row in instrument_rows if str(row.get("instId")) == contract["instrumentId"]),
        {},
    )
    blockers: list[str] = []
    observed_instrument = {field: str(instrument.get(field) or "").strip() for field in _INSTRUMENT_FIELDS}
    if observed_instrument != dict(contract["instrument"]):
        blockers.append("instrument_metadata_changed")
    if str(config.get("acctLv") or "") != str(contract["accountMode"]):
        blockers.append("account_mode_changed")
    if str(config.get("posMode") or "") != str(contract["positionMode"]):
        blockers.append("position_mode_changed")
    if state["pendingOrders"]:
        blockers.append("unknown_pending_order")
    positions = _nonzero_positions(state["positions"])
    unexpected_positions = [
        row for row in positions if str(row.get("instId")) != contract["instrumentId"]
    ]
    if unexpected_positions or (positions and not allow_expected_position):
        blockers.append("unknown_open_position")
    audit = {
        "schemaVersion": "alphapilot_v46_engineering_smoke_private_preflight_v1",
        "generatedAt": _now(),
        "status": "passed" if not blockers else "blocked",
        "environment": "okx_demo",
        "demoHeaderRequired": True,
        "accountSite": str(getattr(client, "site", "")),
        "serverTime": {
            "status": "verified",
            "roundTripMilliseconds": int(time_sync.get("roundTripMilliseconds") or 0),
            "offsetMilliseconds": int(time_sync.get("offsetMilliseconds") or 0),
        },
        "accountMode": str(config.get("acctLv") or ""),
        "positionMode": str(config.get("posMode") or ""),
        "instrument": observed_instrument,
        "nonzeroPositionCount": len(positions),
        "pendingOrderCount": len(state["pendingOrders"]),
        "recentFillCount": len(state["recentFills"]),
        "blockers": blockers,
        "credentialsRetained": False,
        "rawResponsesRetained": False,
        "live": False,
        "withdraw": False,
    }
    return audit, blockers


def _wait_ws(private_ws: Any, timeout_seconds: float) -> dict[str, Any]:
    private_ws.start()
    deadline = time.monotonic() + max(0.1, timeout_seconds)
    status = private_ws.status()
    while time.monotonic() < deadline:
        if status.get("authenticated") and status.get("subscribed") and not status.get("lastError"):
            break
        time.sleep(0.1)
        status = private_ws.status()
    return dict(status)


def _client_id(contract_hash: str, suffix: str) -> str:
    digest = _sha256_bytes(f"{contract_hash}:{suffix}".encode("utf-8"))[:20]
    return f"apv46{suffix}{digest}"[:32]


def _poll_order(client: Any, *, inst_id: str, client_id: str, checks: int, terminal: set[str]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for _ in range(max(1, checks)):
        rows = _rows(client.get_order(instId=inst_id, clOrdId=client_id), "order_query")
        row = rows[0] if rows else {}
        if str(row.get("state") or "") in terminal:
            return row
        time.sleep(0.15)
    return row


def _current_position(client: Any, inst_id: str) -> Decimal:
    rows = _rows(client.get_positions(instrumentId=inst_id), "positions")
    total = Decimal("0")
    for row in rows:
        if str(row.get("instId") or "") == inst_id:
            total += Decimal(str(row.get("pos") or "0"))
    return total


def _wait_position(client: Any, inst_id: str, *, flat: bool, checks: int) -> Decimal:
    value = _current_position(client, inst_id)
    for _ in range(max(1, checks)):
        if (flat and value == 0) or (not flat and value != 0):
            return value
        time.sleep(0.15)
        value = _current_position(client, inst_id)
    return value


def _cancel_all_after_with_retry(
    client: Any,
    timeout_seconds: int,
    *,
    delay_seconds: float,
    attempts: int = 3,
) -> dict[str, Any]:
    response: dict[str, Any] = {}
    for attempt in range(max(1, attempts)):
        response = dict(client.cancel_all_after(timeout_seconds))
        if str(response.get("code") or "") == "0":
            return response
        if str(response.get("code") or "") != "50011" or attempt + 1 >= attempts:
            break
        time.sleep(max(1.05, delay_seconds))
    _rows(response, f"cancel_all_after_{timeout_seconds}")
    return response


def _append_order(output: Path, *, stage: str, payload: Mapping[str, Any], exchange_row: Mapping[str, Any]) -> None:
    _append_jsonl(
        output / "engineering_smoke_order_ledger.jsonl",
        {
            "recordType": "engineering_smoke_order",
            "recordedAt": _now(),
            "stage": stage,
            "instrumentId": payload.get("instId"),
            "clientOrderId": payload.get("clOrdId"),
            "orderType": payload.get("ordType"),
            "side": payload.get("side"),
            "size": payload.get("sz"),
            "reduceOnly": bool(payload.get("reduceOnly")),
            "exchange": _project_rows([dict(exchange_row)])[0],
            "engineeringOnly": True,
            "strategyQualification": False,
            "forwardEvidenceEligible": False,
        },
    )


def _append_fill(output: Path, *, stage: str, row: Mapping[str, Any]) -> None:
    _append_jsonl(
        output / "engineering_smoke_fill_ledger.jsonl",
        {
            "recordType": "engineering_smoke_fill",
            "recordedAt": _now(),
            "stage": stage,
            "exchange": _project_rows([dict(row)])[0],
            "engineeringOnly": True,
            "strategyQualification": False,
            "forwardEvidenceEligible": False,
        },
    )


def _append_position(output: Path, *, stage: str, instrument_id: str, quantity: Decimal) -> None:
    _append_jsonl(
        output / "engineering_smoke_position_ledger.jsonl",
        {
            "recordType": "engineering_smoke_position",
            "recordedAt": _now(),
            "stage": stage,
            "instrumentId": instrument_id,
            "quantity": format(quantity, "f"),
            "engineeringOnly": True,
            "strategyQualification": False,
            "forwardEvidenceEligible": False,
        },
    )


def _write_contract_artifacts(output: Path, contract: Mapping[str, Any]) -> None:
    _atomic_write_json(output / _CONTRACT_FILE, contract)
    _atomic_write_json(
        output / "engineering_smoke_contract_hash_audit.json",
        {
            "schemaVersion": "alphapilot_v46_engineering_smoke_contract_hash_audit_v1",
            "generatedAt": _now(),
            "status": "passed",
            "releaseId": contract["releaseId"],
            "releaseHash": contract["releaseHash"],
            "riskOverlayHash": contract["riskOverlayHash"],
            "executionIntersectionHash": contract["executionIntersectionHash"],
            "approvedRequestEvidenceHash": contract["approvedRequestEvidenceHash"],
            "contractHash": contract["contractHash"],
            "exactBindingsVerified": True,
        },
    )
    _atomic_write_json(
        output / "engineering_smoke_approval_overlay.json",
        {
            "schemaVersion": "alphapilot_v46_engineering_smoke_approval_overlay_v1",
            "generatedAt": _now(),
            "status": "approved_engineering_smoke_only",
            "requestType": "engineering_smoke_only",
            "releaseId": contract["releaseId"],
            "contractHash": contract["contractHash"],
            "approvalDocumentSha256": contract["approvalDocumentSha256"],
            "approvedRequestEvidenceHash": contract["approvedRequestEvidenceHash"],
            "strategyReleaseApprovalAccepted": False,
            "demoArm": False,
            "live": False,
            "withdraw": False,
        },
    )


def _block(output: Path, blockers: list[str], *, preflight: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if preflight is not None:
        _atomic_write_json(output / "engineering_smoke_private_preflight.json", preflight)
    result = {
        "schemaVersion": "alphapilot_v46_engineering_smoke_result_v1",
        "generatedAt": _now(),
        "status": "blocked",
        "blockers": blockers,
        "orderAttemptCount": 0,
        "strategyQualification": False,
        "demoArm": False,
        "live": False,
        "withdraw": False,
    }
    _atomic_write_json(output / "engineering_smoke_final_self_check.json", result)
    return result


def _manifest(output: Path) -> dict[str, Any]:
    entries = []
    for path in sorted(output.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.name in {_CHECKPOINT_FILE, "engineering_smoke_artifact_manifest.json"}:
            continue
        entries.append({"path": path.name, "sha256": _sha256_file(path), "sizeBytes": path.stat().st_size})
    return {
        "schemaVersion": "alphapilot_v46_engineering_smoke_artifact_manifest_v1",
        "generatedAt": _now(),
        "status": "completed",
        "artifactCount": len(entries),
        "artifacts": entries,
        "credentialsRetained": False,
        "live": False,
        "withdraw": False,
    }


def run_v46_engineering_smoke_phase(
    *,
    client: Any,
    private_ws: Any,
    contract: Mapping[str, Any],
    output_dir: Path,
    phase: str,
    strategy_evidence_snapshot: Callable[[], Mapping[str, int]],
    order_status_checks: int = 20,
    private_ws_timeout_seconds: float = 8.0,
    cancel_all_after_delay_seconds: float = 1.05,
) -> dict[str, Any]:
    """Run one process phase; reruns are idempotent and reconcile before writing."""

    validate_v46_engineering_smoke_contract(contract)
    if phase not in {"path_a", "resume_path_b"}:
        raise ValueError("phase must be path_a or resume_path_b")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_contract_artifacts(output, contract)
    checkpoint_path = output / _CHECKPOINT_FILE
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8")) if checkpoint_path.is_file() else {}
    if checkpoint and checkpoint.get("contractHash") != contract["contractHash"]:
        raise PermissionError("Existing engineering smoke checkpoint belongs to another contract")
    if checkpoint.get("status") == "completed":
        return {
            "status": "completed",
            "blockers": [],
            "orderAttemptCount": int(checkpoint.get("orderAttemptCount") or 0),
            "idempotentReplay": True,
        }
    if phase == "path_a" and checkpoint.get("status") == "path_a_completed":
        return {
            "status": "path_a_completed",
            "blockers": [],
            "orderAttemptCount": int(checkpoint.get("orderAttemptCount") or 1),
            "idempotentReplay": True,
        }
    if phase == "resume_path_b" and checkpoint.get("status") != "path_a_completed":
        raise RuntimeError("Path B requires a persisted completed Path A checkpoint")

    allow_position = phase == "resume_path_b" and Decimal(str(checkpoint.get("pathAFilledSize") or "0")) > 0
    preflight, blockers = _preflight(client, contract, allow_expected_position=allow_position)
    _atomic_write_json(output / "engineering_smoke_private_preflight.json", preflight)
    if blockers:
        return _block(output, blockers, preflight=preflight)

    ws_status = _wait_ws(private_ws, private_ws_timeout_seconds)
    ws_ready = bool(ws_status.get("authenticated") and ws_status.get("subscribed") and not ws_status.get("lastError"))
    if not ws_ready:
        private_ws.stop()
        _atomic_write_json(
            output / "engineering_smoke_private_websocket_audit.json",
            {
                "schemaVersion": "alphapilot_v46_engineering_smoke_private_websocket_audit_v1",
                "generatedAt": _now(),
                "status": "blocked",
                "authenticated": bool(ws_status.get("authenticated")),
                "subscribed": bool(ws_status.get("subscribed")),
                "lastError": ws_status.get("lastError"),
                "credentialsRetained": False,
            },
        )
        return _block(output, ["private_websocket_not_ready"], preflight=preflight)

    try:
        if phase == "path_a":
            before = {key: int(value) for key, value in strategy_evidence_snapshot().items()}
            ticker_rows = _rows(client.get_ticker(contract["instrumentId"]), "ticker")
            bid = Decimal(str((ticker_rows[0] if ticker_rows else {}).get("bidPx") or "0"))
            tick = Decimal(str(contract["instrument"]["tickSz"]))
            if bid <= 0 or tick <= 0:
                return _block(output, ["public_ticker_invalid"], preflight=preflight)
            price = ((bid * Decimal("0.99")) / tick).to_integral_value(rounding=ROUND_DOWN) * tick
            path_a_id = _client_id(str(contract["contractHash"]), "A")
            payload = {
                "instId": contract["instrumentId"],
                "tdMode": contract["marginMode"],
                "side": "buy",
                "posSide": "net",
                "ordType": "post_only",
                "sz": contract["maximumOrderSize"],
                "px": format(price, "f"),
                "clOrdId": path_a_id,
                "tag": "alphapilot",
            }
            placed = _accepted(client.place_order(payload), "path_a_submit")
            _append_order(output, stage="path_a_submit", payload=payload, exchange_row=placed)
            queried = _poll_order(
                client,
                inst_id=contract["instrumentId"],
                client_id=path_a_id,
                checks=order_status_checks,
                terminal={"live", "partially_filled", "filled", "canceled"},
            )
            filled_size = Decimal(str(queried.get("accFillSz") or "0"))
            state = str(queried.get("state") or "")
            cancel_requested = state in {"live", "partially_filled"}
            if cancel_requested:
                _accepted(
                    client.cancel_order(instId=contract["instrumentId"], clOrdId=path_a_id),
                    "path_a_cancel",
                )
                queried = _poll_order(
                    client,
                    inst_id=contract["instrumentId"],
                    client_id=path_a_id,
                    checks=order_status_checks,
                    terminal={"canceled", "filled"},
                )
                state = str(queried.get("state") or "")
                filled_size = Decimal(str(queried.get("accFillSz") or filled_size))
            if state not in {"canceled", "filled"}:
                return _block(output, ["path_a_not_terminal"], preflight=preflight)
            if filled_size > 0:
                _append_fill(output, stage="path_a_fill", row=queried)
            position = _current_position(client, contract["instrumentId"])
            _append_position(output, stage="path_a_final", instrument_id=contract["instrumentId"], quantity=position)
            if filled_size == 0 and position != 0:
                return _block(output, ["path_a_unexpected_position"], preflight=preflight)
            _atomic_write_json(
                output / "engineering_smoke_cancel_audit.json",
                {
                    "schemaVersion": "alphapilot_v46_engineering_smoke_cancel_audit_v1",
                    "generatedAt": _now(),
                    "status": "passed",
                    "clientOrderId": path_a_id,
                    "cancelRequested": cancel_requested,
                    "finalOrderState": state,
                    "filledSize": format(filled_size, "f"),
                    "pathAFilledBeforeCancel": filled_size > 0,
                    "orderRequestMade": True,
                    "engineeringOnly": True,
                },
            )
            checkpoint = {
                "schemaVersion": "alphapilot_v46_engineering_smoke_checkpoint_v1",
                "contractHash": contract["contractHash"],
                "status": "path_a_completed",
                "pathAClientOrderId": path_a_id,
                "pathAFilledSize": format(filled_size, "f"),
                "strategyEvidenceBefore": before,
                "orderAttemptCount": 1,
                "updatedAt": _now(),
            }
            _atomic_write_json(checkpoint_path, checkpoint)
            _atomic_write_json(
                output / "engineering_smoke_private_websocket_audit.json",
                {
                    "schemaVersion": "alphapilot_v46_engineering_smoke_private_websocket_audit_v1",
                    "generatedAt": _now(),
                    "status": "passed",
                    "authenticated": True,
                    "subscribed": True,
                    "channels": list(ws_status.get("channels") or []),
                    "credentialsRetained": False,
                },
            )
            return {"status": "path_a_completed", "blockers": [], "orderAttemptCount": 1}

        expected_ids = {str(checkpoint["pathAClientOrderId"])}
        current_state = _private_state(client)
        unknown_pending = [
            row for row in current_state["pendingOrders"]
            if str(row.get("clOrdId") or "") not in expected_ids
        ]
        unknown_positions = [
            row for row in _nonzero_positions(current_state["positions"])
            if str(row.get("instId") or "") != contract["instrumentId"]
        ]
        if unknown_pending or unknown_positions:
            return _block(output, ["restart_reconciliation_unknown_state"], preflight=preflight)
        _atomic_write_json(
            output / "engineering_smoke_restart_recovery_audit.json",
            {
                "schemaVersion": "alphapilot_v46_engineering_smoke_restart_recovery_audit_v1",
                "generatedAt": _now(),
                "status": "passed",
                "checkpointReloaded": True,
                "priorStage": "path_a_completed",
                "duplicateOrderPrevented": True,
                "unknownOrderCount": 0,
                "orphanPositionCount": 0,
            },
        )
        _atomic_write_json(
            output / "engineering_smoke_rest_reconciliation_audit.json",
            {
                "schemaVersion": "alphapilot_v46_engineering_smoke_rest_reconciliation_audit_v1",
                "generatedAt": _now(),
                "status": "passed",
                "phase": "restart_before_path_b",
                "pendingOrderCount": len(current_state["pendingOrders"]),
                "nonzeroPositionCount": len(_nonzero_positions(current_state["positions"])),
                "unknownOrderCount": 0,
                "orphanPositionCount": 0,
            },
        )

        armed = _cancel_all_after_with_retry(
            client,
            10,
            delay_seconds=cancel_all_after_delay_seconds,
        )
        time.sleep(max(0.0, cancel_all_after_delay_seconds))
        disarmed = _cancel_all_after_with_retry(
            client,
            0,
            delay_seconds=cancel_all_after_delay_seconds,
        )
        _rows(armed, "cancel_all_after_arm")
        _rows(disarmed, "cancel_all_after_disarm")
        _atomic_write_json(
            output / "engineering_smoke_kill_switch_audit.json",
            {
                "schemaVersion": "alphapilot_v46_engineering_smoke_kill_switch_audit_v1",
                "generatedAt": _now(),
                "status": "passed",
                "cancelAllAfterArmedSeconds": 10,
                "cancelAllAfterDisarmed": True,
                "environment": "okx_demo",
            },
        )

        position = _current_position(client, contract["instrumentId"])
        open_row: dict[str, Any] | None = None
        order_attempt_count = int(checkpoint.get("orderAttemptCount") or 1)
        if position == 0:
            open_id = _client_id(str(contract["contractHash"]), "BOpen")
            open_payload = {
                "instId": contract["instrumentId"],
                "tdMode": contract["marginMode"],
                "side": "buy",
                "posSide": "net",
                "ordType": "market",
                "sz": contract["maximumOrderSize"],
                "clOrdId": open_id,
                "tag": "alphapilot",
            }
            placed = _accepted(client.place_order(open_payload), "path_b_open")
            _append_order(output, stage="path_b_open", payload=open_payload, exchange_row=placed)
            order_attempt_count += 1
            open_row = _poll_order(
                client,
                inst_id=contract["instrumentId"],
                client_id=open_id,
                checks=order_status_checks,
                terminal={"filled", "canceled"},
            )
            if str(open_row.get("state") or "") != "filled":
                return _block(output, ["path_b_open_not_filled"], preflight=preflight)
            _append_fill(output, stage="path_b_open", row=open_row)
            position = _wait_position(client, contract["instrumentId"], flat=False, checks=order_status_checks)
        if position == 0:
            return _block(output, ["path_b_position_not_observed"], preflight=preflight)
        _append_position(output, stage="path_b_open", instrument_id=contract["instrumentId"], quantity=position)

        close_id = _client_id(str(contract["contractHash"]), "BClose")
        close_payload = {
            "instId": contract["instrumentId"],
            "tdMode": contract["marginMode"],
            "side": "sell" if position > 0 else "buy",
            "posSide": "net",
            "ordType": "market",
            "sz": format(abs(position), "f"),
            "clOrdId": close_id,
            "reduceOnly": True,
            "tag": "alphapilot",
        }
        placed = _accepted(client.place_order(close_payload), "path_b_close")
        _append_order(output, stage="path_b_close", payload=close_payload, exchange_row=placed)
        order_attempt_count += 1
        close_row = _poll_order(
            client,
            inst_id=contract["instrumentId"],
            client_id=close_id,
            checks=order_status_checks,
            terminal={"filled", "canceled"},
        )
        if str(close_row.get("state") or "") != "filled":
            return _block(output, ["path_b_close_not_filled"], preflight=preflight)
        _append_fill(output, stage="path_b_close", row=close_row)
        final_position = _wait_position(client, contract["instrumentId"], flat=True, checks=order_status_checks)
        _append_position(output, stage="path_b_final", instrument_id=contract["instrumentId"], quantity=final_position)
        final_state = _private_state(client)
        final_pending = final_state["pendingOrders"]
        final_positions = _nonzero_positions(final_state["positions"])
        if final_position != 0 or final_pending or final_positions:
            return _block(output, ["final_demo_state_not_flat"], preflight=preflight)
        _atomic_write_json(
            output / "engineering_smoke_fill_close_audit.json",
            {
                "schemaVersion": "alphapilot_v46_engineering_smoke_fill_close_audit_v1",
                "generatedAt": _now(),
                "status": "passed",
                "pathAProvidedFill": Decimal(str(checkpoint.get("pathAFilledSize") or "0")) > 0,
                "separatePathBOpenSubmitted": open_row is not None,
                "actualClosedSize": close_payload["sz"],
                "reduceOnlyClose": True,
                "finalPositionSize": "0",
                "orderAttemptCount": order_attempt_count,
                "engineeringOnly": True,
            },
        )
        _atomic_write_json(
            output / "engineering_smoke_rest_reconciliation_audit.json",
            {
                "schemaVersion": "alphapilot_v46_engineering_smoke_rest_reconciliation_audit_v1",
                "generatedAt": _now(),
                "status": "passed",
                "phase": "final",
                "pendingOrderCount": 0,
                "nonzeroPositionCount": 0,
                "unknownOrderCount": 0,
                "orphanPositionCount": 0,
                "recentFillCount": len(final_state["recentFills"]),
            },
        )
        after = {key: int(value) for key, value in strategy_evidence_snapshot().items()}
        before = {key: int(value) for key, value in dict(checkpoint.get("strategyEvidenceBefore") or {}).items()}
        order_delta = int(after.get("strategyOrderCount", 0)) - int(before.get("strategyOrderCount", 0))
        closed_delta = int(after.get("strategyClosedTradeCount", 0)) - int(before.get("strategyClosedTradeCount", 0))
        isolation_passed = before == after and order_delta == 0 and closed_delta == 0
        _atomic_write_json(
            output / "engineering_smoke_strategy_evidence_isolation_audit.json",
            {
                "schemaVersion": "alphapilot_v46_engineering_smoke_strategy_evidence_isolation_audit_v1",
                "generatedAt": _now(),
                "status": "passed" if isolation_passed else "blocked",
                "before": before,
                "after": after,
                "strategyEvidenceChanged": not isolation_passed,
                "strategyOrderCountDelta": order_delta,
                "strategyClosedTradeCountDelta": closed_delta,
                "forwardEvidenceDelta": 0,
                "formalEvidenceDelta": 0,
                "engineeringOnly": True,
            },
        )
        if not isolation_passed:
            return _block(output, ["strategy_evidence_changed"], preflight=preflight)
        _atomic_write_json(
            output / "engineering_smoke_private_websocket_audit.json",
            {
                "schemaVersion": "alphapilot_v46_engineering_smoke_private_websocket_audit_v1",
                "generatedAt": _now(),
                "status": "passed",
                "authenticated": True,
                "subscribed": True,
                "channels": list(ws_status.get("channels") or []),
                "credentialsRetained": False,
            },
        )
        final_check = {
            "schemaVersion": "alphapilot_v46_engineering_smoke_final_self_check_v1",
            "generatedAt": _now(),
            "status": "passed",
            "engineeringSmokeReady": True,
            "releaseId": contract["releaseId"],
            "releaseHash": contract["releaseHash"],
            "riskOverlayHash": contract["riskOverlayHash"],
            "executionIntersectionHash": contract["executionIntersectionHash"],
            "contractHash": contract["contractHash"],
            "duplicateOrderCount": 0,
            "orphanOrderCount": 0,
            "orphanPositionCount": 0,
            "unknownStateCount": 0,
            "finalPositionCount": 0,
            "strategyOrderCount": 0,
            "strategyClosedTradeCount": 0,
            "forwardEvidenceDelta": 0,
            "formalEvidenceDelta": 0,
            "strategyReleaseApprovalAccepted": False,
            "demoArm": False,
            "live": False,
            "withdraw": False,
            "nextRoute": "blocked_waiting_exact_release_approval",
        }
        _atomic_write_json(output / "engineering_smoke_final_self_check.json", final_check)
        checkpoint = {
            **dict(checkpoint),
            "status": "completed",
            "orderAttemptCount": order_attempt_count,
            "updatedAt": _now(),
        }
        _atomic_write_json(checkpoint_path, checkpoint)
        _atomic_write_json(output / "engineering_smoke_artifact_manifest.json", _manifest(output))
        return {"status": "completed", "blockers": [], "orderAttemptCount": order_attempt_count}
    finally:
        private_ws.stop()


def strategy_evidence_snapshot(data_dir: Path) -> dict[str, int]:
    targets = (
        (data_dir / "evolution_demo_execution.sqlite", "DemoExecutionRecords", "strategyOrderCount"),
        (data_dir / "strategy_validation_demo.sqlite", "StrategyValidationClosedTrades", "strategyClosedTradeCount"),
    )
    result = {"strategyOrderCount": 0, "strategyClosedTradeCount": 0}
    for database, table, key in targets:
        if not database.is_file():
            continue
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        try:
            row = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table,),
            ).fetchone()
            if row:
                result[key] += int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        finally:
            connection.close()
    return result


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the explicitly approved V46 OKX Demo engineering smoke.")
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--risk-overlay", type=Path, required=True)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--smoke-request", type=Path, required=True)
    parser.add_argument("--approval-document", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strategy-data-dir", type=Path, required=True)
    parser.add_argument("--phase", choices=("path_a", "resume_path_b"), required=True)
    args = parser.parse_args(argv)

    bootstrap = bootstrap_demo_credentials()
    if not bootstrap.get("ok"):
        print(_canonical({"status": "blocked", "blocker": bootstrap.get("category"), "promptRequired": True}))
        return 2
    credentials = load_okx_demo_credentials()
    client = OkxDemoClient(credentials, site="global")
    contract_path = args.output / _CONTRACT_FILE
    if contract_path.is_file():
        contract = _load_json(contract_path)
        validate_v46_engineering_smoke_contract(contract)
    else:
        client.synchronize_server_time()
        config_rows = _rows(client.get_account_config(), "account_config")
        instrument_rows = _rows(client.get_account_instruments(instrumentType="SWAP"), "account_instruments")
        config = config_rows[0] if config_rows else {}
        instrument = next((row for row in instrument_rows if row.get("instId") == "BTC-USDT-SWAP"), {})
        contract = build_v46_engineering_smoke_contract(
            release=_load_json(args.release),
            risk_overlay=_load_json(args.risk_overlay),
            universe=_load_json(args.universe),
            smoke_request=_load_json(args.smoke_request),
            approval_document_text=args.approval_document.read_text(encoding="utf-8"),
            generated_at=_now(),
            instrument=instrument,
            account_mode=str(config.get("acctLv") or ""),
            position_mode=str(config.get("posMode") or ""),
        )
    result = run_v46_engineering_smoke_phase(
        client=client,
        private_ws=OkxDemoPrivateWsRuntime(credentials, site="global"),
        contract=contract,
        output_dir=args.output,
        phase=args.phase,
        strategy_evidence_snapshot=lambda: strategy_evidence_snapshot(args.strategy_data_dir),
    )
    print(_canonical(result))
    return 0 if result.get("status") in {"path_a_completed", "completed"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
