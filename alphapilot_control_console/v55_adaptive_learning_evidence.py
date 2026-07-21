"""Build the truthful pre-ARM V55.1 adaptive-learning evidence package."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from .adaptive_learning_contracts import (
    build_feature_schema,
    build_observer_model_registry,
    build_observer_sidecar_binding,
)
from .adaptive_learning_live_readiness import AdaptiveLearningLiveReadinessGate


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(dict(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def _write_parquet(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([dict(row) for row in rows])
    frame.to_parquet(path, index=False)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _not_run(
    *,
    schema_version: str,
    generated_at: str,
    reason: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "schemaVersion": schema_version,
        "generatedAt": generated_at,
        "status": "not_run",
        "reason": reason,
        "nextAction": next_action,
        "passed": None,
    }


def _manifest(root: Path, *, generated_at: str) -> dict[str, Any]:
    paths = sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"
    )
    return {
        "schemaVersion": "alphapilot_v55_1_adaptive_learning_manifest_v1",
        "generatedAt": generated_at,
        "status": "complete_pre_arm_observer",
        "selfReferenceExclusions": ["artifact_manifest.json", "outer ZIP"],
        "fileCount": len(paths),
        "files": [
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in paths
        ],
    }


def generate_v55_adaptive_learning_evidence(
    output_root: Path | str,
    *,
    generated_at: str,
    factor_registry: Mapping[str, Any],
    release_identity: Mapping[str, Any],
    insertion_receipt: Mapping[str, Any],
    ui_screenshots: Sequence[Mapping[str, Any]] | None = None,
    test_results: Mapping[str, Any] | None = None,
    git_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(output_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    feature_schema = build_feature_schema(factor_registry)
    model_registry = build_observer_model_registry(feature_schema)
    observer_policy = model_registry["activeDemoModelPolicy"]
    observer_binding = build_observer_sidecar_binding(
        release_id=str(release_identity.get("releaseId") or ""),
        release_hash=str(release_identity.get("releaseHash") or ""),
        model_policy=observer_policy,
    )

    _write_json(root / "adaptive_learning_insertion_receipt.json", {
        "schemaVersion": "adaptive_learning_insertion_receipt_v1",
        "generatedAt": generated_at,
        "status": "safe_checkpoint_applied",
        "releaseId": release_identity.get("releaseId"),
        "releaseHash": release_identity.get("releaseHash"),
        "riskOverlayHash": release_identity.get("riskOverlayHash"),
        "demoArm": bool(release_identity.get("demoArm")),
        "observerOnlyInsertion": True,
        "releaseMutation": False,
        **dict(insertion_receipt),
    })
    _write_json(root / "adaptive_learning_architecture_contract.json", {
        "schemaVersion": "adaptive_learning_architecture_contract_v1",
        "generatedAt": generated_at,
        "status": "implemented_pre_arm",
        "sharedCore": "AdaptiveLearningCore",
        "environments": ["okx_demo", "okx_live"],
        "sharedContracts": ["Factor Registry", "Feature Schema", "Model Registry"],
        "demoMinimumMode": "observer",
        "liveAllowedModes": ["rank_only", "veto_only", "meta_label"],
        "modelSelfApprovalAllowed": False,
        "automaticRiskIncreaseAllowed": False,
        "strategySourceMutationAllowed": False,
        "releaseHashMutationAllowed": False,
        "decisionChangingModelRequiresSuccessorRelease": True,
        "exactHumanApprovalRequired": True,
        "engineeringSmokeSampleEligible": False,
        "fixtureSampleEligible": False,
        "shadowVirtualSampleEligible": False,
    })
    _write_json(root / "production_factor_registry.json", factor_registry)
    _write_json(root / "production_feature_schema.json", feature_schema)
    _write_json(root / "model_registry.json", model_registry)
    _write_json(root / "observer_sidecar_binding.json", observer_binding)

    _write_parquet(root / "real_factor_bench_matrix.parquet", [{
        "status": "not_run",
        "reason": "demo_observer_infrastructure_precedes_real_factor_bench",
        "passed": None,
    }])
    _write_json(root / "factor_stability_report.json", _not_run(
        schema_version="factor_stability_report_v1",
        generated_at=generated_at,
        reason="real_factor_bench_not_run",
        next_action="Run bounded point-in-time factor bench during Demo observation.",
    ))
    _write_parquet(root / "factor_mining_trial_ledger.parquet", [{
        "status": "not_run",
        "reason": "bounded_factor_mining_campaign_not_started",
        "passed": None,
    }])
    alpha = factor_registry.get("alpha191Compatibility")
    alpha = dict(alpha) if isinstance(alpha, Mapping) else {}
    _write_json(root / "alpha191_compatibility_audit.json", {
        "schemaVersion": "alpha191_compatibility_audit_v1",
        "generatedAt": generated_at,
        "status": "partial_formula_compatibility" if alpha.get("formulaReviewedCount") else "not_run",
        "productionValidatedCount": 0,
        "predictiveValueClaimed": False,
        **alpha,
        "productionValidatedCount": 0,
        "nextAction": "Run PIT, missing-value, divide-by-zero, IC, decay and turnover validation.",
    })

    for name, schema_version, reason, next_action in (
        ("training_dataset_manifest.json", "training_dataset_manifest_v1", "no_reconciled_closed_demo_or_live_samples", "Collect real closed Demo outcomes with feature lineage."),
        ("qlib_campaign_manifest.json", "qlib_campaign_manifest_v1", "qlib_campaign_not_started", "Start only after a reproducible training dataset is frozen."),
        ("model_validation_report.json", "model_validation_report_v1", "decision_model_training_not_run", "Run purged walk-forward and calibration before model promotion."),
        ("champion_challenger_report.json", "champion_challenger_report_v1", "no_trained_challenger", "Compare only reproducible validated models."),
        ("model_drift_report.json", "model_drift_report_v1", "no_running_decision_model", "Measure drift after sufficient forward inference observations."),
        ("model_rollback_audit.json", "model_rollback_audit_v1", "no_promoted_champion_model", "Verify exact rollback when a champion exists."),
        ("online_inference_latency_audit.json", "online_inference_latency_audit_v1", "observer_has_no_decision_authority", "Benchmark preloaded decision model before any Live eligibility."),
        ("live_feature_pipeline_parity.json", "live_feature_pipeline_parity_v1", "live_feature_runtime_not_armed", "Replay identical snapshots through Demo and Live adapters."),
        ("live_model_inference_audit.json", "live_model_inference_audit_v1", "live_decision_model_not_registered", "Validate deterministic rank, veto or meta-label inference."),
    ):
        _write_json(root / name, _not_run(
            schema_version=schema_version,
            generated_at=generated_at,
            reason=reason,
            next_action=next_action,
        ))

    _write_parquet(root / "demo_feature_snapshot_sample.parquet", [{
        "status": "not_run",
        "reason": "no_strategy_demo_signal_observed_after_insertion",
        "sampleEligible": False,
    }])
    _write_parquet(root / "demo_shadow_decision_ledger.parquet", [{
        "status": "not_run",
        "reason": "no_strategy_demo_signal_observed_after_insertion",
        "altersOrderSemantics": False,
    }])
    _write_json(root / "demo_learning_sample_audit.json", _not_run(
        schema_version="demo_learning_sample_audit_v1",
        generated_at=generated_at,
        reason="no_reconciled_closed_strategy_demo_trade_after_insertion",
        next_action="Record only real reconciled closed Demo trades; exclude engineering smoke.",
    ))
    _write_json(root / "continuous_learning_state.json", {
        "schemaVersion": "continuous_learning_state_v1",
        "generatedAt": generated_at,
        "status": "observer_infrastructure_ready",
        "modelMode": "observer",
        "decisionAuthority": "none",
        "automaticRetrainingAllowed": False,
        "automaticPromotionAllowed": False,
        "sampleEligibility": "reconciled_closed_strategy_trade_only",
    })
    _write_jsonl(root / "retraining_run_ledger.jsonl", [{
        "schemaVersion": "retraining_run_ledger_v1",
        "generatedAt": generated_at,
        "status": "not_run",
        "reason": "training_dataset_not_ready",
        "passed": None,
    }])

    readiness = AdaptiveLearningLiveReadinessGate().evaluate(
        model_policy=observer_policy,
        evidence={},
    )
    _write_json(root / "adaptive_learning_live_readiness.json", {
        **readiness,
        "generatedAt": generated_at,
        "status": "blocked_not_ready",
    })

    _write_json(root / "ui_screenshot_manifest.json", {
        "schemaVersion": "adaptive_learning_ui_screenshot_manifest_v1",
        "generatedAt": generated_at,
        "status": "completed" if ui_screenshots else "not_run",
        "screenshots": [dict(row) for row in (ui_screenshots or [])],
    })
    _write_json(root / "test_results.json", {
        "schemaVersion": "adaptive_learning_test_results_v1",
        "generatedAt": generated_at,
        "status": "not_run" if test_results is None else str(test_results.get("status") or "completed"),
        **dict(test_results or {}),
    })
    _write_json(root / "git_tag_push_receipt.json", {
        "schemaVersion": "adaptive_learning_git_tag_push_receipt_v1",
        "generatedAt": generated_at,
        "status": "not_run" if git_receipt is None else str(git_receipt.get("status") or "completed"),
        **dict(git_receipt or {}),
    })

    closeout = f"""# AlphaPilot V55.1 自适应学习安全点 Closeout

