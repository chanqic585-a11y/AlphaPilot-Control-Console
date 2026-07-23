from __future__ import annotations


class StrategyFactoryV2Error(ValueError):
    """Raised when deterministic Strategy Factory 2.0 governance rejects work."""


class StrategyFactoryReviewRequired(StrategyFactoryV2Error):
    """Raised when independent AI reviews disagree or cannot both complete."""
