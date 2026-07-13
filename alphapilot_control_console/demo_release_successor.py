"""Rollback-safe migration from immutable Top20 Demo releases to Top100 successors."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .demo_universe_policy import (
    DEMO_DEEP_SCREENING_LIMIT,
    DEMO_UNIVERSE_POLICY_VERSION,
)
from .evolution_demo_service import _contract_hash, validate_demo_contract
from .unified_auto_execution_store import UnifiedAutoExecutionStore


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Successor migration timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _replace_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    source.replace(target)


def _policy(contract: dict[str, Any]) -> dict[str, Any]:
    strategy = contract.get("strategy") if isinstance(contract.get("strategy"), dict) else {}
    market = strategy.get("marketDefinition") if isinstance(strategy.get("marketDefinition"), dict) else {}
    return market.get("universePolicy") if isinstance(market.get("universePolicy"), dict) else {}


def _is_top100_successor(contract: dict[str, Any]) -> bool:
    policy = _policy(contract)
    return (
        int(policy.get("screeningLimit") or 0) == DEMO_DEEP_SCREENING_LIMIT
        and str(policy.get("policyVersion") or "") == DEMO_UNIVERSE_POLICY_VERSION
        and bool(contract.get("supersedesDemoReleaseId"))
    )


def build_top100_successor(
    predecessor: dict[str, Any],
    created_at: datetime,
) -> dict[str, Any]:
    validate_demo_contract(predecessor)
    if _is_top100_successor(predecessor):
        raise ValueError("Demo release is already a Top100 successor")
    created = _utc(created_at).isoformat()
    result = copy.deepcopy(predecessor)
    strategy = result.get("strategy") if isinstance(result.get("strategy"), dict) else {}
    market = strategy.get("marketDefinition") if isinstance(strategy.get("marketDefinition"), dict) else {}
    policy = market.get("universePolicy") if isinstance(market.get("universePolicy"), dict) else {}
    market["universePolicy"] = {
        **policy,
        "mode": "okx_usdt_linear_perpetual_full_market",
        "screeningLimit": DEMO_DEEP_SCREENING_LIMIT,
        "policyVersion": DEMO_UNIVERSE_POLICY_VERSION,
    }
    strategy["marketDefinition"] = market
    result["strategy"] = strategy
    result["supersedesDemoReleaseId"] = str(predecessor["demoReleaseId"])
    result["successorMetadata"] = {
        "migrationReason": "top100_low_latency_public_market_runtime",
        "createdAt": created,
        "predecessorContractHash": str(predecessor["contractHash"]),
    }
    for key in ("demoReleaseId", "releaseContentHash", "contractHash"):
        result.pop(key, None)
    content_hash = hashlib.sha256(_canonical(result).encode("utf-8")).hexdigest()
    result["releaseContentHash"] = f"demo_release_content_{content_hash}"
    release_hash = hashlib.sha256(
        _canonical(
            {
                "releaseContentHash": result["releaseContentHash"],
                "supersedesDemoReleaseId": result["supersedesDemoReleaseId"],
            }
        ).encode("utf-8")
    ).hexdigest()
    result["demoReleaseId"] = f"demo_release_top100_{release_hash[:32]}"
    result["contractHash"] = _contract_hash(result)
    validate_demo_contract(result)
    return result


def _read_active_contracts(contract_dir: Path) -> list[tuple[Path, bytes, dict[str, Any]]]:
    rows: list[tuple[Path, bytes, dict[str, Any]]] = []
    for path in sorted(contract_dir.glob("demo_release_contract_*.json")):
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Demo release contract is not an object: {path.name}")
        validate_demo_contract(payload)
        rows.append((path, raw, payload))
    return rows


def _latest_manifest(archive_root: Path) -> Path | None:
    manifests = sorted(archive_root.glob("top100_migration_*/migration_manifest.json"))
    return manifests[-1] if manifests else None


def _backup_sqlite(source: UnifiedAutoExecutionStore, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = sqlite3.connect(target)
    try:
        source.connection.backup(backup)
    finally:
        backup.close()


def activate_top100_successors(
    contract_dir: Path | str,
    archive_root: Path | str,
    auto_execution_db: Path | str,
    *,
    expected_count: int = 10,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    active_dir = Path(contract_dir)
    archive_base = Path(archive_root)
    db_path = Path(auto_execution_db)
    active_dir.mkdir(parents=True, exist_ok=True)
    archive_base.mkdir(parents=True, exist_ok=True)
    rows = _read_active_contracts(active_dir)
    expected = max(1, int(expected_count))
    if len(rows) != expected:
        raise RuntimeError(f"Expected {expected} active Demo releases, found {len(rows)}")
    if all(_is_top100_successor(payload) for _, _, payload in rows):
        manifest = _latest_manifest(archive_base)
        if manifest is None:
            raise RuntimeError("Top100 successors exist without a migration manifest")
        return {
            "ok": True,
            "alreadyActive": True,
            "successorCount": len(rows),
            "manifestPath": str(manifest),
        }
    if any(_is_top100_successor(payload) for _, _, payload in rows):
        raise RuntimeError("Mixed predecessor and Top100 successor set is forbidden")

    store = UnifiedAutoExecutionStore(db_path)
    try:
        runtime = store.runtime("okx_demo")
        if runtime.get("desiredEnabled"):
            raise RuntimeError("Disable Demo automatic execution before successor activation")
        created = _utc(created_at or datetime.now(UTC))
        stamp = created.strftime("%Y%m%dT%H%M%S%fZ")
        archive_dir = archive_base / f"top100_migration_{stamp}"
        staging_dir = archive_base / f".staging_{stamp}"
        rollback_dir = archive_base / f".rollback_{stamp}"
        if archive_dir.exists() or staging_dir.exists() or rollback_dir.exists():
            raise RuntimeError("Successor migration staging identity already exists")
        archive_dir.mkdir(parents=True)
        staging_dir.mkdir(parents=True)
        rollback_dir.mkdir(parents=True)

        migrations: list[dict[str, Any]] = []
        successor_paths: list[Path] = []
        predecessor_ids: list[str] = []
        for path, raw, payload in rows:
            successor = build_top100_successor(payload, created)
            successor_name = f"demo_release_contract_{successor['demoReleaseId']}.json"
            successor_path = staging_dir / successor_name
            successor_bytes = _json_bytes(successor)
            successor_path.write_bytes(successor_bytes)
            (archive_dir / path.name).write_bytes(raw)
            predecessor_id = str(payload["demoReleaseId"])
            predecessor_ids.append(predecessor_id)
            successor_paths.append(successor_path)
            migrations.append(
                {
                    "predecessorDemoReleaseId": predecessor_id,
                    "successorDemoReleaseId": str(successor["demoReleaseId"]),
                    "predecessorContractHash": str(payload["contractHash"]),
                    "successorContractHash": str(successor["contractHash"]),
                    "predecessorFileSha256": _sha256_bytes(raw),
                    "successorFileSha256": _sha256_bytes(successor_bytes),
                }
            )
        manifest = {
            "schemaVersion": "alphapilot_demo_top100_migration_v1",
            "createdAt": created.isoformat(),
            "expectedCount": expected,
            "universePolicyVersion": DEMO_UNIVERSE_POLICY_VERSION,
            "screeningLimit": DEMO_DEEP_SCREENING_LIMIT,
            "migrations": migrations,
        }
        manifest_path = archive_dir / "migration_manifest.json"
        manifest_path.write_bytes(_json_bytes(manifest))
        database_backup = archive_dir / "unified_auto_execution.before.sqlite"
        _backup_sqlite(store, database_backup)

        installed_successors: list[Path] = []
        moved_predecessors: list[tuple[Path, Path]] = []
        try:
            for path, _raw, _payload in rows:
                rollback_path = rollback_dir / path.name
                _replace_file(path, rollback_path)
                moved_predecessors.append((path, rollback_path))
            for staged in successor_paths:
                target = active_dir / staged.name
                _replace_file(staged, target)
                installed_successors.append(target)
            retired = store.retire_checkpoints("okx_demo", predecessor_ids)
            store.append_event(
                "okx_demo",
                "demo_top100_successors_activated",
                {
                    "predecessorCount": len(predecessor_ids),
                    "successorCount": len(installed_successors),
                    "retiredCheckpointCount": retired,
                    "manifestSha256": _sha256_bytes(manifest_path.read_bytes()),
                },
            )
        except Exception as error:
            store.close()
            for path in installed_successors:
                path.unlink(missing_ok=True)
            for original, rollback in moved_predecessors:
                if rollback.exists():
                    _replace_file(rollback, original)
            shutil.copy2(database_backup, db_path)
            shutil.rmtree(staging_dir, ignore_errors=True)
            shutil.rmtree(rollback_dir, ignore_errors=True)
            shutil.rmtree(archive_dir, ignore_errors=True)
            raise RuntimeError("Top100 successor activation failed and was rolled back") from error

        shutil.rmtree(staging_dir, ignore_errors=True)
        shutil.rmtree(rollback_dir, ignore_errors=True)
        return {
            "ok": True,
            "alreadyActive": False,
            "predecessorCount": len(predecessor_ids),
            "successorCount": len(installed_successors),
            "retiredCheckpointCount": retired,
            "manifestPath": str(manifest_path),
            "archivePath": str(archive_dir),
        }
    finally:
        try:
            store.close()
        except sqlite3.ProgrammingError:
            pass
