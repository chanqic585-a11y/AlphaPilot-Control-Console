"""Dedicated reconciled ledger for strategy-validation Demo evidence."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .strategy_validation_hashing import reject_sensitive_fields


DEFAULT_DEMO_DB = DATA_DIR / "strategy_validation_demo.sqlite"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class StrategyValidationDemoStore:
    def __init__(self, path: Path | str = DEFAULT_DEMO_DB):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS StrategyValidationOrderIntents (
              intentId TEXT PRIMARY KEY,
              releaseId TEXT NOT NULL,
              marketEventHash TEXT NOT NULL,
              clientOrderId TEXT NOT NULL UNIQUE,
              symbol TEXT NOT NULL,
              side TEXT NOT NULL,
              quantity REAL NOT NULL,
              currency TEXT NOT NULL,
              referencePrice REAL NOT NULL,
              stopPrice REAL NOT NULL,
              targetPrice REAL NOT NULL,
              status TEXT NOT NULL,
              createdAt TEXT NOT NULL,
              UNIQUE(releaseId, marketEventHash)
            );
            CREATE TABLE IF NOT EXISTS StrategyValidationExchangeOrders (
              exchangeOrderId TEXT PRIMARY KEY,
              clientOrderId TEXT NOT NULL UNIQUE,
              status TEXT NOT NULL,
              createdAt TEXT NOT NULL,
              FOREIGN KEY(clientOrderId) REFERENCES StrategyValidationOrderIntents(clientOrderId)
            );
            CREATE TABLE IF NOT EXISTS StrategyValidationFills (
              fillId TEXT PRIMARY KEY,
              exchangeOrderId TEXT NOT NULL,
              role TEXT NOT NULL,
              price REAL NOT NULL,
              quantity REAL NOT NULL,
              fee REAL NOT NULL,
              funding REAL NOT NULL,
              reconciled INTEGER NOT NULL,
              createdAt TEXT NOT NULL,
              FOREIGN KEY(exchangeOrderId) REFERENCES StrategyValidationExchangeOrders(exchangeOrderId)
            );
            CREATE TABLE IF NOT EXISTS StrategyValidationPositionSnapshots (
              snapshotId TEXT PRIMARY KEY,
              releaseId TEXT NOT NULL,
              symbol TEXT NOT NULL,
              quantity REAL NOT NULL,
              averagePrice REAL,
              unrealizedPnl REAL,
              currency TEXT NOT NULL,
              reconciled INTEGER NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS StrategyValidationReconciliationEvents (
              eventId TEXT PRIMARY KEY,
              releaseId TEXT,
              eventType TEXT NOT NULL,
              status TEXT NOT NULL,
              detail TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS StrategyValidationRiskEvents (
              eventId TEXT PRIMARY KEY,
              releaseId TEXT,
              eventType TEXT NOT NULL,
              detail TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS StrategyValidationClosedTrades (
              closedTradeId TEXT PRIMARY KEY,
              releaseId TEXT NOT NULL,
              marketEventHash TEXT NOT NULL,
              entryFillId TEXT NOT NULL UNIQUE,
              exitFillId TEXT NOT NULL UNIQUE,
              netPnl REAL NOT NULL,
              netR REAL NOT NULL,
              reconciliationStatus TEXT NOT NULL,
              closedAt TEXT NOT NULL,
              FOREIGN KEY(entryFillId) REFERENCES StrategyValidationFills(fillId),
              FOREIGN KEY(exitFillId) REFERENCES StrategyValidationFills(fillId)
            );
            CREATE TABLE IF NOT EXISTS StrategyValidationRuntimeCheckpoints (
              checkpointId TEXT PRIMARY KEY,
              releaseId TEXT,
              checkpointType TEXT NOT NULL,
              marketEventHash TEXT,
              createdAt TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def record_order_intent(self, **values: Any) -> dict[str, Any]:
        reject_sensitive_fields(values)
        if float(values.get("quantity") or 0) <= 0:
            raise ValueError("order intent quantity must be positive")
        for price_key in ("referencePrice", "stopPrice", "targetPrice"):
            if float(values.get(price_key) or 0) <= 0:
                raise ValueError(f"{price_key} must be positive")
        if str(values.get("side")) not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        intent_id = f"strategy_validation_intent_{uuid.uuid4().hex}"
        created_at = _now()
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO StrategyValidationOrderIntents(
                      intentId, releaseId, marketEventHash, clientOrderId, symbol,
                      side, quantity, currency, referencePrice, stopPrice,
                      targetPrice, status, createdAt
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        intent_id, values["releaseId"], values["marketEventHash"],
                        values["clientOrderId"], values["symbol"], values["side"],
                        float(values["quantity"]), values["currency"],
                        float(values["referencePrice"]), float(values["stopPrice"]),
                        float(values["targetPrice"]), "created", created_at,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("duplicate market event or client order id") from error
        return {"intentId": intent_id, "status": "created", "createdAt": created_at, **values}

    def record_exchange_order(self, *, clientOrderId: str, exchangeOrderId: str, status: str) -> dict[str, Any]:
        if not exchangeOrderId:
            raise ValueError("exchange order id is required")
        created_at = _now()
        try:
            with self.connection:
                self.connection.execute(
                    "INSERT INTO StrategyValidationExchangeOrders(exchangeOrderId, clientOrderId, status, createdAt) VALUES (?, ?, ?, ?)",
                    (exchangeOrderId, clientOrderId, status, created_at),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("duplicate or orphan exchange order") from error
        return {"clientOrderId": clientOrderId, "exchangeOrderId": exchangeOrderId, "status": status}

    def record_fill(self, **values: Any) -> dict[str, Any]:
        reject_sensitive_fields(values)
        if values.get("role") not in {"entry", "exit"}:
            raise ValueError("fill role must be entry or exit")
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO StrategyValidationFills(
                      fillId, exchangeOrderId, role, price, quantity, fee,
                      funding, reconciled, createdAt
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        values["fillId"], values["exchangeOrderId"], values["role"],
                        float(values["price"]), float(values["quantity"]),
                        float(values["fee"]), float(values["funding"]),
                        int(bool(values["reconciled"])), _now(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("duplicate or orphan fill") from error
        return dict(values)

    def record_position_snapshot(self, **values: Any) -> dict[str, Any]:
        reject_sensitive_fields(values)
        snapshot_id = str(values.get("snapshotId") or f"position_snapshot_{uuid.uuid4().hex}")
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO StrategyValidationPositionSnapshots(
                  snapshotId, releaseId, symbol, quantity, averagePrice,
                  unrealizedPnl, currency, reconciled, createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id, values["releaseId"], values["symbol"], float(values["quantity"]),
                    values.get("averagePrice"), values.get("unrealizedPnl"), values["currency"],
                    int(bool(values.get("reconciled"))), _now(),
                ),
            )
        return {**values, "snapshotId": snapshot_id}

    def record_closed_trade(self, **values: Any) -> dict[str, Any]:
        entry = self._fill(values["entryFillId"])
        exit_fill = self._fill(values["exitFillId"])
        if not entry or not exit_fill:
            raise ValueError("closed trade requires entry and exit fills")
        if entry["role"] != "entry" or exit_fill["role"] != "exit":
            raise ValueError("closed trade fill roles are invalid")
        if not entry["reconciled"] or not exit_fill["reconciled"]:
            raise ValueError("closed trade fills must be reconciled")
        closed_at = _now()
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO StrategyValidationClosedTrades(
                      closedTradeId, releaseId, marketEventHash, entryFillId,
                      exitFillId, netPnl, netR, reconciliationStatus, closedAt
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        values["closedTradeId"], values["releaseId"], values["marketEventHash"],
                        values["entryFillId"], values["exitFillId"], float(values["netPnl"]),
                        float(values["netR"]), "reconciled", closed_at,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("duplicate closed trade or reused fill") from error
        return {**values, "reconciliationStatus": "reconciled", "closedAt": closed_at}

    def has_market_event(self, release_id: str, market_event_hash: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM StrategyValidationOrderIntents WHERE releaseId = ? AND marketEventHash = ?",
            (release_id, market_event_hash),
        ).fetchone()
        return row is not None

    def list_closed_trades(self, release_id: str | None = None) -> list[dict[str, Any]]:
        if release_id:
            rows = self.connection.execute(
                "SELECT * FROM StrategyValidationClosedTrades WHERE releaseId = ? ORDER BY closedAt, rowid",
                (release_id,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM StrategyValidationClosedTrades ORDER BY closedAt, rowid"
            ).fetchall()
        return [dict(row) for row in rows]

    def summary(self) -> dict[str, Any]:
        counts = {}
        for key, table in {
            "orderIntentCount": "StrategyValidationOrderIntents",
            "exchangeOrderCount": "StrategyValidationExchangeOrders",
            "fillCount": "StrategyValidationFills",
            "positionSnapshotCount": "StrategyValidationPositionSnapshots",
            "closedTradeCount": "StrategyValidationClosedTrades",
        }.items():
            counts[key] = int(self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        return counts

    def _fill(self, fill_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM StrategyValidationFills WHERE fillId = ?", (fill_id,)
        ).fetchone()
