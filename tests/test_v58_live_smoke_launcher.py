from __future__ import annotations

import unittest
from pathlib import Path


class V58LiveSmokeLauncherTests(unittest.TestCase):
    def test_launcher_is_one_shot_secure_and_clears_credentials(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = (root / "scripts" / "start_v58_live_engineering_smoke.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("Read-Host -Prompt $Prompt -AsSecureString", script)
        self.assertIn("scripts/run_v58_live_engineering_smoke.py", script.replace("\\", "/"))
        self.assertNotIn("alphapilot_control_console.http_app", script)
        self.assertIn("finally", script)
        self.assertIn("Remove-Item Env:\\ALPHAPILOT_OKX_LIVE_API_KEY", script)
        self.assertIn("Remove-Item Env:\\ALPHAPILOT_OKX_LIVE_SECRET_KEY", script)
        self.assertIn("Remove-Item Env:\\ALPHAPILOT_OKX_LIVE_PASSPHRASE", script)

    def test_runner_persists_a_safe_blocker_code_without_private_values(self) -> None:
        root = Path(__file__).resolve().parents[1]
        runner = (root / "scripts" / "run_v58_live_engineering_smoke.py").read_text(
            encoding="utf-8"
        )

        self.assertIn('"safeBlockerCode"', runner)
        self.assertIn('"safeInstrumentId"', runner)
        self.assertNotIn('str(error)', runner)
        self.assertNotIn('repr(error)', runner)

    def test_launcher_translates_safe_blocker_into_a_next_action(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = (root / "scripts" / "start_v58_live_engineering_smoke.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("safeBlockerCode", script)
        self.assertIn("account_instruments_unavailable", script)
        self.assertIn("isolated_leverage_not_1x", script)
        self.assertIn("unsupported_position_mode", script)
        self.assertIn("safeInstrumentId", script)


if __name__ == "__main__":
    unittest.main()
