"""Idempotent point-in-time evidence storage for adaptive learning."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from .adaptive_learning_contracts import canonical_json, stable_hash
from .config import DATA_DIR


DEFAULT_ADAPTIVE_LEARNING_STORE_PATH = DATA_DIR / "adaptive_learning.sqlite"
_SENSITIVE_FRAGMENTS = (
    "apikey",
    "apisecret",
    "secretkey",
    "passphrase",
    "privatekey",
    "withdraw",
    "credential",
)


def _reject_sensitive(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).replace("_", "").replace("-", "").lower()
            if any(fragment in normalized for fragment in _SENSITIVE_FRAGMENTS):
                raise ValueError(f"adaptive_learning_sensitive_field:{path}{key}")
            _reject_sensitive(nested, f"{path}{key}.")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_sensitive(nested, f"{path}{index}.")


class AdaptiveLearningStore:
    def __init__(self, path: Path | str = DEFAULT_ADAPTIVE_LEARNING_STORE_PATH) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS AdaptiveFeatureSnapshots (
              featureSnapshotId TEXT PRIMARY KEY,
              environment TEXT NOT NULL,
              releaseId TEXT NOT NULL,
              releaseHash TEXT NOT NULL,
              strategyCandidateId TEXT NOT NULL,
              symbol TEXT NOT NULL,
              timeframe TEXT NOT NULL,
              signalAt TEXT NOT NULL,
              observedAt TEXT NOT NULL,
              availableAt TEXT NOT NULL,
              sourceEventHash TEXT NOT NULL,
              universeSnapshotHash TEXT NOT NULL,
              factorRegistryHash TEXT NOT NULL,
              featureSchemaHash TEXT NOT NULL,
              payloadJson TEXT NOT NULL,
              contentHash TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_adaptive_feature_identity
              ON AdaptiveFeatureSnapshots(environment, releaseId, symbol, timeframe, signalAt, sourceEventHash);
            CREATE TABLE IF NOT EXISTS AdaptiveModelDecisions (
              modelDecisionId TEXT PRIMARY KEY,
              featureSnapshotId TEXT NOT NULL,
              environment TEXT NOT NULL,
              modelHash TEXT NOT NULL,
              modelPolicyHash TEXT NOT NULL,
              modelMode TEXT NOT NULL,
              payloadJson TEXT NOT NULL,
              contentHash TEXT NOT NULL,
              FOREIGN KEY(featureSnapshotId) REFERENCES AdaptiveFeatureSnapshots(featureSnapshotId)
            );
            CREATE TABLE IF NOT EXISTS AdaptiveLearningSamples (
              learningSampleId TEXT PRIMARY KEY,
              sourceEnvironment TEXT NOT NULL,
              sourceEntityId TEXT NOT NULL,
              featureSnapshotId TEXT NOT NULL,
              modelDecisionId TEXT NOT NULL,
              payloadJson TEXT NOT NULL,
              contentHash TEXT NOT NULL,
              UNIQUE(sourceEnvironment, sourceEntityId),
              FOREIGN KEY(featureSnapshotId) REFERENCES AdaptiveFeatureSnapshots(featureSnapshotId),
              FOREIGN KEY(modelDecisionId) REFERENCES AdaptiveModelDecisions(modelDecisionId)
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def append_feature_snapshot(self, payload: dict[str, Any]) -> dict[str, Any]:
        _reject_sensitive(payload)
        required = (
            "environment", "releaseId", "releaseHash", "strategyCandidateId",
            "symbol", "timeframe", "signalAt", "observedAt", "availableAt",
            "sourceEventHash", "universeSnapshotHash", "factorRegistryHash",
            "featureSchemaHash",
        )
        if any(not str(payload.get(key) or "").strip() for key in required):
            raise ValueError("adaptive_feature_snapshot_required_field_missing")
        if payload["environment"] not in {"okx_demo", "live"}:
            raise ValueError("adaptive_feature_snapshot_environment_invalid")
        core = {**payload, "schemaVersion": "production_feature_snapshot_v1"}
        content_hash = stable_hash(core, prefix="feature_snapshot_content")
        identity = {
            key: core[key]
            for key in (
                "environment", "releaseId", "symbol", "timeframe", "signalAt", "sourceEventHash"
            )
        }
        snapshot_id = stable_hash(identity, prefix="feature_snapshot")
        with self._lock:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO AdaptiveFeatureSnapshots(
                      featureSnapshotId, environment, releaseId, releaseHash,
                      strategyCandidateId, symbol, timeframe, signalAt, observedAt,
                      availableAt, sourceEventHash, universeSnapshotHash,
                      factorRegistryHash, featureSchemaHash, payloadJson, contentHash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id, core["environment"], core["releaseId"], core["releaseHash"],
                        core["strategyCandidateId"], core["symbol"], core["timeframe"],
                        core["signalAt"], core["observedAt"], core["availableAt"],
                        core["sourceEventHash"], core["universeSnapshotHash"],
                        core["factorRegistryHash"], core["featureSchemaHash"],
                        canonical_json(core), content_hash,
                    ),
                )
            row = self.get_feature_snapshot(snapshot_id)
            if row["contentHash"] != content_hash:
                raise RuntimeError("adaptive_feature_snapshot_identity_reused_with_different_content")
            return row

    def append_model_decision(self, payload: dict[str, Any]) -> dict[str, Any]:
        _reject_sensitive(payload)
        feature_snapshot_id = str(payload.get("featureSnapshotId") or "")
        self.get_feature_snapshot(feature_snapshot_id)
        required = ("environment", "modelHash", "modelPolicyHash", "modelMode")
        if any(not str(payload.get(key) or "").strip() for key in required):
            raise ValueError("adaptive_model_decision_required_field_missing")
        core = {**payload, "schemaVersion": "adaptive_model_decision_v1"}
        decision_id = stable_hash(
            {
                "featureSnapshotId": feature_snapshot_id,
                "modelHash": core["modelHash"],
                "modelPolicyHash": core["modelPolicyHash"],
            },
            prefix="model_decision",
        )
        # Latency is runtime telemetry, not part of the immutable decision identity.
        # Retrying the same point-in-time observation must return the first record.
        semantic_core = {
            key: value
            for key, value in core.items()
            if key != "modelLatencyMs"
        }
        content_hash = stable_hash(semantic_core, prefix="model_decision_content")
        with self._lock:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO AdaptiveModelDecisions(
                      modelDecisionId, featureSnapshotId, environment, modelHash,
                      modelPolicyHash, modelMode, payloadJson, contentHash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        decision_id, feature_snapshot_id, core["environment"], core["modelHash"],
                        core["modelPolicyHash"], core["modelMode"], canonical_json(core), content_hash,
                    ),
                )
            row = self.get_model_decision(decision_id)
            if row["contentHash"] != content_hash:
                raise RuntimeError("adaptive_model_decision_identity_reused_with_different_content")
            return row

    def append_learning_sample(self, payload: dict[str, Any]) -> dict[str, Any]:
        _reject_sensitive(payload)
        if any(bool(payload.get(key)) for key in ("engineeringOnly", "fixture", "shadowVirtual")):
            raise PermissionError("non_strategy_outcome_cannot_enter_learning_samples")
        if payload.get("sourceEnvironment") not in {"okx_demo", "live"}:
            raise ValueError("adaptive_learning_sample_environment_invalid")
        feature_snapshot_id = str(payload.get("featureSnapshotId") or "")
        model_decision_id = str(payload.get("modelDecisionId") or "")
        self.get_feature_snapshot(feature_snapshot_id)
        self.get_model_decision(model_decision_id)
        if not str(payload.get("sourceEntityId") or ""):
            raise ValueError("adaptive_learning_sample_source_missing")
        core = {**payload, "schemaVersion": "strategy_evolution_sample_v2"}
        content_hash = stable_hash(core, prefix="learning_sample_content")
        sample_id = stable_hash(
            {
                "sourceEnvironment": core["sourceEnvironment"],
                "sourceEntityId": core["sourceEntityId"],
                "releaseHash": core.get("releaseHash"),
            },
            prefix="learning_sample",
        )
        with self._lock:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO AdaptiveLearningSamples(
                      learningSampleId, sourceEnvironment, sourceEntityId,
                      featureSnapshotId, modelDecisionId, payloadJson, contentHash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sample_id, core["sourceEnvironment"], core["sourceEntityId"],
                        feature_snapshot_id, model_decision_id, canonical_json(core), content_hash,
                    ),
                )
            row = self.get_learning_sample(sample_id)
            if row["contentHash"] != content_hash:
                raise RuntimeError("adaptive_learning_source_reused_with_different_content")
            return row

    def get_feature_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM AdaptiveFeatureSnapshots WHERE featureSnapshotId = ?", (snapshot_id,)
            ).fetchone()
        if row is None:
            raise KeyError("Adaptive feature snapshot not found")
        return self._payload_row(row, "featureSnapshotId")

    def get_model_decision(self, decision_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM AdaptiveModelDecisions WHERE modelDecisionId = ?", (decision_id,)
            ).fetchone()
        if row is None:
            raise KeyError("Adaptive model decision not found")
        return self._payload_row(row, "modelDecisionId")

    def get_learning_sample(self, sample_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM AdaptiveLearningSamples WHERE learningSampleId = ?", (sample_id,)
            ).fetchone()
        if row is None:
            raise KeyError("Adaptive learning sample not found")
        return self._payload_row(row, "learningSampleId")

    def find_observation(
        self,
        *,
        environment: str,
        release_id: str,
        symbol: str,
        signal_at: str,
    ) -> dict[str, Any]:
        with self._lock:
            row = self.connection.execute(
                """
                SELECT f.*, d.modelDecisionId, d.payloadJson AS decisionPayloadJson,
                       d.contentHash AS decisionContentHash
                FROM AdaptiveFeatureSnapshots AS f
                JOIN AdaptiveModelDecisions AS d
                  ON d.featureSnapshotId = f.featureSnapshotId
                WHERE f.environment = ? AND f.releaseId = ? AND f.symbol = ? AND f.signalAt = ?
                ORDER BY f.observedAt DESC, f.featureSnapshotId DESC
                LIMIT 1
                """,
                (environment, release_id, symbol, signal_at),
            ).fetchone()
        if row is None:
            raise KeyError("adaptive_opening_observation_not_found")
        feature = json.loads(row["payloadJson"])
        feature["featureSnapshotId"] = row["featureSnapshotId"]
        feature["contentHash"] = row["contentHash"]
        decision = json.loads(row["decisionPayloadJson"])
        decision["modelDecisionId"] = row["modelDecisionId"]
        decision["contentHash"] = row["decisionContentHash"]
        return {"featureSnapshot": feature, "modelDecision": decision}

    def projection(self) -> dict[str, Any]:
        counts = {}
        with self._lock:
            for label, table in (
                ("featureSnapshotCount", "AdaptiveFeatureSnapshots"),
                ("modelDecisionCount", "AdaptiveModelDecisions"),
                ("learningSampleCount", "AdaptiveLearningSamples"),
            ):
                counts[label] = int(self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        return {
            "schemaVersion": "adaptive_learning_projection_v1",
            **counts,
            "engineeringSamplesIncluded": False,
            "rawCredentialsPersisted": False,
        }

    @staticmethod
    def _payload_row(row: sqlite3.Row, id_field: str) -> dict[str, Any]:
        result = json.loads(row["payloadJson"])
        result[id_field] = row[id_field]
        result["contentHash"] = row["contentHash"]
        return result
