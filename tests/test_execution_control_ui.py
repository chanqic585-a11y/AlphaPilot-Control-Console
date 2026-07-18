from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExecutionControlUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")

    def test_demo_and_live_render_the_same_compact_execution_control_component(self) -> None:
        self.assertEqual(self.html.count('data-execution-control-panel'), 2)
        self.assertIn('data-execution-control-environment="demo"', self.html)
        self.assertIn('data-execution-control-environment="live"', self.html)
        self.assertIn("function renderExecutionControl", self.js)
        self.assertIn("function renderExecutionEnvironment", self.js)
        self.assertIn("execution-control-grid", self.css)

    def test_five_operator_sections_are_present_and_advanced_evidence_is_collapsed(self) -> None:
        for section in (
            "dual-track-overview",
            "demo-runtime",
            "live-readiness",
            "orders-positions",
            "blockers-next-actions",
        ):
            self.assertIn(f'data-execution-control-section="{section}"', self.js)
        self.assertIn('<details class="execution-control-evidence">', self.js)

    def test_ui_uses_consolidated_backend_and_idempotent_action_requests(self) -> None:
        self.assertIn("/api/execution-control/status", self.js)
        self.assertIn("/api/execution-control/action", self.js)
        self.assertIn("execution-control-request", self.js)
        self.assertIn("data-execution-control-action", self.js)
        self.assertIn("live_arm_requires_existing_manual_path", self.js)

    def test_ui_adds_no_credential_form_and_labels_live_default_off(self) -> None:
        self.assertNotIn('name="executionControlApiKey"', self.html)
        self.assertNotIn('name="executionControlPassphrase"', self.html)
        self.assertIn("实盘默认关闭", self.js)
        self.assertIn("凭据仅存在于独立启动进程", self.js)


if __name__ == "__main__":
    unittest.main()
