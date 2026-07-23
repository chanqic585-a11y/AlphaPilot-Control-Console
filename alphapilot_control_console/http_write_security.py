"""Process-local operator authorization for every control-console write."""

from __future__ import annotations

import hmac
import ipaddress
import os
import secrets
from dataclasses import dataclass
from typing import Iterable, Mapping
from urllib.parse import urlsplit


@dataclass(frozen=True)
class HttpWriteDecision:
    allowed: bool
    mode: str
    reason: str | None
    client_host: str
    method: str
    path: str
    origin: str | None
    content_type: str | None

    def audit_payload(self) -> dict[str, object]:
        """Return security metadata without copying any authentication value."""

        return {
            "allowed": self.allowed,
            "mode": self.mode,
            "reason": self.reason,
            "clientHost": self.client_host,
            "method": self.method,
            "path": self.path,
            "origin": self.origin,
            "contentType": self.content_type,
            "operatorSessionRequired": True,
            "routeSpecificConfirmationRequired": True,
            "credentialValuesStored": False,
        }


def _is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(str(host).split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def _header(headers: Mapping[str, str], name: str) -> str:
    expected = name.casefold()
    for key, value in headers.items():
        if str(key).casefold() == expected:
            return str(value)
    return ""


def _matches(actual: str, expected: str) -> bool:
    return bool(expected) and hmac.compare_digest(actual, expected)


def _normalize_origin(value: str) -> str:
    text = str(value or "").strip().rstrip("/")
    parsed = urlsplit(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"invalid HTTP origin: {value!r}")
    return f"{parsed.scheme}://{parsed.netloc}"


def expected_route_confirmation(method: str, path: str) -> str:
    """Build the exact, route-bound confirmation required for a write."""

    normalized_path = "/" + str(path or "").split("?", 1)[0].lstrip("/")
    return f"CONFIRM {str(method or '').upper()} {normalized_path}"


def ensure_http_write_security_environment(*, origins: Iterable[str]) -> dict[str, object]:
    """Create process-only operator controls and merge explicit allowed origins."""

    configured_origins = {
        _normalize_origin(value)
        for value in os.environ.get("ALPHAPILOT_HTTP_ALLOWED_ORIGINS", "").split(",")
        if str(value).strip()
    }
    configured_origins.update(_normalize_origin(value) for value in origins)
    os.environ.setdefault("ALPHAPILOT_HTTP_WRITE_TOKEN", secrets.token_urlsafe(32))
    os.environ.setdefault("ALPHAPILOT_HTTP_CSRF_TOKEN", secrets.token_urlsafe(32))
    os.environ["ALPHAPILOT_HTTP_ALLOWED_ORIGINS"] = ",".join(sorted(configured_origins))
    return {
        "configured": True,
        "persisted": False,
        "originCount": len(configured_origins),
        "operatorSessionMode": "process_only",
        "credentialValuesStored": False,
    }


def build_operator_write_headers(*, method: str, path: str, origin: str) -> dict[str, str]:
    """Build headers for a trusted same-process UI or test client."""

    write_token = os.environ.get("ALPHAPILOT_HTTP_WRITE_TOKEN", "")
    csrf_token = os.environ.get("ALPHAPILOT_HTTP_CSRF_TOKEN", "")
    if not write_token or not csrf_token:
        raise RuntimeError("operator write security is not configured")
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": _normalize_origin(origin),
        "X-AlphaPilot-Write-Token": write_token,
        "X-AlphaPilot-CSRF": csrf_token,
        "X-AlphaPilot-Confirmation": expected_route_confirmation(method, path),
    }


def build_operator_session_projection(*, origin: str) -> dict[str, object]:
    """Expose only process-local UI tokens; callers must already be loopback."""

    headers = build_operator_write_headers(method="POST", path="/", origin=origin)
    return {
        "schemaVersion": "operator_write_session_v1",
        "mode": "process_only",
        "persisted": False,
        "origin": headers["Origin"],
        "writeToken": headers["X-AlphaPilot-Write-Token"],
        "csrfToken": headers["X-AlphaPilot-CSRF"],
        "confirmationFormat": "CONFIRM <METHOD> <PATH>",
    }


def evaluate_http_write(
    *,
    client_host: str,
    method: str,
    path: str,
    headers: Mapping[str, str],
    loopback: bool | None = None,
) -> HttpWriteDecision:
    """Authorize a write with the same controls for loopback and remote callers."""

    normalized_method = str(method or "").upper()
    normalized_path = "/" + str(path or "").split("?", 1)[0].lstrip("/")
    origin = _header(headers, "Origin") or None
    content_type = (_header(headers, "Content-Type") or "").split(";", 1)[0].strip().lower()
    is_loopback = _is_loopback(client_host) if loopback is None else bool(loopback)
    write_token = os.environ.get("ALPHAPILOT_HTTP_WRITE_TOKEN", "")
    csrf_token = os.environ.get("ALPHAPILOT_HTTP_CSRF_TOKEN", "")
    allowed_origins = {
        value.strip().rstrip("/")
        for value in os.environ.get("ALPHAPILOT_HTTP_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    }

    reason: str | None = None
    if not write_token or not csrf_token or not allowed_origins:
        reason = "write_security_not_configured" if is_loopback else "remote_write_disabled"
    elif content_type != "application/json":
        reason = "application_json_required"
    elif origin not in allowed_origins:
        reason = "origin_not_allowed"
    elif not _matches(_header(headers, "X-AlphaPilot-Write-Token"), write_token):
        reason = "write_token_mismatch"
    elif not _matches(_header(headers, "X-AlphaPilot-CSRF"), csrf_token):
        reason = "csrf_mismatch"
    elif not _matches(
        _header(headers, "X-AlphaPilot-Confirmation"),
        expected_route_confirmation(normalized_method, normalized_path),
    ):
        reason = "exact_confirmation_mismatch"

    if reason is None:
        return HttpWriteDecision(
            True,
            "authenticated_loopback" if is_loopback else "authenticated_remote",
            None,
            client_host,
            normalized_method,
            normalized_path,
            origin,
            content_type,
        )
    return HttpWriteDecision(
        False,
        "read_only_loopback" if is_loopback else "read_only_remote",
        reason,
        client_host,
        normalized_method,
        normalized_path,
        origin,
        content_type or None,
    )