- 状态：Demo Observer 基础设施已就绪，决策模型训练尚未运行。
- 原 V55 Commit：`{insertion_receipt.get('originalV55Commit', '--')}`。
- 冻结 Release：`{release_identity.get('releaseId', '--')}`。
- Release Hash：`{release_identity.get('releaseHash', '--')}`。
- Risk Overlay Hash：`{release_identity.get('riskOverlayHash', '--')}`。
- Observer Model Hash：`{observer_policy.get('modelHash', '--')}`。
- Observer Policy Hash：`{observer_policy.get('modelPolicyHash', '--')}`。
- 当前旁路不排序、不否决、不改变风险、不创建订单。
- Demo 未由本补丁 ARM；Live 与 Withdraw 保持关闭。
- Live Readiness：blocked。必须训练并验证 rank_only / veto_only / meta_label 模型，生成新 Model Hash 与新 Release Hash，再进行精确人工批准。
"""
    (root / "final_closeout_cn.md").write_text(closeout, encoding="utf-8", newline="\n")

    manifest = _manifest(root, generated_at=generated_at)
    _write_json(root / "artifact_manifest.json", manifest)
    return manifest


def package_v55_adaptive_learning_evidence(
    evidence_root: Path | str,
    output_zip: Path | str,
) -> dict[str, Any]:
    root = Path(evidence_root).expanduser().resolve()
    archive = Path(output_zip).expanduser().resolve()
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive.with_suffix(archive.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            bundle.write(path, path.relative_to(root).as_posix())
    temporary.replace(archive)
    return {
        "path": str(archive),
        "bytes": archive.stat().st_size,
        "sha256": _sha256(archive),
    }
