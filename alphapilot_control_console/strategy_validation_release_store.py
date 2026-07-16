"""Immutable local import store for formal strategy-validation releases."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from .advisory_r_exit_policy import exit_policy_hash, validate_canonical_exit_policy
from .config import DATA_DIR
from .strategy_validation_hashing import canonical_bytes, reject_sensitive_fields, stable_hash


DEFAULT_RELEASE_DB = DATA_DIR / "strategy_validation_releases.sqlite"
DEFAULT_CONTRACT_DIR = DATA_DIR / "strategy_validation_release_contracts"

REQUIRED_RELEASE_FIELDS = {
    "releaseId",
    "releaseHash",
    "campaignId",
    "candidateId",
    "strategyId",
    "strategyFamilyId",
    "marketMechanismId",
    "strategyDefinitionHash",
    "externalReferenceManifestHash",
    "dataSnapshotHash",
    "factorRegistryHash",
    "factorShortlistHash",
    "factorDefinitionHashes",
    "factorRoles",
    "preregistrationHash",
    "costModelHash",
    "riskConfigHash",
    "riskProfile",
    "backtestReportHash",
    "formalGateHash",
    "releasePurpose",
    "evidenceClass",
    "environment",
    "approvalRequired",
    "approved",
    "immutable",
    "createdAt",
}

REQUIRED_V2_RELEASE_FIELDS = {
    "schemaVersion",
    "releaseId",
    "releaseHash",
    "campaignId",
    "strategyId",
    "familyId",
    "strategyDefinitionHash",
    "exitPolicyVersion",
    "exitPolicyMode",
    "exitPolicyHash",
    "canonicalExitPolicy",
    "dataSnapshotHash",
    "preregistrationHash",
    "trialLedgerHash",
    "statisticalAuditHash",
    "walkForwardHash",
    "lockedOosHash",
    "costModelHash",
    "riskConfigHash",
    "formalGateHash",
    "environment",
    "approvalRequired",
    "approved",
    "liveEligible",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _validate_release_identity(payload: Mapping[str, Any]) -> None:
    body = {key: value for key, value in payload.items() if key not in {"releaseId", "releaseHash"}}
    expected_release_hash = stable_hash(body, "strategy_validation_release")
    if payload.get("releaseHash") != expected_release_hash:
        raise ValueError("release hash mismatch")
    expected_release_id = stable_hash({"releaseHash": expected_release_hash}, "validation_release")
    if payload.get("releaseId") != expected_release_id:
        raise ValueError("release id mismatch")


def _validate_v1_release(payload: Mapping[str, Any]) -> None:
    missing = sorted(REQUIRED_RELEASE_FIELDS - set(payload))
    if missing:
        raise ValueError(f"strategy-validation release is missing fields: {', '.join(missing)}")
    if payload.get("releasePurpose") != "strategy_forward_validation":
        raise ValueError("only strategy_forward_validation releases can be imported")
    if payload.get("evidenceClass") != "demo_strategy_validation":
        raise ValueError("engineering, shadow, local-history, and legacy evidence are excluded")
    if payload.get("environment") != "demo":
        raise ValueError("strategy-validation release must target Demo")
    if payload.get("approvalRequired") is not True or payload.get("approved") is not False:
        raise ValueError("release must arrive unapproved and require manual approval")
    if payload.get("immutable") is not True:
        raise ValueError("release must be immutable")
    if not isinstance(payload.get("factorDefinitionHashes"), list) or not payload["factorDefinitionHashes"]:
        raise ValueError("factor definition hashes are required")
    if not isinstance(payload.get("factorRoles"), Mapping) or not payload["factorRoles"]:
        raise ValueError("factor roles are required")

    risk_profile = payload.get("riskProfile")
    if not isinstance(risk_profile, Mapping):
        raise ValueError("risk profile is required")
    risk_body = {key: value for key, value in risk_profile.items() if key != "riskConfigHash"}
    expected_risk_hash = stable_hash(risk_body, "demo_risk")
    if risk_profile.get("riskConfigHash") != expected_risk_hash:
        raise ValueError("risk profile hash mismatch")
    if payload.get("riskConfigHash") != expected_risk_hash:
        raise ValueError("release risk hash mismatch")
    if float(risk_profile.get("minimumTargetR") or 0) < 2.0:
        raise ValueError("minimum target must remain at least 2R")
    for key in (
        "stopWideningAllowed",
        "addingToLossAllowed",
        "martingaleAllowed",
        "automaticParameterChangeAllowed",
    ):
        if risk_profile.get(key) is not False:
            raise ValueError(f"unsafe risk option must remain false: {key}")


def _validate_v2_release(payload: Mapping[str, Any]) -> None:
    missing = sorted(REQUIRED_V2_RELEASE_FIELDS - set(payload))
    if missing:
        raise ValueError(f"strategy-validation release is missing fields: {', '.join(missing)}")
    if payload.get("environment") != "demo":
        raise ValueError("strategy-validation release must target Demo")
    if payload.get("approvalRequired") is not True or payload.get("approved") is not False:
        raise ValueError("release must arrive unapproved and require manual approval")
    if payload.get("liveEligible") is not False:
        raise ValueError("Advisory-R release must not be live eligible")
    for field in REQUIRED_V2_RELEASE_FIELDS - {
        "approved",
        "approvalRequired",
        "liveEligible",
        "canonicalExitPolicy",
    }:
        if not str(payload.get(field) or "").strip():
            raise ValueError(f"strategy-validation release field is empty: {field}")

    policy = validate_canonical_exit_policy(payload.get("canonicalExitPolicy"))
    if payload.get("exitPolicyVersion") != policy["version"]:
        raise ValueError("exit policy version mismatch")
    if payload.get("exitPolicyMode") != policy["mode"]:
        raise ValueError("exit policy mode mismatch")
    if payload.get("exitPolicyHash") != exit_policy_hash(policy):
        raise ValueError("exit policy hash mismatch")


def validate_strategy_validation_release(payload: Mapping[str, Any]) -> dict[str, Any]:
    reject_sensitive_fields(payload)
    schema_version = payload.get("schemaVersion")
    if schema_version == "strategy_validation_release_v1":
        _validate_v1_release(payload)
    elif schema_version == "strategy_validation_release_v2":
        _validate_v2_release(payload)
    else:
        raise ValueError("unsupported strategy-validation release schema")

    _validate_release_identity(payload)
    return dict(payload)


class StrategyValidationReleaseStore:
    def __init__(
        self,
        path: Path | str = DEFAULT_RELEASE_DB,
        contract_dir: Path | str = DEFAULT_CONTRACT_DIR,
    ):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.contract_dir = Path(contract_dir)
        self.contract_dir.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS StrategyValidationReleases (
              releaseId TEXT PRIMARY KEY,
              releaseHash TEXT NOT NULL UNIQUE,
              campaignId TEXT NOT NULL,
              candidateId TEXT NOT NULL,
              strategyId TEXT NOT NULL,
              riskConfigHash TEXT NOT NULL,
              canonicalSha256 TEXT NOT NULL,
              canonicalBytes BLOB NOT NULL,
              contractPath TEXT NOT NULL,
              status TEXT NOT NULL,
              importedAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_strategy_validation_campaign
              ON StrategyValidationReleases(campaignId, importedAt);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def import_bytes(self, raw: bytes) -> dict[str, Any]:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("release must be valid UTF-8 JSON") from error
        if not isinstance(payload, Mapping):
            raise ValueError("release JSON must be an object")
        normalized = validate_strategy_validation_release(payload)
        if raw != canonical_bytes(normalized):
            raise ValueError("release bytes must use canonical JSON")
        release_id = str(normalized["releaseId"])
        release_hash = str(normalized["releaseHash"])
        digest = hashlib.sha256(raw).hexdigest()
        existing = self.connection.execute(
            "SELECT * FROM StrategyValidationReleases WHERE releaseId = ? OR releaseHash = ?",
            (release_id, release_hash),
        ).fetchone()
        if existing:
            if bytes(existing["canonicalBytes"]) != raw:
                raise ValueError("release identity conflicts with changed canonical bytes")
            return {**self._row_to_result(existing), "importStatus": "already_imported"}

        path = self.contract_dir / f"{release_hash}.json"
        if path.exists() and path.read_bytes() != raw:
            raise ValueError("hash-addressed release contract conflicts with existing bytes")
        if not path.exists():
            path.write_bytes(raw)
        imported_at = _now()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO StrategyValidationReleases(
                  releaseId, releaseHash, campaignId, candidateId, strategyId,
                  riskConfigHash, canonicalSha256, canonicalBytes, contractPath,
                  status, importedAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    release_id,
                    release_hash,
                    normalized["campaignId"],
                    normalized.get("candidateId") or normalized["strategyId"],
                    normalized["strategyId"],
                    normalized["riskConfigHash"],
                    digest,
                    raw,
                    str(path),
                    "demo_waiting_approval",
                    imported_at,
                ),
            )
        row = self.connection.execute(
            "SELECT * FROM StrategyValidationReleases WHERE releaseId = ?", (release_id,)
        ).fetchone()
        return {**self._row_to_result(row), "importStatus": "imported"}

    def import_file(self, path: Path | str) -> dict[str, Any]:
        return self.import_bytes(Path(path).read_bytes())

    def get(self, release_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM StrategyValidationReleases WHERE releaseId = ?", (release_id,)
        ).fetchone()
        return self._row_to_result(row) if row else None

    def require(self, release_id: str) -> dict[str, Any]:
        result = self.get(release_id)
        if result is None:
            raise KeyError("strategy-validation release not found")
        return result

    def payload(self, release_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT canonicalBytes FROM StrategyValidationReleases WHERE releaseId = ?", (release_id,)
        ).fetchone()
        if row is None:
            raise KeyError("strategy-validation release not found")
        payload = json.loads(bytes(row["canonicalBytes"]).decode("utf-8"))
        validate_strategy_validation_release(payload)
        if bytes(row["canonicalBytes"]) != canonical_bytes(payload):
            raise ValueError("stored canonical release bytes changed")
        return payload

    def list_releases(self, campaign_id: str | None = None) -> list[dict[str, Any]]:
        if campaign_id:
            rows = self.connection.execute(
                "SELECT * FROM StrategyValidationReleases WHERE campaignId = ? ORDER BY importedAt, rowid",
                (campaign_id,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM StrategyValidationReleases ORDER BY importedAt, rowid"
            ).fetchall()
        return [self._row_to_result(row) for row in rows]

    @staticmethod
    def _row_to_result(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "releaseId": row["releaseId"],
            "releaseHash": row["releaseHash"],
            "campaignId": row["campaignId"],
            "candidateId": row["candidateId"],
            "strategyId": row["strategyId"],
            "riskConfigHash": row["riskConfigHash"],
            "canonicalSha256": row["canonicalSha256"],
            "contractPath": row["contractPath"],
            "status": row["status"],
            "importedAt": row["importedAt"],
            "runtimeEligible": False,
        }
