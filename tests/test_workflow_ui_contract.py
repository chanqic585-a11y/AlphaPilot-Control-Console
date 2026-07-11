from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkflowUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        cls.http_app = (ROOT / "alphapilot_control_console" / "http_app.py").read_text(encoding="utf-8")

    def test_failed_or_blocked_workflow_has_three_required_actions(self) -> None:
        for label in ("重新回测", "改善优化", "归档"):
            self.assertIn(f'label: "{label}"', self.js)
        self.assertIn('action: "rerun"', self.js)
        self.assertIn('action: "optimize"', self.js)

    def test_local_and_demo_lifecycle_cards_expose_optimization_action(self) -> None:
        self.assertIn('data-lifecycle-action="optimize"', self.js)
        self.assertIn("openStrategyOptimizationDialog", self.js)
        self.assertIn("latestStrategyLifecyclePayload", self.js)

    def test_parameter_dialog_explains_immutable_restart(self) -> None:
        self.assertIn('id="strategyOptimizationDialog"', self.html)
        self.assertIn('id="strategyOptimizationParameterList"', self.html)
        self.assertIn('id="strategyOptimizationRecommendations"', self.html)
        self.assertIn("创建优化版本并重新回测", self.html)
        self.assertIn("参数改变后会创建新版本", self.html)
        self.assertIn("strategy-optimization-dialog", self.css)

    def test_static_asset_cachebuster_matches_patch(self) -> None:
        self.assertIn("v13-27-1-4-demo-evidence", self.html)

    def test_back_to_strategy_control_is_compact_and_named(self) -> None:
        self.assertIn('title="回到策略页"', self.html)
        self.assertIn(".back-home-button::before", self.css)
        self.assertIn('content: "←"', self.css)

    def test_api_errors_surface_backend_parameter_reason(self) -> None:
        self.assertIn("payload.message || payload.error", self.js)

    def test_demo_workflow_has_projection_and_action_endpoints(self) -> None:
        self.assertIn('path == "/api/demo-workflow"', self.http_app)
        self.assertIn('parsed.path == "/api/demo-workflow/action"', self.http_app)

    def test_okx_demo_launcher_endpoint_is_bound_to_request_client(self) -> None:
        self.assertIn('parsed.path == "/api/local-control/open-okx-demo-launcher"', self.http_app)
        self.assertIn("self.client_address[0]", self.http_app)
        self.assertIn("LOCAL_DEMO_LAUNCHER.open", self.http_app)

    def test_lifecycle_cards_show_visible_stage_progress(self) -> None:
        self.assertIn("lifecycle-progress-track", self.js)
        self.assertIn("progress.percent", self.js)
        self.assertIn("当前步骤", self.js)
        self.assertIn("lifecycle-progress-track", self.css)

    def test_demo_page_uses_four_explicit_workflow_queues(self) -> None:
        for label in ("待 Demo 模拟", "Demo 验证中", "Demo 模拟通过", "实盘候选"):
            self.assertIn(label, self.html)
        for target_id in (
            "demoWorkflowWaitingList",
            "demoWorkflowValidatingList",
            "demoWorkflowPassedList",
            "demoWorkflowLiveCandidateList",
        ):
            self.assertIn(f'id="{target_id}"', self.html)
        self.assertIn("function renderDemoWorkflow", self.js)
        self.assertIn("function runDemoWorkflowAction", self.js)

    def test_demo_cards_show_process_trade_pnl_and_failure_fields(self) -> None:
        for label in (
            "当前首选候选",
            "实际持仓币种",
            "持仓状态",
            "买入 / 开仓价",
            "目标盈利价",
            "止损价",
            "浮动盈亏",
            "已实现盈亏",
            "手续费",
            "滑点",
            "失败原因",
            "改善建议",
        ):
            self.assertIn(label, self.js)
        self.assertIn("demo-process-steps", self.css)
        self.assertIn("demo-workflow-trade-grid", self.css)
        self.assertIn("启动命令", self.js)
        self.assertIn("nextAction.command", self.js)

    def test_all_running_workflows_render_a_visible_progress_track(self) -> None:
        self.assertIn("function dualLayerProgressModel", self.js)
        self.assertIn("workflow-run-progress-track", self.js)
        self.assertIn("workflow-run-progress-track", self.css)
        self.assertIn('status === "paused"', self.js)
        self.assertIn("downloadProgress", self.js)

    def test_demo_cards_show_permanent_evidence_and_full_market_summary(self) -> None:
        for label in (
            "证据清单",
            "系统自动",
            "人工操作",
            "受控放行",
            "OKX USDT 永续全市场",
            "市场合约",
            "流动性合格",
            "策略匹配",
            "深度扫描",
        ):
            self.assertIn(label, self.js)
        self.assertIn("demo-evidence-list", self.css)
        self.assertIn("demo-market-universe", self.css)

    def test_demo_symbol_limit_and_override_have_explicit_controls(self) -> None:
        self.assertIn("每策略最多同时开仓", self.js)
        self.assertIn('action: "update_demo_strategy_settings"', self.js)
        self.assertIn('id="demoOverrideDialog"', self.html)
        self.assertIn('id="demoOverrideReason"', self.html)
        self.assertIn('id="demoOverrideConfirmation"', self.html)
        self.assertIn("仅放行到OKX DEMO", self.html)
        self.assertIn('action: "authorize_demo_override"', self.js)
        self.assertIn("不会直接形成实盘候选", self.html)

    def test_demo_and_live_use_shared_compact_execution_summary(self) -> None:
        self.assertIn("function renderCompactExecutionPositions", self.js)
        self.assertGreaterEqual(self.js.count("renderCompactExecutionPositions("), 3)
        self.assertIn("compact-execution-positions", self.css)
        self.assertIn("风险配置与闭环证据", self.html)
        self.assertIn("高级配置，默认折叠", self.html)


if __name__ == "__main__":
    unittest.main()
