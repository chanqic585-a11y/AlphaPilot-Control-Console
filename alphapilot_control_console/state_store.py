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

ALLOWED_ARTIFACT_REVIEW_STATUSES = {
    "unreviewed",
    "continue_observing",
    "paper_observation",
    "paused",
    "rejected",
}

ARTIFACT_REVIEW_LABELS = {
    "unreviewed": "未复核",
    "continue_observing": "继续观察",
    "paper_observation": "进入纸面观察",
    "paused": "暂停",
    "rejected": "淘汰",
}


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
        state = {"strategies": {}, "artifactReviews": {}, "updatedAt": None}
    if not isinstance(state.get("strategies"), dict):
        state["strategies"] = {}
    if not isinstance(state.get("artifactReviews"), dict):
        state["artifactReviews"] = {}
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
        "source": "alphapilot_control_console_v13_7_6",
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


def list_artifact_reviews() -> dict[str, Any]:
    state = load_state()
    return state.get("artifactReviews", {})


def get_artifact_review(artifact_id: str) -> dict[str, Any]:
    reviews = list_artifact_reviews()
    review = reviews.get(artifact_id)
    if not isinstance(review, dict):
        return {
            "artifactId": artifact_id,
            "reviewStatus": "unreviewed",
            "reviewLabel": ARTIFACT_REVIEW_LABELS["unreviewed"],
            "reviewNote": "",
            "reviewedAt": None,
            "source": "alphapilot_control_console_v13_7_6",
        }
    status = str(review.get("reviewStatus") or "unreviewed")
    return {
        "artifactId": artifact_id,
        "reviewStatus": status if status in ALLOWED_ARTIFACT_REVIEW_STATUSES else "unreviewed",
        "reviewLabel": ARTIFACT_REVIEW_LABELS.get(status, ARTIFACT_REVIEW_LABELS["unreviewed"]),
        "reviewNote": str(review.get("reviewNote") or ""),
        "reviewedAt": review.get("reviewedAt"),
        "source": review.get("source") or "alphapilot_control_console_v13_7_6",
    }


def update_artifact_review(artifact_id: str, review_status: str, note: str = "") -> dict[str, Any]:
    if review_status not in ALLOWED_ARTIFACT_REVIEW_STATUSES:
        raise ValueError(f"Unsupported artifact review status: {review_status}")
    state = load_state()
    review = {
        "artifactId": artifact_id,
        "reviewStatus": review_status,
        "reviewLabel": ARTIFACT_REVIEW_LABELS.get(review_status, review_status),
        "reviewNote": note,
        "reviewedAt": now_iso(),
        "source": "alphapilot_control_console_v13_7_6",
    }
    state["artifactReviews"][artifact_id] = review
    save_state(state)
    append_audit(
        "strategy_artifact_review_updated",
        {"artifactId": artifact_id, "reviewStatus": review_status, "note": note},
    )
    return review


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
