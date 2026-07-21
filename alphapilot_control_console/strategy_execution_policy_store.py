"""Immutable, versioned per-strategy execution policies.

Business parameters can be changed by creating a new policy version. Hard
safety invariants and the active account RiskProfile remain upper bounds.
Creating or activating a policy never starts execution.
"""

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
from .risk_profile_store import RISK_PROFILE_STORE_PATH, RiskProfileStore


STRATEGY_EXECUTION_POLICY_STORE_PATH = DATA_DIR / "strategy_execution_policies.sqlite"
STRATEGY_POLICY_ACTIVATION_CONFIRMATION = "ACTIVATE_STRATEGY_EXECUTION_POLICY"
ENVIRONMENTS = {"okx_demo", "okx_live"}

_IDENTITY_FIELDS = {
    "schemaVersion",
    "policyKey",
    "environment",
    "strategyId",
    "releaseId",
    "releaseHash",
}
_BUSINESS_FIELDS = {
    "name",
    "allocationUsdt",
    "maxOrderNotionalUsdt",
    "riskPerTradePercent",
    "riskPerTradeUsdt",
    "maxLeverage",
    "marginMode",
    "maxConcurrentPositions",
    "maxPositionsPerSymbol",
    "scanTopN",
    "minimumQuoteTurnoverUsdt",
    "minimumDepthNotionalUsdt",
    "targetSignalToOrderSeconds",
    "maximumSignalAgeSeconds",
    "criticalLatencyFailureSeconds",
    "orderAckTimeoutSeconds",
    "cooldownAfterLossMinutes",
    "feeRate",
    "slippageRate",
    "stopPolicy",
    "exitPolicy",
}
_ALLOWED_FIELDS = _IDENTITY_FIELDS | _BUSINESS_FIELDS | {"version"}
_HIGHER_IS_RISKIER = {
    "allocationUsdt",
    "maxOrderNotionalUsdt",
    "riskPerTradePercent",
    "riskPerTradeUsdt",
    "maxLeverage",
    "maxConcurrentPositions",
    "maxPositionsPerSymbol",
    "scanTopN",
    "maximumSignalAgeSeconds",
    "criticalLatencyFailureSeconds",
    "orderAckTimeoutSeconds",
}
_LOWER_IS_RISKIER = {
    "minimumQuoteTurnoverUsdt",
    "minimumDepthNotionalUsdt",
    "cooldownAfterLossMinutes",
}
_SENSITIVE_TOKENS = (
    "apikey",
    "secretkey",
    "passphrase",
    "credential",
    "password",
    "withdraw",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _reject_sensitive(value: Any, path: str = "policy") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            compact = str(key).replace("_", "").replace("-", "").lower()
            if any(token in compact for token in _SENSITIVE_TOKENS):
                raise ValueError(f"Credential-like or prohibited field: {path}.{key}")
            _reject_sensitive(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{path}[{index}]")


def _positive_number(policy: dict[str, Any], field: str) -> float:
    value = float(policy.get(field) or 0)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"Strategy execution policy field must be positive: {field}")
    return value


def _nonnegative_number(policy: dict[str, Any], field: str) -> float:
    value = float(policy.get(field) or 0)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"Strategy execution policy field cannot be negative: {field}")
    return value


def _validate_stop_policy(value: Any) -> None:
    if not isinstance(value, dict) or value.get("type") not in {
        "fixed_percent",
        "atr",
        "structure",
        "hybrid",
    }:
        raise ValueError("Unsupported stop policy")
    if float(value.get("maximumLossR") or 0) <= 0:
        raise ValueError("Stop policy maximumLossR must be positive")


def _validate_exit_policy(value: Any) -> None:
    if not isinstance(value, dict) or value.get("type") not in {
        "fixed_r",
        "tiered",
        "trailing_trend",
        "hybrid_trailing",
    }:
        raise ValueError("Unsupported exit policy")
    numeric_values = [
        float(item)
        for key, item in value.items()
        if key != "type" and isinstance(item, (int, float))
    ]
    if numeric_values and any(not math.isfinite(item) or item < 0 for item in numeric_values):
        raise ValueError("Exit policy numeric fields cannot be negative or non-finite")


