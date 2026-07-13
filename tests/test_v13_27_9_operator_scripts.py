from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class V13279OperatorScriptTests(unittest.TestCase):
    def test_rehearsal_script_uses_no_order_module(self) -> None:
        script = (ROOT / "scripts" / "rehearse_top100_latency.ps1").read_text(encoding="utf-8")

        self.assertIn("alphapilot_control_console.top100_latency_rehearsal", script)
        self.assertNotIn("EnableOrder", script)
        self.assertNotIn("OKX_DEMO_API_KEY", script)

    def test_activation_script_calls_only_successor_cli(self) -> None:
        script = (ROOT / "scripts" / "activate_top100_demo_releases.ps1").read_text(encoding="utf-8")

        self.assertIn("alphapilot_control_console.demo_release_successor_cli", script)
        self.assertNotIn("start_okx_demo_console", script)
        self.assertNotIn("EnableOrder", script)
        self.assertNotIn("OKX_DEMO_API_KEY", script)


if __name__ == "__main__":
    unittest.main()
