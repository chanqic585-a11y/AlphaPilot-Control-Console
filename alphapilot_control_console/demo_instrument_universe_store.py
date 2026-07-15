"""Sanitized cache for the authenticated OKX Demo instrument intersection."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _parse_datetime(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class DemoInstrumentUniverseStore:
    """Persist a compact projection; raw authenticated responses never enter SQLite."""

    def __init__(self, path: Path | str):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS DemoInstrumentUniverseCache (
              environment TEXT NOT NULL,
              publicManifestHash TEXT NOT NULL,
              authenticatedInstrumentHash TEXT NOT NULL,
              projectionJson TEXT NOT NULL,
              generatedAt TEXT NOT NULL,
              cacheTtlSeconds INTEGER NOT NULL,
              PRIMARY KEY(environment, publicManifestHash, authenticatedInstrumentHash)
            );
            CREATE INDEX IF NOT EXISTS idx_demo_instrument_universe_latest
              ON DemoInstrumentUniverseCache(environment, generatedAt DESC);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def save(self, projection: dict[str, Any]) -> None:
        environment = str(projection.get("environment") or "")
        public_hash = str(projection.get("publicManifestHash") or "")
        authenticated_hash = str(projection.get("authenticatedInstrumentHash") or "")
        generated_at = str(projection.get("generatedAt") or "")
        if not all((environment, public_hash, authenticated_hash, generated_at)):
            raise ValueError("Demo universe cache identity is incomplete")
        serialized = json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO DemoInstrumentUniverseCache(
                  environment, publicManifestHash, authenticatedInstrumentHash,
                  projectionJson, generatedAt, cacheTtlSeconds
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(environment, publicManifestHash, authenticatedInstrumentHash)
                DO UPDATE SET projectionJson=excluded.projectionJson,
                              generatedAt=excluded.generatedAt,
                              cacheTtlSeconds=excluded.cacheTtlSeconds
                """,
                (
                    environment,
                    public_hash,
                    authenticated_hash,
                    serialized,
                    generated_at,
                    int(projection.get("cacheTtlSeconds") or 0),
                ),
            )

    def load_latest(self, *, environment: str, now: datetime | None = None) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT projectionJson, generatedAt, cacheTtlSeconds
            FROM DemoInstrumentUniverseCache
            WHERE environment = ?
            ORDER BY generatedAt DESC
            LIMIT 1
            """,
            (environment,),
        ).fetchone()
        if row is None:
            return None
        generated_at = _parse_datetime(row["generatedAt"])
        current = now or datetime.now(UTC)
        if generated_at is None:
            return None
        age = max(0.0, (current - generated_at).total_seconds())
        if age > int(row["cacheTtlSeconds"]):
            return None
        projection = json.loads(row["projectionJson"])
        projection["cacheAgeSeconds"] = age
        projection["cached"] = True
        projection["stale"] = False
        return projection
