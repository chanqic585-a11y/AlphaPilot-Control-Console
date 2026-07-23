from __future__ import annotations

import json
from pathlib import Path

import pytest

from alphapilot_control_console.strategy_factory_v2 import StrategyFactoryV2
from alphapilot_control_console.strategy_factory_v2.policy import (
    evaluate_continuous_research_readiness,
    require_continuous_research_enable,
)
from alphapilot_control_console.strategy_factory_v2.projection import (
    StrategyFactoryV2Projection,
)


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _hypothesis() -> dict:
    return {
        "hypothesisId": "hypothesis_001",
        "familyId": "trend_recovery",
        "familyFingerprint": "family_fp_trend_recovery_v1",
        "mechanism": "Trend recovery after a bounded pullback.",
        "falsifiableHypothesis": "Development expectancy remains positive after costs.",
        "invalidationConditions": ["averageNetR <= 0"],
        "timeframe": "1h",
        "direction": "both",
        "requiredData": ["ohlcv", "fees", "point_in_time_universe"],
        "exitPolicy": {"policyId": "exit_atr_v1", "version": 1},
        "sourceArtifactHashes": ["source:001"],
    }


def test_continuous_research_policy_requires_real_trial_and_formal_closure(
    tmp_path: Path,
) -> None:
    closure_path = tmp_path / "closure.json"
    policy_path = _write_json(
        tmp_path / "policy.json",
        {
            "schemaVersion": "strategy_factory_v2_runtime_policy_v1",
            "continuousResearch": {
                "enabled": True,
                "closureReceiptPath": str(closure_path),
            },
        },
    )

    missing = evaluate_continuous_research_readiness(policy_path)
    assert missing["allowed"] is False
    assert missing["blockers"] == ["real_trial_closure_receipt_missing"]

    _write_json(
        closure_path,
        {
            "schemaVersion": "strategy_factory_v2_real_trial_closure_v1",
            "acceptedRealTrialClosure": True,
            "completedTrialCount": 1,
            "formalEvidence": {
                "job": 1,
                "claim": 1,
                "attempt": 1,
                "result": 1,
                "read": 1,
            },
            "sourceArtifactHashes": ["artifact:trial", "artifact:formal"],
        },
    )

    ready = evaluate_continuous_research_readiness(policy_path)
    assert ready["allowed"] is True
    assert ready["blockers"] == []
    require_continuous_research_enable(policy_path)


def test_continuous_research_disabled_policy_cannot_be_bypassed(tmp_path: Path) -> None:
    policy_path = _write_json(
        tmp_path / "policy.json",
        {
            "schemaVersion": "strategy_factory_v2_runtime_policy_v1",
            "continuousResearch": {"enabled": False},
        },
    )

    with pytest.raises(ValueError, match="continuous_research_policy_disabled"):
        require_continuous_research_enable(policy_path)


def test_v2_projection_reports_real_states_without_execution_authority(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "factory.sqlite"
    factory = StrategyFactoryV2(state_path)
    try:
        factory.create_run(
            run_id="run_001",
            campaign_id="campaign_001",
            hypothesis_draft=_hypothesis(),
        )
    finally:
        factory.close()

    projection = StrategyFactoryV2Projection(state_path)
    summary = projection.summary()
    runs = projection.runs()
    detail = projection.run("run_001")

    assert summary["stateCounts"] == {"hypothesis_draft": 1}
    assert summary["completedTrialCount"] == 0
    assert summary["executionAuthorized"] is False
    assert runs["runs"][0]["state"] == "hypothesis_draft"
    assert detail["runId"] == "run_001"
    assert detail["executionAuthorized"] is False
