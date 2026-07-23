"""Independent semantic verifiers for the V62.4.1 acceptance delta.

Each verifier reads and recomputes one evidence domain. The aggregate runner may
compose their results, but no domain verifier delegates to the package-wide
acceptance verifier.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Sequence

from .ai_orchestration.compliance import (
    find_direct_provider_imports,
    find_execution_path_ai_imports,
)
from .ai_orchestration.contracts import AIRequest
from .ai_orchestration.errors import ForbiddenAITaskError, ToolPolicyError
from .ai_orchestration.model_registry import AIModelRegistry
from .ai_orchestration.task_router import AITaskRouter


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_hash_matches(payload: Mapping[str, object]) -> bool:
    expected = str(payload.get("artifactHash") or "")
    unsigned = {key: value for key, value in payload.items() if key != "artifactHash"}
    return bool(expected) and expected == canonical_hash(unsigned)


def _sqlite_table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return {
        str(name): int(connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0])
        for (name,) in rows
    }


def _sqlite_max_sequences(connection: sqlite3.Connection) -> dict[str, int | None]:
    result: dict[str, int | None] = {}
    rows = connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    for (table_name,) in rows:
        columns = [
            str(row[1])
            for row in connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        ]
        sequence_column = next(
            (
                name
                for name in (
                    "sequenceId",
                    "sequence_id",
                    "eventId",
                    "event_id",
                    "id",
                )
                if name in columns
            ),
            None,
        )
        if sequence_column is None:
            continue
        value = connection.execute(
            f'SELECT MAX("{sequence_column}") FROM "{table_name}"'
        ).fetchone()[0]
        if value is None or isinstance(value, int):
            result[str(table_name)] = value
    return result


def verify_sqlite_snapshots(receipts_path: Path | str) -> dict[str, object]:
    """Open every receipt snapshot read-only and recompute SQLite facts."""

    source = Path(receipts_path)
    receipts = _load_json(source)
    if not isinstance(receipts, list):
        return {
            "schemaVersion": "v62_4_1_sqlite_independent_verifier_v1",
            "passed": False,
            "findings": ["receipts_not_a_list"],
            "snapshots": [],
        }
    snapshots: list[dict[str, object]] = []
    all_findings: list[str] = []
    for index, receipt in enumerate(receipts):
        findings: list[str] = []
        if not isinstance(receipt, Mapping):
            all_findings.append(f"receipt_{index}:invalid")
            continue
        snapshot_path = Path(str(receipt.get("snapshotPath") or ""))
        row: dict[str, object] = {
            "sourcePath": str(receipt.get("sourcePath") or ""),
            "snapshotPath": str(snapshot_path),
            "findings": findings,
        }
        if not snapshot_path.is_file():
            findings.append("snapshot_missing")
            snapshots.append(row)
            all_findings.extend(f"snapshot_{index}:{item}" for item in findings)
            continue
        actual_size = snapshot_path.stat().st_size
        actual_hash = _sha256_file(snapshot_path)
        row["sizeBytes"] = actual_size
        row["sha256"] = actual_hash
        if int(receipt.get("sizeBytes") or -1) != actual_size:
            findings.append("size_mismatch")
        if str(receipt.get("sha256") or "") != actual_hash:
            findings.append("hash_mismatch")
        try:
            uri = f"file:{snapshot_path.as_posix()}?mode=ro"
            connection = sqlite3.connect(uri, uri=True)
            integrity_rows = [
                str(item[0]) for item in connection.execute("PRAGMA integrity_check").fetchall()
            ]
            table_counts = _sqlite_table_counts(connection)
            max_sequences = _sqlite_max_sequences(connection)
            schema_rows = [
                {"type": str(item[0]), "name": str(item[1]), "sql": str(item[2] or "")}
                for item in connection.execute(
                    "SELECT type, name, sql FROM sqlite_master "
                    "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
                ).fetchall()
            ]
            user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
            connection.close()
        except sqlite3.DatabaseError as exc:
            findings.append(f"sqlite_error:{type(exc).__name__}")
            snapshots.append(row)
            all_findings.extend(f"snapshot_{index}:{item}" for item in findings)
            continue
        row.update(
            {
                "integrityCheck": integrity_rows,
                "tableCounts": table_counts,
                "maxSequenceByTable": max_sequences,
                "schema": schema_rows,
                "userVersion": user_version,
                "journalMode": journal_mode,
            }
        )
        if integrity_rows != ["ok"]:
            findings.append("integrity_check_failed")
        if str(receipt.get("integrityCheck") or "") != "ok":
            findings.append("receipt_integrity_not_ok")
        expected_counts = receipt.get("tableCounts")
        if not isinstance(expected_counts, Mapping):
            findings.append("receipt_table_counts_missing")
        else:
            for table_name in sorted(set(expected_counts) | set(table_counts)):
                if int(expected_counts.get(table_name, -1)) != int(
                    table_counts.get(str(table_name), -1)
                ):
                    findings.append(f"table_count_mismatch:{table_name}")
        snapshots.append(row)
        all_findings.extend(f"snapshot_{index}:{item}" for item in findings)
    return {
        "schemaVersion": "v62_4_1_sqlite_independent_verifier_v1",
        "passed": not all_findings and len(snapshots) == len(receipts),
        "findings": all_findings,
        "snapshots": snapshots,
    }


def verify_runtime_evidence(evidence_root: Path | str) -> dict[str, object]:
    """Recompute no-order identity, parity and zero-state semantics."""

    root = Path(evidence_root)
    required = {
        "capture": "runtime_identity_capture.json",
        "summary": "runtime_evidence_summary.json",
        "parity": "historical_shadow_parity_1h_1d.json",
        "zero": "zero_state_reconciliation.json",
    }
    findings: list[str] = []
    payloads: dict[str, Mapping[str, object]] = {}
    for key, filename in required.items():
        path = root / filename
        if not path.is_file():
            findings.append(f"missing:{filename}")
            continue
        payload = _load_json(path)
        if not isinstance(payload, Mapping):
            findings.append(f"invalid:{filename}")
            continue
        payloads[key] = payload
        if not _artifact_hash_matches(payload):
            findings.append(f"artifact_hash_mismatch:{filename}")
    if findings:
        return {
            "schemaVersion": "v62_4_1_runtime_independent_verifier_v1",
            "passed": False,
            "findings": findings,
        }
    capture = payloads["capture"]
    summary = payloads["summary"]
    parity = payloads["parity"]
    zero = payloads["zero"]
    identity = capture.get("runtimeIdentity")
    if not isinstance(identity, Mapping) or capture.get("runtimeIdentityHash") != canonical_hash(
        identity
    ):
        findings.append("runtime_identity_hash_mismatch")
    if bool(capture.get("executionAuthority")):
        findings.append("execution_authority_present")
    if int(capture.get("activeExecutionLeaseCount") or 0) != 0:
        findings.append("active_execution_lease_present")
    observation_lease = capture.get("observationLease")
    if not isinstance(observation_lease, Mapping):
        findings.append("observation_lease_missing")
    elif (
        observation_lease.get("leaseClass") != "read_only_observation"
        or bool(observation_lease.get("executionAuthority"))
        or bool(observation_lease.get("exclusiveWriteAuthority"))
    ):
        findings.append("observation_lease_not_read_only")
    for payload_name, payload in (
        ("capture", capture),
        ("summary", summary),
        ("zero", zero),
    ):
        for field in ("newEntriesAllowed", "demoArm", "liveEnabled", "withdrawEnabled"):
            if bool(payload.get(field)):
                findings.append(f"{payload_name}:{field}_unexpected_true")
    if int(capture.get("orderAttemptCount") or 0) != 0:
        findings.append("capture_order_attempt_present")
    if int(summary.get("orderAttemptCount") or 0) != 0:
        findings.append("summary_order_attempt_present")
    if parity.get("status") != "passed" or float(parity.get("parityRate") or 0.0) != 1.0:
        findings.append("shadow_parity_not_passed")
    if set(parity.get("timeframesCovered") or []) != {"1h", "1d"}:
        findings.append("shadow_parity_timeframes_incomplete")
    if not bool(parity.get("orderAccessDisabled")):
        findings.append("shadow_order_access_not_disabled")
    if int(parity.get("orderAttemptCount") or 0) or int(
        parity.get("createdOrderCount") or 0
    ):
        findings.append("shadow_order_activity_present")
    for event in parity.get("events") or []:
        if not isinstance(event, Mapping):
            findings.append("shadow_event_invalid")
            continue
        if not bool(event.get("passed")) or not bool(
            event.get("independentConservationPassed")
        ):
            findings.append(f"shadow_event_failed:{event.get('timeframe')}")
        if int(event.get("orderAttemptCount") or 0) or int(
            event.get("createdOrderCount") or 0
        ):
            findings.append(f"shadow_event_order_activity:{event.get('timeframe')}")
    if zero.get("status") != "passed_historical_zero_state":
        findings.append("zero_state_not_passed")
    for field in (
        "unknownOrderCount",
        "partiallyFilledOrderCount",
        "openPositionCount",
    ):
        if int(zero.get(field) or 0) != 0:
            findings.append(f"zero_state_nonzero:{field}")
    if list(zero.get("unresolvedExecutionRecordIds") or []):
        findings.append("zero_state_unresolved_records")
    if summary.get("runtimeCaptureStatus") != capture.get("status"):
        findings.append("summary_capture_status_mismatch")
    if summary.get("historicalShadowParityStatus") != parity.get("status"):
        findings.append("summary_parity_status_mismatch")
    if summary.get("zeroStateReconciliationStatus") != zero.get("status"):
        findings.append("summary_zero_state_status_mismatch")
    return {
        "schemaVersion": "v62_4_1_runtime_independent_verifier_v1",
        "passed": not findings,
        "findings": sorted(set(findings)),
        "runtimeIdentityHash": capture.get("runtimeIdentityHash"),
        "repositoryCommit": identity.get("repositoryCommit") if isinstance(identity, Mapping) else None,
        "repositoryTag": identity.get("repositoryTag") if isinstance(identity, Mapping) else None,
        "sourceRuntimeOnline": bool(capture.get("sourceRuntimeOnline")),
        "timeframesCovered": sorted(parity.get("timeframesCovered") or []),
    }


def verify_trial_evidence(evidence_root: Path | str) -> dict[str, object]:
    """Recompute campaign and formal counts from preregistration and projections."""

    root = Path(evidence_root)
    required = {
        "prereg": "preregistration.json",
        "summary": "campaign_summary.json",
        "projection": "development_projection.json",
        "handoff": "formal_handoff.json",
        "route": "formal_route.json",
    }
    findings: list[str] = []
    payloads: dict[str, Mapping[str, object]] = {}
    for key, filename in required.items():
        path = root / filename
        if not path.is_file():
            findings.append(f"missing:{filename}")
            continue
        payload = _load_json(path)
        if not isinstance(payload, Mapping):
            findings.append(f"invalid:{filename}")
            continue
        payloads[key] = payload
    if findings:
        return {
            "schemaVersion": "v62_4_1_trial_independent_verifier_v1",
            "passed": False,
            "findings": findings,
        }
    prereg = payloads["prereg"]
    summary = payloads["summary"]
    projection = payloads["projection"]
    handoff = payloads["handoff"]
    route = payloads["route"]
    campaign_ids = {
        str(payload.get("campaignId") or "") for payload in payloads.values()
    }
    if len(campaign_ids) != 1 or not next(iter(campaign_ids), ""):
        findings.append("campaign_identity_mismatch")
    candidate_ids = [str(item) for item in prereg.get("candidateIds") or []]
    trials_by_candidate = prereg.get("trialsByCandidate")
    if not isinstance(trials_by_candidate, Mapping):
        findings.append("trials_by_candidate_missing")
        trials_by_candidate = {}
    prereg_trial_count = sum(
        len(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else 0
        for value in trials_by_candidate.values()
    )
    if int(prereg.get("candidateCount") or 0) != len(candidate_ids):
        findings.append("prereg_candidate_count_mismatch")
    if set(candidate_ids) != {str(item) for item in trials_by_candidate}:
        findings.append("prereg_candidate_trial_keys_mismatch")
    if int(prereg.get("trialCount") or 0) != prereg_trial_count:
        findings.append("prereg_trial_count_mismatch")
    projections = projection.get("projections") or []
    if not isinstance(projections, list):
        projections = []
        findings.append("projection_rows_invalid")
    completed_trial_ids = {
        str(item.get("trialId"))
        for item in projections
        if isinstance(item, Mapping) and item.get("trialId")
    }
    if int(projection.get("projectionCount") or 0) != len(projections):
        findings.append("projection_count_mismatch")
    if int(summary.get("candidateCount") or 0) != len(candidate_ids):
        findings.append("campaign_candidate_count_mismatch")
    if int(summary.get("trialCount") or 0) != prereg_trial_count:
        findings.append("campaign_trial_count_mismatch")
    if int(summary.get("completedTrialCount") or 0) != len(completed_trial_ids):
        findings.append("campaign_completed_trial_count_mismatch")
    ready_candidates = handoff.get("readyCandidates") or []
    blocked_candidates = handoff.get("blockedCandidates") or []
    if int(handoff.get("formalReadyCandidateCount") or 0) != len(ready_candidates):
        findings.append("handoff_ready_count_mismatch")
    if int(handoff.get("blockedCandidateCount") or 0) != len(blocked_candidates):
        findings.append("handoff_blocked_count_mismatch")
    if int(handoff.get("selectedCandidateCount") or 0) != len(ready_candidates) + len(
        blocked_candidates
    ):
        findings.append("handoff_selected_count_mismatch")
    if int(summary.get("formalReadyCandidateCount") or 0) != len(ready_candidates):
        findings.append("summary_ready_count_mismatch")
    if int(summary.get("formalBlockedCandidateCount") or 0) != len(blocked_candidates):
        findings.append("summary_blocked_count_mismatch")
    for field in ("formalRunCount", "resultReadCount", "releaseCount", "orderCount"):
        values = {
            int(payload.get(field) or 0) for payload in (summary, handoff, route)
        }
        if len(values) != 1:
            findings.append(f"{field}_mismatch")
    for payload_name, payload in (
        ("summary", summary),
        ("handoff", handoff),
        ("route", route),
    ):
        if bool(payload.get("demoArm")):
            findings.append(f"{payload_name}:demo_arm_unexpected")
        if int(payload.get("approvalCount") or 0) != 0:
            findings.append(f"{payload_name}:approval_present")
        if int(payload.get("releaseCount") or 0) != 0:
            findings.append(f"{payload_name}:release_present")
        if int(payload.get("orderCount") or 0) != 0:
            findings.append(f"{payload_name}:order_present")
    return {
        "schemaVersion": "v62_4_1_trial_independent_verifier_v1",
        "passed": not findings,
        "findings": sorted(set(findings)),
        "campaignId": next(iter(campaign_ids), ""),
        "candidateCount": len(candidate_ids),
        "trialCount": prereg_trial_count,
        "completedTrialCount": len(completed_trial_ids),
        "formalReadyCandidateCount": len(ready_candidates),
        "formalBlockedCandidateCount": len(blocked_candidates),
        "formalRunCount": int(summary.get("formalRunCount") or 0),
        "resultReadCount": int(summary.get("resultReadCount") or 0),
    }


def _ai_request(
    task_type: str,
    *,
    tool_names: tuple[str, ...] = (),
    multimodal: bool = False,
    coding: bool = False,
) -> AIRequest:
    return AIRequest(
        request_id=f"verify-{task_type}",
        task_type=task_type,
        payload={"evidence": "sanitized"},
        response_schema={"type": "object"},
        sensitivity="internal",
        prompt_version="independent-verifier-v1",
        tool_names=tool_names,
        multimodal=multimodal,
        coding=coding,
    )


def verify_ai_orchestration(
    repository_root: Path | str,
    provider_smoke_path: Path | str,
) -> dict[str, object]:
    """Resolve real routes and source boundaries without provider credentials."""

    root = Path(repository_root)
    smoke = _load_json(Path(provider_smoke_path))
    findings: list[str] = []
    registry_path = root / "config" / "ai_model_registry.json"
    registry = AIModelRegistry.from_path(registry_path)
    registry_projection = registry.describe()
    router = AITaskRouter()
    route_matrix: dict[str, dict[str, object]] = {}
    route_requests = {
        "strategy_hypothesis": {},
        "failure_attribution": {},
        "architecture_review": {},
        "security_review": {},
        "document_analysis": {"multimodal": True},
        "code_review": {"coding": True},
        "historical_batch": {},
        "research_summary": {},
    }
    for task_type, kwargs in route_requests.items():
        route = router.route(_ai_request(task_type, **kwargs))
        providers = [registry.resolve(alias).provider for alias in route.model_aliases]
        route_matrix[task_type] = {
            "mode": route.mode,
            "modelAliases": list(route.model_aliases),
            "providers": providers,
            "requiresHumanOnDisagreement": route.requires_human_on_disagreement,
        }
        if route.mode == "dual" and len(set(providers)) != 2:
            findings.append(f"dual_route_not_independent:{task_type}")
    forbidden_task_checks: dict[str, str] = {}
    for task_type in (
        "order_submission",
        "risk_decision",
        "position_management",
        "reconciliation",
        "approval",
        "arm",
        "withdraw",
    ):
        try:
            router.route(_ai_request(task_type))
        except ForbiddenAITaskError:
            forbidden_task_checks[task_type] = "blocked"
        else:
            forbidden_task_checks[task_type] = "allowed"
            findings.append(f"forbidden_task_allowed:{task_type}")
    try:
        router.route(
            _ai_request(
                "research_summary",
                tool_names=("place_order",),
            )
        )
    except ToolPolicyError:
        forbidden_tool_status = "blocked"
    else:
        forbidden_tool_status = "allowed"
        findings.append("forbidden_tool_allowed:place_order")
    package_root = root / "alphapilot_control_console"
    direct_provider_imports = find_direct_provider_imports(package_root)
    execution_path_ai_imports = find_execution_path_ai_imports(package_root)
    if direct_provider_imports:
        findings.append("direct_provider_imports_present")
    if execution_path_ai_imports:
        findings.append("execution_path_ai_imports_present")
    if not isinstance(smoke, Mapping) or smoke.get("status") != "provider_smoke_passed":
        findings.append("provider_smoke_not_passed")
    checks: dict[str, str] = {}
    if isinstance(smoke, Mapping) and isinstance(smoke.get("checks"), list):
        checks = {
            str(item.get("taskType")): str(item.get("status"))
            for item in smoke["checks"]
            if isinstance(item, Mapping)
        }
    elif isinstance(smoke, Mapping) and isinstance(smoke.get("providers"), Mapping):
        checks = {
            str(name): str(value.get("status"))
            for name, value in smoke["providers"].items()
            if isinstance(value, Mapping)
        }
    if sorted(checks.values()) != ["accepted"] * 3:
        findings.append("provider_smoke_checks_incomplete")
    if bool(smoke.get("executionAuthorized")) or bool(smoke.get("executionAuthority")):
        findings.append("provider_smoke_has_execution_authority")
    if bool(smoke.get("exchangePrivateCredentialsPresent")):
        findings.append("provider_smoke_has_exchange_private_credentials")
    if bool(smoke.get("runtimeArmed")) or bool(smoke.get("demoArm")) or bool(
        smoke.get("liveArm")
    ):
        findings.append("provider_smoke_runtime_armed")
    if bool(smoke.get("withdrawEnabled")):
        findings.append("provider_smoke_withdraw_enabled")
    return {
        "schemaVersion": "v62_4_1_ai_independent_verifier_v1",
        "passed": not findings,
        "findings": sorted(set(findings)),
        "registryHash": registry_projection["registryHash"],
        "routeMatrix": route_matrix,
        "forbiddenTaskChecks": forbidden_task_checks,
        "forbiddenToolCheck": forbidden_tool_status,
        "directProviderImports": direct_provider_imports,
        "executionPathAiImports": execution_path_ai_imports,
        "providerSmokeChecks": checks,
        "realHistoricalFailureCriticWorkflow": "not_run",
    }


_PILOT_ELEMENT_IDS = (
    "strategyCurrentPilot",
    "strategyPilotCampaign",
    "strategyPilotCandidateTrials",
    "strategyPilotStable",
    "strategyPilotFormalReady",
    "strategyPilotFormalBlocked",
)


def verify_ui_projection(
    api_payload: Mapping[str, object],
    html_text: str,
    *,
    expected_campaign_id: str,
) -> dict[str, object]:
    """Compare current Pilot API truth with the production-route DOM contract."""

    findings: list[str] = []
    strategy = api_payload.get("strategy")
    if not isinstance(strategy, Mapping):
        strategy = api_payload
    pilot = strategy.get("currentPilot") if isinstance(strategy, Mapping) else None
    if not isinstance(pilot, Mapping):
        findings.append("current_pilot_missing")
        pilot = {}
    if pilot.get("authority") != "current_v62_4_pilot":
        findings.append("current_pilot_authority_mismatch")
    if str(pilot.get("campaignId") or "") != expected_campaign_id:
        findings.append("current_pilot_campaign_mismatch")
    for field in (
        "candidateCount",
        "trialCount",
        "stableSelectionCount",
        "formalReadyCandidateCount",
        "formalBlockedCandidateCount",
        "formalRunCount",
        "resultReadCount",
    ):
        value = pilot.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            findings.append(f"current_pilot_invalid_count:{field}")
    missing_elements = [
        element_id
        for element_id in _PILOT_ELEMENT_IDS
        if f'id="{element_id}"' not in html_text
    ]
    findings.extend(f"missing_dom_element:{item}" for item in missing_elements)
    return {
        "schemaVersion": "v62_4_1_ui_independent_verifier_v1",
        "passed": not findings,
        "findings": findings,
        "campaignId": pilot.get("campaignId"),
        "pilotCounts": {
            field: pilot.get(field)
            for field in (
                "candidateCount",
                "trialCount",
                "stableSelectionCount",
                "formalReadyCandidateCount",
                "formalBlockedCandidateCount",
                "formalRunCount",
                "resultReadCount",
            )
        },
        "checkedDomElementIds": list(_PILOT_ELEMENT_IDS),
    }


def verify_ui_endpoint(
    base_url: str,
    *,
    expected_campaign_id: str,
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Request the production route and API directly before semantic comparison."""

    normalized = base_url.rstrip("/")
    with urllib.request.urlopen(normalized + "/", timeout=timeout_seconds) as response:
        html_text = response.read().decode("utf-8")
    with urllib.request.urlopen(
        normalized + "/api/strategy-factory/control?fresh=1",
        timeout=timeout_seconds,
    ) as response:
        api_payload = json.loads(response.read().decode("utf-8"))
    result = verify_ui_projection(
        api_payload,
        html_text,
        expected_campaign_id=expected_campaign_id,
    )
    result["baseUrl"] = normalized
    result["httpRequests"] = ["/", "/api/strategy-factory/control?fresh=1"]
    return result


