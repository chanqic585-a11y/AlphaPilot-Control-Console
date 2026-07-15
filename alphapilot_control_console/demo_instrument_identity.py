"""Exact canonical identity for OKX Demo USDT perpetual contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


_OKX_PATTERN = re.compile(r"^([A-Z0-9]+)-USDT-SWAP$")
_CCXT_PATTERN = re.compile(r"^([A-Z0-9]+)/USDT:USDT$")


@dataclass(frozen=True)
class CanonicalDemoInstrument:
    instId: str
    baseCurrency: str
    quoteCurrency: str
    settleCurrency: str
    instrumentType: str


def _canonical_from_parts(base: str, quote: str, settle: str, instrument_type: str) -> CanonicalDemoInstrument:
    normalized_base = str(base or "").strip().upper()
    normalized_quote = str(quote or "").strip().upper()
    normalized_settle = str(settle or "").strip().upper()
    normalized_type = str(instrument_type or "").strip().upper()
    if not normalized_base or not re.fullmatch(r"[A-Z0-9]+", normalized_base):
        raise ValueError("Demo instrument base currency is invalid")
    if normalized_quote != "USDT" or normalized_settle != "USDT" or normalized_type != "SWAP":
        raise ValueError("Only exact USDT-settled perpetual Demo instruments are supported")
    return CanonicalDemoInstrument(
        instId=f"{normalized_base}-USDT-SWAP",
        baseCurrency=normalized_base,
        quoteCurrency="USDT",
        settleCurrency="USDT",
        instrumentType="SWAP",
    )


def canonicalize_demo_instrument(value: str | dict[str, Any]) -> CanonicalDemoInstrument:
    """Normalize a public/private OKX or CCXT identifier and fail closed."""

    if isinstance(value, dict):
        inst_id = str(value.get("instId") or "").strip().upper()
        base = str(value.get("baseCcy") or "").strip().upper()
        quote = str(value.get("quoteCcy") or "").strip().upper()
        settle = str(value.get("settleCcy") or "").strip().upper()
        instrument_type = str(value.get("instType") or "").strip().upper()
        if not all((inst_id, settle, instrument_type)):
            raise ValueError("Authenticated Demo instrument identity is incomplete")
        if not base and not quote:
            match = _OKX_PATTERN.fullmatch(inst_id)
            if match is None:
                raise ValueError("Authenticated Demo instrument identifier is invalid")
            base = match.group(1)
            quote = "USDT"
        elif not base or not quote:
            raise ValueError("Authenticated Demo instrument identity is incomplete")
        canonical = _canonical_from_parts(base, quote, settle, instrument_type)
        if inst_id != canonical.instId:
            raise ValueError("Authenticated Demo instrument fields conflict")
        return canonical

    normalized = str(value or "").strip().upper().replace("_", "-")
    okx_match = _OKX_PATTERN.fullmatch(normalized)
    if okx_match:
        return _canonical_from_parts(okx_match.group(1), "USDT", "USDT", "SWAP")
    ccxt_match = _CCXT_PATTERN.fullmatch(normalized)
    if ccxt_match:
        return _canonical_from_parts(ccxt_match.group(1), "USDT", "USDT", "SWAP")
    raise ValueError("Demo instrument must be an exact USDT perpetual contract")


def to_okx_inst_id(value: str | CanonicalDemoInstrument) -> str:
    if isinstance(value, CanonicalDemoInstrument):
        return value.instId
    return canonicalize_demo_instrument(value).instId


def same_demo_contract(left: str | dict[str, Any], right: str | dict[str, Any]) -> bool:
    try:
        return canonicalize_demo_instrument(left) == canonicalize_demo_instrument(right)
    except (TypeError, ValueError):
        return False
