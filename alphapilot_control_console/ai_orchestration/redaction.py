"""Local minimization and credential blocking before any provider call."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import AIRequest, PreparedAIRequest
from .errors import SensitiveDataError


_CREDENTIAL_KEY_FRAGMENTS = (
    "apikey",
    "apisecret",
    "secretkey",
    "passphrase",
    "privatekey",
    "authorization",
    "bearer",
    "cookie",
    "credential",
)
_RESTRICTED_IDENTIFIERS = {
    "accountid",
    "subaccountid",
    "userid",
    "orderid",
    "clientorderid",
    "tradeid",
    "positionid",
    "sessionid",
    "ipaddress",
}
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
)
_PROMPT_INJECTION_PATTERNS = (
    re.compile(
        r"(?i)(?:ignore|disregard|override).{0,80}(?:previous|system|developer).{0,80}(?:instruction|prompt)",
    ),
    re.compile(
        r"(?i)(?:reveal|print|show|exfiltrate).{0,80}(?:system|developer).{0,80}(?:instruction|prompt)",
    ),
    re.compile(r"(?i)<\s*(?:tool_call|function_call|system|developer)\b"),
    re.compile(
        r"(?i)\b(?:call|invoke|execute|run|use)\s+"
        r"(?:place_order|create_order|cancel_order|close_position|modify_position|"
        r"set_leverage|approve_release|arm_runtime|kill_switch|withdraw|transfer_funds)\b"
    ),
)


def _normalized_key(key: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _contains_credential_key(key: object) -> bool:
    normalized = _normalized_key(key)
    return any(fragment in normalized for fragment in _CREDENTIAL_KEY_FRAGMENTS)


def _reject_secrets(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _contains_credential_key(key):
                raise SensitiveDataError(f"credential-shaped field blocked at {path}{key}")
            _reject_secrets(nested, f"{path}{key}.")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_secrets(nested, f"{path}{index}.")
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in _SECRET_PATTERNS):
            raise SensitiveDataError(f"credential-shaped value blocked at {path or '<root>'}")


@dataclass(slots=True)
class _RedactionState:
    paths: list[str]


def _minimize_restricted(value: Any, state: _RedactionState, path: str = "") -> Any:
    if isinstance(value, Mapping):
        output: dict[str, Any] = {}
        for key, nested in value.items():
            child_path = f"{path}{key}"
            if _normalized_key(key) in _RESTRICTED_IDENTIFIERS:
                output[str(key)] = "[REDACTED]"
                state.paths.append(child_path)
            else:
                output[str(key)] = _minimize_restricted(nested, state, f"{child_path}.")
        return output
    if isinstance(value, list):
        return [_minimize_restricted(item, state, f"{path}{index}.") for index, item in enumerate(value)]
    if isinstance(value, tuple):
        return tuple(
            _minimize_restricted(item, state, f"{path}{index}.") for index, item in enumerate(value)
        )
    return copy.deepcopy(value)


def _neutralize_untrusted_instructions(value: Any, state: _RedactionState, path: str = "") -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _neutralize_untrusted_instructions(nested, state, f"{path}{key}.")
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [
            _neutralize_untrusted_instructions(item, state, f"{path}{index}.")
            for index, item in enumerate(value)
        ]
    if isinstance(value, tuple):
        return tuple(
            _neutralize_untrusted_instructions(item, state, f"{path}{index}.")
            for index, item in enumerate(value)
        )
    if isinstance(value, str):
        output = value
        for pattern in _PROMPT_INJECTION_PATTERNS:
            if pattern.search(output):
                output = pattern.sub("[UNTRUSTED_INSTRUCTION_REDACTED]", output)
                state.paths.append(path.rstrip(".") or "<root>")
        return output
    return copy.deepcopy(value)


class LocalRedactor:
    """Reject secrets and minimize restricted trading context before routing."""

    def prepare(self, request: AIRequest) -> PreparedAIRequest:
        if request.sensitivity == "secret":
            raise SensitiveDataError("SECRET data is forbidden for external AI providers")
        _reject_secrets(request.payload)
        _reject_secrets(request.metadata)
        state = _RedactionState(paths=[])
        payload = (
            _minimize_restricted(request.payload, state)
            if request.sensitivity == "restricted_trading"
            else copy.deepcopy(dict(request.payload))
        )
        payload = _neutralize_untrusted_instructions(payload, state)
        envelope = {
            "taskType": request.task_type,
            "payload": payload,
            "promptVersion": request.prompt_version,
            "artifactHashes": list(request.artifact_hashes),
        }
        input_hash = "sha256:" + hashlib.sha256(_canonical_json(envelope).encode("utf-8")).hexdigest()
        return PreparedAIRequest(
            request=request,
            payload=payload,
            input_hash=input_hash,
            redaction_count=len(state.paths),
            redacted_paths=tuple(state.paths),
        )
