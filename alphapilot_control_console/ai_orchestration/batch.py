"""Durable idempotency ledger for asynchronous provider Batch jobs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import BatchConflictError


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _payload_hash(provider: str, model_alias: str, request_hashes: list[str]) -> str:
    payload = json.dumps(
        {
            "provider": provider,
            "modelAlias": model_alias,
            "requestHashes": request_hashes,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AIBatchLedger:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS AIBatchJobs (
                batchJobId TEXT PRIMARY KEY,
                idempotencyKey TEXT NOT NULL UNIQUE,
                provider TEXT NOT NULL,
                modelAlias TEXT NOT NULL,
                requestHashesJson TEXT NOT NULL,
                payloadHash TEXT NOT NULL,
                status TEXT NOT NULL,
                providerJobId TEXT NOT NULL,
                resultArtifactHash TEXT NOT NULL,
                createdAt TEXT NOT NULL,
                updatedAt TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def _row(self, batch_job_id: str) -> sqlite3.Row:
        row = self._connection.execute(
            "SELECT * FROM AIBatchJobs WHERE batchJobId = ?", (batch_job_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown AI batch job: {batch_job_id}")
        return row

    def get(self, batch_job_id: str) -> dict[str, Any]:
        return self._project(self._row(batch_job_id))

    @staticmethod
    def _project(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "batchJobId": row["batchJobId"],
            "idempotencyKey": row["idempotencyKey"],
            "provider": row["provider"],
            "modelAlias": row["modelAlias"],
            "requestHashes": json.loads(row["requestHashesJson"]),
            "payloadHash": row["payloadHash"],
            "status": row["status"],
            "providerJobId": row["providerJobId"],
            "resultArtifactHash": row["resultArtifactHash"],
            "createdAt": row["createdAt"],
            "updatedAt": row["updatedAt"],
        }

    def register(
        self,
        *,
        idempotency_key: str,
        provider: str,
        model_alias: str,
        request_hashes: list[str],
    ) -> dict[str, Any]:
        if not idempotency_key.strip():
            raise ValueError("AI batch idempotency key is required")
        if not request_hashes:
            raise ValueError("AI batch requires at least one request hash")
        payload_hash = _payload_hash(provider, model_alias, request_hashes)
        existing = self._connection.execute(
            "SELECT * FROM AIBatchJobs WHERE idempotencyKey = ?", (idempotency_key,)
        ).fetchone()
        if existing is not None:
            if existing["payloadHash"] != payload_hash:
                raise BatchConflictError(
                    f"AI batch idempotency key already binds a different payload: {idempotency_key}"
                )
            return self._project(existing)
        now = _utc_now()
        batch_job_id = "ai-batch-" + uuid.uuid4().hex
        self._connection.execute(
            """
            INSERT INTO AIBatchJobs (
                batchJobId, idempotencyKey, provider, modelAlias,
                requestHashesJson, payloadHash, status, providerJobId,
                resultArtifactHash, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, 'registered', '', '', ?, ?)
            """,
            (
                batch_job_id,
                idempotency_key,
                provider,
                model_alias,
                json.dumps(request_hashes, separators=(",", ":")),
                payload_hash,
                now,
                now,
            ),
        )
        self._connection.commit()
        return self._project(self._row(batch_job_id))

    def mark_submitted(self, batch_job_id: str, provider_job_id: str) -> dict[str, Any]:
        if not provider_job_id.strip():
            raise ValueError("provider batch job identity is required")
        current = self._row(batch_job_id)
        if current["providerJobId"] and current["providerJobId"] != provider_job_id:
            raise BatchConflictError("AI batch job is already bound to another provider job")
        self._connection.execute(
            """
            UPDATE AIBatchJobs
            SET status = 'submitted', providerJobId = ?, updatedAt = ?
            WHERE batchJobId = ?
            """,
            (provider_job_id, _utc_now(), batch_job_id),
        )
        self._connection.commit()
        return self._project(self._row(batch_job_id))

    def mark_completed(self, batch_job_id: str, result_artifact_hash: str) -> dict[str, Any]:
        current = self._row(batch_job_id)
        if not current["providerJobId"]:
            raise BatchConflictError("AI batch must be submitted before completion")
        if not result_artifact_hash.startswith("sha256:"):
            raise ValueError("AI batch result must use a sha256 artifact hash")
        self._connection.execute(
            """
            UPDATE AIBatchJobs
            SET status = 'completed', resultArtifactHash = ?, updatedAt = ?
            WHERE batchJobId = ?
            """,
            (result_artifact_hash, _utc_now(), batch_job_id),
        )
        self._connection.commit()
        return self._project(self._row(batch_job_id))

    def projection(self) -> dict[str, Any]:
        rows = self._connection.execute("SELECT * FROM AIBatchJobs ORDER BY createdAt").fetchall()
        counts = Counter(str(row["status"]) for row in rows)
        return {
            "schemaVersion": "alphapilot_ai_batch_projection_v1",
            "jobCount": len(rows),
            "statusCounts": dict(sorted(counts.items())),
            "jobs": [self._project(row) for row in rows],
        }

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "AIBatchLedger":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
