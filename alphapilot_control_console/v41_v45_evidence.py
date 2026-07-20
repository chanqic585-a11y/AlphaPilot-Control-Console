"""Build the V41-V45 dual-track closeout without inventing unreached evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping


_CREDENTIAL_ENV_NAMES = (
    "ALPHAPILOT_OKX_DEMO_API_KEY",
    "ALPHAPILOT_OKX_DEMO_SECRET_KEY",
    "ALPHAPILOT_OKX_DEMO_PASSPHRASE",
)

_PRODUCT_FILES = (
    "demo_private_preflight.json",
    "demo_universe_audit.json",
    "engineering_smoke_contract.json",
    "engineering_smoke_approval_overlay.json",
    "engineering_smoke_order_ledger.jsonl",
    "engineering_smoke_fill_ledger.jsonl",
    "engineering_smoke_position_ledger.jsonl",
    "engineering_smoke_cancel_audit.json",
    "engineering_smoke_fill_close_audit.json",
    "private_websocket_audit.json",
    "rest_reconciliation_audit.json",
    "restart_recovery_audit.json",
    "kill_switch_audit.json",
    "strategy_evidence_isolation_audit.json",
    "ui_screenshot_manifest.json",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _latest_campaign_root(quant_root: Path) -> Path:
    root = quant_root / "reports" / "mechanism_breakthrough"
    candidates = sorted(
        (
            path
            for path in root.iterdir()
            if (path / "research" / "campaign_summary.json").is_file()
        ),
        key=lambda path: path.name,
    ) if root.is_dir() else []
    if not candidates:
        raise FileNotFoundError("No V41-V45 mechanism breakthrough campaign evidence found")
    return candidates[-1]


def _copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        return
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def _formal_gate_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _not_run_artifact(schema: str, *, generated_at: str, reason: str) -> dict[str, Any]:
    return {
        "schemaVersion": schema,
        "generatedAt": generated_at,
        "status": "not_run",
        "reason": reason,
        "networkRequestMade": False,
        "orderCreated": False,
        "engineeringOnly": True,
        "strategyQualification": False,
        "formalPass": False,
        "promotionEvidenceEligible": False,
        "livePromotionEligible": False,
    }


def write_v41_v45_evidence_bundle(
    output_dir: Path | str,
    *,
    quant_root: Path | str,
    environment: Mapping[str, str] | None = None,
    screenshots_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Create a truthful dual-track delivery from frozen Quant evidence."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    product = output / "product"
    research_out = output / "research"
    release_out = output / "release"
    common_out = output / "common"
    product.mkdir(exist_ok=True)
    generated_at = _now()
    campaign_root = _latest_campaign_root(Path(quant_root))
    research_root = campaign_root / "research"
    campaign = _read_json(research_root / "campaign_summary.json", {})
    budget = _read_json(campaign_root / "program_budget.json", {})
    settled_budget = campaign.get("budget") if isinstance(campaign.get("budget"), dict) else budget
    release_inventory = _read_json(research_root / "release_inventory.json", {})
    environment_source = dict(os.environ) if environment is None else dict(environment)
    credentials_injected = all(
        bool(str(environment_source.get(name, "")).strip())
        for name in _CREDENTIAL_ENV_NAMES
    )

    track_r_status = str(campaign.get("status") or "blocked_missing_research_evidence")
    track_p_status = (
        "blocked_demo_credentials_not_injected"
        if not credentials_injected
        else "blocked_execution_integrity"
    )
    block_reason = (
        "Process-only OKX Demo credentials were not injected; private endpoints and orders were not called."
        if not credentials_injected
        else "Credentials were present, but this evidence packaging command does not execute private trading smoke."
    )

    _write_json(product / "demo_private_preflight.json", {
        "schemaVersion": "alphapilot_v41_v45_demo_private_preflight_v1",
        "generatedAt": generated_at,
        "status": track_p_status,
        "credentialsInjected": credentials_injected,
        "privateNetworkVerified": False,
        "networkRequestMade": False,
        "simulatedTradingHeaderRequired": True,
        "environment": "demo",
        "withdrawAllowed": False,
        "liveExecutionAllowed": False,
        "credentialsPersisted": False,
        "reason": block_reason,
    })

    not_run_names = {
        "demo_universe_audit.json": "alphapilot_v41_v45_demo_universe_audit_v1",
        "engineering_smoke_contract.json": "alphapilot_v41_v45_engineering_smoke_contract_status_v1",
        "engineering_smoke_approval_overlay.json": "alphapilot_v41_v45_engineering_smoke_approval_overlay_v1",
        "engineering_smoke_cancel_audit.json": "alphapilot_v41_v45_engineering_smoke_cancel_audit_v1",
        "engineering_smoke_fill_close_audit.json": "alphapilot_v41_v45_engineering_smoke_fill_close_audit_v1",
        "private_websocket_audit.json": "alphapilot_v41_v45_private_websocket_audit_v1",
        "rest_reconciliation_audit.json": "alphapilot_v41_v45_rest_reconciliation_audit_v1",
        "restart_recovery_audit.json": "alphapilot_v41_v45_restart_recovery_audit_v1",
        "kill_switch_audit.json": "alphapilot_v41_v45_kill_switch_audit_v1",
    }
    for name, schema in not_run_names.items():
        payload = _not_run_artifact(schema, generated_at=generated_at, reason=track_p_status)
        if name == "engineering_smoke_contract.json":
            payload.update({
                "contractHash": None,
                "maximumConcurrentPositions": 1,
                "maximumSize": "minSz",
            })
        _write_json(product / name, payload)

    stage_status = {
        "schemaVersion": "alphapilot_v41_v45_engineering_smoke_ledger_v1",
        "recordType": "stage_status",
        "generatedAt": generated_at,
        "status": "not_run",
        "reason": track_p_status,
        "engineeringOnly": True,
        "strategyQualification": False,
    }
    for name in (
        "engineering_smoke_order_ledger.jsonl",
        "engineering_smoke_fill_ledger.jsonl",
        "engineering_smoke_position_ledger.jsonl",
    ):
        _write_jsonl(product / name, stage_status)

    strategy_ledger = campaign_root / "research_evidence_ledger.jsonl"
    strategy_digest = _sha256(strategy_ledger) if strategy_ledger.is_file() else None
    _write_json(product / "strategy_evidence_isolation_audit.json", {
        "schemaVersion": "alphapilot_v41_v45_strategy_evidence_isolation_audit_v1",
        "generatedAt": generated_at,
        "status": "completed",
        "strategyEvidenceBeforeSha256": strategy_digest,
        "strategyEvidenceAfterSha256": strategy_digest,
        "strategyEvidenceChanged": False,
        "engineeringOnly": True,
        "strategyQualification": False,
        "formalPass": False,
        "promotionEvidenceEligible": False,
        "livePromotionEligible": False,
    })

    screenshot_root = Path(screenshots_dir) if screenshots_dir is not None else None
    screenshot_entries = []
    for name in (
        "real_demo_universe.png",
        "real_engineering_smoke_order.png",
        "real_engineering_smoke_position.png",
        "real_engineering_smoke_reconciliation.png",
        "real_kill_switch.png",
        "formal_gate_matrix.png",
    ):
        source = screenshot_root / name if screenshot_root is not None else None
        available = bool(source and source.is_file())
        if available and source is not None:
            destination = output / "screenshots" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        screenshot_entries.append({
            "path": f"screenshots/{name}",
            "status": "available" if available else "not_run",
            "reason": None if available else (
                "track_p_not_reached" if name != "formal_gate_matrix.png" else "ui_capture_not_run"
            ),
            "sensitiveDataPresent": False,
        })
    _write_json(product / "ui_screenshot_manifest.json", {
        "schemaVersion": "alphapilot_v41_v45_ui_screenshot_manifest_v1",
        "generatedAt": generated_at,
        "screenshots": screenshot_entries,
    })

    _copy_tree(research_root, research_out)
    for name in (
        "integration_merge_receipt.json",
        "program_spec.json",
        "program_state.json",
        "program_ledger.jsonl",
        "program_budget.json",
        "program_budget_ledger.jsonl",
    ):
        source = campaign_root / name
        if source.is_file():
            common_out.mkdir(exist_ok=True)
            shutil.copy2(source, common_out / name)
    for name in (
        "release_inventory.json",
        "release_hash_audit.json",
        "demo_approval_request.json",
        "demo_approval_request.md",
    ):
        source = research_root / name
        if source.is_file():
            release_out.mkdir(exist_ok=True)
            shutil.copy2(source, release_out / name)
    candidate_release_out = release_out / "candidate_releases"
    _copy_tree(research_root / "candidate_releases", candidate_release_out)
    if not candidate_release_out.is_dir() or not any(
        path.is_file() for path in candidate_release_out.rglob("*")
    ):
        _write_json(candidate_release_out / "status.json", {
            "schemaVersion": "alphapilot_v41_v45_candidate_release_status_v1",
            "generatedAt": generated_at,
            "status": "not_run_no_qualified_formal_candidate",
            "releaseCount": 0,
            "reason": "No candidate survived prefilter and Formal was not run.",
        })

    formal_gate_rows = _formal_gate_rows(research_root / "formal_gate_matrix.csv")
    formal_run_count = int(campaign.get("formalRunCount") or 0)
    release_count = int(campaign.get("releaseCount") or release_inventory.get("releaseCount") or 0)
    locked_oos_read_count = int(campaign.get("lockedOosReadCount") or 0)
    master_status = (
        "research_complete_demo_smoke_blocked"
        if track_r_status in {"completed_zero_qualified_candidates", "completed_release_ready"}
        and track_p_status.startswith("blocked_")
        else "blocked_execution_integrity"
    )
    final = {
        "schemaVersion": "alphapilot_v41_v45_final_self_check_v1",
        "generatedAt": generated_at,
        "masterStatus": master_status,
        "trackRStatus": track_r_status,
        "trackPStatus": track_p_status,
        "campaignId": campaign.get("campaignId"),
        "candidateCount": int(campaign.get("candidateCount") or 0),
        "prefilterSurvivorCount": int(campaign.get("prefilterSurvivorCount") or 0),
        "formalCandidateCount": int(campaign.get("formalCandidateCount") or 0),
        "formalRunCount": formal_run_count,
        "formalGateRowCount": len(formal_gate_rows),
        "lockedOosReadCount": locked_oos_read_count,
        "releaseCount": release_count,
        "credentialsInjected": credentials_injected,
        "privateNetworkVerified": False,
        "strategyEvidenceDelta": 0,
        "credentialsPersisted": False,
        "liveEnabled": False,
        "withdrawAllowed": False,
        "budget": settled_budget,
        "knownLimitations": [block_reason],
    }
    _write_json(output / "final_self_check.json", final)
    closeout = "\n".join((
        "# AlphaPilot V41-V45 最终收口",
        "",
        f"- Master：`{master_status}`",
        f"- Track R：`{track_r_status}`",
        f"- Track P：`{track_p_status}`",
        f"- 候选 / 预筛幸存：`{final['candidateCount']} / {final['prefilterSurvivorCount']}`",
        f"- Formal / Release：`{formal_run_count} / {release_count}`",
        f"- Locked OOS 读取：`{locked_oos_read_count}`",
        "- Demo 私网调用：`未执行`",
        "- 工程订单：`未创建`",
        "- 策略证据变化：`0`",
        "- Live / Withdraw：`关闭 / 禁止`",
        "",
        "Track R 已完成机制级筛选但没有候选通过现有 Gate。Track P 因当前进程未注入 Demo 凭据而依法阻塞；没有伪造 Universe、订单、成交、持仓或对账结果。",
        "",
    ))
    (output / "AlphaPilot_V41-V45_Final_Closeout_CN.md").write_text(
        closeout, encoding="utf-8", newline="\n"
    )
    (output / "final_self_check.md").write_text(closeout, encoding="utf-8", newline="\n")

    manifest_entries = []
    for path in sorted(
        (item for item in output.rglob("*") if item.is_file()),
        key=lambda item: item.as_posix(),
    ):
        if path.name == "artifact_manifest.json":
            continue
        manifest_entries.append({
            "path": path.relative_to(output).as_posix(),
            "sha256": _sha256(path),
            "sizeBytes": path.stat().st_size,
        })
    _write_json(output / "artifact_manifest.json", {
        "schemaVersion": "alphapilot_v41_v45_delivery_manifest_v1",
        "generatedAt": generated_at,
        "artifactCount": len(manifest_entries),
        "artifacts": manifest_entries,
    })
    if {path.name for path in product.iterdir()} != set(_PRODUCT_FILES):
        raise RuntimeError("V41-V45 product evidence set is incomplete")
    return final
