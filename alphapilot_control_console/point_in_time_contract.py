"""Point-in-time ordering contract shared by feature and execution paths."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _parse(value: Any, name: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a timezone")
    return parsed.astimezone(UTC)


def validate_point_in_time(
    *,
    source_timestamp: Any,
    available_at: Any,
    observed_at: Any,
    decision_at: Any,
    order_send_at: Any | None = None,
) -> dict[str, Any]:
    source = _parse(source_timestamp, "sourceTimestamp")
    available = _parse(available_at, "availableAt")
    observed = _parse(observed_at, "observedAt")
    decision = _parse(decision_at, "decisionAt")
    ordered = [source, available, observed, decision]
    labels = ["sourceTimestamp", "availableAt", "observedAt", "decisionAt"]
    if order_send_at is not None:
        ordered.append(_parse(order_send_at, "orderSendAt"))
        labels.append("orderSendAt")
    if any(left > right for left, right in zip(ordered, ordered[1:])):
        raise ValueError(
            "Point-in-time ordering must satisfy sourceTimestamp <= availableAt "
            "<= observedAt <= decisionAt <= orderSendAt"
        )
    return {
        "schemaVersion": "point_in_time_contract_v2",
        "passed": True,
        "ordering": labels,
        "timestamps": {
            label: value.isoformat().replace("+00:00", "Z")
            for label, value in zip(labels, ordered)
        },
    }
