from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StrategyValidationUiContractTests(unittest.TestCase):
    def test_strategy_and_demo_have_separate_validation_panels(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="strategyValidationResearchPanel"', html)
        self.assertIn('id="strategyValidationDemoPanel"', html)
        self.assertIn("正式通过", html)
        self.assertIn("工程烟测、影子观察、旧诊断和历史本地模拟均不计入", html)
        self.assertNotIn("强制批准", html)

    def test_browser_loads_read_only_status_and_keeps_approval_separate_from_arm(self) -> None:
        javascript = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('/api/strategy-validation/status', javascript)
        self.assertIn('/api/strategy-validation-releases/approve', javascript)
        self.assertIn('/api/strategy-validation-runtime/arm', javascript)
        self.assertIn('renderStrategyValidation', javascript)


if __name__ == "__main__":
    unittest.main()
