"""Restore validated OKX Demo credentials into the current process only."""

from __future__ import annotations

import os
from collections.abc import Callable, MutableMapping
from typing import Any

from .demo_credential_enrollment import validate_demo_credentials
from .local_demo_launcher import LOCAL_DEMO_LAUNCHER, LocalDemoLauncher
from .state_store import append_audit
from .windows_demo_credential_vault import (
    DEMO_CREDENTIAL_LABEL,
    DEMO_CREDENTIAL_VAULT,
    DemoCredentialBundle,
    DemoCredentialVaultError,
    WindowsDemoCredentialVault,
)


Validator = Callable[[DemoCredentialBundle], dict[str, object]]
AuditWriter = Callable[[str, dict[str, object]], Any]

_CREDENTIAL_VARIABLES = (
    "ALPHAPILOT_OKX_DEMO_API_KEY",
    "ALPHAPILOT_OKX_DEMO_SECRET_KEY",
    "ALPHAPILOT_OKX_DEMO_PASSPHRASE",
)
_ENABLED_GATES = (
    "ALPHAPILOT_OKX_DEMO_ENABLED",
    "ALPHAPILOT_OKX_DEMO_ORDER_ENABLED",
    "ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED",
    "ALPHAPILOT_OKX_DEMO_LAUNCHER_CONFIRMED",
)


def _safe_context(process_id: int | None) -> dict[str, object]:
    return {
        "processId": int(os.getpid() if process_id is None else process_id),
        "targetLabel": DEMO_CREDENTIAL_LABEL,
    }


def _complete_process_environment(environment: MutableMapping[str, str]) -> bool:
    return all(str(environment.get(name, "")).strip() for name in _CREDENTIAL_VARIABLES)


def bootstrap_demo_credentials(
    *,
    environment: MutableMapping[str, str] | None = None,
    vault: WindowsDemoCredentialVault = DEMO_CREDENTIAL_VAULT,
    validator: Validator = validate_demo_credentials,
    audit_writer: AuditWriter = append_audit,
    process_id: int | None = None,
) -> dict[str, object]:
    """Load one validated Demo bundle without persisting ARM state or exposing secrets."""

    target = os.environ if environment is None else environment
    context = _safe_context(process_id)
    if _complete_process_environment(target):
        return {
            "ok": True,
            "status": "process_environment",
            "category": "process_environment",
            "promptRequired": False,
        }

    try:
        bundle = vault.load()
    except DemoCredentialVaultError as error:
        audit_writer("demo_vault_bootstrap_failed", {**context, "category": error.category})
        return {
            "ok": False,
            "status": "blocked",
            "category": error.category,
            "promptRequired": True,
        }

    if bundle is None:
        audit_writer("demo_vault_bootstrap_failed", {**context, "category": "credential_missing"})
        return {
            "ok": False,
            "status": "missing",
            "category": "credential_missing",
            "promptRequired": True,
        }

    try:
        validation = validator(bundle)
    except (PermissionError, RuntimeError, TypeError, ValueError):
        validation = {"ok": False, "category": "demo_validation_unavailable"}
    category = str(validation.get("category") or "demo_validation_rejected")
    if not validation.get("ok"):
        audit_writer("demo_vault_bootstrap_failed", {**context, "category": category})
        return {
            "ok": False,
            "status": "blocked",
            "category": category,
            "promptRequired": True,
        }

    target[_CREDENTIAL_VARIABLES[0]] = bundle.apiKey
    target[_CREDENTIAL_VARIABLES[1]] = bundle.secretKey
    target[_CREDENTIAL_VARIABLES[2]] = bundle.passphrase
    for gate in _ENABLED_GATES:
        target[gate] = "1"
    target["ALPHAPILOT_OKX_DEMO_CANCEL_ENABLED"] = "0"
    audit_writer("demo_vault_loaded", {**context, "category": "validated"})
    return {
        "ok": True,
        "status": "loaded",
        "category": "validated",
        "promptRequired": False,
    }


def demo_prompt_failure_class(
    bootstrap_result: dict[str, object],
    runtime_status: dict[str, object],
) -> str | None:
    """Return a stable prompt class only for an eligible, disarmed Demo runtime."""

    if not bootstrap_result.get("promptRequired"):
        return None
    environments = runtime_status.get("environments")
    demo = environments.get("okx_demo") if isinstance(environments, dict) else None
    if not isinstance(demo, dict):
        return None
    if not demo.get("desiredEnabled") or demo.get("armedForCurrentProcess"):
        return None
    if int(demo.get("releaseCount") or 0) <= 0:
        return None
    return str(bootstrap_result.get("category") or "credential_required")


def maybe_open_demo_credential_prompt(
    bootstrap_result: dict[str, object],
    runtime_status: dict[str, object],
    *,
    host: str,
    port: int,
    process_id: int | None = None,
    launcher: LocalDemoLauncher = LOCAL_DEMO_LAUNCHER,
) -> dict[str, object]:
    """Open at most one visible enrollment prompt for this process and failure class."""

    failure_class = demo_prompt_failure_class(bootstrap_result, runtime_status)
    if failure_class is None:
        return {"ok": True, "status": "prompt_not_required"}
    return launcher.open_once_for_failure(
        "127.0.0.1",
        current_pid=int(os.getpid() if process_id is None else process_id),
        port=port,
        failure_class=failure_class,
        mobile=host in {"0.0.0.0", "::"},
    )
