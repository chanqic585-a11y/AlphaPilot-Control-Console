"""Hard no-order boundary for V63 Track A."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoOrderShadowPolicy:
    mode: str = "shadow_no_order"
    orderAllowed: bool = False
    demoArmAllowed: bool = False
    liveArmAllowed: bool = False
    withdrawAllowed: bool = False
    positionMutationAllowed: bool = False

    def assert_order_allowed(self) -> None:
        raise PermissionError("shadow_no_order:order_capability_disabled")

    def to_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": "alphapilot_v63_no_order_shadow_policy_v1",
            "mode": self.mode,
            "orderAllowed": self.orderAllowed,
            "demoArmAllowed": self.demoArmAllowed,
            "liveArmAllowed": self.liveArmAllowed,
            "withdrawAllowed": self.withdrawAllowed,
            "positionMutationAllowed": self.positionMutationAllowed,
        }
