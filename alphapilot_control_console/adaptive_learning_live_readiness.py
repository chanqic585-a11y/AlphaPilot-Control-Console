"""Compatibility facade for the technical-only adaptive-learning gate."""

from __future__ import annotations

from .adaptive_learning_technical_readiness import (
    REQUIRED_TECHNICAL_EVIDENCE,
    AdaptiveLearningTechnicalReadinessGate,
    resolve_technical_evidence,
)


REQUIRED_EVIDENCE = REQUIRED_TECHNICAL_EVIDENCE
_REQUIRED_EVIDENCE = REQUIRED_EVIDENCE
_resolved_evidence = resolve_technical_evidence


class AdaptiveLearningLiveReadinessGate(AdaptiveLearningTechnicalReadinessGate):
    """Deprecated name retained for callers that have not migrated yet."""
