from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StrategyLabUiContractTests(unittest.TestCase):
    def test_strategy_lab_is_read_only_and_visible_in_existing_console_stack(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        javascript = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        http_app = (ROOT / "alphapilot_control_console" / "http_app.py").read_text(encoding="utf-8")

        self.assertIn('id="strategyLabPanel"', html)
        self.assertIn('<link rel="icon" href="data:,"', html)
        self.assertIn('id="strategyLabSourceRegistry"', html)
        self.assertIn('id="strategyLabCampaigns"', html)
        self.assertIn('id="strategyLabFailureAttribution"', html)
        self.assertIn('id="strategyLabFormalGateMatrix"', html)
        self.assertIn("Formal Gate Matrix", html)
        self.assertIn("只读", html)
        self.assertIn("function renderStrategyLab", javascript)
        self.assertIn("formalGateMatrix", javascript)
        self.assertIn("Formal 未运行：预筛没有幸存候选", javascript)
        self.assertIn('url: "/api/strategy-lab"', javascript)
        self.assertIn('path == "/api/strategy-lab"', http_app)
        self.assertNotIn("strategyLabApprove", javascript)
        self.assertNotIn("strategyLabCreateOrder", javascript)


if __name__ == "__main__":
    unittest.main()
