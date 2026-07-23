"""Synthetic read-only provider smoke sequence executed through the service."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

from .bootstrap import build_ai_runtime
from .contracts import AIRequest
from .provider_readiness import (
    CREDENTIAL_ENVIRONMENT_VARIABLES,
    build_fixed_provider_smoke_request,
    build_provider_readiness_report,
)
from .service import AIOrchestrationService


_SMOKE_TASKS = (
    "provider_smoke_deepseek",
    "provider_smoke_gemini",
    "provider_smoke_dual",
)
_SMOKE_SCHEMA = {
    "type": "object",
    "properties": {
        "evidenceStatus": {
            "type": "string",
            "enum": ["synthetic_fixture_only"],
        },
        "executionIntent": {"type": "string", "enum": ["none"]},
        "summary": {"type": "string", "minLength": 1, "maxLength": 240},
        "sourceArtifactHashes": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 1,
        },
    },
    "required": [
        "evidenceStatus",
        "executionIntent",
        "summary",
        "sourceArtifactHashes",
    ],
    "additionalProperties": False,
}


def _safe_error_message(error: Exception) -> str:
    message = " ".join(str(error).split()) or type(error).__name__
    for name in CREDENTIAL_ENVIRONMENT_VARIABLES:
        credential = str(os.environ.get(name) or "")
        if credential:
            message = message.replace(credential, "[REDACTED]")
    return message[:500]


def _failure_check(task_type: str, error: Exception) -> dict[str, object]:
    return {
        "taskType": task_type,
        "status": "provider_error",
        "routeMode": "unknown",
        "responseHashes": [],
        "executionAuthorized": False,
        "errorType": type(error).__name__,
        "errorMessage": _safe_error_message(error),
    }


def _request(task_type: str) -> AIRequest:
    base = build_fixed_provider_smoke_request()
    return AIRequest(
        request_id=f"provider-smoke-v62-4:{task_type}",
        task_type=task_type,
        payload=base.payload,
        response_schema=_SMOKE_SCHEMA,
        sensitivity=base.sensitivity,
        prompt_version="provider-smoke-v1",
        artifact_hashes=base.artifact_hashes,
        tool_names=base.tool_names,
        cost_ceiling_usd=base.cost_ceiling_usd,
        token_ceiling=base.token_ceiling,
        metadata=base.metadata,
    )


def execute_provider_smoke_sequence(
    service: AIOrchestrationService,
) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    for task_type in _SMOKE_TASKS:
        try:
            result = service.execute(_request(task_type))
        except Exception as error:  # Keep independent provider diagnosis running.
            checks.append(_failure_check(task_type, error))
            continue
        checks.append(
            {
                "taskType": task_type,
                "status": result.status,
                "routeMode": result.route_mode,
                "responseHashes": list(result.response_hashes),
                "executionAuthorized": result.execution_authorized,
            }
        )
    passed = all(
        item["status"] == "accepted" and item["executionAuthorized"] is False
        for item in checks
    )
    return {
        "schemaVersion": "alphapilot_ai_provider_smoke_v1",
        "status": "provider_smoke_passed" if passed else "provider_smoke_failed",
        "checks": checks,
        "executionAuthorized": False,
        "runtimeArmed": False,
        "withdrawEnabled": False,
    }


def run_provider_smoke(
    *, repository_root: Path | str, data_root: Path | str
) -> dict[str, object]:
    readiness = build_provider_readiness_report(repository_root=repository_root)
    if readiness["status"] != "provider_credentials_ready":
        return {**readiness, "checks": []}
    with build_ai_runtime(repository_root=repository_root, data_root=data_root) as runtime:
        smoke = execute_provider_smoke_sequence(runtime.service)
    return {
        **smoke,
        "providerSmokeInputHash": readiness["providerSmokeInputHash"],
        "providerSmokeLimits": readiness["providerSmokeLimits"],
        "aiWorkerIdentity": readiness["aiWorkerIdentity"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run synthetic DeepSeek-only, Gemini-only and dual-model smokes."
    )
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run_provider_smoke(
            repository_root=args.repository_root,
            data_root=args.data_root,
        )
    except Exception as error:
        report = {
            "schemaVersion": "alphapilot_ai_provider_smoke_v1",
            "status": "provider_smoke_failed",
            "failureStage": "runtime",
            "errorType": type(error).__name__,
            "errorMessage": _safe_error_message(error),
            "checks": [],
            "executionAuthorized": False,
            "runtimeArmed": False,
            "withdrawEnabled": False,
        }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if report["status"] == "provider_smoke_passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
