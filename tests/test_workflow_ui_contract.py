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
        self.assertIn("v13-27-1-2-targeted-optimization", self.html)

    def test_api_errors_surface_backend_parameter_reason(self) -> None:
        self.assertIn("payload.message || payload.error", self.js)


if __name__ == "__main__":
    unittest.main()