def validate_strategy_execution_policy(
    policy: dict[str, Any],
    account_profile: dict[str, Any],
) -> None:
    _reject_sensitive(policy)
    unknown = sorted(set(policy) - _ALLOWED_FIELDS)
    if unknown:
        raise ValueError("Unsupported strategy execution policy fields: " + ",".join(unknown))
    if policy.get("schemaVersion") != "strategy_execution_policy_v1":
        raise ValueError("Strategy execution policy schema is invalid")
    if policy.get("environment") not in ENVIRONMENTS:
        raise ValueError("Strategy execution policy environment is invalid")
    for field in ("policyKey", "strategyId", "releaseId", "releaseHash", "name"):
        if not str(policy.get(field) or "").strip():
            raise ValueError(f"Strategy execution policy identity is incomplete: {field}")
    if int(policy.get("version") or 0) <= 0:
        raise ValueError("Strategy execution policy version must be positive")
    if policy["environment"] != account_profile.get("environment"):
        raise ValueError("Strategy policy and account RiskProfile environments differ")

    for field in (
        "allocationUsdt",
        "maxOrderNotionalUsdt",
        "riskPerTradePercent",
        "riskPerTradeUsdt",
        "maxLeverage",
        "maxConcurrentPositions",
        "maxPositionsPerSymbol",
        "scanTopN",
        "minimumQuoteTurnoverUsdt",
        "minimumDepthNotionalUsdt",
        "targetSignalToOrderSeconds",
        "maximumSignalAgeSeconds",
        "criticalLatencyFailureSeconds",
        "orderAckTimeoutSeconds",
    ):
        _positive_number(policy, field)
    for field in ("cooldownAfterLossMinutes", "feeRate", "slippageRate"):
        _nonnegative_number(policy, field)

    if policy.get("marginMode") != "isolated":
        raise ValueError("Only isolated margin is allowed")
    if float(policy["allocationUsdt"]) > float(account_profile["capitalLimitUsdt"]):
        raise ValueError("Strategy policy exceeds account RiskProfile allocation")
    account_limits = {
        "maxOrderNotionalUsdt": "maxOrderNotionalUsdt",
        "riskPerTradePercent": "riskPerTradePercent",
        "riskPerTradeUsdt": "riskPerTradeUsdt",
        "maxLeverage": "maxLeverage",
        "maxConcurrentPositions": "maxPositionsPerStrategy",
        "maxPositionsPerSymbol": "maxPositionsPerSymbol",
        "scanTopN": "scanTopN",
    }
    for policy_field, profile_field in account_limits.items():
        if float(policy[policy_field]) > float(account_profile[profile_field]):
            raise ValueError(
                f"Strategy policy exceeds account RiskProfile: {policy_field}"
            )
    if float(policy["maxOrderNotionalUsdt"]) > float(policy["allocationUsdt"]):
        raise ValueError("Strategy order notional exceeds strategy allocation")
    if float(policy["riskPerTradeUsdt"]) > float(policy["allocationUsdt"]):
        raise ValueError("Strategy per-trade risk exceeds strategy allocation")
    target = float(policy["targetSignalToOrderSeconds"])
    maximum = float(policy["maximumSignalAgeSeconds"])
    critical = float(policy["criticalLatencyFailureSeconds"])
    if not target <= maximum <= critical:
        raise ValueError("Strategy latency thresholds must satisfy target <= maximum <= critical")
    _validate_stop_policy(policy.get("stopPolicy"))
    _validate_exit_policy(policy.get("exitPolicy"))


def _classification(previous: dict[str, Any] | None, current: dict[str, Any]) -> str:
    if previous is None:
        return "initial"
    if any(previous.get(field) != current.get(field) for field in ("stopPolicy", "exitPolicy")):
        return "execution_semantics_change"
    riskier = any(
        float(current[field]) > float(previous[field])
        for field in _HIGHER_IS_RISKIER
    ) or any(
        float(current[field]) < float(previous[field])
        for field in _LOWER_IS_RISKIER
    )
    if riskier:
        return "higher_risk"
    changed = any(previous.get(field) != current.get(field) for field in _BUSINESS_FIELDS)
    if not changed:
        return "unchanged"
    safer_or_equal = all(
        float(current[field]) <= float(previous[field])
        for field in _HIGHER_IS_RISKIER
    ) and all(
        float(current[field]) >= float(previous[field])
        for field in _LOWER_IS_RISKIER
    )
    return "lower_risk" if safer_or_equal else "configuration_change"


