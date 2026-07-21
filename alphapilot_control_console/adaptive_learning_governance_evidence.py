"""Build a non-mutating governance overlay for adaptive-learning Live readiness."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .adaptive_learning_technical_readiness import (
    AdaptiveLearningTechnicalReadinessGate,
    REQUIRED_TECHNICAL_EVIDENCE,
)
from .exact_live_release_approval_gate import ExactLiveReleaseApprovalGate
from .execution_latency_profile import build_execution_latency_profile
from .live_arm_gate import LiveArmGate


BLOCKED_STATUS = "draft_blocked_technical_readiness"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


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


def _stable_hash(prefix: str, payload: Mapping[str, Any]) -> str:
    body = json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return prefix + hashlib.sha256(body).hexdigest()


def _load_required_source(source: Path) -> dict[str, dict[str, Any]]:
    names = (
        "experimental_live_release.json",
        "exact_live_approval_request.json",
        "experimental_live_risk_overlay.json",
        "adaptive_learning_live_readiness.json",
        "observer_sidecar_binding.json",
    )
    missing = [name for name in names if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError(
            "Adaptive-learning governance source is incomplete: " + ",".join(missing)
        )
    return {name: _read_json(source / name) for name in names}


def _model_policy(
    release: Mapping[str, Any],
    observer: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "modelMode": str(readiness.get("modelMode") or "observer"),
        "modelHash": str(release.get("modelHash") or observer.get("modelHash") or ""),
        "modelPolicyHash": str(
            release.get("modelPolicyHash") or observer.get("modelPolicyHash") or ""
        ),
        "featureSchemaHash": str(
            observer.get("featureSchemaHash") or release.get("featureSchemaHash") or ""
        ),
        "factorRegistryHash": str(
            observer.get("factorRegistryHash") or release.get("factorRegistryHash") or ""
        ),
        "lifecycleStatus": str(observer.get("lifecycleStatus") or "observer"),
    }


def _technical_evidence(readiness: Mapping[str, Any]) -> dict[str, bool]:
    capabilities = readiness.get("capabilities")
    if isinstance(capabilities, list):
        indexed = {
            str(row.get("capability") or ""): row.get("ready") is True
            for row in capabilities
            if isinstance(row, Mapping)
        }
        return {
            key: indexed.get(key) is True
            for key in REQUIRED_TECHNICAL_EVIDENCE
        }
    existing = readiness.get("evidenceStatus")
    if not isinstance(existing, Mapping):
        return {key: False for key in REQUIRED_TECHNICAL_EVIDENCE}
    return {
        key: existing.get(key) is True
        for key in REQUIRED_TECHNICAL_EVIDENCE
    }


def _latest_technical_snapshot(
    source: Path,
    configured: Path | str | None,
) -> tuple[dict[str, Any] | None, Path | None]:
    if configured is not None:
        path = Path(configured).expanduser().resolve()
        return _read_json(path), path
    project_root = source.parents[2]
    candidates = sorted(
        (project_root / "reports" / "v59_adaptive_learning").glob(
            "*/adaptive_learning_readiness_snapshot.json"
        )
    )
    if not candidates:
        return None, None
    path = candidates[-1]
    return _read_json(path), path


def _gap_next_action(capability: str) -> str:
    actions = {
        "factorProductionReady": "Freeze a production factor registry and feature schema.",
        "realFactorBenchReady": "Run a real point-in-time Factor Bench with costs.",
        "alpha101Ready": "Validate the bounded Alpha101-compatible subset.",
        "alpha191CompatibilityReady": "Validate the bounded Alpha191-compatible subset.",
        "validatedCryptoFactorSubsetReady": "Freeze the validated crypto factor shortlist.",
        "boundedFactorMiningReady": "Complete a budgeted factor-mining campaign.",
        "adaptiveMlTrainingReady": "Train and validate a decision-participating model.",
        "qlibOfflineCampaignReady": "Complete the registered Qlib offline campaign.",
        "modelRegistryReady": "Register the validated model and immutable hashes.",
        "continuousLearningDatasetReady": "Freeze a reconciled learning dataset.",
        "demoOutcomeToTrainingSampleReady": "Bind reconciled Demo outcomes to samples.",
        "shadowInferenceReady": "Run deterministic shadow inference.",
        "demoDecisionModeValidated": "Validate rank_only, veto_only, or meta_label in Demo.",
        "modelDriftMonitoringReady": "Validate drift thresholds and monitoring.",
        "modelRollbackReady": "Rehearse exact model rollback.",
        "onlineInferenceLatencyReady": "Validate versioned inference and order latency.",
        "liveFeaturePipelineReady": "Prove Demo and Live feature-pipeline parity.",
        "liveModelInferenceReady": "Prove deterministic Live decision inference.",
        "modelReleaseBindingReady": "Bind new model and policy hashes to a new Live Release.",
    }
    return actions[capability]


def _manifest(root: Path, *, generated_at: str) -> dict[str, Any]:
    paths = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"
    )
    core: dict[str, Any] = {
        "schemaVersion": "adaptive_learning_governance_manifest_v1",
        "generatedAt": generated_at,
        "status": BLOCKED_STATUS,
        "selfReferenceExclusions": ["artifact_manifest.json"],
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
    return {**core, "manifestHash": _stable_hash("adaptive_governance_", core)}


def generate_adaptive_learning_governance_evidence(
    source_root: Path | str,
    output_root: Path | str,
    *,
    generated_at: str,
    technical_snapshot_path: Path | str | None = None,
) -> dict[str, Any]:
    """Create a superseding governance disposition without editing frozen inputs."""

    source = Path(source_root).expanduser().resolve()
    output = Path(output_root).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    payloads = _load_required_source(source)
    release = payloads["experimental_live_release.json"]
    approval_request = payloads["exact_live_approval_request.json"]
    source_risk = payloads["experimental_live_risk_overlay.json"]
    old_readiness = payloads["adaptive_learning_live_readiness.json"]
    observer = payloads["observer_sidecar_binding.json"]
    technical_snapshot, technical_snapshot_source = _latest_technical_snapshot(
        source,
        technical_snapshot_path,
    )

    source_artifacts = [
        {
            "path": name,
            "sha256": _sha256(source / name),
        }
        for name in sorted(payloads)
    ]
    model_policy = _model_policy(release, observer, old_readiness)
    evidence = _technical_evidence(technical_snapshot or old_readiness)
    technical = AdaptiveLearningTechnicalReadinessGate().evaluate(
        model_policy=model_policy,
        evidence=evidence,
    )
    technical = {
        **technical,
        "generatedAt": generated_at,
        "status": "blocked_not_ready" if not technical["passed"] else "passed",
    }

    disposition_core: dict[str, Any] = {
        "schemaVersion": "adaptive_learning_live_draft_disposition_v1",
        "generatedAt": generated_at,
        "status": BLOCKED_STATUS,
        "releaseId": str(release.get("releaseId") or ""),
        "releaseHash": str(release.get("releaseHash") or ""),
        "riskOverlayHash": str(
            release.get("riskOverlayHash") or source_risk.get("riskOverlayHash") or ""
        ),
        "approvalRequestHash": str(approval_request.get("approvalRequestHash") or ""),
        "modelHash": str(release.get("modelHash") or observer.get("modelHash") or ""),
        "modelPolicyHash": str(
            release.get("modelPolicyHash") or observer.get("modelPolicyHash") or ""
        ),
        "modelMode": str(old_readiness.get("modelMode") or "observer"),
        "approvalRequestActionable": False,
        "mechanicalExecutionAllowedAfterExactApproval": False,
        "exactLiveReleaseApprovalRequested": False,
        "liveArmAllowed": False,
        "strategyLiveOrdersAllowed": False,
        "liveEnabled": False,
        "withdrawAllowed": False,
        "immutableSourceArtifactsPreserved": True,
        "sourceArtifacts": source_artifacts,
        "technicalSnapshotSource": (
            {
                "path": str(technical_snapshot_source),
                "sha256": _sha256(technical_snapshot_source),
            }
            if technical_snapshot_source is not None
            else None
        ),
        "successorIdentityRequiredAfterTechnicalReadiness": {
            "newModelHash": True,
            "newModelPolicyHash": True,
            "newLiveReleaseHash": True,
            "newApprovalRequestHash": True,
        },
    }
    disposition = {
        **disposition_core,
        "dispositionHash": _stable_hash("adaptive_live_disposition_", disposition_core),
    }

    draft_release = {
        **release,
        "status": BLOCKED_STATUS,
        "executionBoundary": {
            **dict(release.get("executionBoundary") or {}),
            "mechanicalExecutionAllowedAfterExactApproval": False,
            "withdrawAllowed": False,
        },
    }
    draft_approval_request = {
        **approval_request,
        "status": BLOCKED_STATUS,
        "requiredConfirmation": None,
        "approvalRequestActionable": False,
        "mechanicalExecutionAllowedAfterExactApproval": False,
    }
    draft_risk = {
        **source_risk,
        "schemaVersion": "adaptive_learning_draft_risk_profile_v1",
        "generatedAt": generated_at,
        "status": "draft",
        "allRiskParametersAdjustableBeforeApproval": True,
        "riskChangeRequiresNewRiskOverlayHash": True,
        "approvalRequestActionable": False,
    }
    bundle = {
        "liveRelease": draft_release,
        "approvalRequest": draft_approval_request,
        "riskOverlay": draft_risk,
        "adaptiveLearningTechnicalReadiness": technical,
    }
    exact = ExactLiveReleaseApprovalGate().evaluate(bundle=bundle, approval=None)
    exact = {**exact, "generatedAt": generated_at, "status": "not_actionable"}
    arm = LiveArmGate().evaluate(
        bundle=bundle,
        approval_gate=exact,
        runtime={
            "credentialsConfigured": False,
            "privateReadReady": False,
            "reconciliationMatched": False,
            "zeroOpenPositions": True,
            "zeroOpenOrders": True,
            "liveEnabled": False,
            "withdrawAllowed": False,
        },
    )
    arm = {**arm, "generatedAt": generated_at, "status": "not_run"}
    latency = {
        **build_execution_latency_profile(),
        "generatedAt": generated_at,
        "maximumSignalAgeSecondsAllowed": False,
        "criticalLatencyFailureMeaning": "fail_closed_critical_latency_only",
        "operatorConfigurableWithNewVersionAndHash": [
            "signalToOrderSendTargetMs",
            "maximumSignalAgeMs",
            "exchangeAckTimeoutMs",
        ],
    }
    gap_matrix = {
        "schemaVersion": "adaptive_learning_technical_gap_matrix_v1",
        "generatedAt": generated_at,
        "status": "blocked_not_ready",
        "readyCount": sum(technical["evidenceStatus"].values()),
        "requiredCount": len(REQUIRED_TECHNICAL_EVIDENCE),
        "gaps": [
            {
                "capability": capability,
                "ready": technical["evidenceStatus"][capability],
                "nextAction": _gap_next_action(capability),
            }
            for capability in REQUIRED_TECHNICAL_EVIDENCE
            if not technical["evidenceStatus"][capability]
        ],
        "modelModeBlocker": model_policy["modelMode"] not in {
            "rank_only",
            "veto_only",
            "meta_label",
        },
        "observerModelMayEnterLive": False,
    }

    _write_json(output / "adaptive_learning_technical_readiness_gate.json", technical)
    _write_json(output / "current_experimental_live_draft_disposition.json", disposition)
    _write_json(output / "current_experimental_live_release_projection.json", draft_release)
    _write_json(output / "current_exact_live_approval_request_projection.json", draft_approval_request)
    _write_json(output / "exact_live_release_approval_gate.json", exact)
    _write_json(output / "live_arm_gate.json", arm)
    _write_json(output / "execution_latency_policy_binding.json", latency)
    _write_json(output / "draft_risk_profile.json", draft_risk)
    _write_json(output / "technical_gap_matrix.json", gap_matrix)
    closeout = f"""# Adaptive Learning Live 治理修正 Closeout

