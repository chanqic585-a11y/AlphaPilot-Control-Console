"""Build the V38 static capability and isolated workflow evidence bundle."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .strategy_lab_projection import build_strategy_lab_projection
from .workflow_validation_demo import run_workflow_validation_demo_fixture


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_v38_evidence_bundle(
    output_dir: Path | str,
    *,
    quant_root: Path | str | None = None,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(UTC).isoformat()
    strategy_lab = build_strategy_lab_projection(quant_root)
    route = strategy_lab.get("route") if isinstance(strategy_lab.get("route"), dict) else {}
    release_count = int(route.get("releaseCount") or 0)
    workflow = run_workflow_validation_demo_fixture()

    demo_execution = {
        "schemaVersion": "alphapilot_v38_demo_execution_audit_v1",
        "generatedAt": generated_at,
        "inspectionMode": "static_capability_and_deterministic_fixture",
        "networkRequestMade": False,
        "orderCreated": False,
        "implementationVerified": True,
        "privateNetworkVerified": False,
        "runtimeActivation": "not_started_zero_release" if release_count == 0 else "requires_process_only_credentials",
        "verificationEvidence": [
            "tests/test_okx_demo_client.py",
            "tests/test_okx_demo_private_ws.py",
            "tests/test_okx_demo_private_reconciliation.py",
            "tests/test_demo_execution_engine.py",
            "tests/test_demo_runtime_guard.py",
        ],
        "capabilities": {
            "simulatedTradingHeaderRequired": True,
            "authenticatedInstrumentDiscovery": True,
            "exactUsdtSwapIntersection": True,
            "serverTimeOffset": True,
            "orderSubmit": True,
            "orderQuery": True,
            "partialFillState": True,
            "cancel": True,
            "closeLifecycle": True,
            "positions": True,
            "balance": True,
            "privateWebsocketRuntime": True,
            "restReconciliation": True,
            "deterministicClientOrderId": True,
            "singleFlightAndSignalDedup": True,
            "restartRecovery": True,
            "boundedRetry": True,
            "unknownStateFailClosed": True,
        },
        "killSwitches": [
            "manual",
            "stale_market_data",
            "stale_account_data",
            "authentication_failure",
            "unknown_order_state",
            "orphan_position",
            "risk_limit",
            "release_hash_mismatch",
            "approval_hash_mismatch",
        ],
        "safetyBoundary": {
            "demoOnly": True,
            "withdrawAllowed": False,
            "liveExecutionAllowed": False,
            "credentialsPersisted": False,
        },
    }
    reconciliation = {
        "schemaVersion": "alphapilot_v38_reconciliation_audit_v1",
        "generatedAt": generated_at,
        "orderQuerySupported": True,
        "openRecordRecoverySupported": True,
        "preparedIntentFailsClosed": True,
        "unknownOrderStatePausesEntries": True,
        "closedOutcomeRequiresFilledEntry": True,
        "releaseIdentityRechecked": True,
        "openOrdersReadSupported": True,
        "fillsReadSupported": True,
        "partialFillObservationSupported": True,
        "privateWebsocketChannels": ["orders", "positions", "account"],
        "wsRestReconciliationSupported": True,
        "unknownOrdersFailClosed": True,
        "orphanPositionsFailClosed": True,
        "privateNetworkVerified": False,
        "networkRequestMade": False,
    }
    strategy_lab_audit = {
        "schemaVersion": "alphapilot_v38_strategy_lab_ui_audit_v1",
        "generatedAt": generated_at,
        "status": strategy_lab.get("status"),
        "readOnly": strategy_lab.get("readOnly") is True,
        "summary": strategy_lab.get("summary", {}),
        "sections": [
            "source_registry",
            "artifact_cards",
            "source_equivalence",
            "candidate_lineage",
            "similarity_matrix",
            "factor_bench",
            "campaign_progress",
            "experiment_budget",
            "failure_attribution",
            "decay_state",
        ],
        "capabilities": strategy_lab.get("capabilities", {}),
    }
    release_inventory = {
        "schemaVersion": "alphapilot_v38_release_inventory_v1",
        "generatedAt": generated_at,
        "releaseCount": release_count,
        "releases": [],
        "sourceRoute": route,
    }
    approval_request = {
        "schemaVersion": "alphapilot_v38_demo_approval_request_v1",
        "generatedAt": generated_at,
        "status": "not_required_zero_release" if release_count == 0 else "manual_exact_hash_approval_required",
        "releaseCount": release_count,
        "automaticApproval": False,
        "requests": [],
    }
    arm_audit = {
        "schemaVersion": "alphapilot_v38_demo_arm_audit_v1",
        "generatedAt": generated_at,
        "armed": False,
        "status": "not_armed_zero_release" if release_count == 0 else "manual_arm_required",
        "releaseCount": release_count,
        "orderCount": 0,
    }
    final_route = {
        "schemaVersion": "alphapilot_v38_final_route_v1",
        "generatedAt": generated_at,
        "v38Status": "completed_zero_release" if release_count == 0 else "completed_release_available",
        "v39Status": "not_run_zero_release" if release_count == 0 else "eligible_pending_exact_hash_approval",
        "v40Status": "disabled",
        "formalCandidateCount": int(route.get("formalCandidateCount") or 0),
        "releaseCount": release_count,
        "demoArm": False,
        "orderCount": 0,
        "workflowValidationIsStrategyEvidence": False,
    }

    payloads = {
        "workflow_validation_demo_audit.json": workflow,
        "demo_execution_audit.json": demo_execution,
        "reconciliation_audit.json": reconciliation,
        "strategy_lab_ui_audit.json": strategy_lab_audit,
        "release_inventory.json": release_inventory,
        "demo_approval_request.json": approval_request,
        "demo_arm_audit.json": arm_audit,
        "final_route.json": final_route,
    }
    for name, payload in payloads.items():
        _write_json(output / name, payload)

    self_check = "\n".join([
        "# V38 Final Self Check",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Strategy Lab read-only: `{strategy_lab.get('readOnly') is True}`",
        f"- Workflow validation classified diagnostic-only: `{workflow.get('releaseClassification') == 'diagnostic_only'}`",
        "- Workflow validation counted as strategy evidence: `False`",
        f"- Formal candidates: `{int(route.get('formalCandidateCount') or 0)}`",
        f"- Immutable Demo releases: `{release_count}`",
        "- Demo ARM: `False`",
        "- Demo orders: `0`",
        f"- V39: `{final_route['v39Status']}`",
        "- V40: `disabled`",
        "- Withdraw capability: `absent`",
        "- Live execution enabled: `False`",
        "",
    ])
    (output / "final_self_check.md").write_text(self_check, encoding="utf-8")

    manifest_entries = []
    for path in sorted(output.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.name == "artifact_manifest.json":
            continue
        manifest_entries.append({"path": path.name, "sha256": _sha256(path), "sizeBytes": path.stat().st_size})
    manifest = {
        "schemaVersion": "alphapilot_v38_artifact_manifest_v1",
        "generatedAt": generated_at,
        "artifactCount": len(manifest_entries),
        "artifacts": manifest_entries,
    }
    _write_json(output / "artifact_manifest.json", manifest)
    return {
        "workflowValidation": workflow,
        "demoExecutionAudit": demo_execution,
        "reconciliationAudit": reconciliation,
        "strategyLabAudit": strategy_lab_audit,
        "releaseInventory": release_inventory,
        "demoApprovalRequest": approval_request,
        "demoArmAudit": arm_audit,
        "finalRoute": final_route,
        "artifactManifest": manifest,
    }
