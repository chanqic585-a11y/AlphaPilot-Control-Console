from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alphapilot_control_console.credential_runtime import load_okx_live_credentials
from alphapilot_control_console.exchange_connectors.okx_live_client import OkxLiveClient
from alphapilot_control_console.live_engineering_smoke_contract import V58_EVIDENCE_ROOT
from alphapilot_control_console.live_engineering_smoke_runner import (
    build_artifact_manifest,
    run_approved_live_engineering_smoke,
    write_json,
)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def main() -> int:
    root = V58_EVIDENCE_ROOT
    contract = _load(root / "live_engineering_smoke_contract.json")
    approval = _load(root / "live_engineering_smoke_approval.json")
    result_path = root / "live_engineering_smoke_result.json"
    attempt_path = root / "live_engineering_smoke_attempt.json"
    status_path = root / "live_engineering_smoke_status.json"
    if result_path.exists() or attempt_path.exists():
        raise PermissionError("The approved V58 Live smoke attempt is already consumed or reserved")

    generated_at = _now()
    try:
        client = OkxLiveClient(
            load_okx_live_credentials(),
            site=os.environ.get("ALPHAPILOT_OKX_SITE", "global"),
        )
        result = run_approved_live_engineering_smoke(
            client=client,
            contract=contract,
            approval=approval,
            result_path=result_path,
            attempt_path=attempt_path,
        )
        status = {
            "schemaVersion": "alphapilot_live_engineering_smoke_status_v2",
            "generatedAt": _now(),
            "status": result["status"],
            "environment": "okx_live",
            "contractHash": contract["contractHash"],
            "approvalRecorded": True,
            "smokeExecuted": True,
            "orderAttemptCount": 1,
            "finalReconciliationMatched": result["finalReconciliationMatched"],
            "strategyQualification": False,
            "promotionEligible": False,
            "liveCanaryEvidenceEligible": False,
            "liveEnabled": False,
            "withdrawAllowed": False,
        }
        write_json(status_path, status)
        write_json(
            root / "artifact_manifest.json",
            build_artifact_manifest(root, generated_at=_now(), status=result["status"]),
        )
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "instrumentId": result["instrumentId"],
                    "orderAttemptCount": 1,
                    "orderNotionalUsdt": result["orderNotionalUsdt"],
                    "cancelConfirmed": result["cancelConfirmed"],
                    "finalOpenPositionCount": result["finalOpenPositionCount"],
                    "finalOpenOrderCount": result["finalOpenOrderCount"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except Exception as error:
        status = {
            "schemaVersion": "alphapilot_live_engineering_smoke_status_v2",
            "generatedAt": _now(),
            "status": "blocked_live_engineering_smoke_requires_review",
            "environment": "okx_live",
            "contractHash": contract.get("contractHash"),
            "approvalRecorded": True,
            "smokeExecuted": attempt_path.exists(),
            "orderAttemptCount": 1 if attempt_path.exists() else 0,
            "errorType": type(error).__name__,
            "strategyQualification": False,
            "promotionEligible": False,
            "liveCanaryEvidenceEligible": False,
            "liveEnabled": False,
            "withdrawAllowed": False,
        }
        write_json(status_path, status)
        write_json(
            root / "artifact_manifest.json",
            build_artifact_manifest(root, generated_at=_now(), status=status["status"]),
        )
        print(
            json.dumps(
                {
                    "status": status["status"],
                    "errorType": type(error).__name__,
                    "orderAttemptCount": status["orderAttemptCount"],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
