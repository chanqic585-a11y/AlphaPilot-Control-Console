"""Shared public-universe policy for immutable OKX Demo releases."""

from __future__ import annotations

from typing import Any


DEMO_DEEP_SCREENING_LIMIT = 100
DEMO_UNIVERSE_POLICY_VERSION = "okx_full_market_policy_v2_top100"


def build_demo_universe_policy() -> dict[str, Any]:
    """Return a fresh Top100 public-market policy value."""

    return {
        "mode": "okx_usdt_linear_perpetual_full_market",
        "screeningLimit": DEMO_DEEP_SCREENING_LIMIT,
        "ranking": "public_quote_volume_proxy_then_spread",
        "policyVersion": DEMO_UNIVERSE_POLICY_VERSION,
    }
