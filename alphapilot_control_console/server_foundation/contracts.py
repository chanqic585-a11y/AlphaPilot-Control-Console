"""Stable role and mode contracts for the V63 process boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FoundationRole(str, Enum):
    CONTROL = "control"
    MARKET = "market"
    DEMO = "demo"
    RESEARCH = "research"
    AI = "ai"
    FACTOR = "factor"


FOUNDATION_ROLES = tuple(FoundationRole)


class RuntimeMode(str, Enum):
    SHADOW_NO_ORDER = "shadow_no_order"


@dataclass(frozen=True)
class RoleSecurityPolicy:
    role: FoundationRole
    orderCapabilityEnabled: bool
    exchangePrivateCredentialsAllowed: bool
    aiProviderCredentialsAllowed: bool


ROLE_SECURITY_POLICIES = {
    role: RoleSecurityPolicy(
        role=role,
        orderCapabilityEnabled=False,
        exchangePrivateCredentialsAllowed=False,
        aiProviderCredentialsAllowed=role is FoundationRole.AI,
    )
    for role in FOUNDATION_ROLES
}
