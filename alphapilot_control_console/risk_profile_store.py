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

_RUNTIME_RISK_HIGHER_IS_RISKIER = {
    "capitalLimitUsdt",
    "maxActiveStrategies",
    "maxConcurrentPositions",
    "maxPositionsPerStrategy",
    "maxPositionsPerSymbol",
    "maxOrderNotionalUsdt",
    "maxLeverage",
    "riskPerTradePercent",
    "riskPerTradeUsdt",
    "maxOpenRiskPercent",
    "maxOpenRiskUsdt",
    "maxStrategyOpenRiskPercent",
    "maxSymbolOpenRiskPercent",
    "maxDirectionOpenRiskPercent",
    "maxCorrelatedOpenRiskPercent",
    "dailyLossStopPercent",
    "maxDrawdownStopPercent",
    "canaryLossStopUsdt",
    "maxPortfolioBeta",
    "scanTopN",
}
_RUNTIME_RISK_LOWER_IS_RISKIER = {
    "cooldownAfterLossMinutes",
    "rewardRiskRatio",
}
_RUNTIME_RISK_BOOLEAN_FIELDS = {"allowNewEntries"}
_RUNTIME_RISK_NEUTRAL_FIELDS = {"marginMode"}
_RUNTIME_RISK_FIELDS = (
    _RUNTIME_RISK_HIGHER_IS_RISKIER
    | _RUNTIME_RISK_LOWER_IS_RISKIER
    | _RUNTIME_RISK_BOOLEAN_FIELDS
    | _RUNTIME_RISK_NEUTRAL_FIELDS
)

_RUNTIME_PUBLIC_FIELD_MAP = {
    "allocatedCapital": "capitalLimitUsdt",
    "riskPerTradePercent": "riskPerTradePercent",
    "riskPerTradeUSDT": "riskPerTradeUsdt",
    "maximumPortfolioOpenRiskPercent": "maxOpenRiskPercent",
    "maximumPortfolioOpenRiskUSDT": "maxOpenRiskUsdt",
    "maximumConcurrentPositions": "maxConcurrentPositions",
    "maximumInstrumentRisk": "maxSymbolOpenRiskPercent",
    "maximumSameDirectionRisk": "maxDirectionOpenRiskPercent",
    "maximumCorrelationClusterRisk": "maxCorrelatedOpenRiskPercent",
    "maximumPortfolioBeta": "maxPortfolioBeta",
    "maximumLeverage": "maxLeverage",
    "marginMode": "marginMode",
    "dailyLossLimit": "dailyLossStopPercent",
    "programLossLimit": "maxDrawdownStopPercent",
    "hardKillLossLimit": "canaryLossStopUsdt",
    "scanTopN": "scanTopN",
}

_RUNTIME_MINIMUMS: dict[str, Any] = {
    "capitalLimitUsdt": 1.0,
    "riskPerTradePercent": 0.01,
    "riskPerTradeUsdt": 0.01,
    "maxOpenRiskPercent": 0.01,
    "maxOpenRiskUsdt": 0.01,
    "maxConcurrentPositions": 1,
    "maxSymbolOpenRiskPercent": 0.01,
    "maxDirectionOpenRiskPercent": 0.01,
    "maxCorrelatedOpenRiskPercent": 0.01,
    "maxPortfolioBeta": 0.01,
    "maxLeverage": 1,
    "marginMode": "isolated",
    "dailyLossStopPercent": 0.01,
    "maxDrawdownStopPercent": 0.01,
    "canaryLossStopUsdt": 0.01,
    "scanTopN": 1,
}


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
        "maxRiskPerTradeUsdt": 1000.0 if live else 2000.0,
        "maxOpenRiskPercent": 5.0 if live else 10.0,
        "maxOpenRiskUsdt": 5000.0 if live else 10000.0,
        "maxDailyLossStopPercent": 5.0 if live else 10.0,
        "maxDrawdownStopPercent": 15.0 if live else 25.0,
        "maxPortfolioBeta": 2.0,
        "maxScanTopN": 200,
        "minimumRewardRiskRatio": 0.01,
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
        "riskPerTradeUsdt": 2.5,
        "maxOpenRiskPercent": 1.0,
        "maxOpenRiskUsdt": 10.0,
        "maxStrategyOpenRiskPercent": 1.0,
        "maxSymbolOpenRiskPercent": 0.5,
        "maxDirectionOpenRiskPercent": 1.0,
        "maxCorrelatedOpenRiskPercent": 1.0,
        "dailyLossStopPercent": 1.0,
        "maxDrawdownStopPercent": 2.5,
        "canaryLossStopUsdt": 25.0,
        "maxPortfolioBeta": 1.0,
        "scanTopN": 200,
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


