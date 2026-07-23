from __future__ import annotations

import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from alphapilot_control_console.http_app import ConsoleHandler
from alphapilot_control_console.http_write_security import (
    build_operator_write_headers,
    ensure_http_write_security_environment,
)


class HttpWriteRequestContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.security_keys = (
            "ALPHAPILOT_HTTP_WRITE_TOKEN",
            "ALPHAPILOT_HTTP_CSRF_TOKEN",
            "ALPHAPILOT_HTTP_ALLOWED_ORIGINS",
        )
        self.original_security = {key: os.environ.get(key) for key in self.security_keys}
        for key in self.security_keys:
            os.environ.pop(key, None)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ConsoleHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"
        ensure_http_write_security_environment(origins=[self.base_url])

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        for key, value in self.original_security.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _headers(self, path: str, *, method: str = "POST") -> dict[str, str]:
        return build_operator_write_headers(
            method=method,
            path=path,
            origin=self.base_url,
        )

    def test_loopback_operator_session_is_process_only(self) -> None:
        with urlopen(self.base_url + "/api/operator-session", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["mode"], "process_only")
        self.assertFalse(payload["persisted"])
        self.assertTrue(payload["writeToken"])
        self.assertTrue(payload["csrfToken"])

    def test_malformed_json_is_rejected_before_route_dispatch(self) -> None:
        path = "/api/manual-interventions"
        request = Request(
            self.base_url + path,
            data=b"{not-json",
            headers=self._headers(path),
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=2)

        self.assertEqual(raised.exception.code, 400)
        payload = json.loads(raised.exception.read().decode("utf-8"))
        self.assertEqual(payload["error"], "malformed_json")

    def test_non_json_write_is_rejected_with_415(self) -> None:
        path = "/api/manual-interventions"
        headers = self._headers(path)
        headers["Content-Type"] = "text/plain"
        request = Request(
            self.base_url + path,
            data=b"plain",
            headers=headers,
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=2)

        self.assertEqual(raised.exception.code, 415)

    def test_put_and_delete_are_secured_before_method_rejection(self) -> None:
        for method in ("PUT", "DELETE"):
            path = "/api/not-implemented"
            unauthenticated = Request(
                self.base_url + path,
                data=b"{}",
                headers={"Content-Type": "application/json", "Origin": self.base_url},
                method=method,
            )
            with self.assertRaises(HTTPError) as rejected:
                urlopen(unauthenticated, timeout=2)
            self.assertEqual(rejected.exception.code, 403)

            authenticated = Request(
                self.base_url + path,
                data=b"{}",
                headers=self._headers(path, method=method),
                method=method,
            )
            with self.assertRaises(HTTPError) as unsupported:
                urlopen(authenticated, timeout=2)
            self.assertEqual(unsupported.exception.code, 405)
            payload = json.loads(unsupported.exception.read().decode("utf-8"))
            self.assertEqual(payload["error"], "method_not_allowed")


if __name__ == "__main__":
    unittest.main()
