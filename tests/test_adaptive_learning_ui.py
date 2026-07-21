from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AdaptiveLearningUiTests(unittest.TestCase):
    def test_primary_pages_expose_compact_learning_truth(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "adaptive-learning-ui.js").read_text(encoding="utf-8")

        for element_id in (
            "strategyAdaptiveLearning",
            "demoAdaptiveLearning",
            "liveAdaptiveLearning",
            "adaptiveFactorCount",
            "adaptiveDemoSnapshotCount",
            "adaptiveLiveReadiness",
        ):
            self.assertIn(f'id="{element_id}"', html)

        self.assertIn('/api/adaptive-learning?fresh=1', script)
        self.assertIn('modelMode', script)
        self.assertIn('liveDecisionReady', script)
        self.assertNotIn('apiKey', script)
        self.assertNotIn('passphrase', script.lower())

    def test_adaptive_ui_script_is_loaded_after_main_ui(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<script src="/adaptive-learning-ui.js?v=20260721-v55-1"></script>', html)

    def test_mobile_bottom_navigation_replaces_overlapping_back_button(self) -> None:
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".back-home-button {\n    display: none !important;", css)


if __name__ == "__main__":
    unittest.main()
