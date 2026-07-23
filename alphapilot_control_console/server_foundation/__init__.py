"""Local-first, no-order server foundation for AlphaPilot V63.0."""

from .contracts import FOUNDATION_ROLES, FoundationRole, RuntimeMode
from .evidence import build_foundation_evidence, write_foundation_evidence

__all__ = [
    "FOUNDATION_ROLES",
    "FoundationRole",
    "RuntimeMode",
    "build_foundation_evidence",
    "write_foundation_evidence",
]
