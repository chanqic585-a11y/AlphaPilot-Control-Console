"""Isolated strategy-validation Demo execution and reconciliation service."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from .strategy_validation_demo_store import StrategyValidationDemoStore
from .strategy_validation_hashing import stable_hash
from .strategy_validation_risk_gateway import StrategyValidationRiskGateway


SignalMatcher = Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any] | None]


def _default_matcher(_release: Mapping[str, Any], _universe: Mapping[str, Any]) -> None:
    return None


def _accepted_order_id(response: Mapping[str, Any]) -> str | None:
    if str(response.get("code") or "") not in {"0", ""}:
        return None
    rows = response.get("data")
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], Mapping):
        return None
    row = rows[0]
    if str(row.get("sCode") or "0") != "0":
        return None
    value = str(row.get("ordId") or "").strip()
    return value or None


def run_strategy_validation_cycle(
    *,
    approvedReleases: Sequence[Mapping[str, Any]],
    universe: Mapping[str, Any],
    client: Any,
    store: StrategyValidationDemoStore,
    riskGateway: StrategyValidationRiskGateway,
    admission: Any,
    matcher: SignalMatcher = _default_matcher,
) -> dict[str, Any]:
    fresh = bool(universe.get("fresh"))
    eligible_symbols = set(universe.get("eligibleInstrumentIds") or [])
    summary = {
        "evaluatedReleaseCount": 0,
        "matchedSignalCount": 0,
        "riskRejectedCount": 0,
        "duplicateEventCount": 0,
        "exchangeRejectedCount": 0,
        "acceptedOrderCount": 0,
        "createdFillCount": 0,
        "createdPositionCount": 0,
        "engineeringEvidenceCount": 0,
        "shadowEvidenceCount": 0,
    }
    for release in approvedReleases:
        release_id = str(release.get("releaseId") or "")
        decision = admission.evaluate(
            release_id,
            universeFresh=fresh,
            riskPaused=riskGateway.store.state()["paused"],
        )
        if not decision.get("eligible"):
            continue
        summary["evaluatedReleaseCount"] += 1
        signal = matcher(release, universe)
        if not signal:
            continue
        summary["matchedSignalCount"] += 1
        event_hash = str(signal.get("marketEventHash") or "")
        symbol = str(signal.get("symbol") or "")
        if not event_hash:
            summary["exchangeRejectedCount"] += 1
            continue
        if store.has_market_event(release_id, event_hash):
            summary["duplicateEventCount"] += 1
            continue
        if symbol not in eligible_symbols:
            summary["exchangeRejectedCount"] += 1
            continue
        risk = riskGateway.evaluate(
            releaseId=release_id,
            profile=release["riskProfile"],
            requestedRiskR=float(signal.get("requestedRiskR") or 0),
            snapshot=signal.get("riskSnapshot") or {},
        )
        if not risk["passed"]:
            summary["riskRejectedCount"] += 1
            continue
        client_order_id = stable_hash(
            {"releaseId": release_id, "marketEventHash": event_hash}, "svdemo"
        )[:32]
        store.record_order_intent(
            releaseId=release_id,
            marketEventHash=event_hash,
            clientOrderId=client_order_id,
            symbol=symbol,
            side=str(signal["side"]),
            quantity=float(signal["quantity"]),
            currency=str(signal.get("currency") or "USDT"),
            referencePrice=float(signal["referencePrice"]),
            stopPrice=float(signal["stopPrice"]),
            targetPrice=float(signal["targetPrice"]),
        )
        order_payload = {
            "instId": symbol,
            "tdMode": "isolated",
            "side": signal["side"],
            "ordType": "market",
            "sz": str(signal["quantity"]),
            "clOrdId": client_order_id,
        }
        response = client.place_order(order_payload)
        exchange_order_id = _accepted_order_id(response)
        if not exchange_order_id:
            summary["exchangeRejectedCount"] += 1
            continue
        store.record_exchange_order(
            clientOrderId=client_order_id,
            exchangeOrderId=exchange_order_id,
            status="accepted",
        )
        summary["acceptedOrderCount"] += 1
    return summary


def reconcile_strategy_validation_demo(
    *, client: Any, store: StrategyValidationDemoStore
) -> dict[str, Any]:
    """Read exchange state without inventing fills or positions."""

    positions_response = client.get_positions() if hasattr(client, "get_positions") else {"data": []}
    rows = positions_response.get("data") if isinstance(positions_response, Mapping) else []
    positions = rows if isinstance(rows, list) else []
    return {
        "status": "read_only_reconciliation_completed",
        "exchangePositionCount": len(positions),
        "ledger": store.summary(),
        "fillsCreated": 0,
        "closedTradesCreated": 0,
    }

def recover_strategy_validation_runtime(
    *, client: Any, store: StrategyValidationDemoStore
) -> dict[str, Any]:
    reconciliation = reconcile_strategy_validation_demo(client=client, store=store)
    return {
        "status": "recovered",
        "reconciliation": reconciliation,
        "duplicateOrdersCreated": 0,
        "parameterChanges": 0,
    }