def verify_artifact_manifest(
    package_root: Path | str,
    manifest_path: Path | str,
) -> dict[str, object]:
    """Recompute manifest path, size and SHA-256 independently."""

    root = Path(package_root)
    manifest = _load_json(Path(manifest_path))
    rows = (
        manifest.get("artifacts")
        if isinstance(manifest, Mapping)
        else manifest
        if isinstance(manifest, list)
        else None
    )
    if not isinstance(rows, list):
        return {
            "schemaVersion": "v62_4_1_hash_independent_verifier_v1",
            "passed": False,
            "findings": ["manifest_artifacts_missing"],
            "artifacts": [],
        }
    artifacts: list[dict[str, object]] = []
    findings: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(rows):
        if not isinstance(item, Mapping):
            findings.append(f"manifest_row_invalid:{index}")
            continue
        relative = str(item.get("relativePath") or item.get("path") or "")
        if not relative or relative in seen or Path(relative).is_absolute() or ".." in Path(relative).parts:
            findings.append(f"manifest_path_invalid:{index}")
            continue
        seen.add(relative)
        path = root / Path(relative)
        status = "verified"
        actual_size: int | None = None
        actual_hash: str | None = None
        if not path.is_file():
            status = "missing"
        else:
            actual_size = path.stat().st_size
            actual_hash = _sha256_file(path)
            expected_hash = str(item.get("sha256") or "")
            if expected_hash and not expected_hash.startswith("sha256:"):
                expected_hash = "sha256:" + expected_hash
            if actual_hash != expected_hash:
                status = "hash_mismatch"
            expected_size = item.get("sizeBytes")
            if expected_size is None:
                expected_size = item.get("size")
            if expected_size is None:
                expected_size = item.get("bytes")
            if status == "verified" and int(expected_size or -1) != actual_size:
                status = "size_mismatch"
        if status != "verified":
            findings.append(f"{relative}:{status}")
        artifacts.append(
            {
                "relativePath": relative,
                "status": status,
                "sizeBytes": actual_size,
                "sha256": actual_hash,
            }
        )
    return {
        "schemaVersion": "v62_4_1_hash_independent_verifier_v1",
        "passed": not findings,
        "findings": findings,
        "artifacts": artifacts,
    }
