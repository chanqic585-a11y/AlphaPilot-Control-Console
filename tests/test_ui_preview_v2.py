from __future__ import annotations

import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from alphapilot_control_console.http_app import ConsoleHandler


ROOT = Path(__file__).resolve().parents[1]


class UiPreviewV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ConsoleHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _html(self, path: str) -> str:
        with urlopen(self.base_url + path, timeout=2) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("text/html", response.headers.get("Content-Type", ""))
            return response.read().decode("utf-8")

    def test_root_is_the_minimal_strategy_console_and_legacy_is_preserved(self) -> None:
        root = self._html("/")
        legacy = self._html("/legacy")

        self.assertIn('data-preview-page="strategy"', root)
        self.assertIn("策略研究与发布", root)
        self.assertIn("生成 / 组合策略", root)
        self.assertIn("AlphaPilot", legacy)

    def test_demo_preview_is_chinese_and_operational(self) -> None:
        html = self._html("/ui-preview/demo-v2")

        self.assertIn('data-preview-page="demo"', html)
        self.assertIn("Demo 模拟控制台", html)
        self.assertIn("当前策略", html)
        self.assertIn("当前持仓", html)
        self.assertIn("扫描漏斗", html)
        self.assertIn("可用余额", html)
        self.assertNotIn('method="post"', html.lower())

    def test_live_preview_separates_readiness_approval_and_arm(self) -> None:
        html = self._html("/ui-preview/live-v2")

        self.assertIn('data-preview-page="live"', html)
        self.assertIn("实盘交易控制台", html)
        self.assertIn("技术就绪", html)
        self.assertIn("精确批准", html)
        self.assertIn("运行 ARM", html)
        self.assertIn("Withdraw 关闭", html)
        self.assertIn("当前持仓", html)
        self.assertNotIn('method="post"', html.lower())

    def test_shared_assets_use_runtime_truth_and_versioned_policy_api(self) -> None:
        script = (ROOT / "web" / "ui-preview-v2.js").read_text(encoding="utf-8")
        styles = (ROOT / "web" / "ui-preview-v2.css").read_text(encoding="utf-8")

        self.assertIn("/api/research-factory/summary", script)
        self.assertIn("item.floatingPnl", script)
        self.assertIn("/api/demo/summary", script)
        self.assertIn("/api/live/summary", script)
        self.assertIn("/api/live/canary-readiness", script)
        self.assertIn("/api/strategy-execution-policies", script)
        self.assertIn("/api/strategy-execution-policies/bootstrap", script)
        self.assertIn("生成初始参数版本", script)
        self.assertIn("unrealizedPnlUsdt", script)
        self.assertIn("escapeHtml", script)
        self.assertIn("readiness.adaptiveLearning?.blockers", script)
        self.assertIn('rows(releases, "candidateReviews")', script)
        self.assertIn("pending_human_review", script)
        self.assertIn("系统不会自动批准或 ARM", script)
        self.assertIn("@media (max-width: 760px)", styles)

    def test_demo_and_live_pages_do_not_expose_execution_write_actions(self) -> None:
        script = (ROOT / "web" / "ui-preview-v2.js").read_text(encoding="utf-8")

        self.assertNotIn("/api/auto-execution/action", script)
        self.assertNotIn("/api/live-auto-execution/action", script)
        self.assertNotIn("/api/demo/orders/create", script)
        self.assertNotIn("/api/live/orders/create", script)

    def test_historical_factory_system_issues_do_not_trigger_a_current_issue_dialog(self) -> None:
        html = self._html("/")
        script = (ROOT / "web" / "ui-preview-v2.js").read_text(encoding="utf-8")

        self.assertIn("历史系统问题", html)
        self.assertIn('factory.resultClass === "system_issue"', script)
        self.assertNotIn(
            'Number(counts.systemIssue) > 0 ? "策略工厂存在系统问题"',
            script,
        )

    def test_strategy_page_labels_historical_totals_and_hides_superseded_releases(self) -> None:
        html = self._html("/")
        script = (ROOT / "web" / "ui-preview-v2.js").read_text(encoding="utf-8")

        self.assertIn("当前验收 Pilot", html)
        self.assertIn('id="pilotCampaignId"', html)
        self.assertIn('id="pilotCandidateCount"', html)
        self.assertIn('id="pilotTrialCount"', html)
        self.assertIn('id="pilotStableCount"', html)
        self.assertIn('id="pilotFormalReadyCount"', html)
        self.assertIn('id="pilotFormalBlockedCount"', html)
        self.assertIn('id="pilotFormalRunCount"', html)
        self.assertIn("AI 编排状态", html)
        self.assertIn('id="aiCredentialState"', html)
        self.assertIn('id="aiHistoricalSmokeState"', html)
        self.assertIn('id="aiHistoricalSmokeTime"', html)
        self.assertIn("/api/ai/control", script)
        self.assertIn("strategy.currentPilot", script)
        self.assertIn("历史未通过", html)
        self.assertIn("历史数据不足", html)
        self.assertIn("当前 Demo / 历史 Release", html)
        self.assertIn('rows(releases, "historicalReleases")', script)
        self.assertNotIn(
            "[...candidateItems, ...releaseItems, ...historicalReleaseItems]",
            script,
        )

    def test_screenshot_harness_is_fixture_only_and_cannot_write(self) -> None:
        harness = (ROOT / "scripts" / "render_ui_preview_evidence.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('fixturePurpose: "layout_and_browser_acceptance_only"', harness)
        self.assertIn("writeActions: 0", harness)
        self.assertIn('{ page: "strategy"', harness)
        self.assertIn('"/api/research-factory/summary"', harness)
        self.assertIn("candidateReviews", harness)
        self.assertIn("reviewReminderShown", harness)
        self.assertIn("unrealizedPnlUsdt", harness)
        self.assertNotIn('method: "POST"', harness)
        self.assertNotIn("/api/auto-execution/action", harness)


if __name__ == "__main__":
    unittest.main()
