from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alphapilot_control_console.live_engineering_smoke_contract import (
    V58_EVIDENCE_ROOT,
    build_live_engineering_smoke_approval_request,
    build_live_engineering_smoke_contract,
)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest(root: Path, generated_at: str) -> dict[str, Any]:
    rows = []
    for path in sorted(root.glob("*.json")):
        if path.name == "artifact_manifest.json":
            continue
        rows.append(
            {
                "path": path.name,
                "sha256": _sha256(path),
                "sizeBytes": path.stat().st_size,
            }
        )
    return {
        "schemaVersion": "alphapilot_v58_live_engineering_smoke_manifest_v1",
        "generatedAt": generated_at,
        "status": "complete_readiness_only",
        "artifactCount": len(rows),
        "artifacts": rows,
        "liveOrdersCreated": 0,
        "withdrawAllowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build V58 exact Live smoke approval evidence")
    parser.add_argument("--output", type=Path, default=V58_EVIDENCE_ROOT)
    parser.add_argument("--maximum-notional-usdt", type=float, default=10.0)
    args = parser.parse_args()

    generated_at = _now()
    contract = build_live_engineering_smoke_contract(
        created_at=generated_at,
        maximum_notional_usdt=args.maximum_notional_usdt,
    )
    request = build_live_engineering_smoke_approval_request(contract)
    status = {
        "schemaVersion": "alphapilot_live_engineering_smoke_status_v1",
        "generatedAt": generated_at,
        "status": "blocked_waiting_exact_live_smoke_approval",
        "environment": "okx_live",
        "contractHash": contract["contractHash"],
        "approvalRecorded": False,
        "smokeExecuted": False,
        "orderAttemptCount": 0,
        "strategyQualification": False,
        "promotionEligible": False,
        "liveCanaryEvidenceEligible": False,
        "liveEnabled": False,
        "withdrawAllowed": False,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    _write(args.output / "live_engineering_smoke_contract.json", contract)
    _write(args.output / "live_engineering_smoke_approval_request.json", request)
    _write(args.output / "live_engineering_smoke_status.json", status)
    manifest = _manifest(args.output, generated_at)
    _write(args.output / "artifact_manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": status["status"],
                "contractHash": contract["contractHash"],
                "requiredConfirmation": request["requiredConfirmation"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
