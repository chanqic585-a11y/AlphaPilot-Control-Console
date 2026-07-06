from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ALLOWED_STRATEGY_STATUSES, DATA_DIR, ensure_data_dir


STATE_PATH = DATA_DIR / "console_state.json"
AUDIT_PATH = DATA_DIR / "audit_log.jsonl"
MOBILE_STATUS_PATH = DATA_DIR / "mobile_control_status.json"
EXCHANGE_PROBE_PATH = DATA_DIR / "exchange_probe_results.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def write_json(path: Path, payload: Any) -> None:
    ensure_data_dir()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_state() -> dict[str, Any]:
    state = read_json(STATE_PATH, {"strategies": {}, "updatedAt": None})
    if not isinstance(state, dict):
        return {"strategies": {}, "updatedAt": None}
    if not isinstance(state.get("strategies"), dict):
        state["strategies"] = {}
    return state


def save_state(state: dict[str, Any]) -> None:
    state["updatedAt"] = now_iso()
    write_json(STATE_PATH, state)


def append_audit(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_data_dir()
    event = {
        "eventType": event_type,
        "payload": payload,
        "createdAt": now_iso(),
        "source": "alphapilot_control_console_v13_6_1",
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def list_audit(limit: int = 50) -> list[dict[str, Any]]:
    if not AUDIT_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def update_strategy_status(strategy_id: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ALLOWED_STRATEGY_STATUSES:
        raise ValueError(f"Unsupported strategy status: {status}")
    state = load_state()
    strategy_state = state["strategies"].setdefault(strategy_id, {})
    strategy_state["status"] = status
    strategy_state["note"] = note
    strategy_state["updatedAt"] = now_iso()
    save_state(state)
    append_audit(
        "strategy_status_updated",
        {"strategyId": strategy_id, "status": status, "note": note},
    )
    return strategy_state


def write_mobile_status(payload: dict[str, Any]) -> None:
    write_json(MOBILE_STATUS_PATH, payload)


def read_exchange_probe_results() -> dict[str, Any] | None:
    payload = read_json(EXCHANGE_PROBE_PATH, None)
    return payload if isinstance(payload, dict) else None


def write_exchange_probe_results(payload: dict[str, Any]) -> None:
    write_json(EXCHANGE_PROBE_PATH, payload)
    append_audit(
        "public_exchange_probe_completed",
        {
            "symbol": payload.get("symbol"),
            "timeframe": payload.get("timeframe"),
            "resultCount": len(payload.get("results") or []),
            "publicOnly": True,
        },
    )
