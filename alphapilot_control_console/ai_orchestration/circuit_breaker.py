"""Provider health states and bounded circuit-breaker cooldown."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .errors import ProviderUnavailableError


@dataclass(slots=True)
class _ProviderState:
    consecutive_failures: int = 0
    opened_at: float | None = None
    disabled: bool = False


class ProviderCircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        cooldown_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold <= 0:
            raise ValueError("failure threshold must be positive")
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = max(0.0, cooldown_seconds)
        self._clock = clock
        self._states: dict[str, _ProviderState] = {}

    def _state(self, provider: str) -> _ProviderState:
        return self._states.setdefault(provider, _ProviderState())

    def status(self, provider: str) -> str:
        state = self._state(provider)
        if state.disabled:
            return "disabled"
        if state.opened_at is not None:
            if self._clock() - state.opened_at < self._cooldown_seconds:
                return "unavailable"
            state.opened_at = None
            state.consecutive_failures = max(1, self._failure_threshold - 1)
            return "degraded"
        if state.consecutive_failures:
            return "degraded"
        return "healthy"

    def assert_available(self, provider: str) -> None:
        status = self.status(provider)
        if status in {"unavailable", "disabled"}:
            raise ProviderUnavailableError(f"AI provider circuit is {status}: {provider}")

    def record_failure(self, provider: str) -> None:
        state = self._state(provider)
        state.consecutive_failures += 1
        if state.consecutive_failures >= self._failure_threshold:
            state.opened_at = self._clock()

    def record_success(self, provider: str) -> None:
        state = self._state(provider)
        state.consecutive_failures = 0
        state.opened_at = None

    def disable(self, provider: str) -> None:
        self._state(provider).disabled = True

    def enable(self, provider: str) -> None:
        state = self._state(provider)
        state.disabled = False
        state.consecutive_failures = 0
        state.opened_at = None

    def projection(self) -> dict[str, object]:
        return {
            "schemaVersion": "alphapilot_ai_provider_health_v1",
            "providers": {
                provider: {
                    "status": self.status(provider),
                    "consecutiveFailures": state.consecutive_failures,
                    "disabled": state.disabled,
                }
                for provider, state in sorted(self._states.items())
            },
        }
