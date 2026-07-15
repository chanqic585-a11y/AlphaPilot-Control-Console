from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from .config import DATA_DIR


DEFAULT_SHADOW_PATH = DATA_DIR / "shadow_observations.sqlite"

_ALLOWED_FIELDS = frozenset(
    {
        "shadowObservationId",
        "releaseId",
        "strategyId",
        "strategyFamilyId",
        "timestamp",
        "symbol",
        "direction",
        "timeframe",
        "signalMatched",
        "passOrReject",
        "reasonZh",
        "featureSnapshot",
        "marketRegime",
        "publicUniverseIncluded",
        "demoUniverseIncluded",
        "liquidityPassed",
        "dataQualityPassed",
        "riskGatePassed",
        "wouldAttemptDemoOrder",
        "sourceDataHashes",
    }
)

_FORBIDDEN_FRAGMENTS = (
    "order",
    "fill",
    "position",
    "capital",
    "equity",
    "pnl",
    "profit",
    "loss",
    "mfe",
    "mae",
    "return",
    "outcome",
    "targethit",
    "stophit",
    "closedtrade",
    "promotion",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _identifier(payload: dict[str, Any]) -> str:
    hashes = payload.get("sourceDataHashes") if isinstance(payload.get("sourceDataHashes"), dict) else {}
    identity = {
        "releaseId": payload.get("releaseId"),
        "symbol": payload.get("symbol"),
        "timeframe": payload.get("timeframe"),
        "timestamp": payload.get("timestamp"),
        "definitionHash": hashes.get("definitionHash"),
    }
    return "shadow_" + hashlib.sha256(_canonical(identity).encode("utf-8")).hexdigest()


def _validate_nested_keys(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).replace("_", "").lower()
            if any(fragment in normalized for fragment in _FORBIDDEN_FRAGMENTS):
                raise ValueError(f"shadow_forbidden_field:{path}{key}")
            _validate_nested_keys(nested, f"{path}{key}.")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_nested_keys(nested, f"{path}{index}.")


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


class ShadowObservationStore:
    def __init__(self, path: Path = DEFAULT_SHADOW_PATH) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ShadowObservations (
              shadowObservationId TEXT PRIMARY KEY,
              releaseId TEXT NOT NULL,
              strategyId TEXT NOT NULL,
              strategyFamilyId TEXT NOT NULL,
              timestamp TEXT NOT NULL,
              symbol TEXT NOT NULL,
              direction TEXT NOT NULL,
              timeframe TEXT NOT NULL,
              signalMatched INTEGER NOT NULL,
              passOrReject TEXT NOT NULL,
              reasonZh TEXT NOT NULL,
              featureSnapshot TEXT NOT NULL,
              marketRegime TEXT NOT NULL,
              publicUniverseIncluded INTEGER NOT NULL,
              demoUniverseIncluded INTEGER NOT NULL,
              liquidityPassed INTEGER,
              dataQualityPassed INTEGER,
              riskGatePassed INTEGER,
              wouldAttemptDemoOrder INTEGER NOT NULL,
              sourceDataHashes TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_shadow_release_time "
            "ON ShadowObservations(releaseId, timestamp DESC)"
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        unexpected = set(payload) - _ALLOWED_FIELDS
        if unexpected:
            raise ValueError(f"shadow_unexpected_fields:{','.join(sorted(unexpected))}")
        feature_snapshot = payload.get("featureSnapshot") if isinstance(payload.get("featureSnapshot"), dict) else {}
        source_hashes = payload.get("sourceDataHashes") if isinstance(payload.get("sourceDataHashes"), dict) else {}
        _validate_nested_keys(feature_snapshot, "featureSnapshot.")
        _validate_nested_keys(source_hashes, "sourceDataHashes.")
        normalized = {
            **payload,
            "shadowObservationId": str(payload.get("shadowObservationId") or _identifier(payload)),
            "featureSnapshot": feature_snapshot,
            "sourceDataHashes": source_hashes,
        }
        required = ("releaseId", "strategyId", "timestamp", "symbol", "timeframe")
        if any(not str(normalized.get(key) or "").strip() for key in required):
            raise ValueError("shadow_required_field_missing")
        self.connection.execute(
            """
            INSERT OR IGNORE INTO ShadowObservations (
              shadowObservationId, releaseId, strategyId, strategyFamilyId,
              timestamp, symbol, direction, timeframe, signalMatched,
              passOrReject, reasonZh, featureSnapshot, marketRegime,
              publicUniverseIncluded, demoUniverseIncluded, liquidityPassed,
              dataQualityPassed, riskGatePassed, wouldAttemptDemoOrder,
              sourceDataHashes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized["shadowObservationId"],
                normalized["releaseId"],
                normalized["strategyId"],
                normalized.get("strategyFamilyId") or normalized["strategyId"],
                normalized["timestamp"],
                normalized["symbol"],
                normalized.get("direction") or "unknown",
                normalized["timeframe"],
                int(bool(normalized.get("signalMatched"))),
                normalized.get("passOrReject") or "reject",
                normalized.get("reasonZh") or "未提供原因",
                _canonical(feature_snapshot),
                normalized.get("marketRegime") or "unknown",
                int(bool(normalized.get("publicUniverseIncluded"))),
                int(bool(normalized.get("demoUniverseIncluded"))),
                None if normalized.get("liquidityPassed") is None else int(bool(normalized.get("liquidityPassed"))),
                None if normalized.get("dataQualityPassed") is None else int(bool(normalized.get("dataQualityPassed"))),
                None if normalized.get("riskGatePassed") is None else int(bool(normalized.get("riskGatePassed"))),
                int(bool(normalized.get("wouldAttemptDemoOrder"))),
                _canonical(source_hashes),
            ),
        )
        self.connection.commit()
        row = self.connection.execute(
            "SELECT * FROM ShadowObservations WHERE shadowObservationId = ?",
            (normalized["shadowObservationId"],),
        ).fetchone()
        if row is None:  # pragma: no cover
            raise RuntimeError("shadow_observation_write_failed")
        return self._row(row)

    def query(self, *, release_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        bounded_limit = max(1, min(int(limit), 500))
        where = "WHERE releaseId = ?" if release_id else ""
        parameters: tuple[Any, ...] = (release_id,) if release_id else ()
        rows = self.connection.execute(
            f"SELECT * FROM ShadowObservations {where} ORDER BY timestamp DESC LIMIT ?",
            (*parameters, bounded_limit),
        ).fetchall()
        all_rows = self.connection.execute(
            f"SELECT * FROM ShadowObservations {where} ORDER BY timestamp DESC",
            parameters,
        ).fetchall()
        projected = [self._row(row) for row in rows]
        aggregate = [self._row(row) for row in all_rows]
        reason_counts = Counter(row["reasonZh"] for row in aggregate)
        family_counts = Counter(row["strategyFamilyId"] for row in aggregate)
        symbol_counts = Counter(row["symbol"] for row in aggregate)
        direction_counts = Counter(row["direction"] for row in aggregate)
        public_rows = [row for row in aggregate if row["publicUniverseIncluded"]]
        demo_hits = sum(row["demoUniverseIncluded"] for row in public_rows)
        return {
            "summary": {
                "observationCount": len(aggregate),
                "matchedCount": sum(row["signalMatched"] for row in aggregate),
                "rejectedCount": sum(row["passOrReject"] == "reject" for row in aggregate),
                "warningCount": sum(row["passOrReject"] == "warning" for row in aggregate),
                "reasonCounts": dict(reason_counts),
                "familyCounts": dict(family_counts),
                "symbolCounts": dict(symbol_counts),
                "directionCounts": dict(direction_counts),
                "demoUniverseHitRate": round(demo_hits / len(public_rows), 6) if public_rows else 0.0,
                "latestObservedAt": aggregate[0]["timestamp"] if aggregate else None,
            },
            "rows": projected,
        }

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        for key in (
            "signalMatched",
            "publicUniverseIncluded",
            "demoUniverseIncluded",
            "wouldAttemptDemoOrder",
        ):
            payload[key] = bool(payload[key])
        for key in ("liquidityPassed", "dataQualityPassed", "riskGatePassed"):
            payload[key] = _bool_or_none(payload[key])
        payload["featureSnapshot"] = json.loads(payload["featureSnapshot"])
        payload["sourceDataHashes"] = json.loads(payload["sourceDataHashes"])
        return payload
