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

    def test_demo_preview_is_read_only_and_operational(self) -> None:
        html = self._html("/ui-preview/demo-v2")

        self.assertIn('data-preview-page="demo"', html)
        self.assertIn("Demo 交易控制台", html)
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
        self.assertIn("持仓行情", html)
        self.assertNotIn('method="post"', html.lower())

    def test_shared_preview_assets_exist_and_only_fetch_read_routes(self) -> None:
        script = (ROOT / "web" / "ui-preview-v2.js").read_text(encoding="utf-8")
        styles = (ROOT / "web" / "ui-preview-v2.css").read_text(encoding="utf-8")

        self.assertIn("/api/demo/summary", script)
        self.assertIn("/api/live/canary-readiness", script)
        self.assertNotIn('method: "POST"', script)
        self.assertIn("escapeHtml", script)
        self.assertIn("readiness.adaptiveLearning?.blockers", script)
        self.assertIn("@media (max-width: 760px)", styles)

    def test_screenshot_harness_is_fixture_only_and_cannot_write(self) -> None:
        harness = (ROOT / "scripts" / "render_ui_preview_evidence.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('fixturePurpose: "layout_and_browser_acceptance_only"', harness)
        self.assertIn("writeActions: 0", harness)
        self.assertNotIn('method: "POST"', harness)
        self.assertNotIn("/api/auto-execution/action", harness)


if __name__ == "__main__":
    unittest.main()
