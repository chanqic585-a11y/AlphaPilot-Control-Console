"""Canonical hashing helpers shared by the isolated strategy-validation path."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


SENSITIVE_KEY_FRAGMENTS = (
    "apikey",
    "api_key",
    "apisecret",
    "api_secret",
    "passphrase",
    "withdraw",
    "privatekey",
    "private_key",
)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def stable_hash(value: Any, prefix: str | None = None) -> str:
    digest = hashlib.sha256(canonical_bytes(value)).hexdigest()
    return f"{prefix}_{digest}" if prefix else digest


def reject_sensitive_fields(value: Any, *, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).replace("-", "").lower()
            if any(fragment.replace("_", "") in normalized for fragment in SENSITIVE_KEY_FRAGMENTS):
                raise ValueError(f"sensitive field is forbidden at {path}.{key}")
            reject_sensitive_fields(item, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            reject_sensitive_fields(item, path=f"{path}[{index}]")
