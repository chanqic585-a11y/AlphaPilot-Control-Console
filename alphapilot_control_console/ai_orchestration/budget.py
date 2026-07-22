"""Versionable provider, task and campaign cost-budget enforcement."""

from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .errors import BudgetExceededError


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _utc_day() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class AIBudgetLedger:
    """Cost usage only; prompts and responses are intentionally absent."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS AIBudgetUsage (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                occurredAt TEXT NOT NULL,
                utcDay TEXT NOT NULL,
                provider TEXT NOT NULL,
                taskType TEXT NOT NULL,
                campaignId TEXT NOT NULL,
                requestId TEXT NOT NULL UNIQUE,
                costUsd REAL NOT NULL,
                totalTokens INTEGER NOT NULL
            )
            """
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_budget_day ON AIBudgetUsage(utcDay, provider, taskType)"
        )
        self._connection.commit()

    def record(
        self,
        *,
        provider: str,
        task_type: str,
        campaign_id: str,
        request_id: str,
        cost_usd: float,
        total_tokens: int,
    ) -> None:
        self._connection.execute(
            """
            INSERT OR IGNORE INTO AIBudgetUsage (
                occurredAt, utcDay, provider, taskType, campaignId,
                requestId, costUsd, totalTokens
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _utc_now(),
                _utc_day(),
                provider,
                task_type,
                campaign_id,
                request_id,
                max(0.0, float(cost_usd)),
                max(0, int(total_tokens)),
            ),
        )
        self._connection.commit()

    def spend(self, *, provider: str, task_type: str, campaign_id: str) -> dict[str, float]:
        day = _utc_day()
        row = self._connection.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN utcDay = ? AND provider = ? THEN costUsd END), 0) providerSpend,
                COALESCE(SUM(CASE WHEN utcDay = ? AND taskType = ? THEN costUsd END), 0) taskSpend,
                COALESCE(SUM(CASE WHEN campaignId = ? THEN costUsd END), 0) campaignSpend
            FROM AIBudgetUsage
            """,
            (day, provider, day, task_type, campaign_id),
        ).fetchone()
        return {
            "provider": float(row["providerSpend"]),
            "taskType": float(row["taskSpend"]),
            "campaign": float(row["campaignSpend"]),
        }

    def projection(self) -> dict[str, Any]:
        rows = self._connection.execute(
            "SELECT provider, taskType, campaignId, requestId, costUsd, totalTokens, utcDay FROM AIBudgetUsage ORDER BY sequence"
        ).fetchall()
        providers = Counter(str(row["provider"]) for row in rows)
        return {
            "schemaVersion": "alphapilot_ai_budget_projection_v1",
            "usageCount": len(rows),
            "providerRequestCounts": dict(sorted(providers.items())),
            "totalCostUsd": round(sum(float(row["costUsd"]) for row in rows), 10),
            "totalTokens": sum(int(row["totalTokens"]) for row in rows),
        }

    def close(self) -> None:
        self._connection.close()


class AIBudgetPolicy:
    def __init__(
        self,
        *,
        ledger: AIBudgetLedger,
        daily_provider_limits: Mapping[str, float],
        daily_task_limits: Mapping[str, float],
        campaign_limits: Mapping[str, float],
        default_campaign_limit_usd: float | None = None,
    ) -> None:
        self._ledger = ledger
        self._provider_limits = dict(daily_provider_limits)
        self._task_limits = dict(daily_task_limits)
        self._campaign_limits = dict(campaign_limits)
        self._default_campaign_limit_usd = default_campaign_limit_usd

    def assert_available(
        self,
        *,
        provider: str,
        task_type: str,
        campaign_id: str,
        requested_cost_ceiling_usd: float,
    ) -> None:
        spend = self._ledger.spend(
            provider=provider, task_type=task_type, campaign_id=campaign_id
        )
        checks = (
            ("provider", spend["provider"], self._provider_limits.get(provider)),
            ("task type", spend["taskType"], self._task_limits.get(task_type)),
            (
                "campaign",
                spend["campaign"],
                self._campaign_limits.get(campaign_id, self._default_campaign_limit_usd),
            ),
        )
        for label, used, limit in checks:
            if limit is not None and used + requested_cost_ceiling_usd > float(limit):
                raise BudgetExceededError(f"AI {label} budget exhausted")

    def record_usage(
        self,
        *,
        provider: str,
        task_type: str,
        campaign_id: str,
        request_id: str,
        cost_usd: float,
        total_tokens: int,
    ) -> None:
        self._ledger.record(
            provider=provider,
            task_type=task_type,
            campaign_id=campaign_id,
            request_id=request_id,
            cost_usd=cost_usd,
            total_tokens=total_tokens,
        )
