"""Read-only V47 evidence for OKX Demo runtime, releases, and scan funnels."""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _connect_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _load_releases(release_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(release_dir.glob("*.json")):
        before = _sha256(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        strategy = payload.get("strategy") if isinstance(payload.get("strategy"), dict) else {}
        market = (
            strategy.get("marketDefinition")
            if isinstance(strategy.get("marketDefinition"), dict)
            else {}
        )
        mode = str(payload.get("releaseMode") or "")
        legacy = mode == "experimental_override"
        rows.append(
            {
                "contractFile": path.name,
                "releaseId": str(payload.get("demoReleaseId") or ""),
                "releaseHash": before,
                "contractHash": str(payload.get("contractHash") or ""),
                "strategyCandidateId": str(payload.get("strategyCandidateId") or ""),
                "timeframe": str(market.get("timeframe") or ""),
                "universeMode": str((market.get("universePolicy") or {}).get("mode") or ""),
                "originalReleaseMode": mode,
                "overlayClassification": (
                    "legacy_experimental_override" if legacy else "current_release"
                ),
                "executionAllowed": False if legacy else None,
                "strategyQualificationAllowed": False if legacy else None,
                "forwardEvidenceAllowed": False if legacy else None,
                "livePromotionAllowed": False if legacy else None,
                "fileHashUnchanged": before == _sha256(path),
                "instrumentType": str(market.get("instrumentType") or ""),
                "settleCurrency": str(market.get("settleCurrency") or ""),
            }
        )
    return rows


def _latest_universe(path: Path) -> dict[str, Any]:
    with _connect_read_only(path) as connection:
        row = connection.execute(
            "SELECT projectionJson, generatedAt FROM DemoInstrumentUniverseCache "
            "ORDER BY generatedAt DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return {"status": "unavailable", "eligibleInstrumentIds": []}
    payload = json.loads(row["projectionJson"])
    payload["cacheRecordGeneratedAt"] = row["generatedAt"]
    return payload


def _runtime_evidence(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    with _connect_read_only(path) as connection:
        runtime_row = connection.execute(
            "SELECT * FROM AutoExecutionRuntime WHERE environment = 'okx_demo'"
        ).fetchone()
        events = connection.execute(
            "SELECT eventType, payloadJson, createdAt FROM AutoExecutionEvents "
            "WHERE environment = 'okx_demo' ORDER BY eventId"
        ).fetchall()
    runtime = dict(runtime_row) if runtime_row is not None else {"status": "unavailable"}
    funnel_rows: list[dict[str, Any]] = []
    blockers: Counter[tuple[str, str]] = Counter()
    blocker_latest: dict[tuple[str, str], str] = {}
    for row in events:
        try:
            payload = json.loads(row["payloadJson"])
        except (TypeError, json.JSONDecodeError):
            payload = {}
        event_type = str(row["eventType"])
        if event_type == "heartbeat_completed":
            audit = payload.get("evaluationAudit") if isinstance(payload.get("evaluationAudit"), dict) else {}
            market = audit.get("marketSummary") if isinstance(audit.get("marketSummary"), dict) else {}
            sequence = str(audit.get("closeSequenceId") or payload.get("closeSequenceId") or "")
            funnel_rows.append(
                {
                    "eventType": event_type,
                    "createdAt": row["createdAt"],
                    "closeSequenceId": sequence,
                    "timeframe": sequence.partition(":")[0],
                    "evaluatedReleaseCount": int(audit.get("evaluatedReleaseCount") or 0),
                    "marketInstrumentCount": int(market.get("totalInstrumentCount") or 0),
                    "liquidityEligibleCount": int(market.get("liquidityEligibleCount") or 0),
                    "deepScreenCount": int(market.get("deepScreenCount") or 0),
                    "matchedSignalCount": int(audit.get("matchedSignalCount") or 0),
                    "orderAttemptCount": int(audit.get("orderAttemptCount") or 0),
                    "createdOrderCount": int(audit.get("createdOrderCount") or 0),
                    "exchangeAcceptedEvidence": (
                        "available_in_execution_store" if int(audit.get("createdOrderCount") or 0) else "not_reached"
                    ),
                }
            )
        if event_type in {"heartbeat_blocked", "heartbeat_degraded", "heartbeat_failed"}:
            reasons = payload.get("blockers")
            if not isinstance(reasons, list):
                reasons = [payload.get("reason") or "unknown"]
            for reason in reasons:
                key = (event_type, str(reason))
                blockers[key] += 1
                blocker_latest[key] = str(row["createdAt"])
    blocker_rows = [
        {
            "eventType": event_type,
            "blocker": blocker,
            "count": count,
            "latestAt": blocker_latest[(event_type, blocker)],
        }
        for (event_type, blocker), count in sorted(blockers.items())
    ]
    return runtime, funnel_rows, blocker_rows


def _credential_audit(
    metadata: Mapping[str, Any], process_credential_injected: bool, generated_at: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    stored = bool(metadata.get("stored"))
    if process_credential_injected:
        source = "process_environment"
    elif stored:
        source = "windows_credential_manager"
    else:
        source = "missing"
    vault_status = str(metadata.get("status") or "unknown")
    audit = {
        "credentialSource": source,
        "credentialValueInArtifact": False,
        "credentialValueLogged": False,
        "currentProcessCredentialReady": process_credential_injected,
        "generatedAt": generated_at,
        "osCredentialVaultStored": stored,
        "osCredentialVaultSupported": bool(metadata.get("supported")),
        "processCredentialInjected": process_credential_injected,
        "rawCredentialDatabasePersisted": False,
        "rawCredentialFilePersisted": False,
        "vaultValidationStatus": (
            "stored_not_validated_in_read_only_audit" if stored else vault_status
        ),
    }
    sidecar = {
        "classification": source,
        "currentAuditProcessOnly": True,
        "generatedAt": generated_at,
        "historicalBlockedCredentialStatusMeaning": (
            "The evidence process did not bootstrap the vault; it does not mean Demo integration is absent."
        ),
        "rawCredentialMaterialIncluded": False,
    }
    return audit, sidecar


def _private_read_audit(evidence: Mapping[str, Any] | None, generated_at: str) -> dict[str, Any]:
    source = dict(evidence or {})
    return {
        "currentAuditNetworkRequestMade": False,
        "currentAuditStatus": "not_attempted_read_only_audit",
        "generatedAt": generated_at,
        "historicalEvidenceNetworkRequestMade": bool(source.get("networkRequestMade")),
        "historicalEvidenceStatus": source.get("status") or "unavailable",
        "privateReadClaimedByCurrentAudit": False,
        "rawPrivatePayloadStored": False,
    }

def _manifest(root: Path, generated_at: str) -> dict[str, Any]:
    artifacts = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.name == "artifact_manifest.json":
            continue
        artifacts.append(
            {"bytes": path.stat().st_size, "path": path.name, "sha256": _sha256(path)}
        )
    return {"artifactCount": len(artifacts), "artifacts": artifacts, "generatedAt": generated_at}


def generate_demo_truth_audit(
    *,
    release_dir: str | Path,
    runtime_db: str | Path,
    universe_db: str | Path,
    output_dir: str | Path,
    credential_metadata: Mapping[str, Any],
    process_credential_injected: bool,
    private_read_evidence: Mapping[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    timestamp = generated_at or _now()
    release_root = Path(release_dir).expanduser().resolve()
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    releases = _load_releases(release_root)
    universe = _latest_universe(Path(universe_db))
    runtime, funnel, blockers = _runtime_evidence(Path(runtime_db))
    credential, vault_sidecar = _credential_audit(
        credential_metadata, process_credential_injected, timestamp
    )

    eligible_ids = list(universe.get("eligibleInstrumentIds") or [])
    compatibility = []
    for row in releases:
        compatible = (
            row["instrumentType"] == "SWAP"
            and row["settleCurrency"] == "USDT"
            and bool(eligible_ids)
        )
        compatibility.append(
            {
                "releaseId": row["releaseId"],
                "strategyCandidateId": row["strategyCandidateId"],
                "timeframe": row["timeframe"],
                "universeMode": row["universeMode"],
                "authenticatedEligibleInstrumentCount": len(eligible_ids),
                "compatibilityStatus": (
                    "compatible_dynamic_universe" if compatible else "blocked_no_authenticated_overlap"
                ),
            }
        )

    latest_batch = funnel[-1] if funnel else {"status": "unavailable"}
    truth = {
        "auditMode": "read_only",
        "generatedAt": timestamp,
        "immutableReleaseFilesChanged": False,
        "latestCompletedBatch": latest_batch,
        "legacyReleaseCount": sum(
            row["overlayClassification"] == "legacy_experimental_override" for row in releases
        ),
        "releaseCount": len(releases),
        "runtime": runtime,
        "universe": {
            "authenticatedEligibleInstrumentCount": len(eligible_ids),
            "demoAccountInstrumentCount": universe.get("demoAccountInstrumentCount"),
            "publicUniverseCount": universe.get("publicUniverseCount"),
            "rawPrivatePayloadStored": bool(universe.get("rawPrivatePayloadStored")),
            "status": universe.get("status"),
        },
    }
    _write_json(root / "demo_runtime_truth_audit.json", truth)
    _write_json(root / "demo_credential_source_audit.json", credential)
    _write_json(root / "demo_vault_vs_process_classification_sidecar.json", vault_sidecar)
    _write_json(root / "demo_private_read_audit.json", _private_read_audit(private_read_evidence, timestamp))
    _write_csv(root / "legacy_demo_release_inventory.csv", releases)
    _write_csv(root / "release_symbol_compatibility_matrix.csv", compatibility)
    _write_csv(root / "release_scan_funnel.csv", funnel)
    _write_csv(root / "demo_runtime_blocker_matrix.csv", blockers)
    _write_json(root / "artifact_manifest.json", _manifest(root, timestamp))
    return {
        "legacyReleaseCount": truth["legacyReleaseCount"],
        "releaseCount": len(releases),
        "status": "completed_read_only",
    }
