from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Iterable


class ActionKind(StrEnum):
    NAVIGATE = "navigate"
    RESEARCH_COMMAND = "research_command"
    READ_ONLY_EXPORT = "read_only_export"
    FORBIDDEN_EXECUTION = "forbidden_execution"


@dataclass(frozen=True)
class StatusPresentation:
    code: str
    labelZh: str
    tone: str
    semanticColor: str
    icon: str
    isHealthy: bool = False
    isTerminal: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class StatusPresentationCatalog:
    def __init__(
        self,
        presentations: Iterable[StatusPresentation],
        *,
        unknown: StatusPresentation,
    ) -> None:
        self._presentations = {
            presentation.code: presentation for presentation in presentations
        }
        self._unknown = unknown

    @classmethod
    def default(cls) -> "StatusPresentationCatalog":
        rows = (
            StatusPresentation(
                "healthy", "健康", "success", "green", "check-circle", True
            ),
            StatusPresentation(
                "running", "运行中", "info", "blue", "activity", True
            ),
            StatusPresentation(
                "queued", "排队中", "neutral", "gray", "clock"
            ),
            StatusPresentation(
                "waiting", "等待中", "warning", "yellow", "clock"
            ),
            StatusPresentation(
                "blocked", "已阻塞", "danger", "red", "octagon-alert", False, True
            ),
            StatusPresentation(
                "failed", "未通过", "danger", "red", "circle-x", False, True
            ),
            StatusPresentation(
                "passed", "已通过", "success", "green", "circle-check", True, True
            ),
            StatusPresentation(
                "archived", "已归档", "neutral", "gray", "archive", False, True
            ),
            StatusPresentation(
                "stale", "数据陈旧", "danger", "red", "wifi-off"
            ),
            StatusPresentation(
                "disconnected", "连接已断开", "danger", "red", "wifi-off"
            ),
            StatusPresentation(
                "not_run", "尚未运行", "neutral", "gray", "minus-circle"
            ),
        )
        return cls(
            rows,
            unknown=StatusPresentation(
                "unknown",
                "状态未知",
                "warning",
                "yellow",
                "circle-help",
            ),
        )

    def present(self, code: str | None) -> StatusPresentation:
        normalized = str(code or "").strip().lower()
        return self._presentations.get(normalized, self._unknown)

    def to_dict(self) -> dict[str, dict[str, object]]:
        rows = {
            code: presentation.to_dict()
            for code, presentation in sorted(self._presentations.items())
        }
        rows["unknown"] = self._unknown.to_dict()
        return rows


@dataclass(frozen=True)
class NextActionProjection:
    actionId: str
    labelZh: str
    actionKind: ActionKind
    enabled: bool
    primary: bool = False
    expectedStateVersionRequired: bool = False
    href: str | None = None
    commandEndpoint: str | None = None
    forbiddenReasonCode: str | None = None
    forbiddenReasonZh: str | None = None

    def __post_init__(self) -> None:
        if not self.actionId.strip() or not self.labelZh.strip():
            raise ValueError("actionId and labelZh are required")
        if self.actionKind is ActionKind.FORBIDDEN_EXECUTION and self.enabled:
            raise ValueError("forbidden execution actions cannot be enabled")
        if (
            self.actionKind is ActionKind.RESEARCH_COMMAND
            and self.enabled
            and not self.expectedStateVersionRequired
        ):
            raise ValueError("research commands require expectedStateVersion")
        if self.primary and not self.enabled:
            raise ValueError("disabled actions cannot be primary")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["actionKind"] = self.actionKind.value
        return payload


def validate_primary_action_uniqueness(
    actions: Iterable[NextActionProjection],
) -> None:
    primary_count = sum(action.primary for action in actions)
    if primary_count > 1:
        raise ValueError("a projection may expose at most one primary action")


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class DataFreshness:
    asOf: str | None
    ageSeconds: float | None
    staleAfterSeconds: int
    status: str
    labelZh: str
    isStale: bool
    allowsStrictMatch: bool

    @classmethod
    def unknown(cls, *, stale_after_seconds: int = 3) -> "DataFreshness":
        return cls(
            asOf=None,
            ageSeconds=None,
            staleAfterSeconds=stale_after_seconds,
            status="unknown",
            labelZh="时间未知",
            isStale=True,
            allowsStrictMatch=False,
        )

    @classmethod
    def from_timestamp(
        cls,
        value: str | None,
        *,
        stale_after_seconds: int,
        now: datetime | None = None,
    ) -> "DataFreshness":
        if stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        if not value:
            return cls.unknown(stale_after_seconds=stale_after_seconds)
        try:
            timestamp = _parse_datetime(value)
        except (TypeError, ValueError):
            return cls.unknown(stale_after_seconds=stale_after_seconds)
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        age = max(0.0, (current - timestamp).total_seconds())
        stale = age > stale_after_seconds
        return cls(
            asOf=timestamp.isoformat().replace("+00:00", "Z"),
            ageSeconds=round(age, 3),
            staleAfterSeconds=stale_after_seconds,
            status="stale" if stale else "fresh",
            labelZh="数据陈旧" if stale else "实时",
            isStale=stale,
            allowsStrictMatch=not stale,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectionConflict:
    expectedStateVersion: str
    actualStateVersion: str
    httpStatus: int = 409
    error: str = "state_version_mismatch"
    refreshProjectionRequired: bool = True
    operatorMessageZh: str = "底层状态已变更，请基于最新状态操作"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class LineageProjection:
    lineageId: str
    parentIds: tuple[str, ...]
    definitionHash: str
    releaseHash: str | None
    immutable: bool

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["parentIds"] = list(self.parentIds)
        return payload


@dataclass(frozen=True)
class MLOriginProjection:
    generatedByML: bool
    generationId: str | None
    modelHash: str | None
    humanPromoted: bool
    labelZh: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
