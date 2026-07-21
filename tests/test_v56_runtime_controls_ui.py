from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (ROOT / "web" / "top200-minimal-ui.js").read_text(encoding="utf-8")


RUNTIME_FIELDS = {
    "allocatedCapital",
    "riskPerTradePercent",
    "riskPerTradeUSDT",
    "maximumPortfolioOpenRiskPercent",
    "maximumPortfolioOpenRiskUSDT",
    "maximumConcurrentPositions",
    "maximumInstrumentRisk",
    "maximumSameDirectionRisk",
    "maximumCorrelationClusterRisk",
    "maximumPortfolioBeta",
    "maximumLeverage",
    "marginMode",
    "dailyLossLimit",
    "programLossLimit",
    "hardKillLossLimit",
    "scanTopN",
}


def test_v56_controls_stay_collapsed_on_the_simple_demo_page() -> None:
    assert 'id="top200RuntimeControls"' in HTML
    assert '<details id="top200RuntimeControls"' in HTML
    assert 'id="runtimeRiskEnvironment"' in HTML
    assert 'id="runtimeRiskFields"' in HTML
    assert 'id="runtimeRiskCreateButton"' in HTML
    assert 'id="runtimeRiskApprovalPanel"' in HTML
    assert 'id="strategyVersionSwitchForm"' in HTML
    assert 'id="manualInterventionForm"' in HTML


def test_runtime_risk_ui_projects_the_complete_bounded_contract() -> None:
    for field in RUNTIME_FIELDS:
        assert field in SCRIPT
    assert 'fetchJson("/api/risk-profiles"' in SCRIPT
    assert 'fetchJson("/api/risk-profiles/runtime-overlays/create"' in SCRIPT
    assert 'fetchJson("/api/risk-profiles/runtime-overlays/approve"' in SCRIPT
    create_section = SCRIPT.split("async function createRuntimeRiskOverlay", 1)[1].split(
        "async function approveRuntimeRiskOverlay", 1
    )[0]
    assert "/runtime-overlays/approve" not in create_section


def test_strategy_switch_and_intervention_use_audited_non_execution_routes() -> None:
    assert 'fetchJson("/api/strategy-version-switch/action"' in SCRIPT
    assert 'fetchJson("/api/manual-interventions/record"' in SCRIPT
    assert "new_entries_only" in HTML
    assert "flatten_then_switch" in HTML
    assert "manual_position_migration" in HTML
    assert "executionEnabled" in SCRIPT
