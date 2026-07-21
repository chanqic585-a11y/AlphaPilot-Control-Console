from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from alphapilot_control_console.http_write_security import evaluate_http_write


class HttpWriteSecurityTests(unittest.TestCase):
    def test_loopback_write_is_allowed_without_remote_secrets(self) -> None:
        decision = evaluate_http_write(
            client_host="127.0.0.1",
            path="/api/research-factory/runs",
            headers={},
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.mode, "loopback")

    def test_remote_write_is_read_only_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            decision = evaluate_http_write(
                client_host="192.168.1.10",
                path="/api/research-factory/runs",
                headers={},
            )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "remote_write_disabled")

    def test_remote_write_requires_all_four_controls(self) -> None:
        environment = {
            "ALPHAPILOT_HTTP_WRITE_TOKEN": "write-token",
            "ALPHAPILOT_HTTP_CSRF_TOKEN": "csrf-token",
            "ALPHAPILOT_HTTP_ALLOWED_ORIGINS": "https://console.example",
            "ALPHAPILOT_HTTP_EXACT_CONFIRMATION": "CONFIRM_REMOTE_WRITE",
        }
        headers = {
            "X-AlphaPilot-Write-Token": "write-token",
            "X-AlphaPilot-CSRF": "csrf-token",
            "Origin": "https://console.example",
            "X-AlphaPilot-Confirmation": "CONFIRM_REMOTE_WRITE",
        }

        with patch.dict(os.environ, environment, clear=True):
            decision = evaluate_http_write(
                client_host="192.168.1.10",
                path="/api/research-factory/runs",
                headers=headers,
            )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.mode, "authenticated_remote")

    def test_remote_write_rejects_origin_token_csrf_or_confirmation_mismatch(self) -> None:
        environment = {
            "ALPHAPILOT_HTTP_WRITE_TOKEN": "write-token",
            "ALPHAPILOT_HTTP_CSRF_TOKEN": "csrf-token",
            "ALPHAPILOT_HTTP_ALLOWED_ORIGINS": "https://console.example",
            "ALPHAPILOT_HTTP_EXACT_CONFIRMATION": "CONFIRM_REMOTE_WRITE",
        }
        valid = {
            "X-AlphaPilot-Write-Token": "write-token",
            "X-AlphaPilot-CSRF": "csrf-token",
            "Origin": "https://console.example",
            "X-AlphaPilot-Confirmation": "CONFIRM_REMOTE_WRITE",
        }
        cases = (
            ("X-AlphaPilot-Write-Token", "wrong", "write_token_mismatch"),
            ("X-AlphaPilot-CSRF", "wrong", "csrf_mismatch"),
            ("Origin", "https://evil.example", "origin_not_allowed"),
            ("X-AlphaPilot-Confirmation", "wrong", "exact_confirmation_mismatch"),
        )

        with patch.dict(os.environ, environment, clear=True):
            for key, value, expected in cases:
                headers = {**valid, key: value}
                with self.subTest(key=key):
                    decision = evaluate_http_write(
                        client_host="192.168.1.10",
                        path="/api/research-factory/runs",
                        headers=headers,
                    )
                    self.assertFalse(decision.allowed)
                    self.assertEqual(decision.reason, expected)

    def test_audit_projection_never_contains_secret_values(self) -> None:
        environment = {
            "ALPHAPILOT_HTTP_WRITE_TOKEN": "write-token",
            "ALPHAPILOT_HTTP_CSRF_TOKEN": "csrf-token",
            "ALPHAPILOT_HTTP_ALLOWED_ORIGINS": "https://console.example",
            "ALPHAPILOT_HTTP_EXACT_CONFIRMATION": "CONFIRM_REMOTE_WRITE",
        }
        headers = {
            "X-AlphaPilot-Write-Token": "wrong-secret-value",
            "X-AlphaPilot-CSRF": "csrf-token",
            "Origin": "https://console.example",
            "X-AlphaPilot-Confirmation": "CONFIRM_REMOTE_WRITE",
        }

        with patch.dict(os.environ, environment, clear=True):
            decision = evaluate_http_write(
                client_host="192.168.1.10",
                path="/api/research-factory/runs",
                headers=headers,
            )

        audit_text = repr(decision.audit_payload())
        self.assertNotIn("wrong-secret-value", audit_text)
        self.assertNotIn("write-token", audit_text)
        self.assertNotIn("csrf-token", audit_text)


if __name__ == "__main__":
    unittest.main()
