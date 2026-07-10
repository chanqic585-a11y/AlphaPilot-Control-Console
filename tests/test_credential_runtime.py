from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from alphapilot_control_console.credential_runtime import (
    load_okx_demo_credentials,
    load_okx_live_credentials,
)


class CredentialRuntimeTests(unittest.TestCase):
    def test_credentials_are_loaded_from_process_environment_and_redacted(self) -> None:
        values = {
            "ALPHAPILOT_OKX_DEMO_API_KEY": "demo-key",
            "ALPHAPILOT_OKX_DEMO_SECRET_KEY": "demo-secret",
            "ALPHAPILOT_OKX_DEMO_PASSPHRASE": "demo-passphrase",
        }
        with patch.dict(os.environ, values, clear=False):
            credentials = load_okx_demo_credentials()

        self.assertTrue(credentials.status()["allConfigured"])
        rendered = repr(credentials)
        self.assertNotIn("demo-key", rendered)
        self.assertNotIn("demo-secret", rendered)
        self.assertNotIn("demo-passphrase", rendered)

    def test_missing_credentials_fail_closed(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                load_okx_demo_credentials()

    def test_live_credentials_use_separate_process_environment(self) -> None:
        values = {
            "ALPHAPILOT_OKX_LIVE_API_KEY": "live-key",
            "ALPHAPILOT_OKX_LIVE_SECRET_KEY": "live-secret",
            "ALPHAPILOT_OKX_LIVE_PASSPHRASE": "live-passphrase",
        }
        with patch.dict(os.environ, values, clear=True):
            credentials = load_okx_live_credentials()

        self.assertTrue(credentials.status()["allConfigured"])
        self.assertNotIn("live-key", repr(credentials))
        self.assertNotIn("live-secret", repr(credentials))


if __name__ == "__main__":
    unittest.main()
