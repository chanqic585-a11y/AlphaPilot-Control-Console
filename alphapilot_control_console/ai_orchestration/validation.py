"""JSON Schema subset and AlphaPilot business-semantic validation."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .errors import OutputValidationError


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: Any, prefix: str = "ai_output") -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _type_matches(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, Mapping),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def validate_json_schema(value: Any, schema: Mapping[str, Any], path: str = "$") -> None:
    expected = schema.get("type")
    if isinstance(expected, str) and not _type_matches(value, expected.lower()):
        raise OutputValidationError(f"{path} expected {expected}")
    if "enum" in schema and value not in schema["enum"]:
        raise OutputValidationError(f"{path} is outside allowed enum")
    if isinstance(value, Mapping):
        required = schema.get("required") or []
        missing = [str(key) for key in required if key not in value]
        if missing:
            raise OutputValidationError(f"{path} missing required fields: {', '.join(missing)}")
        properties = schema.get("properties") or {}
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise OutputValidationError(f"{path} has additional fields: {', '.join(extra)}")
        for key, nested in value.items():
            nested_schema = properties.get(key)
            if isinstance(nested_schema, Mapping):
                validate_json_schema(nested, nested_schema, f"{path}.{key}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < int(schema["minItems"]):
            raise OutputValidationError(f"{path} has too few items")
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            raise OutputValidationError(f"{path} has too many items")
        item_schema = schema.get("items")
        if isinstance(item_schema, Mapping):
            for index, nested in enumerate(value):
                validate_json_schema(nested, item_schema, f"{path}[{index}]")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            raise OutputValidationError(f"{path} is too short")
        if "maxLength" in schema and len(value) > int(schema["maxLength"]):
            raise OutputValidationError(f"{path} is too long")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise OutputValidationError(f"{path} is below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise OutputValidationError(f"{path} is above maximum")


_FORBIDDEN_DECISION_KEYS = {
    "autoApprove",
    "approvalGranted",
    "armRuntime",
    "placeOrder",
    "submitOrder",
    "cancelOrder",
    "withdraw",
    "raiseRisk",
}


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, nested in value.items():
            keys.add(str(key))
            keys.update(_walk_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(_walk_keys(nested))
    return keys


def validate_business_semantics(
    *,
    task_type: str,
    output: Mapping[str, Any],
    artifact_hashes: tuple[str, ...],
) -> None:
    forbidden = sorted(_FORBIDDEN_DECISION_KEYS.intersection(_walk_keys(output)))
    if forbidden:
        raise OutputValidationError(f"AI output contains forbidden execution decisions: {', '.join(forbidden)}")
    source_hashes = output.get("sourceArtifactHashes")
    if source_hashes is not None:
        if not isinstance(source_hashes, list) or any(item not in artifact_hashes for item in source_hashes):
            raise OutputValidationError("AI output references an unbound source artifact hash")
    if task_type == "strategy_hypothesis":
        if not str(output.get("falsifiableHypothesis") or "").strip():
            raise OutputValidationError("strategy hypothesis must be falsifiable")
        if not output.get("invalidationConditions"):
            raise OutputValidationError("strategy hypothesis needs invalidation conditions")
        if not isinstance(output.get("exitPolicy"), Mapping):
            raise OutputValidationError("strategy hypothesis needs a versionable exit policy")
    if task_type == "failure_attribution":
        facts = output.get("facts")
        inferences = output.get("inferences")
        if not isinstance(facts, list) or not facts:
            raise OutputValidationError("failure attribution needs evidence-backed facts")
        if not isinstance(inferences, list):
            raise OutputValidationError("failure attribution needs a separate inference list")


def validate_output(
    *,
    task_type: str,
    output: Mapping[str, Any],
    schema: Mapping[str, Any],
    artifact_hashes: tuple[str, ...],
) -> str:
    validate_json_schema(output, schema)
    validate_business_semantics(
        task_type=task_type,
        output=output,
        artifact_hashes=artifact_hashes,
    )
    return stable_hash(output)
