"""Export only fully closed, reconciled Demo/Live outcomes for Quant Engine."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .demo_execution_store import DemoExecutionStore
from .evolution_demo_service import STORE_PATH as DEMO_EXECUTION_STORE_PATH
from .execution_outcome_store import EXECUTION_OUTCOME_STORE_PATH, ExecutionOutcomeStore
from .live_execution_store import LIVE_EXECUTION_STORE_PATH, LiveExecutionStore


EXECUTION_OUTCOME_EXPORT_DIR = DATA_DIR / "formal_outcome_exports"
LATEST_EXECUTION_OUTCOME_EXPORT = EXECUTION_OUTCOME_EXPORT_DIR / "latest_execution_outcomes.json"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _execution_inventory(
    *,
    formal_sources: set[tuple[str, str]],
    demo_store_path: Path | str,
    live_store_path: Path | str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if Path(demo_store_path).exists():
        store = DemoExecutionStore(demo_store_path)
        try:
            for record in store.list_records():
                if ("okx_demo", record.recordId) in formal_sources:
                    continue
                reason = "position_close_evidence_missing" if record.status == "filled" else (
                    "execution_did_not_create_trade_outcome" if record.status in {"canceled", "rejected", "mmp_canceled"}
                    else "execution_not_terminal"
                )
                rows.append({"environment": "okx_demo", "sourceRecordId": record.recordId, "status": record.status, "reason": reason})
        finally:
            store.close()
    if Path(live_store_path).exists():
        store = LiveExecutionStore(live_store_path)
        try:
            for record in store.list_records():
                if ("live", record.recordId) in formal_sources:
                    continue
                reason = "position_close_evidence_missing" if record.status == "filled" else (
                    "execution_did_not_create_trade_outcome" if record.status in {"canceled", "rejected", "mmp_canceled"}
                    else "execution_not_terminal"
                )
                rows.append({"environment": "live", "sourceRecordId": record.recordId, "status": record.status, "reason": reason})
        finally:
            store.close()
    return rows


def build_execution_outcome_export(
    *,
    outcome_store_path: Path | str = EXECUTION_OUTCOME_STORE_PATH,
    demo_store_path: Path | str = DEMO_EXECUTION_STORE_PATH,
    live_store_path: Path | str = LIVE_EXECUTION_STORE_PATH,
) -> dict[str, Any]:
    store = ExecutionOutcomeStore(outcome_store_path)
    try:
        outcomes = store.list_outcomes()
    finally:
        store.close()
    records = [
        {
            **row.outcome,
            "executionOutcomeId": row.executionOutcomeId,
            "contentHash": row.contentHash,
            "createdAt": row.createdAt,
        }
        for row in outcomes
    ]
    formal_sources = {(row.environment, row.sourceRecordId) for row in outcomes}
    quarantined = _execution_inventory(
        formal_sources=formal_sources,
        demo_store_path=demo_store_path,
        live_store_path=live_store_path,
    )
    core = {
        "schemaVersion": "alphapilot_execution_outcome_export_v1",
        "records": records,
        "quarantinedExecutionRecords": quarantined,
    }
    return {
        **core,
        "generatedAt": datetime.now(UTC).isoformat(),
        "manifestHash": _hash(core),
        "summary": {
            "formalClosedOutcomeCount": len(records),
            "okxDemoOutcomeCount": sum(row.get("evidenceClass") == "okx_demo" for row in records),
            "liveOutcomeCount": sum(row.get("evidenceClass") == "live" for row in records),
            "quarantinedExecutionCount": len(quarantined),
        },
        "safetyBoundary": {
            "incompleteExecutionsPromoted": False,
            "accountValuesPersisted": False,
            "rawCredentialsPersisted": False,
            "createsOrders": False,
        },
    }


def write_execution_outcome_export(
    *,
    output_path: Path | str = LATEST_EXECUTION_OUTCOME_EXPORT,
    outcome_store_path: Path | str = EXECUTION_OUTCOME_STORE_PATH,
    demo_store_path: Path | str = DEMO_EXECUTION_STORE_PATH,
    live_store_path: Path | str = LIVE_EXECUTION_STORE_PATH,
) -> dict[str, Any]:
    payload = build_execution_outcome_export(
        outcome_store_path=outcome_store_path,
        demo_store_path=demo_store_path,
        live_store_path=live_store_path,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, target)
    return {**payload, "exportPath": str(target.resolve())}


def build_execution_outcome_status() -> dict[str, Any]:
    payload = build_execution_outcome_export()
    latest = str(LATEST_EXECUTION_OUTCOME_EXPORT.resolve()) if LATEST_EXECUTION_OUTCOME_EXPORT.exists() else None
    return {
        "version": "V13.26.0",
        "source": "formal_execution_outcome_export_v1",
        **payload,
        "latestExportPath": latest,
    }
