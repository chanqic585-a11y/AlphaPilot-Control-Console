"""Redacted, append-only audit metadata for AI research calls."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class AIAuditLedger:
    """Persist hashes and operational metadata, never prompts or model output."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS AIOrchestrationAuditEvents (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                occurredAt TEXT NOT NULL,
                requestId TEXT NOT NULL,
                taskType TEXT NOT NULL,
                status TEXT NOT NULL,
                routeMode TEXT NOT NULL,
                inputHash TEXT NOT NULL,
                responseHashesJson TEXT NOT NULL,
                reasoningContentHashesJson TEXT NOT NULL DEFAULT '[]',
                providerAliasesJson TEXT NOT NULL,
                modelAliasesJson TEXT NOT NULL,
                registryHash TEXT NOT NULL,
                promptVersion TEXT NOT NULL,
                promptRegistryHash TEXT NOT NULL DEFAULT '',
                promptContentHash TEXT NOT NULL DEFAULT '',
                schemaValidationStatus TEXT NOT NULL DEFAULT 'not_run',
                semanticValidationStatus TEXT NOT NULL DEFAULT 'not_run',
                artifactHashesJson TEXT NOT NULL,
                redactionCount INTEGER NOT NULL,
                disagreementFieldsJson TEXT NOT NULL,
                totalInputTokens INTEGER NOT NULL,
                totalOutputTokens INTEGER NOT NULL,
                totalTokens INTEGER NOT NULL,
                estimatedCostUsd REAL NOT NULL,
                latencyMs INTEGER NOT NULL,
                errorType TEXT NOT NULL
            )
            """
        )
        existing_columns = {
            str(row[1])
            for row in self._connection.execute(
                "PRAGMA table_info(AIOrchestrationAuditEvents)"
            ).fetchall()
        }
        for name, definition in (
            ("promptRegistryHash", "TEXT NOT NULL DEFAULT ''"),
            ("promptContentHash", "TEXT NOT NULL DEFAULT ''"),
            ("reasoningContentHashesJson", "TEXT NOT NULL DEFAULT '[]'"),
            ("schemaValidationStatus", "TEXT NOT NULL DEFAULT 'not_run'"),
            ("semanticValidationStatus", "TEXT NOT NULL DEFAULT 'not_run'"),
        ):
            if name not in existing_columns:
                self._connection.execute(
                    f"ALTER TABLE AIOrchestrationAuditEvents ADD COLUMN {name} {definition}"
                )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_audit_request ON AIOrchestrationAuditEvents(requestId)"
        )
        self._connection.commit()

    def record(self, event: Mapping[str, Any]) -> int:
        fields = {
            "occurredAt": str(event.get("occurredAt") or _utc_now()),
            "requestId": str(event.get("requestId") or ""),
            "taskType": str(event.get("taskType") or ""),
            "status": str(event.get("status") or "unknown"),
            "routeMode": str(event.get("routeMode") or "unknown"),
            "inputHash": str(event.get("inputHash") or ""),
            "responseHashesJson": json.dumps(event.get("responseHashes") or [], separators=(",", ":")),
            "reasoningContentHashesJson": json.dumps(
                event.get("reasoningContentHashes") or [], separators=(",", ":")
            ),
            "providerAliasesJson": json.dumps(event.get("providers") or [], separators=(",", ":")),
            "modelAliasesJson": json.dumps(event.get("modelAliases") or [], separators=(",", ":")),
            "registryHash": str(event.get("registryHash") or ""),
            "promptVersion": str(event.get("promptVersion") or ""),
            "promptRegistryHash": str(event.get("promptRegistryHash") or ""),
            "promptContentHash": str(event.get("promptContentHash") or ""),
            "schemaValidationStatus": str(
                event.get("schemaValidationStatus") or "not_run"
            ),
            "semanticValidationStatus": str(
                event.get("semanticValidationStatus") or "not_run"
            ),
            "artifactHashesJson": json.dumps(event.get("artifactHashes") or [], separators=(",", ":")),
            "redactionCount": int(event.get("redactionCount") or 0),
            "disagreementFieldsJson": json.dumps(
                event.get("disagreements") or [], separators=(",", ":")
            ),
            "totalInputTokens": int(event.get("totalInputTokens") or 0),
            "totalOutputTokens": int(event.get("totalOutputTokens") or 0),
            "totalTokens": int(event.get("totalTokens") or 0),
            "estimatedCostUsd": float(event.get("estimatedCostUsd") or 0.0),
            "latencyMs": int(event.get("latencyMs") or 0),
            "errorType": str(event.get("errorType") or ""),
        }
        cursor = self._connection.execute(
            """
            INSERT INTO AIOrchestrationAuditEvents (
                occurredAt, requestId, taskType, status, routeMode, inputHash,
                responseHashesJson, reasoningContentHashesJson,
                providerAliasesJson, modelAliasesJson,
                registryHash, promptVersion, artifactHashesJson, redactionCount,
                promptRegistryHash, promptContentHash, schemaValidationStatus,
                semanticValidationStatus,
                disagreementFieldsJson, totalInputTokens, totalOutputTokens,
                totalTokens, estimatedCostUsd, latencyMs, errorType
            ) VALUES (
                :occurredAt, :requestId, :taskType, :status, :routeMode, :inputHash,
                :responseHashesJson, :reasoningContentHashesJson,
                :providerAliasesJson, :modelAliasesJson,
                :registryHash, :promptVersion, :artifactHashesJson, :redactionCount,
                :promptRegistryHash, :promptContentHash, :schemaValidationStatus,
                :semanticValidationStatus,
                :disagreementFieldsJson, :totalInputTokens, :totalOutputTokens,
                :totalTokens, :estimatedCostUsd, :latencyMs, :errorType
            )
            """,
            fields,
        )
        self._connection.commit()
        return int(cursor.lastrowid)

    def projection(self) -> dict[str, Any]:
        rows = self._connection.execute(
            """
            SELECT sequence, occurredAt, requestId, taskType, status, routeMode,
                   inputHash, responseHashesJson, providerAliasesJson,
                   reasoningContentHashesJson,
                   modelAliasesJson, registryHash, promptVersion,
                   promptRegistryHash, promptContentHash,
                   schemaValidationStatus, semanticValidationStatus,
                   artifactHashesJson, redactionCount, disagreementFieldsJson,
                   totalInputTokens, totalOutputTokens, totalTokens,
                   estimatedCostUsd, latencyMs, errorType
            FROM AIOrchestrationAuditEvents
            ORDER BY sequence
            """
        ).fetchall()
        status_counts = Counter(str(row["status"]) for row in rows)
        return {
            "schemaVersion": "alphapilot_ai_audit_projection_v1",
            "eventCount": len(rows),
            "statusCounts": dict(sorted(status_counts.items())),
            "events": [
                {
                    "sequence": int(row["sequence"]),
                    "occurredAt": row["occurredAt"],
                    "requestId": row["requestId"],
                    "taskType": row["taskType"],
                    "status": row["status"],
                    "routeMode": row["routeMode"],
                    "inputHash": row["inputHash"],
                    "responseHashes": json.loads(row["responseHashesJson"]),
                    "reasoningContentHashes": json.loads(
                        row["reasoningContentHashesJson"]
                    ),
                    "providers": json.loads(row["providerAliasesJson"]),
                    "modelAliases": json.loads(row["modelAliasesJson"]),
                    "registryHash": row["registryHash"],
                    "promptVersion": row["promptVersion"],
                    "promptRegistryHash": row["promptRegistryHash"],
                    "promptContentHash": row["promptContentHash"],
                    "schemaValidationStatus": row["schemaValidationStatus"],
                    "semanticValidationStatus": row["semanticValidationStatus"],
                    "artifactHashes": json.loads(row["artifactHashesJson"]),
                    "redactionCount": int(row["redactionCount"]),
                    "disagreements": json.loads(row["disagreementFieldsJson"]),
                    "usage": {
                        "inputTokens": int(row["totalInputTokens"]),
                        "outputTokens": int(row["totalOutputTokens"]),
                        "totalTokens": int(row["totalTokens"]),
                        "estimatedCostUsd": float(row["estimatedCostUsd"]),
                    },
                    "latencyMs": int(row["latencyMs"]),
                    "errorType": row["errorType"],
                }
                for row in rows
            ],
        }

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "AIAuditLedger":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
