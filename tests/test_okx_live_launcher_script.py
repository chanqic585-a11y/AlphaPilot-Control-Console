from __future__ import annotations

import unittest
from pathlib import Path


class OkxLiveLauncherScriptTests(unittest.TestCase):
    def test_automation_requires_order_gate_and_is_process_only(self) -> None:
        script = (
            Path(__file__).resolve().parents[1] / "scripts" / "start_okx_live_canary_console.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn("[switch]$EnableAutomation", script)
        self.assertIn("-EnableAutomation requires -EnableOrder", script)
        self.assertIn("ALPHAPILOT_OKX_LIVE_AUTOMATION_ENABLED", script)
        self.assertIn("Remove-Item Env:\\ALPHAPILOT_OKX_LIVE_AUTOMATION_ENABLED", script)
        self.assertNotIn("Set-Content", script)
        self.assertNotIn("Out-File", script)


if __name__ == "__main__":
    unittest.main()
