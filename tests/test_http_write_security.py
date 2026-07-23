from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from alphapilot_control_console.http_write_security import (
    build_operator_write_headers,
    ensure_http_write_security_environment,
    evaluate_http_write,
    expected_route_confirmation,
)


class HttpWriteSecurityTests(unittest.TestCase):
    def test_loopback_write_requires_operator_session_controls(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            decision = evaluate_http_write(
                client_host="127.0.0.1",
                method="POST",
                path="/api/research-factory/runs",
                headers={"Content-Type": "application/json"},
            )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "write_security_not_configured")

    def test_loopback_operator_session_is_ephemeral_and_route_specific(self) -> None:
        origin = "http://127.0.0.1:8766"
        path = "/api/research-factory/runs"
        with patch.dict(os.environ, {}, clear=True):
            session = ensure_http_write_security_environment(origins=[origin])
            headers = build_operator_write_headers(
                method="POST",
                path=path,
                origin=origin,
            )
            decision = evaluate_http_write(
                client_host="127.0.0.1",
                method="POST",
                path=path,
                headers=headers,
            )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.mode, "authenticated_loopback")
        self.assertFalse(session["persisted"])
        self.assertEqual(
            headers["X-AlphaPilot-Confirmation"],
            expected_route_confirmation("POST", path),
        )

    def test_write_rejects_non_json_content_type(self) -> None:
        origin = "http://127.0.0.1:8766"
        path = "/api/research-factory/runs"
        with patch.dict(os.environ, {}, clear=True):
            ensure_http_write_security_environment(origins=[origin])
            headers = build_operator_write_headers(
                method="POST",
                path=path,
                origin=origin,
            )
            headers["Content-Type"] = "text/plain"
            decision = evaluate_http_write(
                client_host="127.0.0.1",
                method="POST",
                path=path,
                headers=headers,
            )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "application_json_required")

    def test_remote_write_is_read_only_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            decision = evaluate_http_write(
                client_host="192.168.1.10",
                method="POST",
                path="/api/research-factory/runs",
                headers={"Content-Type": "application/json"},
            )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "remote_write_disabled")

    def test_remote_write_requires_all_four_controls(self) -> None:
        environment = {
            "ALPHAPILOT_HTTP_WRITE_TOKEN": "write-token",
            "ALPHAPILOT_HTTP_CSRF_TOKEN": "csrf-token",
            "ALPHAPILOT_HTTP_ALLOWED_ORIGINS": "https://console.example",
        }
        path = "/api/research-factory/runs"
        headers = {
            "X-AlphaPilot-Write-Token": "write-token",
            "X-AlphaPilot-CSRF": "csrf-token",
            "Origin": "https://console.example",
            "Content-Type": "application/json",
            "X-AlphaPilot-Confirmation": expected_route_confirmation("POST", path),
        }

        with patch.dict(os.environ, environment, clear=True):
            decision = evaluate_http_write(
                client_host="192.168.1.10",
                method="POST",
                path=path,
                headers=headers,
            )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.mode, "authenticated_remote")

    def test_remote_write_rejects_origin_token_csrf_or_confirmation_mismatch(self) -> None:
        environment = {
            "ALPHAPILOT_HTTP_WRITE_TOKEN": "write-token",
            "ALPHAPILOT_HTTP_CSRF_TOKEN": "csrf-token",
            "ALPHAPILOT_HTTP_ALLOWED_ORIGINS": "https://console.example",
        }
        path = "/api/research-factory/runs"
        valid = {
            "X-AlphaPilot-Write-Token": "write-token",
            "X-AlphaPilot-CSRF": "csrf-token",
            "Origin": "https://console.example",
            "Content-Type": "application/json",
            "X-AlphaPilot-Confirmation": expected_route_confirmation("POST", path),
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
                        method="POST",
                        path=path,
                        headers=headers,
                    )
                    self.assertFalse(decision.allowed)
                    self.assertEqual(decision.reason, expected)

    def test_audit_projection_never_contains_secret_values(self) -> None:
        environment = {
            "ALPHAPILOT_HTTP_WRITE_TOKEN": "write-token",
            "ALPHAPILOT_HTTP_CSRF_TOKEN": "csrf-token",
            "ALPHAPILOT_HTTP_ALLOWED_ORIGINS": "https://console.example",
        }
        path = "/api/research-factory/runs"
        headers = {
            "X-AlphaPilot-Write-Token": "wrong-secret-value",
            "X-AlphaPilot-CSRF": "csrf-token",
            "Origin": "https://console.example",
            "Content-Type": "application/json",
            "X-AlphaPilot-Confirmation": expected_route_confirmation("POST", path),
        }

        with patch.dict(os.environ, environment, clear=True):
            decision = evaluate_http_write(
                client_host="192.168.1.10",
                method="POST",
                path=path,
                headers=headers,
            )

        audit_text = repr(decision.audit_payload())
        self.assertNotIn("wrong-secret-value", audit_text)
        self.assertNotIn("write-token", audit_text)
        self.assertNotIn("csrf-token", audit_text)


if __name__ == "__main__":
    unittest.main()