- 当前状态：`{BLOCKED_STATUS}`。
- 当前 Experimental Live Release：`{disposition['releaseHash']}`，仅保留历史身份，不可批准、不可 ARM、不可机械执行。
- 当前 Model Mode：`{disposition['modelMode']}`，observer 不得进入 Live。
- 技术就绪门：未通过；人工精确批准不参与技术就绪计算。
- 精确批准门：不可操作，未请求用户批准。
- Live ARM 门：未运行；Live 与 Withdraw 保持关闭；未创建策略 Live 订单。
- 延迟语义：`criticalLatencyFailureMs=20000` 仅表示严重延迟故障；最大信号年龄必须小于该阈值。
- 风险参数：当前 Risk Profile 保持草稿；任何调整都必须生成新的 Risk Overlay Hash。
- 后续身份：只有技术证据全部通过后，才生成新的 Model Hash、Model Policy Hash、Live Release Hash 和 Approval Request。
"""
    (output / "final_closeout_cn.md").write_text(
        closeout,
        encoding="utf-8",
        newline="\n",
    )
    manifest = _manifest(output, generated_at=generated_at)
    _write_json(output / "artifact_manifest.json", manifest)
    return {
        "status": BLOCKED_STATUS,
        "releaseHash": disposition["releaseHash"],
        "riskOverlayHash": disposition["riskOverlayHash"],
        "technicalReadinessPassed": technical["passed"],
        "approvalRequestActionable": False,
        "liveArmStatus": "not_run",
        "manifestHash": manifest["manifestHash"],
        "output": str(output),
    }
