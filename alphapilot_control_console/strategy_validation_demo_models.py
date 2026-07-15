"""Typed records for the isolated strategy-validation Demo ledger."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyValidationOrderIntent:
    releaseId: str
    marketEventHash: str
    clientOrderId: str
    symbol: str
    side: str
    quantity: float
    currency: str
    referencePrice: float
    stopPrice: float
    targetPrice: float


@dataclass(frozen=True)
class StrategyValidationClosedTrade:
    closedTradeId: str
    releaseId: str
    marketEventHash: str
    entryFillId: str
    exitFillId: str
    netPnl: float
    netR: float
