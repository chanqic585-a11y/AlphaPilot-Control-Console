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
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        patch_doc = ROOT / "docs" / "V13.27.9-top100-demo-release.md"
        cls.patch_doc = patch_doc.read_text(encoding="utf-8") if patch_doc.exists() else ""
        issue_guidance_path = ROOT / "web" / "issue-guidance.js"
        cls.issue_js = issue_guidance_path.read_text(encoding="utf-8") if issue_guidance_path.exists() else ""

    def test_failed_or_blocked_workflow_has_three_required_actions(self) -> None:
        for label in ("重新回测", "改善优化", "归档"):
            self.assertIn(f'label: "{label}"', self.js)
        self.assertIn('action: "rerun"', self.js)
        self.assertIn('action: "optimize"', self.js)

    def test_failed_workflow_exposes_bounded_auto_optimization_state(self) -> None:
        self.assertIn('action: "auto-optimize"', self.js)
        self.assertIn('label: "自动优化（最多3次）"', self.js)
        self.assertIn("自动优化已审查", self.js)
        self.assertIn("结构性弱势", self.js)

    def test_auto_optimization_requires_explicit_backend_capability(self) -> None:
        self.assertIn(
            "payload?.capabilities?.boundedOptimizationRecovery === true",
            self.js,
        )
        self.assertIn("当前控制台后端未加载自动优化", self.js)

    def test_structural_redesign_lifecycle_requires_explicit_capability(self) -> None:
        self.assertIn(
            "payload?.capabilities?.structuralRedesignRecovery === true",
            self.js,
        )
        self.assertIn("自动重设计 ${generation}/${maxGenerations}", self.js)
        self.assertIn("失败父版本已归档", self.js)
        self.assertIn("生成子策略", self.js)
        self.assertIn("结构重设计已达到最多 3 代", self.js)
        self.assertIn("没有新的受控结构配方可用", self.js)

    def test_local_and_demo_lifecycle_cards_expose_optimization_action(self) -> None:
        self.assertIn('data-lifecycle-action="optimize"', self.js)
        self.assertIn("openStrategyOptimizationDialog", self.js)
        self.assertIn("latestStrategyLifecyclePayload", self.js)

    def test_local_forward_card_can_open_audited_demo_release_dialog(self) -> None:
        self.assertIn("人工放行到 Demo", self.js)
        self.assertIn("data-local-forward-demo-release", self.js)
        self.assertIn("item.result?.strategyCandidateId", self.js)
        self.assertIn(
            "openDemoOverrideDialog(demoButton.dataset.strategyId",
            self.js,
        )
        self.assertIn("Demo 验证通过后可进入实盘候选复核", self.html)

    def test_parameter_dialog_explains_immutable_restart(self) -> None:
        self.assertIn('id="strategyOptimizationDialog"', self.html)
        self.assertIn('id="strategyOptimizationParameterList"', self.html)
        self.assertIn('id="strategyOptimizationRecommendations"', self.html)
        self.assertIn("创建优化版本并重新回测", self.html)
        self.assertIn("参数改变后会创建新版本", self.html)
        self.assertIn("strategy-optimization-dialog", self.css)

    def test_static_asset_cachebuster_matches_patch(self) -> None:
        self.assertIn("v13-27-11-family-current", self.html)

    def test_patch_version_and_documentation_are_consistent(self) -> None:
        self.assertIn('version: "V13.27.9"', self.js)
        self.assertIn('"version": "V13.27.9"', self.http_app)
        self.assertIn("AlphaPilot V13.27.9", self.readme)
        self.assertIn("Top100 Demo Release", self.patch_doc)
        self.assertIn("process-only", self.patch_doc)
        self.assertIn("Top100", self.patch_doc)
        self.assertIn("no-order", self.patch_doc)

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

    def test_failed_auto_execution_action_shows_backend_blockers(self) -> None:
        self.assertIn("responsePayload.blockers", self.js)
        self.assertIn("translateExchangeDemoBlocker(value)", self.js)

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

    def test_demo_preflight_action_normalizes_stale_running_projection(self) -> None:
        self.assertIn("function normalizeDemoWorkflowItem", self.js)
        self.assertIn('nextAction.actionId === "run_demo_preflight"', self.js)
        self.assertIn('matchStatus === "not_started"', self.js)
        self.assertIn("normalizedMarket.currentTopCandidate = null", self.js)
        self.assertIn('if (action === "run_demo_preflight")', self.js)
        self.assertIn("await runExchangeDemoReadOnlyCheck()", self.js)
        self.assertIn("await loadDemoWorkflow(true)", self.js)

    def test_demo_readonly_failure_registers_one_time_actionable_guidance(self) -> None:
        self.assertIn("function collectDemoReadonlyIssue", self.js)
        self.assertIn("okx_demo_50110_key_type_ip_or_domain", self.js)
        self.assertIn("OKX Demo 前检查失败", self.js)
        self.assertIn("IP 白名单", self.js)
        self.assertIn("refreshDemoPageIssues", self.js)
        self.assertIn('version: "readonly-preflight-v1"', self.js)
        self.assertIn("issueController.presentHighestPriority", self.js)
        self.assertIn("const exchangePayloadReady", self.js)
        self.assertIn("if (!exchangePayloadReady) return", self.js)

    def test_demo_preflight_final_status_is_set_before_workflow_refresh(self) -> None:
        branch_start = self.js.index('if (action === "run_demo_preflight")')
        branch_end = self.js.index("return;", branch_start)
        branch = self.js[branch_start:branch_end]
        final_status = branch.index('response?.ok ? "Demo 前检查已通过')
        refresh = branch.index("await loadDemoWorkflow(true)")
        self.assertLess(final_status, refresh)

    def test_backtest_summary_separates_queued_running_and_paused(self) -> None:
        self.assertIn('const queued = items.filter((item) => item.status === "queued")', self.js)
        self.assertIn('const running = items.filter((item) => item.status === "running")', self.js)
        self.assertIn('const paused = items.filter((item) => item.status === "paused")', self.js)
        for label in ("排队中", "正在执行", "已暂停"):
            self.assertIn(label, self.js)
        self.assertNotIn(
            'const running = items.filter((item) => ["queued", "running", "paused"].includes(item.status))',
            self.js,
        )

    def test_terminal_backtest_counts_use_current_strategy_family_only(self) -> None:
        self.assertIn("function workflowCurrentFamilyItems", self.js)
        self.assertIn("const currentItems = workflowCurrentFamilyItems(payload)", self.js)
        self.assertIn(
            'const currentBacktests = currentItems.filter((item) => item.stage === "backtest")',
            self.js,
        )
        self.assertIn(
            'const passed = currentBacktests.filter((item) => item.status === "passed")',
            self.js,
        )
        self.assertIn(
            'const failed = currentBacktests.filter((item) => ["failed", "blocked", "cancelled"].includes(item.status))',
            self.js,
        )
        self.assertIn("历史失败尝试保留在审计记录", self.js)

    def test_demo_strategy_settings_include_one_to_five_leverage(self) -> None:
        self.assertIn("data-demo-leverage", self.js)
        self.assertIn("value === requestedLeverage", self.js)
        self.assertIn("leverage: Number", self.js)
        self.assertIn("Array.from({ length: 5 }", self.js)
        self.assertIn("${value}x", self.js)

    def test_strategy_lists_are_grouped_by_timeframe_across_all_pages(self) -> None:
        self.assertIn("function renderStrategyTimeframeGroups", self.js)
        self.assertIn("function groupStrategiesByTimeframe", self.js)
        grouped_renderers = {
            "renderStrategyObservationDailyReport": "renderStrategyTimeframeGroups",
            "renderUsableStrategyCatalog": "renderStrategyTimeframeGroups",
            "renderLifecycleCards": "renderStrategyTimeframeGroups",
            "renderSimpleStrategyCards": "renderStrategyTimeframeGroups",
            "renderSimpleReviewQueue": "renderStrategyTimeframeGroups",
            "renderQualityCenter": "renderStrategyTimeframeGroups",
            "renderStrategyAssetPlaybook": "renderStrategyTimeframeGroups",
            "renderTestnetDrill": "renderStrategyTimeframeGroups",
            "renderLocalLab": "renderStrategyTimeframeGroups",
            "renderExchangeDemoPipeline": "renderStrategyTimeframeGroups",
            "renderNoKeyPreLiveWorkbench": "renderStrategyTimeframeGroups",
            "renderAutoExecutionReview": "renderStrategyTimeframeGroups",
            "renderAutoExecutionLearning": "renderStrategyTimeframeGroups",
            "renderClosedSampleReplay": "renderStrategyTimeframeGroups",
            "renderCandidateQueue": "renderStrategyTimeframeGroups",
            "renderShortCycleCandidatePool": "renderStrategyTimeframeGroups",
            "renderStrategyPlaybookSelector": "renderStrategyTimeframeGroups",
            "renderPromotionRows": "renderStrategyTimeframeGroups",
            "renderStrategyArtifacts": "renderStrategyTimeframeGroups",
            "renderStrategyLearningLoop": "renderStrategyTimeframeGroups",
            "renderStrategies": "groupStrategiesByTimeframe",
            "renderStrategySlots": "renderStrategyTimeframeGroups",
        }
        for function_name, expected in grouped_renderers.items():
            start = self.js.index(f"function {function_name}")
            next_function = self.js.find("\nfunction ", start + 1)
            segment = self.js[start:next_function if next_function >= 0 else len(self.js)]
            self.assertIn(expected, segment, function_name)
        for renderer in (
            "renderDualLayerCard",
            "renderFormalLocalForwardCard",
            "renderDemoWorkflowCard",
            "renderLiveCandidateCard",
        ):
            self.assertIn(renderer, self.js)
        for label in ("5m", "15m", "1H", "4H", "1D", "其他"):
            self.assertIn(label, self.js)

    def test_demo_runtime_separates_current_result_from_historical_blocker(self) -> None:
        self.assertIn('id="demoAutoExecutionLastBlocked"', self.html)
        self.assertIn("automaticExecutionCurrentResultLabel", self.js)
        self.assertIn("automaticExecutionLastBlockedLabel", self.js)
        self.assertIn("当前结果", self.html)
        self.assertIn("上次阻塞", self.html)

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
        self.assertIn("function renderFormalDataProgress", self.js)
        self.assertIn("official-download-progress", self.js)
        self.assertIn("official-download-progress", self.css)
        self.assertIn("requestCount", self.js)
        self.assertIn("rowCount", self.js)
        self.assertIn("控制台重启后会从当前检查点自动继续", self.html)

    def test_local_formal_progress_distinguishes_conversion_from_reuse(self) -> None:
        self.assertIn("function formalPreparationModeLabel", self.js)
        for label in (
            "首次转换本地正式数据",
            "复用本地正式数据仓",
            "校验本地正式数据",
            "本地正式数据已就绪",
            "正式回测计算中",
            "不会请求交易所历史接口",
        ):
            self.assertIn(label, self.js)
        self.assertNotIn("首次下载官方数据", self.js)

    def test_repaired_optimizer_copy_does_not_mislabel_allowlist_gap(self) -> None:
        self.assertIn("当前新策略族已纳入受控参数白名单", self.js)
        self.assertIn("自动 Challenger 已创建并排队", self.js)
        self.assertNotIn("当前是数据或工程证据阻塞，不应通过调参掩盖", self.js)

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
            "Top100 深度扫描",
        ):
            self.assertIn(label, self.js)
        self.assertIn("demo-evidence-list", self.css)
        self.assertIn("demo-market-universe", self.css)

    def test_one_time_issue_guidance_has_persistent_and_session_fallbacks(self) -> None:
        self.assertIn('id="issueGuidanceDialog"', self.html)
        self.assertIn('id="issueGuidanceNextAction"', self.html)
        self.assertIn('/issue-guidance.js?v=20260715-demo-runtime-recovery', self.html)
        self.assertIn('/app.js?v=20260715-demo-runtime-recovery', self.html)
        self.assertIn("ALPHAPILOT_ISSUE_ACK_V1", self.issue_js)
        self.assertIn("function issueFingerprint", self.issue_js)
        self.assertIn("localStorage", self.issue_js)
        self.assertIn("sessionStorage", self.issue_js)
        self.assertIn("presentHighestPriority", self.issue_js)
        self.assertIn("if (dialog.open) return false", self.issue_js)

    def test_issue_guidance_acknowledge_button_persists_before_closing(self) -> None:
        self.assertIn('id="issueGuidanceAcknowledgeButton"', self.html)
        self.assertIn('getElementById("issueGuidanceAcknowledgeButton")', self.issue_js)
        self.assertIn("event.preventDefault()", self.issue_js)
        acknowledge_index = self.issue_js.index("acknowledgeCurrent();", self.issue_js.index("issueGuidanceAcknowledgeButton"))
        close_index = self.issue_js.index("dialog.close", self.issue_js.index("issueGuidanceAcknowledgeButton"))
        self.assertLess(acknowledge_index, close_index)

    def test_demo_guidance_uses_one_page_level_acknowledgement(self) -> None:
        self.assertIn("issue.acknowledgementId", self.issue_js)
        self.assertIn("issue.acknowledgementVersion", self.issue_js)
        self.assertIn("issue.acknowledgementScope", self.issue_js)
        self.assertGreaterEqual(self.js.count('acknowledgementId: "demo-page-guidance"'), 2)
        self.assertGreaterEqual(self.js.count('acknowledgementVersion: "demo-guidance-v1"'), 2)
        self.assertGreaterEqual(self.js.count('acknowledgementScope: "page"'), 2)

    def test_demo_evidence_is_collapsed_by_default(self) -> None:
        self.assertIn('<details class="demo-evidence-section">', self.js)
        self.assertIn('<summary class="demo-section-head">', self.js)
        self.assertNotIn('<details class="demo-evidence-section" open', self.js)

    def test_primary_pages_map_blockers_to_actionable_guidance(self) -> None:
        for name in (
            "collectStrategyIssues",
            "collectLocalIssues",
            "collectDemoIssues",
            "collectLiveIssues",
        ):
            self.assertIn(f"function {name}", self.js)
        self.assertIn("data-issue-guidance-key", self.js)
        self.assertIn("查看处理办法", self.js)
        self.assertIn("presentHighestPriority", self.js)

    def test_demo_runtime_has_one_click_local_launcher_and_shared_account_copy(self) -> None:
        self.assertIn('id="demoRuntimeLauncherButton"', self.html)
        self.assertIn("启动 OKX Demo", self.html)
        self.assertIn("/api/local-control/open-okx-demo-launcher", self.js)
        self.assertIn("启动器已打开，请在 PowerShell 窗口输入三项 Demo 凭据", self.js)
        self.assertIn("Demo 凭据每次运行只输入一次，全部合格策略共用", self.js)

    def test_demo_page_shows_compact_authenticated_instrument_universe(self) -> None:
        for target_id in (
            "demoInstrumentUniverseStatus",
            "demoInstrumentUniverseCounts",
            "demoInstrumentUniverseCache",
            "demoInstrumentUniverseBlockers",
        ):
            self.assertIn(f'id="{target_id}"', self.html)
        self.assertIn("function renderDemoInstrumentUniverse", self.js)
        self.assertIn("/api/demo-instrument-universe", self.js)
        self.assertIn("loadDemoInstrumentUniverse(force)", self.js)

    def test_demo_vault_controls_are_redacted_and_do_not_collect_browser_credentials(self) -> None:
        self.assertIn('id="demoCredentialVaultStatus"', self.html)
        self.assertIn('id="demoCredentialVaultUpdateButton"', self.html)
        self.assertIn('id="demoCredentialVaultDeleteButton"', self.html)
        self.assertIn("尚未保存 Demo 凭据", self.html)
        self.assertIn("更新 Demo 凭据", self.html)
        self.assertIn("删除已保存凭据", self.html)
        self.assertIn("/api/local-control/okx-demo-credential-vault", self.js)
        self.assertIn("/api/local-control/delete-okx-demo-credential-vault", self.js)
        self.assertIn("DELETE_OKX_DEMO_CREDENTIAL", self.js)
        self.assertNotIn('id="demoCredentialApiKey', self.html)
        self.assertNotIn('id="demoCredentialSecret', self.html)
        self.assertNotIn('id="demoCredentialPassphrase', self.html)
        self.assertIn("实盘账户凭据输入一次；每条策略仍需逐条批准启用", self.html)
        self.assertIn("window.location.hostname", self.js)
        self.assertIn("127.0.0.1:8766", self.js)
        self.assertIn("备用手动启动命令", self.js)
        self.assertIn('<details class="demo-workflow-command"', self.js)

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

    def test_demo_and_live_share_automatic_execution_controls(self) -> None:
        for target_id in (
            "demoAutoExecutionStatus",
            "demoAutoExecutionToggle",
            "liveAutoExecutionStatus",
            "liveAutoExecutionToggle",
            "autoExecutionLastHeartbeat",
            "autoExecutionNextEvaluation",
        ):
            self.assertIn(f'id="{target_id}"', self.html)
        self.assertIn("data-auto-execution-action", self.html)
        self.assertIn("function renderAutomaticExecution", self.js)
        self.assertIn("function runAutomaticExecutionAction", self.js)
        for label in (
            "等待下一根闭合 K 线",
            "最近已评估但零匹配",
            "匹配后被风控或执行拒绝",
            "已提交 Demo 订单",
            "暂停新开仓",
            "紧急停止",
        ):
            self.assertIn(label, self.js)
        self.assertIn("auto-execution-control", self.css)

    def test_three_primary_workflow_pages_have_single_selected_and_all_controls(self) -> None:
        for target_id in (
            "workflowRunSelectedButton",
            "workflowRunAllButton",
            "localForwardRunSelectedButton",
            "localForwardRunAllButton",
            "demoWorkflowRunSelectedButton",
            "demoWorkflowRunAllButton",
        ):
            self.assertIn(f'id="{target_id}"', self.html)
        for label in ("启动这一条", "启动选中", "启动全部待运行"):
            self.assertIn(label, self.js + self.html)

    def test_workflow_bulk_controls_send_explicit_id_lists(self) -> None:
        self.assertIn("workflowSelection.backtest", self.js)
        self.assertIn("workflowSelection.localForward", self.js)
        self.assertIn("workflowSelection.demo", self.js)
        self.assertIn('action: "run-selected"', self.js)
        self.assertIn('action: "run-selected-forward"', self.js)
        self.assertIn('action: "run_selected_demo"', self.js)
        self.assertIn("workflowRunIds", self.js)
        self.assertIn("strategyIds", self.js)

    def test_backtest_cards_pause_queued_work_and_restart_cancelled_attempts(self) -> None:
        self.assertIn(
            'item.status === "queued") actions.push({ action: "pause", label: "暂停排队" })',
            self.js,
        )
        self.assertIn(
            'item.status === "cancelled") actions.push({ action: "retry", label: "从检查点重新开始", primary: true })',
            self.js,
        )
        self.assertNotIn(
            'item.status === "queued") actions.push({ action: "cancel", label: "取消排队" })',
            self.js,
        )
        self.assertIn("取消会结束本次尝试", self.js)

    def test_only_eligible_cards_receive_selection_checkboxes(self) -> None:
        self.assertIn("data-workflow-select", self.js)
        self.assertIn("data-local-forward-select", self.js)
        self.assertIn("data-demo-workflow-select", self.js)
        self.assertIn("pruneWorkflowSelection", self.js)
        self.assertIn("demoBatchActionEligible", self.js)
        self.assertIn('payload?.controlConsoleVersion === "V13.27.9"', self.js)

    def test_demo_page_exposes_compact_public_runtime_and_latency_metrics(self) -> None:
        for target_id in (
            "demoMarketRuntimeStatus",
            "demoMarketRuntimeUniverse",
            "demoMarketRuntimeTimeframes",
            "demoMarketRuntimeClose",
            "demoMarketRuntimeLatency",
            "demoMarketRuntimeBlocker",
        ):
            self.assertIn(f'id="{target_id}"', self.html)
        for label in (
            "公共行情预热",
            "最近确认收线",
            "收线到评估",
            "策略仲裁",
            "风险检查",
            "订单发送",
            "交易所响应",
            "延迟等级",
        ):
            self.assertIn(label, self.html + self.js)
        self.assertIn("function renderDemoPublicMarketRuntime", self.js)
        self.assertIn('payload?.version === "V13.27.9"', self.js)

    def test_live_gate_copy_includes_automation_and_mobile_copy_stays_read_only(self) -> None:
        self.assertIn("五层独立门", self.html)
        self.assertIn("Master / Read / Canary / Order / Automation", self.html)
        self.assertIn("gates.automationEnabled", self.js)
        self.assertIn('setText("liveCanaryProcessGate", `${processGateCount}/5`)', self.js)
        self.assertIn('live_automation_gate_disabled: "自动执行门关闭"', self.js)
        self.assertIn("手机端不发起下单；后台自动执行状态仅用于查看。", self.html)


if __name__ == "__main__":
    unittest.main()