class StrategyExecutionPolicyStore:
    def __init__(
        self,
        path: Path | str = STRATEGY_EXECUTION_POLICY_STORE_PATH,
        *,
        risk_profile_store: RiskProfileStore | None = None,
        risk_profile_store_path: Path | str = RISK_PROFILE_STORE_PATH,
    ) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS StrategyExecutionPolicies (
              policyId TEXT PRIMARY KEY,
              policyKey TEXT NOT NULL,
              version INTEGER NOT NULL,
              environment TEXT NOT NULL,
              strategyId TEXT NOT NULL,
              releaseId TEXT NOT NULL,
              releaseHash TEXT NOT NULL,
              parentPolicyId TEXT,
              classification TEXT NOT NULL,
              initialStatus TEXT NOT NULL,
              policyJson TEXT NOT NULL,
              accountRiskProfileId TEXT NOT NULL,
              accountRiskProfileHash TEXT NOT NULL,
              contentHash TEXT NOT NULL UNIQUE,
              createdAt TEXT NOT NULL,
              UNIQUE(policyKey, version)
            );
            CREATE TABLE IF NOT EXISTS StrategyExecutionPolicyEvents (
              eventId TEXT PRIMARY KEY,
              policyId TEXT NOT NULL,
              policyKey TEXT NOT NULL,
              environment TEXT NOT NULL,
              action TEXT NOT NULL,
              actor TEXT NOT NULL,
              reason TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_strategy_execution_policy_events
              ON StrategyExecutionPolicyEvents(policyKey, createdAt);
            """
        )
        self.connection.commit()
        self._owns_risk_store = risk_profile_store is None
        self.risk_store = risk_profile_store or RiskProfileStore(risk_profile_store_path)

    def close(self) -> None:
        self.connection.close()
        if self._owns_risk_store:
            self.risk_store.close()

    def create_policy(
        self,
        policy: dict[str, Any],
        *,
        status: str = "draft",
        parent_policy_id: str | None = None,
    ) -> dict[str, Any]:
        values = dict(policy)
        policy_key = str(values.get("policyKey") or "")
        if values.get("version") is None:
            row = self.connection.execute(
                "SELECT MAX(version) AS maximum FROM StrategyExecutionPolicies WHERE policyKey = ?",
                (policy_key,),
            ).fetchone()
            values["version"] = int(row["maximum"] or 0) + 1
        environment = str(values.get("environment") or "")
        active_risk = self.risk_store.get_active_profile(environment)
        if active_risk is None:
            raise ValueError("No active account RiskProfile exists")
        account_profile = active_risk["profile"]
        validate_strategy_execution_policy(values, account_profile)
        parent = self.get_policy(parent_policy_id) if parent_policy_id else None
        if parent and parent["policyKey"] != policy_key:
            raise ValueError("Parent strategy execution policy key differs")
        classification = _classification(parent["policy"] if parent else None, values)
        identity = {
            "policyKey": policy_key,
            "version": int(values["version"]),
            "policy": values,
            "parentPolicyId": parent_policy_id,
            "accountRiskProfileId": active_risk["riskProfileId"],
            "accountRiskProfileHash": active_risk["contentHash"],
        }
        content_hash = _hash(identity)
        policy_id = "strategy_policy_" + content_hash
        existing = self.connection.execute(
            "SELECT * FROM StrategyExecutionPolicies WHERE policyKey = ? AND version = ?",
            (policy_key, int(values["version"])),
        ).fetchone()
        if existing:
            if existing["contentHash"] != content_hash:
                raise ValueError("Strategy execution policy version already exists with different content")
            return self._row(existing)
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO StrategyExecutionPolicies(
                  policyId, policyKey, version, environment, strategyId,
                  releaseId, releaseHash, parentPolicyId, classification,
                  initialStatus, policyJson, accountRiskProfileId,
                  accountRiskProfileHash, contentHash, createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    policy_id,
                    policy_key,
                    int(values["version"]),
                    environment,
                    values["strategyId"],
                    values["releaseId"],
                    values["releaseHash"],
                    parent_policy_id,
                    classification,
                    status,
                    _canonical(values),
                    active_risk["riskProfileId"],
                    active_risk["contentHash"],
                    content_hash,
                    _now(),
                ),
            )
        return self.get_policy(policy_id)

    def bootstrap_policy(self, identity: dict[str, Any]) -> dict[str, Any]:
        """Create the first editable draft from a frozen identity and active risk cap."""
        values = dict(identity)
        _reject_sensitive(values, "identity")
        allowed = {"environment", "strategyId", "releaseId", "releaseHash", "name"}
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise ValueError("Unsupported strategy bootstrap fields: " + ",".join(unknown))
        for field in allowed:
            if not str(values.get(field) or "").strip():
                raise ValueError(f"Strategy bootstrap identity is incomplete: {field}")

        environment = str(values["environment"])
        strategy_id = str(values["strategyId"])
        release_id = str(values["releaseId"])
        release_hash = str(values["releaseHash"])
        existing = [
            row
            for row in self.list_policies(environment=environment, strategy_id=strategy_id)
            if row["releaseId"] == release_id and row["releaseHash"] == release_hash
        ]
        if existing:
            return max(existing, key=lambda row: int(row["version"]))

        active_risk = self.risk_store.get_active_profile(environment)
        if active_risk is None:
            raise ValueError("No active account RiskProfile exists")
        profile = active_risk["profile"]
        policy_key = (
            f"{environment}:{strategy_id}:"
            f"{hashlib.sha256(release_hash.encode('utf-8')).hexdigest()[:12]}"
        )
        reward_risk = float(profile.get("rewardRiskRatio") or 2.0)
        policy = {
            "schemaVersion": "strategy_execution_policy_v1",
            "policyKey": policy_key,
            "environment": environment,
            "strategyId": strategy_id,
            "releaseId": release_id,
            "releaseHash": release_hash,
            "name": str(values["name"]),
            "allocationUsdt": float(profile["capitalLimitUsdt"]),
            "maxOrderNotionalUsdt": float(profile["maxOrderNotionalUsdt"]),
            "riskPerTradePercent": float(profile["riskPerTradePercent"]),
            "riskPerTradeUsdt": float(profile["riskPerTradeUsdt"]),
            "maxLeverage": int(profile["maxLeverage"]),
            "marginMode": "isolated",
            "maxConcurrentPositions": int(profile["maxPositionsPerStrategy"]),
            "maxPositionsPerSymbol": int(profile["maxPositionsPerSymbol"]),
            "scanTopN": int(profile["scanTopN"]),
            "minimumQuoteTurnoverUsdt": 1_000_000.0,
            "minimumDepthNotionalUsdt": 25_000.0,
            "targetSignalToOrderSeconds": 5.0,
            "maximumSignalAgeSeconds": 10.0,
            "criticalLatencyFailureSeconds": 20.0,
            "orderAckTimeoutSeconds": 5.0,
            "cooldownAfterLossMinutes": int(profile["cooldownAfterLossMinutes"]),
            "feeRate": float(profile["feeRate"]),
            "slippageRate": float(profile["slippageRate"]),
            "stopPolicy": {
                "type": "atr",
                "atrMultiple": 1.2,
                "maximumLossR": 1.0,
            },
            "exitPolicy": {
                "type": "hybrid_trailing",
                "initialTargetR": reward_risk,
                "trailingAtrMultiple": 1.5,
                "partialTakeProfitR": min(1.0, reward_risk),
                "partialTakeProfitPercent": 50.0,
            },
        }
        return self.create_policy(policy)

    def create_revision(
        self,
        parent_policy_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        parent = self.get_policy(parent_policy_id)
        protected = sorted(set(changes) & _IDENTITY_FIELDS)
        if protected:
            raise ValueError("Policy revision cannot change frozen identity: " + ",".join(protected))
        values = {**parent["policy"], **dict(changes)}
        values.pop("version", None)
        return self.create_policy(values, parent_policy_id=parent_policy_id)

    def get_policy(self, policy_id: str | None) -> dict[str, Any]:
        if not policy_id:
            raise KeyError("Strategy execution policy not found")
        row = self.connection.execute(
            "SELECT * FROM StrategyExecutionPolicies WHERE policyId = ?",
            (policy_id,),
        ).fetchone()
        if row is None:
            raise KeyError("Strategy execution policy not found")
        return self._row(row)

    def list_policies(
        self,
        *,
        environment: str | None = None,
        strategy_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        values: list[str] = []
        if environment:
            clauses.append("environment = ?")
            values.append(environment)
        if strategy_id:
            clauses.append("strategyId = ?")
            values.append(strategy_id)
        query = "SELECT * FROM StrategyExecutionPolicies"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY policyKey, version"
        return [self._row(row) for row in self.connection.execute(query, values).fetchall()]

    def activate(
        self,
        policy_id: str,
        *,
        actor: str,
        confirmation: str,
        reason: str,
    ) -> dict[str, Any]:
        policy = self.get_policy(policy_id)
        if actor != "user_manual":
            raise PermissionError("Strategy policy activation requires user_manual")
        requires_exact = policy["classification"] != "lower_risk"
        if requires_exact and confirmation != STRATEGY_POLICY_ACTIVATION_CONFIRMATION:
            raise PermissionError("Exact strategy policy activation confirmation is required")
        current = self.get_active_policy(policy["policyKey"])
        if current and current["policyId"] == policy_id:
            return {"activePolicy": current, "event": None, "executionEnabled": False}
        event = {
            "eventId": "strategy_policy_event_" + uuid.uuid4().hex,
            "policyId": policy_id,
            "policyKey": policy["policyKey"],
            "environment": policy["environment"],
            "action": "activated",
            "actor": actor,
            "reason": str(reason or "strategy_policy_activation"),
            "createdAt": _now(),
        }
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO StrategyExecutionPolicyEvents(
                  eventId, policyId, policyKey, environment, action,
                  actor, reason, createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(event[field] for field in (
                    "eventId", "policyId", "policyKey", "environment",
                    "action", "actor", "reason", "createdAt",
                )),
            )
        return {
            "activePolicy": self.get_policy(policy_id),
            "event": event,
            "executionEnabled": False,
        }

    def get_active_policy(self, policy_key: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT p.* FROM StrategyExecutionPolicyEvents e
            JOIN StrategyExecutionPolicies p ON p.policyId = e.policyId
            WHERE e.policyKey = ? AND e.action = 'activated'
            ORDER BY e.createdAt DESC, e.rowid DESC LIMIT 1
            """,
            (policy_key,),
        ).fetchone()
        return self._row(row) if row else None

    def list_events(self, policy_key: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM StrategyExecutionPolicyEvents"
        values: tuple[str, ...] = ()
        if policy_key:
            query += " WHERE policyKey = ?"
            values = (policy_key,)
        query += " ORDER BY createdAt, rowid"
        return [dict(row) for row in self.connection.execute(query, values).fetchall()]

    def _row(self, row: sqlite3.Row) -> dict[str, Any]:
        active = self.connection.execute(
            """
            SELECT policyId FROM StrategyExecutionPolicyEvents
            WHERE policyKey = ? AND action = 'activated'
            ORDER BY createdAt DESC, rowid DESC LIMIT 1
            """,
            (row["policyKey"],),
        ).fetchone()
        if active and active["policyId"] == row["policyId"]:
            status = "active"
        elif self.connection.execute(
            "SELECT 1 FROM StrategyExecutionPolicyEvents WHERE policyId = ? LIMIT 1",
            (row["policyId"],),
        ).fetchone():
            status = "superseded"
        else:
            status = row["initialStatus"]
        return {
            "policyId": row["policyId"],
            "policyKey": row["policyKey"],
            "version": int(row["version"]),
            "environment": row["environment"],
            "strategyId": row["strategyId"],
            "releaseId": row["releaseId"],
            "releaseHash": row["releaseHash"],
            "parentPolicyId": row["parentPolicyId"],
            "classification": row["classification"],
            "status": status,
            "policy": json.loads(row["policyJson"]),
            "accountRiskProfileId": row["accountRiskProfileId"],
            "accountRiskProfileHash": row["accountRiskProfileHash"],
            "contentHash": row["contentHash"],
            "createdAt": row["createdAt"],
        }
