from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DemoReleaseClassificationStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS DemoReleaseClassifications (
              releaseId TEXT NOT NULL,
              releaseHash TEXT NOT NULL,
              releasePurpose TEXT NOT NULL,
              strategyQualification INTEGER NOT NULL,
              promotionEligible INTEGER NOT NULL,
              forwardPerformanceEligible INTEGER NOT NULL,
              demoPerformanceEligible INTEGER NOT NULL,
              classifiedAt TEXT NOT NULL,
              classificationReason TEXT NOT NULL,
              PRIMARY KEY (releaseId, releaseHash)
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_demo_release_classification_id "
            "ON DemoReleaseClassifications(releaseId, classifiedAt DESC)"
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def classify_legacy_diagnostic(
        self,
        *,
        release_id: str,
        release_hash: str,
        reason: str,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        self.connection.execute(
            """
            INSERT INTO DemoReleaseClassifications (
              releaseId, releaseHash, releasePurpose, strategyQualification,
              promotionEligible, forwardPerformanceEligible, demoPerformanceEligible,
              classifiedAt, classificationReason
            ) VALUES (?, ?, 'legacy_diagnostic', 0, 0, 0, 0, ?, ?)
            ON CONFLICT(releaseId, releaseHash) DO NOTHING
            """,
            (release_id, release_hash, now, reason),
        )
        self.connection.commit()
        row = self.get(release_id, release_hash)
        if row is None:  # pragma: no cover - defensive invariant
            raise RuntimeError("release_classification_write_failed")
        return row

    def get(self, release_id: str, release_hash: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM DemoReleaseClassifications WHERE releaseId = ? AND releaseHash = ?",
            (release_id, release_hash),
        ).fetchone()
        return self._row(row) if row is not None else None

    def get_latest(self, release_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT * FROM DemoReleaseClassifications
            WHERE releaseId = ? ORDER BY classifiedAt DESC LIMIT 1
            """,
            (release_id,),
        ).fetchone()
        return self._row(row) if row is not None else None

    def list_all(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM DemoReleaseClassifications ORDER BY classifiedAt, releaseId"
        ).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        for key in (
            "strategyQualification",
            "promotionEligible",
            "forwardPerformanceEligible",
            "demoPerformanceEligible",
        ):
            payload[key] = bool(payload[key])
        return json.loads(json.dumps(payload, ensure_ascii=False))