def _with_runtime_defaults(profile: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(profile)
    capital = float(normalized.get("capitalLimitUsdt") or 1000.0)
    risk_percent = float(normalized.get("riskPerTradePercent") or 0.25)
    open_risk_percent = float(normalized.get("maxOpenRiskPercent") or 1.0)
    normalized.setdefault("riskPerTradeUsdt", capital * risk_percent / 100.0)
    normalized.setdefault("maxOpenRiskUsdt", capital * open_risk_percent / 100.0)
    normalized.setdefault("maxPortfolioBeta", 1.0)
    normalized.setdefault("scanTopN", 200)
    return normalized


def _normalize_runtime_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for requested_key, value in overrides.items():
        key = _RUNTIME_PUBLIC_FIELD_MAP.get(requested_key, requested_key)
        if key in normalized and normalized[key] != value:
            raise ValueError(f"Conflicting runtime risk field: {requested_key}")
        normalized[key] = value
    unsupported = sorted(set(normalized) - _RUNTIME_RISK_FIELDS)
    if unsupported:
        raise ValueError("Unsupported runtime risk fields: " + ",".join(unsupported))
    return normalized


def _merge_runtime_profile(
    reference: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    effective = {**_with_runtime_defaults(reference), **overrides}
    if {"capitalLimitUsdt", "riskPerTradePercent"} & set(overrides) and "riskPerTradeUsdt" not in overrides:
        effective["riskPerTradeUsdt"] = (
            float(effective["capitalLimitUsdt"])
            * float(effective["riskPerTradePercent"])
            / 100.0
        )
    if {"capitalLimitUsdt", "maxOpenRiskPercent"} & set(overrides) and "maxOpenRiskUsdt" not in overrides:
        effective["maxOpenRiskUsdt"] = (
            float(effective["capitalLimitUsdt"])
            * float(effective["maxOpenRiskPercent"])
            / 100.0
        )
    return effective


def validate_profile(profile: dict[str, Any], envelope: dict[str, Any] | None = None) -> None:
    profile = _with_runtime_defaults(profile)
    environment = str(profile.get("environment") or "")
    if environment not in ENVIRONMENTS or profile.get("schemaVersion") != "risk_profile_v1":
        raise ValueError("RiskProfile identity or schema is invalid")
    if not str(profile.get("profileKey") or "").strip() or not str(profile.get("name") or "").strip():
        raise ValueError("RiskProfile key and name are required")
    if int(profile.get("version") or 0) <= 0:
        raise ValueError("RiskProfile version must be positive")
    limits = {**_safety_envelope(environment), **dict(envelope or {})}
    positive = (
        "capitalLimitUsdt", "maxActiveStrategies", "maxConcurrentPositions",
        "maxPositionsPerStrategy", "maxPositionsPerSymbol", "maxOrderNotionalUsdt",
        "maxLeverage", "riskPerTradePercent", "maxOpenRiskPercent",
        "riskPerTradeUsdt", "maxOpenRiskUsdt", "maxPortfolioBeta", "scanTopN",
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
        "riskPerTradeUsdt": "maxRiskPerTradeUsdt",
        "maxOpenRiskPercent": "maxOpenRiskPercent",
        "maxOpenRiskUsdt": "maxOpenRiskUsdt",
        "dailyLossStopPercent": "maxDailyLossStopPercent",
        "maxDrawdownStopPercent": "maxDrawdownStopPercent",
        "maxPortfolioBeta": "maxPortfolioBeta",
        "scanTopN": "maxScanTopN",
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
    if float(profile["riskPerTradeUsdt"]) > float(profile["maxOpenRiskUsdt"]):
        raise ValueError("RiskProfile per-trade USDT risk exceeds portfolio USDT risk")
    if float(profile["maxOpenRiskUsdt"]) > float(profile["capitalLimitUsdt"]):
        raise ValueError("RiskProfile portfolio USDT risk exceeds capital")
    if not float(profile["scanTopN"]).is_integer():
        raise ValueError("RiskProfile scanTopN must be an integer")
    if float(profile["rewardRiskRatio"]) < float(limits["minimumRewardRiskRatio"]):
        raise ValueError("RiskProfile reward/risk is below the versioned safety envelope")
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
            CREATE TABLE IF NOT EXISTS RuntimeRiskOverlays (
              runtimeRiskOverlayId TEXT PRIMARY KEY,
              environment TEXT NOT NULL,
              baseRiskProfileId TEXT NOT NULL,
              previousRuntimeRiskOverlayId TEXT,
              classification TEXT NOT NULL,
              initialStatus TEXT NOT NULL,
              overridesJson TEXT NOT NULL,
              effectiveProfileJson TEXT NOT NULL,
              contentHash TEXT NOT NULL UNIQUE,
              actor TEXT NOT NULL,
              reason TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS RuntimeRiskOverlayEvents (
              eventId TEXT PRIMARY KEY,
              runtimeRiskOverlayId TEXT NOT NULL,
              environment TEXT NOT NULL,
              action TEXT NOT NULL,
              actor TEXT NOT NULL,
              reason TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_runtime_risk_overlay_events_environment
              ON RuntimeRiskOverlayEvents(environment, createdAt);
            """
        )
        self.connection.commit()
        self.seed_defaults()

    def close(self) -> None:
        self.connection.close()

    def seed_defaults(self) -> None:
        for environment in sorted(ENVIRONMENTS):
            profile = default_profile(environment)
            desired_profile = dict(profile)
            desired_profile.pop("version", None)
            desired_envelope = _safety_envelope(environment)
            record = None
            for existing in self.list_profiles(environment):
                existing_profile = dict(existing["profile"])
                existing_profile.pop("version", None)
                if (
                    existing["profileKey"] == profile["profileKey"]
                    and existing_profile == desired_profile
                    and existing["safetyEnvelope"] == desired_envelope
                ):
                    record = existing
                    break
            if record is None:
                versioned_profile = {**profile, "version": None}
                record = self.create_profile(versioned_profile, status="preset")
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
            ORDER BY a.createdAt DESC, a.rowid DESC LIMIT 1
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
        query += " ORDER BY createdAt, rowid"
        return [dict(row) for row in self.connection.execute(query, values).fetchall()]

    @staticmethod
    def _risk_increase_fields(
        reference: dict[str, Any],
        candidate: dict[str, Any],
    ) -> list[str]:
        increases: list[str] = []
        for key in sorted(_RUNTIME_RISK_HIGHER_IS_RISKIER):
            if float(candidate[key]) > float(reference[key]):
                increases.append(key)
        for key in sorted(_RUNTIME_RISK_LOWER_IS_RISKIER):
            if float(candidate[key]) < float(reference[key]):
                increases.append(key)
        for key in sorted(_RUNTIME_RISK_BOOLEAN_FIELDS):
            if bool(candidate[key]) and not bool(reference[key]):
                increases.append(key)
        return increases

    def create_runtime_overlay(
        self,
        environment: str,
        overrides: dict[str, Any],
        *,
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        if environment not in ENVIRONMENTS:
            raise ValueError("Unsupported runtime risk environment")
        if actor not in {"user_manual", "system_policy"}:
            raise PermissionError("Runtime risk overlay requires an audited actor")
        if not isinstance(overrides, dict) or not overrides:
            raise ValueError("Runtime risk overrides are required")
        normalized_overrides = _normalize_runtime_overrides(overrides)

        base = self.get_active_profile(environment)
        if base is None:
            raise ValueError("No active frozen RiskProfile is available")
        current = self.get_active_runtime_overlay(environment)
        base_profile = _with_runtime_defaults(base["profile"])
        reference = _with_runtime_defaults(
            current["effectiveProfile"] if current else base_profile
        )
        effective = _merge_runtime_profile(reference, normalized_overrides)
        validate_profile(effective, base["safetyEnvelope"])

        frozen_cap_violations = self._risk_increase_fields(base_profile, effective)
        if frozen_cap_violations:
            raise ValueError(
                "Runtime risk overlay exceeds frozen base profile: "
                + ",".join(frozen_cap_violations)
            )
        increase_fields = self._risk_increase_fields(reference, effective)
        classification = "risk_increase" if increase_fields else "risk_decrease_or_equal"
        identity = {
            "schemaVersion": "runtime_risk_overlay_v1",
            "environment": environment,
            "baseRiskProfileId": base["riskProfileId"],
            "baseRiskProfileHash": base["contentHash"],
            "previousRuntimeRiskOverlayId": (
                current["runtimeRiskOverlayId"] if current else None
            ),
            "overrides": overrides,
            "effectiveProfile": effective,
            "classification": classification,
            "appliesTo": "new_orders_only",
        }
        content_hash = _hash(identity)
        overlay_id = "runtime_risk_overlay_" + content_hash
        existing = self.connection.execute(
            "SELECT * FROM RuntimeRiskOverlays WHERE runtimeRiskOverlayId = ?",
            (overlay_id,),
        ).fetchone()
        if existing:
            return self._runtime_overlay_row(existing)

        status = "pending_exact_approval" if increase_fields else "applied"
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO RuntimeRiskOverlays(
                  runtimeRiskOverlayId, environment, baseRiskProfileId,
                  previousRuntimeRiskOverlayId, classification, initialStatus,
                  overridesJson, effectiveProfileJson, contentHash, actor, reason,
                  createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    overlay_id,
                    environment,
                    base["riskProfileId"],
                    current["runtimeRiskOverlayId"] if current else None,
                    classification,
                    status,
                    _canonical(overrides),
                    _canonical(effective),
                    content_hash,
                    actor,
                    str(reason or "runtime_risk_overlay_created"),
                    _now(),
                ),
            )
        if status == "applied":
            self._append_runtime_overlay_event(
                overlay_id,
                environment,
                action="applied_risk_decrease",
                actor=actor,
                reason=str(reason or "runtime_risk_decrease"),
            )
        return self.get_runtime_overlay(overlay_id)

    def approve_runtime_overlay(
        self,
        runtime_risk_overlay_id: str,
        *,
        actor: str,
        confirmation: str,
        reason: str,
    ) -> dict[str, Any]:
        overlay = self.get_runtime_overlay(runtime_risk_overlay_id)
        if overlay["classification"] != "risk_increase":
            raise ValueError("Only a pending risk increase requires exact approval")
        if actor != "user_manual":
            raise PermissionError("Risk increase approval requires user_manual")
        expected = "APPROVE_RUNTIME_RISK_OVERLAY:" + overlay["contentHash"]
        if confirmation != expected:
            raise PermissionError("Exact runtime risk overlay approval is required")
        if overlay["status"] == "applied":
            return overlay
        self._append_runtime_overlay_event(
            overlay["runtimeRiskOverlayId"],
            overlay["environment"],
            action="approved_risk_increase",
            actor=actor,
            reason=str(reason or "runtime_risk_increase_approved"),
        )
        return self.get_runtime_overlay(runtime_risk_overlay_id)

    def get_runtime_overlay(self, overlay_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM RuntimeRiskOverlays WHERE runtimeRiskOverlayId = ?",
            (overlay_id,),
        ).fetchone()
        if not row:
            raise KeyError("Runtime risk overlay not found")
        return self._runtime_overlay_row(row)

    def get_active_runtime_overlay(self, environment: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT o.* FROM RuntimeRiskOverlayEvents e
            JOIN RuntimeRiskOverlays o
              ON o.runtimeRiskOverlayId = e.runtimeRiskOverlayId
            WHERE e.environment = ?
              AND e.action IN ('applied_risk_decrease', 'approved_risk_increase', 'rolled_back')
            ORDER BY e.createdAt DESC, e.rowid DESC LIMIT 1
            """,
            (environment,),
        ).fetchone()
        return self._runtime_overlay_row(row) if row else None

    def list_runtime_overlays(self, environment: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM RuntimeRiskOverlays"
        values: tuple[str, ...] = ()
        if environment:
            query += " WHERE environment = ?"
            values = (environment,)
        query += " ORDER BY createdAt, rowid"
        return [self._runtime_overlay_row(row) for row in self.connection.execute(query, values)]

    def list_runtime_overlay_events(
        self, environment: str | None = None
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM RuntimeRiskOverlayEvents"
        values: tuple[str, ...] = ()
        if environment:
            query += " WHERE environment = ?"
            values = (environment,)
        query += " ORDER BY createdAt, rowid"
        return [dict(row) for row in self.connection.execute(query, values)]

    def get_runtime_risk_contract(self, environment: str) -> dict[str, Any]:
        if environment not in ENVIRONMENTS:
            raise ValueError("Unsupported runtime risk environment")
        base = self.get_active_profile(environment)
        if base is None:
            raise ValueError("No active frozen RiskProfile is available")
        current = self.get_active_runtime_overlay(environment)
        base_profile = _with_runtime_defaults(base["profile"])
        effective = _with_runtime_defaults(
            current["effectiveProfile"] if current else base_profile
        )
        fields: dict[str, dict[str, Any]] = {}
        for public_key, profile_key in _RUNTIME_PUBLIC_FIELD_MAP.items():
            fields[public_key] = {
                "currentValue": effective[profile_key],
                "suggestedValue": base_profile[profile_key],
                "minimumAllowed": _RUNTIME_MINIMUMS[profile_key],
                "maximumAllowed": base_profile[profile_key],
                "effectiveAt": "next_new_order",
                "changeMode": "runtime_overlay_hash",
            }
        return {
            "schemaVersion": "runtime_risk_contract_v1",
            "environment": environment,
            "baseRiskProfileId": base["riskProfileId"],
            "baseRiskProfileHash": base["contentHash"],
            "activeRuntimeRiskOverlayId": (
                current["runtimeRiskOverlayId"] if current else None
            ),
            "activeRuntimeRiskOverlayHash": current["contentHash"] if current else None,
            "fields": fields,
            "executionEnabled": False,
            "safetyBoundary": {
                "riskDecreaseAppliesTo": "next_new_order",
                "riskIncreaseRequiresExactHashApproval": True,
                "runningPositionsKeepOpeningRiskProfile": True,
                "safetyEnvelopeEditable": False,
            },
        }

    def _append_runtime_overlay_event(
        self,
        overlay_id: str,
        environment: str,
        *,
        action: str,
        actor: str,
        reason: str,
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO RuntimeRiskOverlayEvents(
                  eventId, runtimeRiskOverlayId, environment, action, actor,
                  reason, createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "runtime_risk_event_" + uuid.uuid4().hex,
                    overlay_id,
                    environment,
                    action,
                    actor,
                    reason,
                    _now(),
                ),
            )

    def _runtime_overlay_row(self, row: sqlite3.Row) -> dict[str, Any]:
        event = self.connection.execute(
            """
            SELECT action FROM RuntimeRiskOverlayEvents
            WHERE runtimeRiskOverlayId = ?
            ORDER BY createdAt DESC, rowid DESC LIMIT 1
            """,
            (row["runtimeRiskOverlayId"],),
        ).fetchone()
        status = (
            "applied"
            if event and event["action"] in {
                "applied_risk_decrease", "approved_risk_increase", "rolled_back"
            }
            else row["initialStatus"]
        )
        return {
            "runtimeRiskOverlayId": row["runtimeRiskOverlayId"],
            "environment": row["environment"],
            "baseRiskProfileId": row["baseRiskProfileId"],
            "previousRuntimeRiskOverlayId": row["previousRuntimeRiskOverlayId"],
            "classification": row["classification"],
            "status": status,
            "overrides": json.loads(row["overridesJson"]),
            "effectiveProfile": json.loads(row["effectiveProfileJson"]),
            "contentHash": row["contentHash"],
            "actor": row["actor"],
            "reason": row["reason"],
            "createdAt": row["createdAt"],
            "appliesTo": "new_orders_only",
            "runningPositionsKeepOpeningProfile": True,
            "executionEnabled": False,
        }

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
        runtime_overlays = store.list_runtime_overlays()
        active_runtime_overlays = {
            environment: store.get_active_runtime_overlay(environment)
            for environment in sorted(ENVIRONMENTS)
        }
        runtime_risk_contracts = {
            environment: store.get_runtime_risk_contract(environment)
            for environment in sorted(ENVIRONMENTS)
        }
        runtime_events = store.list_runtime_overlay_events()[-30:]
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
        "runtimeOverlays": runtime_overlays,
        "activeRuntimeOverlays": active_runtime_overlays,
        "runtimeRiskContracts": runtime_risk_contracts,
        "recentRuntimeOverlayEvents": runtime_events,
        "safetyBoundary": {
            "profileEditEnablesExecution": False,
            "liveActivationRequiresManualConfirmation": True,
            "runningPositionsKeepOpeningProfile": True,
            "runtimeRiskDecreaseAppliesToNewOrdersOnly": True,
            "runtimeRiskIncreaseRequiresExactHashApproval": True,
            "routineUiCanChangeSafetyEnvelope": False,
            "withdrawAllowed": False,
            "rawCredentialStorageAllowed": False,
        },
    }
