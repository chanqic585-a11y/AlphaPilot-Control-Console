"""Central write authorization for the local control-console HTTP surface."""

from __future__ import annotations

import hmac
import ipaddress
import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class HttpWriteDecision:
    allowed: bool
    mode: str
    reason: str | None
    client_host: str
    path: str
    origin: str | None

    def audit_payload(self) -> dict[str, object]:
        """Return security metadata without copying any authentication value."""

        return {
            "allowed": self.allowed,
            "mode": self.mode,
            "reason": self.reason,
            "clientHost": self.client_host,
            "path": self.path,
            "origin": self.origin,
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


def evaluate_http_write(
    *,
    client_host: str,
    path: str,
    headers: Mapping[str, str],
    loopback: bool | None = None,
) -> HttpWriteDecision:
    """Authorize a write; remote callers are read-only unless fully configured."""

    origin = _header(headers, "Origin") or None
    if _is_loopback(client_host) if loopback is None else loopback:
        return HttpWriteDecision(True, "loopback", None, client_host, path, origin)

    write_token = os.environ.get("ALPHAPILOT_HTTP_WRITE_TOKEN", "")
    csrf_token = os.environ.get("ALPHAPILOT_HTTP_CSRF_TOKEN", "")
    confirmation = os.environ.get("ALPHAPILOT_HTTP_EXACT_CONFIRMATION", "")
    allowed_origins = {
        value.strip()
        for value in os.environ.get("ALPHAPILOT_HTTP_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    }
    if not write_token or not csrf_token or not confirmation or not allowed_origins:
        reason = "remote_write_disabled"
    elif origin not in allowed_origins:
        reason = "origin_not_allowed"
    elif not _matches(_header(headers, "X-AlphaPilot-Write-Token"), write_token):
        reason = "write_token_mismatch"
    elif not _matches(_header(headers, "X-AlphaPilot-CSRF"), csrf_token):
        reason = "csrf_mismatch"
    elif not _matches(
        _header(headers, "X-AlphaPilot-Confirmation"), confirmation
    ):
        reason = "exact_confirmation_mismatch"
    else:
        return HttpWriteDecision(
            True,
            "authenticated_remote",
            None,
            client_host,
            path,
            origin,
        )
    return HttpWriteDecision(False, "read_only_remote", reason, client_host, path, origin)
