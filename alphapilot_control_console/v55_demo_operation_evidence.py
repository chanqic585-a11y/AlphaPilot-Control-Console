"""Generate V55 engineering-only latency and first-scan evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from .demo_entry_latency_policy import evaluate_demo_entry_latency
from .execution_latency_profile import build_execution_latency_profile


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _latency_scenarios() -> list[dict[str, Any]]:
    close = datetime(2026, 7, 21, 0, 0, tzinfo=UTC)
    signal = {
        "candidateId": "v55-engineering-latency-fixture",
        "side": "buy",
        "entryPrice": 100.0,
        "stopLossPrice": 98.0,
        "takeProfitPrice": 104.0,
    }
    rows: list[dict[str, Any]] = []
    for scenario_id, elapsed_ms, expected_class, expected_passed in (
        ("target_500ms", 500, "on_target", True),
        ("soft_warning_1000ms", 1_000, "delayed", True),
        ("conditional_2000ms", 2_000, "conditional", True),
        ("stale_3001ms", 3_001, "stale", False),
        ("critical_20000ms", 20_000, "critical", False),
    ):
        ready = close + timedelta(milliseconds=elapsed_ms)
        quote_received = min(ready, close + timedelta(milliseconds=1_500))
        decision = evaluate_demo_entry_latency(
            signal,
            {
                "bidPrice": 100.01,
                "askPrice": 100.02,
                "receivedAt": quote_received.isoformat(),
                "spreadPct": 0.0001,
                "liquidityPassed": True,
            },
            close_received_at=close,
            order_ready_at=ready,
            fee_rate=0.0005,
            slippage_rate=0.0002,
        )
        payload = asdict(decision)
        rows.append({
            "scenarioId": scenario_id,
            "expectedLatencyClass": expected_class,
            "expectedPassed": expected_passed,
            "actual": payload,
            "assertionPassed": (
                payload["latencyClass"] == expected_class
                and payload["passed"] is expected_passed
            ),
            "engineeringOnly": True,
            "strategyEvidenceEligible": False,
        })
    return rows


def generate_v55_demo_operation_evidence(
    output_root: Path | str,
    *,
    generated_at: str,
    release_identity: Mapping[str, Any],
    first_scan_audit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    profile = build_execution_latency_profile()
    scenarios = _latency_scenarios()

    _write_json(root / "execution_latency_profile.json", profile)
    benchmark = {
        "schemaVersion": "alphapilot_v55_latency_benchmark_v1",
        "generatedAt": generated_at,
        "status": "passed" if all(row["assertionPassed"] for row in scenarios) else "blocked",
        "engineeringOnly": True,
        "strategyEvidenceEligible": False,
        "scenarioCount": len(scenarios),
        "scenarios": scenarios,
    }
    _write_json(root / "latency_benchmark.json", benchmark)

    ledger_path = root / "latency_ledger.jsonl"
    ledger_path.write_text(
        "".join(_canonical({"generatedAt": generated_at, **row}) + "\n" for row in scenarios),
        encoding="utf-8",
        newline="\n",
    )
    stale_rows = [row for row in scenarios if row["actual"]["reasonCode"] == "stale_signal_rejected"]
    critical_rows = [row for row in scenarios if row["actual"]["reasonCode"] == "critical_latency_failure"]
    _write_json(root / "stale_signal_audit.json", {
        "schemaVersion": "alphapilot_v55_stale_signal_audit_v1",
        "generatedAt": generated_at,
        "status": "passed" if len(stale_rows) == 1 and len(critical_rows) == 1 else "blocked",
        "engineeringOnly": True,
        "strategyEvidenceEligible": False,
        "staleRejectedCount": len(stale_rows),
        "criticalRejectedCount": len(critical_rows),
        "rejectedScenarioIds": [row["scenarioId"] for row in stale_rows + critical_rows],
    })

    if first_scan_audit is None:
        scan_payload = {
            "schemaVersion": "alphapilot_v55_first_scan_audit_v1",
            "generatedAt": generated_at,
            "status": "not_run_pre_arm",
            "strategyOrderCount": 0,
            "reason": "exact_demo_release_not_armed",
            "engineeringSmokeExcluded": True,
            **{
                field: release_identity.get(field)
                for field in ("releaseId", "releaseHash", "riskOverlayHash")
            },
        }
    else:
        funnel = (
            first_scan_audit.get("funnel")
            if isinstance(first_scan_audit.get("funnel"), Mapping)
            else {}
        )
        scan_payload = {
            "schemaVersion": "alphapilot_v55_first_scan_audit_v1",
            "generatedAt": generated_at,
            "status": "completed",
            "strategyOrderCount": int(funnel.get("orderAcceptedCount") or 0),
            "evaluationAudit": dict(first_scan_audit),
            "engineeringSmokeExcluded": True,
            **{
                field: release_identity.get(field)
                for field in ("releaseId", "releaseHash", "riskOverlayHash")
            },
        }
    _write_json(root / "first_scan_audit.json", scan_payload)

    artifact_paths = [
        root / "execution_latency_profile.json",
        root / "latency_benchmark.json",
        root / "latency_ledger.jsonl",
        root / "stale_signal_audit.json",
        root / "first_scan_audit.json",
    ]
    manifest = {
        "schemaVersion": "alphapilot_v55_demo_operation_manifest_v1",
        "generatedAt": generated_at,
        "status": "complete_pre_arm" if first_scan_audit is None else "complete_after_first_scan",
        "fileCount": len(artifact_paths),
        "files": [
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in artifact_paths
        ],
    }
    _write_json(root / "artifact_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--release-path", required=True)
    parser.add_argument("--generated-at")
    arguments = parser.parse_args()
    release = json.loads(Path(arguments.release_path).read_text(encoding="utf-8"))
    generated_at = arguments.generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    result = generate_v55_demo_operation_evidence(
        arguments.output_root,
        generated_at=generated_at,
        release_identity=release,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
