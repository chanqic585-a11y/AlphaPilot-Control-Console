from __future__ import annotations

import json
from urllib.request import Request

from alphapilot_control_console.http_write_security import (
    build_operator_write_headers,
    ensure_http_write_security_environment,
)


def secure_json_request(
    base_url: str,
    path: str,
    payload: dict | None = None,
    *,
    method: str = "POST",
) -> Request:
    """Build the same process-only authenticated write used by the browser UI."""

    ensure_http_write_security_environment(origins=[base_url])
    return Request(
        base_url + path,
        data=json.dumps(payload or {}).encode("utf-8"),
        headers=build_operator_write_headers(
            method=method,
            path=path,
            origin=base_url,
        ),
        method=method,
    )
