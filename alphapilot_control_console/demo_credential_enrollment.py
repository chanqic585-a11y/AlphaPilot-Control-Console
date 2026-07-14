"""Validate and enroll one Demo-only credential bundle without secret echo."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

from .credential_runtime import OkxDemoCredentials
from .exchange_connectors.okx_demo_client import OkxDemoClient, OkxDemoError
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
ClientFactory = Callable[[OkxDemoCredentials], Any]


def _default_client_factory(credentials: OkxDemoCredentials) -> OkxDemoClient:
    return OkxDemoClient(credentials, site="global")


def validate_demo_credentials(
    bundle: DemoCredentialBundle,
    *,
    client_factory: ClientFactory = _default_client_factory,
) -> dict[str, object]:
    """Make one allowlisted Demo read-only request and return a safe category."""

    credentials = OkxDemoCredentials(
        apiKey=bundle.apiKey,
        secretKey=bundle.secretKey,
        passphrase=bundle.passphrase,
    )
    try:
        response = client_factory(credentials).get_account_config()
    except OkxDemoError:
        return {"ok": False, "category": "demo_validation_unavailable"}
    except (PermissionError, RuntimeError, TypeError, ValueError):
        return {"ok": False, "category": "demo_validation_rejected"}
    code = str(response.get("code") or "") if isinstance(response, dict) else ""
    if code != "0":
        return {"ok": False, "category": "demo_validation_rejected"}
    return {"ok": True, "category": "validated"}


def enroll_demo_credentials(
    *,
    environment: Mapping[str, str] | None = None,
    vault: WindowsDemoCredentialVault = DEMO_CREDENTIAL_VAULT,
    validator: Validator = validate_demo_credentials,
    audit_writer: AuditWriter = append_audit,
    process_id: int | None = None,
    store_hook: Callable[[DemoCredentialBundle], Any] | None = None,
) -> dict[str, object]:
    """Validate then persist credentials; never return or audit secret material."""

    source = os.environ if environment is None else environment
    bundle = DemoCredentialBundle(
        apiKey=str(source.get("ALPHAPILOT_OKX_DEMO_API_KEY", "")).strip(),
        secretKey=str(source.get("ALPHAPILOT_OKX_DEMO_SECRET_KEY", "")).strip(),
        passphrase=str(source.get("ALPHAPILOT_OKX_DEMO_PASSPHRASE", "")).strip(),
    )
    safe_context = {
        "processId": int(os.getpid() if process_id is None else process_id),
        "targetLabel": DEMO_CREDENTIAL_LABEL,
    }
    if not all((bundle.apiKey, bundle.secretKey, bundle.passphrase)):
        audit_writer(
            "demo_vault_validation_failed",
            {**safe_context, "category": "credential_incomplete"},
        )
        return {"ok": False, "status": "rejected", "category": "credential_incomplete"}

    validation = validator(bundle)
    category = str(validation.get("category") or "demo_validation_rejected")
    if not validation.get("ok"):
        audit_writer("demo_vault_validation_failed", {**safe_context, "category": category})
        return {"ok": False, "status": "rejected", "category": category}

    audit_writer("demo_vault_validation_succeeded", safe_context)
    try:
        if store_hook is not None:
            store_hook(bundle)
        vault.store(bundle)
    except DemoCredentialVaultError as error:
        audit_writer(
            "demo_vault_enrollment_failed",
            {**safe_context, "category": error.category},
        )
        return {"ok": False, "status": "rejected", "category": error.category}

    audit_writer("demo_vault_enrollment_succeeded", safe_context)
    return {
        "ok": True,
        "status": "stored",
        "metadata": vault.metadata(),
    }
