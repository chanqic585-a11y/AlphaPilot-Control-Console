"""Process-only OKX Demo credentials with deliberately redacted representation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class OkxDemoCredentials:
    apiKey: str = field(repr=False)
    secretKey: str = field(repr=False)
    passphrase: str = field(repr=False)

    def status(self) -> dict[str, bool]:
        return {
            "apiKeyConfigured": bool(self.apiKey),
            "secretKeyConfigured": bool(self.secretKey),
            "passphraseConfigured": bool(self.passphrase),
            "allConfigured": bool(self.apiKey and self.secretKey and self.passphrase),
            "stored": False,
        }

    def __repr__(self) -> str:
        return "OkxDemoCredentials(apiKey=<redacted>, secretKey=<redacted>, passphrase=<redacted>)"


@dataclass(frozen=True)
class OkxLiveCredentials:
    apiKey: str = field(repr=False)
    secretKey: str = field(repr=False)
    passphrase: str = field(repr=False)

    def status(self) -> dict[str, bool]:
        return {
            "apiKeyConfigured": bool(self.apiKey),
            "secretKeyConfigured": bool(self.secretKey),
            "passphraseConfigured": bool(self.passphrase),
            "allConfigured": bool(self.apiKey and self.secretKey and self.passphrase),
            "stored": False,
        }

    def __repr__(self) -> str:
        return "OkxLiveCredentials(apiKey=<redacted>, secretKey=<redacted>, passphrase=<redacted>)"


def load_okx_demo_credentials(
    environment: Mapping[str, str] | None = None,
) -> OkxDemoCredentials:
    source = os.environ if environment is None else environment
    credentials = OkxDemoCredentials(
        apiKey=str(source.get("ALPHAPILOT_OKX_DEMO_API_KEY", "")).strip(),
        secretKey=str(source.get("ALPHAPILOT_OKX_DEMO_SECRET_KEY", "")).strip(),
        passphrase=str(source.get("ALPHAPILOT_OKX_DEMO_PASSPHRASE", "")).strip(),
    )
    if not credentials.status()["allConfigured"]:
        raise RuntimeError("OKX Demo runtime credentials are incomplete")
    return credentials


def runtime_credential_status(environment: Mapping[str, str] | None = None) -> dict[str, bool]:
    source = os.environ if environment is None else environment
    values = (
        str(source.get("ALPHAPILOT_OKX_DEMO_API_KEY", "")).strip(),
        str(source.get("ALPHAPILOT_OKX_DEMO_SECRET_KEY", "")).strip(),
        str(source.get("ALPHAPILOT_OKX_DEMO_PASSPHRASE", "")).strip(),
    )
    return {
        "apiKeyConfigured": bool(values[0]),
        "secretKeyConfigured": bool(values[1]),
        "passphraseConfigured": bool(values[2]),
        "allConfigured": all(bool(value) for value in values),
        "stored": False,
    }


def load_okx_live_credentials(
    environment: Mapping[str, str] | None = None,
) -> OkxLiveCredentials:
    source = os.environ if environment is None else environment
    credentials = OkxLiveCredentials(
        apiKey=str(source.get("ALPHAPILOT_OKX_LIVE_API_KEY", "")).strip(),
        secretKey=str(source.get("ALPHAPILOT_OKX_LIVE_SECRET_KEY", "")).strip(),
        passphrase=str(source.get("ALPHAPILOT_OKX_LIVE_PASSPHRASE", "")).strip(),
    )
    if not credentials.status()["allConfigured"]:
        raise RuntimeError("OKX Live runtime credentials are incomplete")
    return credentials


def live_runtime_credential_status(
    environment: Mapping[str, str] | None = None,
) -> dict[str, bool]:
    source = os.environ if environment is None else environment
    values = (
        str(source.get("ALPHAPILOT_OKX_LIVE_API_KEY", "")).strip(),
        str(source.get("ALPHAPILOT_OKX_LIVE_SECRET_KEY", "")).strip(),
        str(source.get("ALPHAPILOT_OKX_LIVE_PASSPHRASE", "")).strip(),
    )
    return {
        "apiKeyConfigured": bool(values[0]),
        "secretKeyConfigured": bool(values[1]),
        "passphraseConfigured": bool(values[2]),
        "allConfigured": all(bool(value) for value in values),
        "stored": False,
    }
