"""Explicitly isolate the OKX Live environment and its private read-only audit."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from .config import PROJECT_ROOT
from .credential_runtime import live_runtime_credential_status, load_okx_live_credentials
from .exchange_connectors.okx_live_client import OkxLiveClient


V57_EVIDENCE_ROOT = PROJECT_ROOT / "reports" / "v54_v60" / "v57_live_core"
LIVE_ENVIRONMENT_CONTRACT_PATH = V57_EVIDENCE_ROOT / "live_environment_contract.json"
LIVE_PRIVATE_READ_AUDIT_PATH = V57_EVIDENCE_ROOT / "live_private_read_audit.json"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _flag(source: Mapping[str, str], name: str) -> bool:
    return str(source.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def build_live_environment_contract(
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    source = os.environ if environment is None else environment
    credentials = live_runtime_credential_status(source)
    gates = {
        "masterEnabled": _flag(source, "ALPHAPILOT_OKX_LIVE_ENABLED"),
        "readEnabled": _flag(source, "ALPHAPILOT_OKX_LIVE_READ_ENABLED"),
        "canaryEnabled": _flag(source, "ALPHAPILOT_OKX_LIVE_CANARY_ENABLED"),
        "orderEnabled": _flag(source, "ALPHAPILOT_OKX_LIVE_ORDER_ENABLED"),
        "automationEnabled": _flag(source, "ALPHAPILOT_OKX_LIVE_AUTOMATION_ENABLED"),
    }
    write_gates_disabled = not any(
        gates[key] for key in ("canaryEnabled", "orderEnabled", "automationEnabled")
    )
    if not credentials["allConfigured"]:
        status = "not_run_live_credentials_absent"
    elif not gates["masterEnabled"] or not gates["readEnabled"]:
        status = "not_run_live_read_gate_disabled"
    elif not write_gates_disabled:
        status = "blocked_readonly_boundary_not_isolated"
    else:
        status = "ready_for_private_read_audit"
    core = {
        "schemaVersion": "alphapilot_live_environment_contract_v1",
        "environment": "okx_live",
        "exchange": "okx",
        "accountMode": "live",
        "status": status,
        "site": str(source.get("ALPHAPILOT_OKX_SITE", "global") or "global").strip().lower(),
        "runtimeGates": gates,
        "credentialStatus": credentials,
        "credentialEnvironmentPrefix": "ALPHAPILOT_OKX_LIVE_",
        "demoCredentialFallbackAllowed": False,
        "simulatedTradingHeaderAllowed": False,
        "rawCredentialStorageAllowed": False,
        "privateAccountValuesPersisted": False,
        "readOnlyEndpoints": list(OkxLiveClient.read_only_endpoint_paths()),
        "orderSubmissionAllowed": False,
        "automationAllowed": False,
        "withdrawAllowed": False,
        "transferAllowed": False,
        "exactLiveReleaseApprovalRequired": True,
        "exactLiveArmRequired": True,
    }
    contract_hash = hashlib.sha256(
        json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {**core, "contractHash": f"live_environment_contract_{contract_hash}"}


def build_live_private_read_audit_status(
    path: Path | str = LIVE_PRIVATE_READ_AUDIT_PATH,
) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        return {
            "schemaVersion": "alphapilot_live_private_read_audit_v1",
            "status": "not_run",
            "reason": "private_read_audit_not_run",
            "liveOrdersCreated": 0,
            "withdrawAllowed": False,
        }
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Live private read audit must be a JSON object")
    return payload


def run_live_private_read_audit(
    *,
    environment: Mapping[str, str] | None = None,
    client: Any | None = None,
    output_path: Path | str | None = None,
) -> dict[str, Any]:
    source = os.environ if environment is None else environment
    contract = build_live_environment_contract(source)
    status = str(contract["status"])
    if status != "ready_for_private_read_audit":
        if status == "not_run_live_credentials_absent":
            result_status, reason = "not_run", "live_runtime_credentials_missing"
        elif status == "not_run_live_read_gate_disabled":
            result_status, reason = "not_run", "live_read_gate_disabled"
        else:
            result_status, reason = "blocked", "live_readonly_boundary_not_isolated"
        result = {
            "schemaVersion": "alphapilot_live_private_read_audit_v1",
            "generatedAt": _now(),
            "status": result_status,
            "reason": reason,
            "contractHash": contract["contractHash"],
            "readOnly": True,
            "liveOrdersCreated": 0,
            "privateAccountValuesPersisted": False,
            "withdrawAllowed": False,
        }
    else:
        live_client = client or OkxLiveClient(
            load_okx_live_credentials(source),
            site=str(source.get("ALPHAPILOT_OKX_SITE", "global") or "global"),
        )
        responses = {
            "accountConfig": live_client.get_account_config(),
            "balance": live_client.get_balance("USDT"),
            "positions": live_client.get_positions(),
            "openOrders": live_client.get_open_orders(),
        }
        endpoint_codes = {key: str(value.get("code") or "") for key, value in responses.items()}
        positions = responses["positions"].get("data")
        open_orders = responses["openOrders"].get("data")
        passed = all(code == "0" for code in endpoint_codes.values())
        result = {
            "schemaVersion": "alphapilot_live_private_read_audit_v1",
            "generatedAt": _now(),
            "status": "completed" if passed else "blocked",
            "reason": None if passed else "live_private_endpoint_error",
            "contractHash": contract["contractHash"],
            "readOnly": True,
            "endpointCodes": endpoint_codes,
            "positionCount": len(positions) if isinstance(positions, list) else 0,
            "openOrderCount": len(open_orders) if isinstance(open_orders, list) else 0,
            "liveOrdersCreated": 0,
            "privateAccountValuesPersisted": False,
            "withdrawAllowed": False,
        }
    if output_path is not None:
        _write_json_atomic(Path(output_path), result)
    return result


def write_live_environment_contract(
    path: Path | str = LIVE_ENVIRONMENT_CONTRACT_PATH,
    *,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    contract = build_live_environment_contract(environment)
    _write_json_atomic(Path(path), contract)
    return contract
