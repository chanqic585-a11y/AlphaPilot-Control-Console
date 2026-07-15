from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PrimaryNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    def test_primary_navigation_has_exactly_four_destinations(self) -> None:
        nav = re.search(r'<nav class="rail-nav">(?P<body>.*?)</nav>', self.html, re.S)
        self.assertIsNotNone(nav)
        labels = re.findall(r'<span>\s*([^<]+?)\s*</span>\s*</a>', nav.group("body"))
        self.assertEqual(labels, ["策略", "Demo模拟", "实盘交易", "手机控制台"])
        self.assertNotIn('href="#localLab"', nav.group("body"))

    def test_local_simulation_page_is_not_mounted_and_old_hash_redirects_once(self) -> None:
        self.assertNotIn('<section id="localLab"', self.html)
        self.assertIn(
            'const primaryPageIds = ["simpleConsole", "exchangeDemo", "liveTradingPage", "mobileConsole"]',
            self.js,
        )
        self.assertIn("retireLocalLabHashOnce", self.js)
        self.assertIn("alphapilot.localSimulationRetirementNotice", self.js)
        self.assertIn('window.location.replace("#simpleConsole")', self.js)
        self.assertEqual(self.js.count("renderLocalLabPage("), 1)
        self.assertNotIn("void loadSandboxReviewDataIfNeeded();", self.js)


if __name__ == "__main__":
    unittest.main()
