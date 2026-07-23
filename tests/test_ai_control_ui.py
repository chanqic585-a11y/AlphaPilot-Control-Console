from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AIControlUiTests(unittest.TestCase):
    def test_strategy_page_has_folded_read_only_ai_control(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "top200-minimal-ui.js").read_text(encoding="utf-8")

        self.assertIn('id="strategyAiControl"', html)
        self.assertIn('id="strategyAiProviderHealth"', html)
        self.assertIn('id="strategyAiModelSummary"', html)
        self.assertIn('id="strategyAiQueueSummary"', html)
        self.assertIn('id="strategyAiBudgetSummary"', html)
        self.assertIn('/api/ai/control', script)
        self.assertIn('renderAiControl', script)
        self.assertNotIn('DEEPSEEK_API_KEY', html)
        self.assertNotIn('GEMINI_API_KEY', html)


if __name__ == "__main__":
    unittest.main()
