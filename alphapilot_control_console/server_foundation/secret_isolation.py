"""Role-scoped environment construction without exchange private credentials."""

from __future__ import annotations

from collections.abc import Mapping

from .contracts import FoundationRole


class SecretIsolationViolation(PermissionError):
    """Raised when a worker receives a secret outside its role policy."""


_COMMON_ENVIRONMENT_KEYS = {
    "ALLUSERSPROFILE",
    "APPDATA",
    "COMMONPROGRAMFILES",
    "COMMONPROGRAMFILES(X86)",
    "COMMONPROGRAMW6432",
    "COMPUTERNAME",
    "COMSPEC",
    "HOMEDRIVE",
    "HOMEPATH",
    "LOCALAPPDATA",
    "NUMBER_OF_PROCESSORS",
    "OS",
    "PATH",
    "PATHEXT",
    "PROCESSOR_ARCHITECTURE",
    "PROCESSOR_IDENTIFIER",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "PROGRAMW6432",
    "PSMODULEPATH",
    "PUBLIC",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERDOMAIN",
    "USERNAME",
    "USERPROFILE",
    "WINDIR",
}
_AI_PROVIDER_KEYS = {"DEEPSEEK_API_KEY", "GEMINI_API_KEY"}
_SECRET_MARKERS = (
    "API_KEY",
    "APIKEY",
    "SECRET",
    "PASSPHRASE",
    "PASSWORD",
    "PRIVATE_KEY",
    "TOKEN",
)


def _looks_secret(name: str) -> bool:
    normalized = name.upper()
    return any(marker in normalized for marker in _SECRET_MARKERS)


def sanitized_environment_for_role(
    role: FoundationRole,
    source: Mapping[str, str],
    *,
    reject_disallowed: bool = False,
) -> dict[str, str]:
    role = FoundationRole(role)
    allowed_secrets = _AI_PROVIDER_KEYS if role is FoundationRole.AI else set()
    environment: dict[str, str] = {}
    disallowed: list[str] = []
    for key, value in source.items():
        normalized = str(key).upper()
        if normalized in _COMMON_ENVIRONMENT_KEYS or normalized.startswith(
            "ALPHAPILOT_V63_"
        ):
            environment[str(key)] = str(value)
        elif normalized in allowed_secrets:
            environment[normalized] = str(value)
        elif _looks_secret(normalized):
            disallowed.append(normalized)
    if reject_disallowed and disallowed:
        raise SecretIsolationViolation(
            "secret_not_allowed_for_role:"
            f"{role.value}:{','.join(sorted(set(disallowed)))}"
        )
    return environment
