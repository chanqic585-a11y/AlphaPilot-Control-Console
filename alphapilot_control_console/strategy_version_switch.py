"""Append-only strategy version routing without mutating open positions."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DATA_DIR


STRATEGY_VERSION_SWITCH_PATH = DATA_DIR / "strategy_version_switch.sqlite"
SWITCH_MODES = {"new_entries_only", "flatten_then_switch", "manual_position_migration"}
CONTROL_ACTIONS = {"pause_new_entries", "resume_new_entries", "close_only"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _identity(value: Any, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


class StrategyVersionSwitchStore:
    def __init__(self, path: Path | str = STRATEGY_VERSION_SWITCH_PATH):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS StrategyVersionSwitchEvents (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              eventId TEXT NOT NULL UNIQUE,
              strategyId TEXT NOT NULL,
              action TEXT NOT NULL,
              actor TEXT NOT NULL,
              reason TEXT NOT NULL,
              stateJson TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_strategy_switch_strategy
              ON StrategyVersionSwitchEvents(strategyId, sequence);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def register(
        self,
        *,
        strategy_id: str,
        release_id: str,
        release_hash: str,
        actor: str,
    ) -> dict[str, Any]:
        strategy = _identity(strategy_id, "strategy_id")
        existing = self.get_state(strategy)
        if existing:
            if (
                existing["newEntryReleaseId"] != release_id
                or existing["newEntryReleaseHash"] != release_hash
            ):
                raise ValueError("Strategy is already registered with another release")
            return existing
        state = {
            "strategyId": strategy,
            "newEntryReleaseId": _identity(release_id, "release_id"),
            "newEntryReleaseHash": _identity(release_hash, "release_hash"),
            "openPositionBindings": [],
            "allowNewEntries": True,
            "closeOnly": False,
            "status": "active",
            "switchMode": "new_entries_only",
            "pendingTarget": None,
            "executionEnabled": False,
        }
        return self._append(strategy, "registered", actor, "initial_registration", state)

    def switch_version(
        self,
        *,
        strategy_id: str,
        release_id: str,
        release_hash: str,
        mode: str,
        open_position_bindings: list[dict[str, Any]],
        actor: str,
        reason: str,
        confirmation: str = "",
    ) -> dict[str, Any]:
        strategy = _identity(strategy_id, "strategy_id")
        current = self._require_state(strategy)
        target_id = _identity(release_id, "release_id")
        target_hash = _identity(release_hash, "release_hash")
        if mode not in SWITCH_MODES:
            raise ValueError("Unsupported strategy switch mode")
        bindings = json.loads(json.dumps(open_position_bindings or []))
        state = {**current, "openPositionBindings": bindings, "switchMode": mode}

        if mode == "flatten_then_switch" and bindings:
            state.update({
                "allowNewEntries": False,
                "closeOnly": True,
                "status": "pending_flatten",
                "pendingTarget": {"releaseId": target_id, "releaseHash": target_hash},
                "executionEnabled": False,
            })
            return self._append(strategy, "switch_pending_flatten", actor, reason, state)
        if mode == "manual_position_migration":
            expected = "MIGRATE_STRATEGY_POSITIONS:" + target_hash
            if actor != "user_manual" or confirmation != expected:
                raise PermissionError("Exact manual position migration confirmation is required")
            bindings = [
                {**binding, "releaseId": target_id, "releaseHash": target_hash,
                 "manualMigrationAudited": True}
                for binding in bindings
            ]
        state.update({
            "newEntryReleaseId": target_id,
            "newEntryReleaseHash": target_hash,
            "openPositionBindings": bindings,
            "allowNewEntries": True,
            "closeOnly": False,
            "status": "active",
            "pendingTarget": None,
            "executionEnabled": False,
        })
        return self._append(strategy, "version_switched", actor, reason, state)

    def control(self, strategy_id: str, *, action: str, actor: str) -> dict[str, Any]:
        strategy = _identity(strategy_id, "strategy_id")
        if action not in CONTROL_ACTIONS:
            raise ValueError("Unsupported strategy control action")
        state = self._require_state(strategy)
        if action == "pause_new_entries":
            state.update({"allowNewEntries": False, "closeOnly": False, "status": "paused"})
        elif action == "close_only":
            state.update({"allowNewEntries": False, "closeOnly": True, "status": "close_only"})
        else:
            state.update({"allowNewEntries": True, "closeOnly": False, "status": "active"})
        state["executionEnabled"] = False
        return self._append(strategy, action, actor, action, state)

    def rollback(
        self,
        strategy_id: str,
        *,
        open_position_bindings: list[dict[str, Any]],
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        strategy = _identity(strategy_id, "strategy_id")
        current = self._require_state(strategy)
        previous = next(
            (
                event for event in reversed(self.list_events(strategy)[:-1])
                if event["newEntryReleaseHash"] != current["newEntryReleaseHash"]
            ),
            None,
        )
        if not previous:
            raise ValueError("No previous strategy release is available")
        state = {
            **current,
            "newEntryReleaseId": previous["newEntryReleaseId"],
            "newEntryReleaseHash": previous["newEntryReleaseHash"],
            "openPositionBindings": json.loads(json.dumps(open_position_bindings or [])),
            "allowNewEntries": True,
            "closeOnly": False,
            "status": "active",
            "switchMode": "new_entries_only",
            "pendingTarget": None,
            "executionEnabled": False,
        }
        return self._append(strategy, "rolled_back", actor, reason, state)

    def get_state(self, strategy_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT * FROM StrategyVersionSwitchEvents
            WHERE strategyId = ? ORDER BY sequence DESC LIMIT 1
            """,
            (strategy_id,),
        ).fetchone()
        return self._event_row(row) if row else None

    def list_events(self, strategy_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM StrategyVersionSwitchEvents"
        values: tuple[str, ...] = ()
        if strategy_id:
            query += " WHERE strategyId = ?"
            values = (strategy_id,)
        query += " ORDER BY sequence"
        return [self._event_row(row) for row in self.connection.execute(query, values)]

    def _require_state(self, strategy_id: str) -> dict[str, Any]:
        state = self.get_state(strategy_id)
        if not state:
            raise KeyError("Strategy version routing is not registered")
        return state

    def _append(
        self,
        strategy_id: str,
        action: str,
        actor: str,
        reason: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        now = _now()
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO StrategyVersionSwitchEvents(
                  eventId, strategyId, action, actor, reason, stateJson, createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "strategy_switch_event_" + uuid.uuid4().hex,
                    strategy_id,
                    action,
                    str(actor or "unknown"),
                    str(reason or action),
                    json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    now,
                ),
            )
        result = {**state, "sequence": int(cursor.lastrowid), "action": action, "createdAt": now}
        return result

    @staticmethod
    def _event_row(row: sqlite3.Row) -> dict[str, Any]:
        state = json.loads(row["stateJson"])
        return {
            **state,
            "sequence": int(row["sequence"]),
            "eventId": row["eventId"],
            "action": row["action"],
            "actor": row["actor"],
            "reason": row["reason"],
            "createdAt": row["createdAt"],
        }


def build_strategy_version_switch_status(
    path: Path | str = STRATEGY_VERSION_SWITCH_PATH,
) -> dict[str, Any]:
    store = StrategyVersionSwitchStore(path)
    try:
        events = store.list_events()
        strategy_ids = sorted({event["strategyId"] for event in events})
        states = [store.get_state(strategy_id) for strategy_id in strategy_ids]
    finally:
        store.close()
    return {
        "schemaVersion": "strategy_version_switch_status_v1",
        "strategies": [state for state in states if state],
        "recentEvents": events[-50:],
        "executionEnabled": False,
        "safetyBoundary": {
            "switchEnablesExecution": False,
            "defaultMode": "new_entries_only",
            "runningPositionsKeepOpeningRelease": True,
            "manualMigrationRequiresExactConfirmation": True,
        },
    }


def run_strategy_version_switch_action(payload: dict[str, Any]) -> dict[str, Any]:
    store = StrategyVersionSwitchStore(STRATEGY_VERSION_SWITCH_PATH)
    try:
        action = str(payload.get("action") or "")
        strategy_id = str(payload.get("strategyId") or "")
        if action == "register":
            result = store.register(
                strategy_id=strategy_id,
                release_id=str(payload.get("releaseId") or ""),
                release_hash=str(payload.get("releaseHash") or ""),
                actor=str(payload.get("actor") or ""),
            )
        elif action == "switch":
            result = store.switch_version(
                strategy_id=strategy_id,
                release_id=str(payload.get("releaseId") or ""),
                release_hash=str(payload.get("releaseHash") or ""),
                mode=str(payload.get("mode") or "new_entries_only"),
                open_position_bindings=(
                    payload.get("openPositionBindings")
                    if isinstance(payload.get("openPositionBindings"), list)
                    else []
                ),
                actor=str(payload.get("actor") or ""),
                reason=str(payload.get("reason") or "strategy_version_switch"),
                confirmation=str(payload.get("confirmation") or ""),
            )
        elif action in CONTROL_ACTIONS:
            result = store.control(
                strategy_id,
                action=action,
                actor=str(payload.get("actor") or ""),
            )
        elif action == "rollback":
            result = store.rollback(
                strategy_id,
                open_position_bindings=(
                    payload.get("openPositionBindings")
                    if isinstance(payload.get("openPositionBindings"), list)
                    else []
                ),
                actor=str(payload.get("actor") or ""),
                reason=str(payload.get("reason") or "strategy_version_rollback"),
            )
        else:
            raise ValueError("Unsupported strategy version switch action")
    finally:
        store.close()
    return {
        "ok": True,
        "result": result,
        "status": build_strategy_version_switch_status(STRATEGY_VERSION_SWITCH_PATH),
    }
