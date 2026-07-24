from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (ROOT / "web" / "top200-minimal-ui.js").read_text(encoding="utf-8")


def test_strategy_factory_has_compact_bounded_controls() -> None:
    assert 'id="top200StrategyGenerateButton"' in HTML
    assert 'id="strategyFactoryContinuousButton"' in HTML
    assert 'id="strategyFactoryContinuousStatus"' in HTML
    assert 'id="strategyFactoryDialog"' in HTML
    assert 'id="strategyFactoryOperation"' in HTML
    assert 'id="strategyFactoryTimeframe"' in HTML
    assert 'id="strategyFactoryMode"' in HTML
    assert 'id="strategyFactoryCandidateBudget"' in HTML
    assert 'id="strategyFactoryTrialBudget"' in HTML
    assert 'id="strategyFactorySubmit"' in HTML
    assert 'id="strategyFactoryTaskEvidence"' in HTML
    assert 'id="strategyFactoryTaskStage"' in HTML
    assert 'id="strategyFactoryTaskProgress"' in HTML
    assert 'id="strategyFactoryDataEvidence"' in HTML
    assert 'id="strategyFactoryMetricEvidence"' in HTML
    assert 'id="strategyFactoryFormalEvidence"' in HTML
    assert 'id="strategyFactoryArtifactEvidence"' in HTML
    assert "生成策略" in HTML
    assert "组合策略" in HTML
    assert "快速" in HTML
    assert "标准" in HTML
    assert 'id="top200StrategyGenerateButton" type="button" disabled' not in HTML


def test_strategy_factory_ui_calls_only_bounded_research_routes() -> None:
    assert 'fetchJson("/api/research-factory/runs", {' in SCRIPT
    assert 'method: "POST"' in SCRIPT
    assert "/api/research-factory/runs/${encodeURIComponent(runId)}/pause" in SCRIPT
    assert "/api/research-factory/runs/${encodeURIComponent(runId)}/resume" in SCRIPT
    assert 'fetchJson("/api/research-factory/continuous")' in SCRIPT
    assert 'fetchJson(`/api/research-factory/continuous/${action}`' in SCRIPT
    assert "停止持续研究" in SCRIPT
    assert "持续研究" in SCRIPT
    assert "automaticPromotionAllowed" in SCRIPT
    assert "demoArm" in SCRIPT
    assert "orderCount" in SCRIPT
    assert "/approve" not in SCRIPT.split("async function submitStrategyFactory", 1)[-1].split("function renderDemoStrategyCard", 1)[0]
    assert "/arm" not in SCRIPT.split("async function submitStrategyFactory", 1)[-1].split("function renderDemoStrategyCard", 1)[0]


def test_strategy_factory_pause_request_is_visible_and_not_resumable_early() -> None:
    assert 'factory.status === "pause_requested"' in SCRIPT
    assert "正在安全暂停" in SCRIPT


def test_strategy_factory_dialog_stays_open_and_renders_truthful_evidence() -> None:
    submit_body = SCRIPT.split("async function submitStrategyFactory", 1)[1].split(
        "async function toggleStrategyFactoryRun", 1
    )[0]
    assert "closeStrategyFactoryDialog" not in submit_body
    assert "renderStrategyFactoryTaskEvidence" in SCRIPT
    assert "executionEvidence" in SCRIPT
    assert "Development 回测" in SCRIPT
    assert "Formal 正式验证" in SCRIPT
    assert "锁定 OOS 未读取" in SCRIPT
    assert "setInterval" not in submit_body
