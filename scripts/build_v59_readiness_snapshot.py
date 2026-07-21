"""Build the versioned V59 adaptive-learning readiness matrix."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphapilot_control_console.adaptive_learning_readiness_snapshot import (
    build_adaptive_learning_readiness_snapshot,
)


_JSON_ARTIFACTS = {
    "alpha101Ready": "alpha101_compatibility_audit.json",
    "alpha191CompatibilityReady": "alpha191_compatibility_audit.json",
    "adaptiveMlTrainingReady": "model_validation_report.json",
    "qlibOfflineCampaignReady": "qlib_campaign_manifest.json",
    "continuousLearningDatasetReady": "training_dataset_manifest.json",
    "demoOutcomeToTrainingSampleReady": "demo_learning_sample_audit.json",
    "demoDecisionModeValidated": "demo_decision_mode_validation.json",
    "modelDriftMonitoringReady": "model_drift_report.json",
    "modelRollbackReady": "model_rollback_audit.json",
    "onlineInferenceLatencyReady": "online_inference_latency_audit.json",
    "liveFeaturePipelineReady": "live_feature_pipeline_parity.json",
    "liveModelInferenceReady": "live_model_inference_audit.json",
    "exactModelReleaseApprovalReady": "exact_model_release_approval.json",
}

_PARQUET_ARTIFACTS = {
    "boundedFactorMiningReady": "factor_mining_trial_ledger.parquet",
    "shadowInferenceReady": "demo_shadow_decision_ledger.parquet",
}


def _missing(path: Path) -> dict[str, Any]:
    return {
        "status": "not_run",
        "passed": None,
        "reason": "artifact_missing",
        "evidenceRef": path.name,
    }


def _read_json_evidence(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _missing(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {
            "status": "invalid",
            "passed": False,
            "reason": f"artifact_unreadable:{type(error).__name__}",
            "evidenceRef": path.name,
        }
    return {
        "status": str(payload.get("status") or "blocked"),
        "passed": payload.get("passed"),
        "reason": payload.get("reason"),
        "evidenceRef": path.name,
    }


def _read_parquet_evidence(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _missing(path)
    try:
        import pandas as pd

        frame = pd.read_parquet(path)
        payload = frame.iloc[0].to_dict() if not frame.empty else {}
    except Exception as error:  # pragma: no cover - dependency and codec failures vary
        return {
            "status": "invalid",
            "passed": False,
            "reason": f"artifact_unreadable:{type(error).__name__}",
            "evidenceRef": path.name,
        }
    return {
        "status": str(payload.get("status") or "blocked"),
        "passed": True if payload.get("passed") is True else payload.get("passed"),
        "reason": payload.get("reason"),
        "evidenceRef": path.name,
    }


def collect_artifact_evidence(adaptive_root: Path | str) -> dict[str, dict[str, Any]]:
    root = Path(adaptive_root).expanduser().resolve()
    evidence = {
        capability: _read_json_evidence(root / filename)
        for capability, filename in _JSON_ARTIFACTS.items()
    }
    evidence.update(
        {
            capability: _read_parquet_evidence(root / filename)
            for capability, filename in _PARQUET_ARTIFACTS.items()
        }
    )
    return evidence


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object in {path}")
    return payload


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adaptive-root", type=Path, required=True)
    parser.add_argument("--registry-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generated-at")
    args = parser.parse_args(argv)

    root = args.adaptive_root.expanduser().resolve()
    factor_registry = _load_json(root / "production_factor_registry.json")
    model_registry = _load_json(root / "model_registry.json")
    model_policy = dict(
        model_registry.get("activeLiveModelPolicy")
        or model_registry.get("activeDemoModelPolicy")
        or {}
    )
    offline_path = root / "adaptive_learning_offline_evidence_binding.json"
    offline_evidence = _load_json(offline_path) if offline_path.is_file() else {}
    result = build_adaptive_learning_readiness_snapshot(
        generated_at=args.generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        model_policy=model_policy,
        factor_registry=factor_registry,
        registry_audit=_load_json(args.registry_audit.expanduser().resolve()),
        offline_evidence=offline_evidence,
        artifact_evidence=collect_artifact_evidence(root),
    )
    output = args.output.expanduser().resolve()
    _write_json_atomic(output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "readinessHash": result["readinessHash"],
                "readyCount": result["readyCount"],
                "totalCount": result["totalCount"],
                "output": str(output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
