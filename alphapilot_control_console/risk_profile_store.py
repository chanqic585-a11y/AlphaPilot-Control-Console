"""Append-only local RiskProfile versions and activation history."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DATA_DIR


RISK_PROFILE_STORE_PATH = DATA_DIR / "risk_profiles.sqlite"
ACTIVATION_CONFIRMATION = "ACTIVATE_RISK_PROFILE"
LIVE_ACTIVATION_CONFIRMATION = "ACTIVATE_LIVE_RISK_PROFILE"
ENVIRONMENTS = {"local_forward", "okx_demo", "live_canary", "live_standard"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _safety_envelope(environment: str) -> dict[str, Any]:
    live = environment.startswith("live_")
    return {
        "schemaVersion": "risk_safety_envelope_v1",
        "environment": environment,
        "maxCapitalLimitUsdt": 100000.0,
        "maxActiveStrategies": 10 if live else 20,
        "maxConcurrentPositions": 20 if live else 50,
        "maxOrderNotionalToCapitalRatio": 1.0,
        "maxLeverage": 5,
        "maxRiskPerTradePercent": 1.0 if live else 2.0,
        "maxOpenRiskPercent": 5.0 if live else 10.0,
        "maxDailyLossStopPercent": 5.0 if live else 10.0,
        "maxDrawdownStopPercent": 15.0 if live else 25.0,
        "minimumRewardRiskRatio": 2.0,
        "allowedMarginModes": ["isolated"],
        "routineUiCanChangeEnvelope": False,
    }


def default_profile(environment: str) -> dict[str, Any]:
    if environment not in ENVIRONMENTS:
        raise ValueError("Unsupported RiskProfile environment")
    profile = {
        "schemaVersion": "risk_profile_v1",
        "profileKey": f"{environment}_conservative",
        "version": 1,
        "environment": environment,
        "name": f"{environment.replace('_', ' ').title()} Conservative",
        "capitalLimitUsdt": 1000.0,
        "maxActiveStrategies": 1,
        "maxConcurrentPositions": 1,
        "maxPositionsPerStrategy": 1,
        "maxPositionsPerSymbol": 1,
        "maxOrderNotionalUsdt": 100.0,
        "maxLeverage": 1,
        "marginMode": "isolated",
        "riskPerTradePercent": 0.25,
        "maxOpenRiskPercent": 1.0,
        "maxStrategyOpenRiskPercent": 1.0,
        "maxSymbolOpenRiskPercent": 0.5,
        "maxDirectionOpenRiskPercent": 1.0,
        "maxCorrelatedOpenRiskPercent": 1.0,
        "dailyLossStopPercent": 1.0,
        "maxDrawdownStopPercent": 2.5,
        "canaryLossStopUsdt": 25.0,
        "cooldownAfterLossMinutes": 60,
        "rewardRiskRatio": 2.0,
        "feeRate": 0.0005,
        "slippageRate": 0.0002,
        "allowNewEntries": True,
        "allowedStrategyIds": [],
    }
    if environment in {"local_forward", "okx_demo"}:
        profile.update({
            "maxActiveStrategies": 4,
            "maxConcurrentPositions": 3,
            "maxPositionsPerStrategy": 2,
            "maxOrderNotionalUsdt": 250.0,
            "maxLeverage": 2,
            "dailyLossStopPercent": 2.0,
            "maxDrawdownStopPercent": 5.0,
        })
    if environment == "live_standard":
        profile.update({
            "maxActiveStrategies": 3,
            "maxConcurrentPositions": 3,
            "maxPositionsPerStrategy": 2,
            "maxOrderNotionalUsdt": 250.0,
            "maxLeverage": 2,
            "dailyLossStopPercent": 2.0,
            "maxDrawdownStopPercent": 5.0,
            "allowNewEntries": False,
        })
    return profile


def validate_profile(profile: dict[str, Any], envelope: dict[str, Any] | None = None) -> None:
    environment = str(profile.get("environment") or "")
    if environment not in ENVIRONMENTS or profile.get("schemaVersion") != "risk_profile_v1":
        raise ValueError("RiskProfile identity or schema is invalid")
    if not str(profile.get("profileKey") or "").strip() or not str(profile.get("name") or "").strip():
        raise ValueError("RiskProfile key and name are required")
    if int(profile.get("version") or 0) <= 0:
        raise ValueError("RiskProfile version must be positive")
    limits = dict(envelope or _safety_envelope(environment))
    positive = (
        "capitalLimitUsdt", "maxActiveStrategies", "maxConcurrentPositions",
        "maxPositionsPerStrategy", "maxPositionsPerSymbol", "maxOrderNotionalUsdt",
        "maxLeverage", "riskPerTradePercent", "maxOpenRiskPercent",
        "maxStrategyOpenRiskPercent", "maxSymbolOpenRiskPercent",
        "maxDirectionOpenRiskPercent", "maxCorrelatedOpenRiskPercent",
        "dailyLossStopPercent", "maxDrawdownStopPercent", "canaryLossStopUsdt",
        "rewardRiskRatio",
    )
    for key in positive:
        value = float(profile.get(key) or 0)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"RiskProfile field must be positive: {key}")
    bounded = {
        "capitalLimitUsdt": "maxCapitalLimitUsdt",
        "maxActiveStrategies": "maxActiveStrategies",
        "maxConcurrentPositions": "maxConcurrentPositions",
        "maxLeverage": "maxLeverage",
        "riskPerTradePercent": "maxRiskPerTradePercent",
        "maxOpenRiskPercent": "maxOpenRiskPercent",
        "dailyLossStopPercent": "maxDailyLossStopPercent",
        "maxDrawdownStopPercent": "maxDrawdownStopPercent",
    }
    for key, limit_key in bounded.items():
        if float(profile[key]) > float(limits[limit_key]):
            raise ValueError(f"RiskProfile exceeds SafetyEnvelope: {key}")
    if profile.get("marginMode") not in limits["allowedMarginModes"]:
        raise ValueError("RiskProfile margin mode is not allowed")
    if float(profile["maxOrderNotionalUsdt"]) > float(profile["capitalLimitUsdt"]):
        raise ValueError("RiskProfile order notional exceeds capital")
    if int(profile["maxPositionsPerStrategy"]) > int(profile["maxConcurrentPositions"]):
        raise ValueError("RiskProfile strategy concurrency exceeds portfolio concurrency")
    if int(profile["maxPositionsPerSymbol"]) > int(profile["maxConcurrentPositions"]):
        raise ValueError("RiskProfile symbol concurrency exceeds portfolio concurrency")
    for key in (
        "riskPerTradePercent", "maxStrategyOpenRiskPercent", "maxSymbolOpenRiskPercent",
        "maxDirectionOpenRiskPercent", "maxCorrelatedOpenRiskPercent",
    ):
        if float(profile[key]) > float(profile["maxOpenRiskPercent"]):
            raise ValueError(f"RiskProfile sub-limit exceeds total risk: {key}")
    if float(profile["canaryLossStopUsdt"]) > float(profile["capitalLimitUsdt"]):
        raise ValueError("RiskProfile Canary stop exceeds capital")
    if float(profile["rewardRiskRatio"]) < float(limits["minimumRewardRiskRatio"]):
        raise ValueError("RiskProfile reward/risk must remain at least 2R")
    if float(profile.get("feeRate") or 0) < 0 or float(profile.get("slippageRate") or 0) < 0:
        raise ValueError("RiskProfile costs cannot be negative")
    if int(profile.get("cooldownAfterLossMinutes") or 0) < 0:
        raise ValueError("RiskProfile cooldown cannot be negative")


class RiskProfileStore:
    def __init__(self, path: Path | str = RISK_PROFILE_STORE_PATH):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS RiskProfiles (
              riskProfileId TEXT PRIMARY KEY,
              profileKey TEXT NOT NULL,
              version INTEGER NOT NULL,
              environment TEXT NOT NULL,
              name TEXT NOT NULL,
              status TEXT NOT NULL,
              profileJson TEXT NOT NULL,
              safetyEnvelopeJson TEXT NOT NULL,
              contentHash TEXT NOT NULL,
              createdAt TEXT NOT NULL,
              UNIQUE(profileKey, version)
            );
            CREATE TABLE IF NOT EXISTS RiskProfileActivations (
              activationId TEXT PRIMARY KEY,
              environment TEXT NOT NULL,
              riskProfileId TEXT NOT NULL,
              previousRiskProfileId TEXT,
              action TEXT NOT NULL,
              actor TEXT NOT NULL,
              reason TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_risk_profile_activation_environment
              ON RiskProfileActivations(environment, createdAt);
            """
        )
        self.connection.commit()
        self.seed_defaults()

    def close(self) -> None:
        self.connection.close()

    def seed_defaults(self) -> None:
        for environment in sorted(ENVIRONMENTS):
            profile = default_profile(environment)
            record = self.create_profile(profile, status="preset")
            if self.get_active_profile(environment) is None:
                self.activate(
                    record["riskProfileId"],
                    actor="system_seed",
                    confirmation="",
                    reason="initial_conservative_profile",
                )

    def create_profile(self, profile: dict[str, Any], *, status: str = "draft") -> dict[str, Any]:
        values = dict(profile)
        environment = str(values.get("environment") or "")
        if values.get("version") is None:
            row = self.connection.execute(
                "SELECT MAX(version) AS maximum FROM RiskProfiles WHERE profileKey = ?",
                (str(values.get("profileKey") or ""),),
            ).fetchone()
            values["version"] = int(row["maximum"] or 0) + 1
        limits = _safety_envelope(environment)
        validate_profile(values, limits)
        identity = {
            "profileKey": values["profileKey"],
            "version": int(values["version"]),
            "environment": environment,
            "profile": values,
            "safetyEnvelope": limits,
        }
        content_hash = _hash(identity)
        profile_id = "risk_profile_" + content_hash
        existing = self.connection.execute(
            "SELECT * FROM RiskProfiles WHERE profileKey = ? AND version = ?",
            (values["profileKey"], values["version"]),
        ).fetchone()
        if existing:
            if existing["contentHash"] != content_hash:
                raise ValueError("RiskProfile version already exists with different content")
            return self._profile_row(existing)
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO RiskProfiles(
                  riskProfileId, profileKey, version, environment, name, status,
                  profileJson, safetyEnvelopeJson, contentHash, createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id, values["profileKey"], values["version"], environment,
                    values["name"], status, _canonical(values), _canonical(limits),
                    content_hash, _now(),
                ),
            )
        return self.get_profile(profile_id)

    def get_profile(self, profile_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM RiskProfiles WHERE riskProfileId = ?", (profile_id,)
        ).fetchone()
        if not row:
            raise KeyError("RiskProfile not found")
        return self._profile_row(row)

    def list_profiles(self, environment: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM RiskProfiles"
        values: tuple[str, ...] = ()
        if environment:
            query += " WHERE environment = ?"
            values = (environment,)
        query += " ORDER BY environment, profileKey, version"
        return [self._profile_row(row) for row in self.connection.execute(query, values).fetchall()]

    def activate(
        self,
        profile_id: str,
        *,
        actor: str,
        confirmation: str,
        reason: str,
        action: str = "activated",
    ) -> dict[str, Any]:
        profile = self.get_profile(profile_id)
        if actor != "system_seed":
            if actor != "user_manual":
                raise PermissionError("RiskProfile activation requires user_manual")
            expected = LIVE_ACTIVATION_CONFIRMATION if profile["environment"].startswith("live_") else ACTIVATION_CONFIRMATION
            if confirmation != expected:
                raise PermissionError("Exact RiskProfile activation confirmation is required")
        current = self.get_active_profile(profile["environment"])
        if current and current["riskProfileId"] == profile_id:
            return {"activeProfile": current, "activation": None, "executionEnabled": False}
        now = _now()
        activation_id = "risk_activation_" + uuid.uuid4().hex
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO RiskProfileActivations(
                  activationId, environment, riskProfileId, previousRiskProfileId,
                  action, actor, reason, createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activation_id, profile["environment"], profile_id,
                    current["riskProfileId"] if current else None,
                    action, actor, str(reason or "risk_profile_activation"), now,
                ),
            )
        return {
            "activeProfile": profile,
            "activation": {
                "activationId": activation_id,
                "environment": profile["environment"],
                "riskProfileId": profile_id,
                "previousRiskProfileId": current["riskProfileId"] if current else None,
                "action": action,
                "actor": actor,
                "reason": str(reason or "risk_profile_activation"),
                "createdAt": now,
            },
            "executionEnabled": False,
        }

    def rollback(self, environment: str, *, actor: str, confirmation: str) -> dict[str, Any]:
        activations = self.list_activations(environment)
        if len(activations) < 2:
            raise ValueError("No previous RiskProfile activation is available")
        current_id = activations[-1]["riskProfileId"]
        target = next(
            (row for row in reversed(activations[:-1]) if row["riskProfileId"] != current_id),
            None,
        )
        if target is None:
            raise ValueError("No distinct RiskProfile rollback target exists")
        return self.activate(
            target["riskProfileId"],
            actor=actor,
            confirmation=confirmation,
            reason="manual_risk_profile_rollback",
            action="rolled_back",
        )

    def get_active_profile(self, environment: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT p.* FROM RiskProfileActivations a
            JOIN RiskProfiles p ON p.riskProfileId = a.riskProfileId
            WHERE a.environment = ?
            ORDER BY a.createdAt DESC, a.activationId DESC LIMIT 1
            """,
            (environment,),
        ).fetchone()
        return self._profile_row(row) if row else None

    def list_activations(self, environment: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM RiskProfileActivations"
        values: tuple[str, ...] = ()
        if environment:
            query += " WHERE environment = ?"
            values = (environment,)
        query += " ORDER BY createdAt, activationId"
        return [dict(row) for row in self.connection.execute(query, values).fetchall()]

    @staticmethod
    def _profile_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "riskProfileId": row["riskProfileId"],
            "profileKey": row["profileKey"],
            "version": int(row["version"]),
            "environment": row["environment"],
            "name": row["name"],
            "status": row["status"],
            "profile": json.loads(row["profileJson"]),
            "safetyEnvelope": json.loads(row["safetyEnvelopeJson"]),
            "contentHash": row["contentHash"],
            "createdAt": row["createdAt"],
        }


def build_risk_profile_status(path: Path | str = RISK_PROFILE_STORE_PATH) -> dict[str, Any]:
    store = RiskProfileStore(path)
    try:
        profiles = store.list_profiles()
        active = {
            environment: store.get_active_profile(environment)
            for environment in sorted(ENVIRONMENTS)
        }
        activations = store.list_activations()[-30:]
    finally:
        store.close()
    return {
        "version": "V13.24.0",
        "source": "versioned_risk_profile_store_v1",
        "summary": {
            "profileCount": len(profiles),
            "activeEnvironmentCount": sum(value is not None for value in active.values()),
            "liveExecutionEnabled": False,
        },
        "profiles": profiles,
        "activeProfiles": active,
        "recentActivations": activations,
        "safetyBoundary": {
            "profileEditEnablesExecution": False,
            "liveActivationRequiresManualConfirmation": True,
            "runningPositionsKeepOpeningProfile": True,
            "routineUiCanChangeSafetyEnvelope": False,
            "withdrawAllowed": False,
            "rawCredentialStorageAllowed": False,
        },
    }
