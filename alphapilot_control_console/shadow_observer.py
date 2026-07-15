from __future__ import annotations

import hashlib
import json
import queue
import threading
from pathlib import Path
from typing import Any, Callable

from .shadow_observation_store import DEFAULT_SHADOW_PATH, ShadowObservationStore


Writer = Callable[..., dict[str, Any]]

_REASON_ZH = {
    "frozen_rules_not_matched": "冻结规则未匹配",
    "insufficient_confirmed_history": "已确认历史 K 线不足",
    "public_market_or_liquidity_gate_failed": "公共行情或流动性检查未通过",
    "signal_sizing_failed": "信号构造检查未通过",
}


def _definition_hash(contract: dict[str, Any]) -> str:
    explicit = str(contract.get("releaseContentHash") or contract.get("contractHash") or "")
    if explicit:
        return explicit
    strategy = contract.get("strategy") if isinstance(contract.get("strategy"), dict) else {}
    canonical = json.dumps(strategy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _feature_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    context = row.get("factorContext") if isinstance(row.get("factorContext"), dict) else {}
    factors = context.get("factors") if isinstance(context.get("factors"), dict) else {}
    result: dict[str, Any] = {}
    for key in sorted(factors)[:32]:
        value = factors[key]
        if value is None or isinstance(value, (str, int, float, bool)):
            result[str(key)] = value
    return result


def _market_regime(row: dict[str, Any]) -> str:
    context = row.get("factorContext") if isinstance(row.get("factorContext"), dict) else {}
    btc = context.get("btcContext") if isinstance(context.get("btcContext"), dict) else {}
    return str(btc.get("regime") or context.get("marketRegime") or "unknown")


def observe_release_scan(
    contract: dict[str, Any],
    scan: dict[str, Any],
    *,
    observed_at: str,
    source_event_hash: str,
    demo_instrument_ids: set[str],
    store: ShadowObservationStore | None = None,
    store_path: Path = DEFAULT_SHADOW_PATH,
) -> dict[str, Any]:
    owned_store = store is None
    target_store = store or ShadowObservationStore(store_path)
    strategy = contract.get("strategy") if isinstance(contract.get("strategy"), dict) else {}
    market = strategy.get("marketDefinition") if isinstance(strategy.get("marketDefinition"), dict) else {}
    policy = strategy.get("forwardSignalPolicy") if isinstance(strategy.get("forwardSignalPolicy"), dict) else {}
    release_id = str(contract.get("demoReleaseId") or "")
    strategy_id = str(contract.get("strategyCandidateId") or "")
    family_id = str(strategy.get("familyKey") or strategy_id)
    timeframe = str(market.get("timeframe") or "unknown")
    direction = str(policy.get("direction") or "unknown")
    hashes = {
        "definitionHash": _definition_hash(contract),
        "sourceEventHash": source_event_hash,
    }
    rows: list[dict[str, Any]] = []
    for signal in scan.get("signals", []):
        if not isinstance(signal, dict):
            continue
        symbol = str(signal.get("instId") or "")
        demo_included = symbol in demo_instrument_ids
        rows.append(
            {
                "releaseId": release_id,
                "strategyId": strategy_id,
                "strategyFamilyId": family_id,
                "timestamp": observed_at,
                "symbol": symbol,
                "direction": direction,
                "timeframe": timeframe,
                "signalMatched": True,
                "passOrReject": "pass",
                "reasonZh": "冻结规则匹配",
                "featureSnapshot": _feature_snapshot(signal),
                "marketRegime": _market_regime(signal),
                "publicUniverseIncluded": True,
                "demoUniverseIncluded": demo_included,
                "liquidityPassed": True,
                "dataQualityPassed": True,
                "riskGatePassed": None,
                "wouldAttemptDemoOrder": demo_included,
                "sourceDataHashes": hashes,
            }
        )
    for rejected in scan.get("rejections", []):
        if not isinstance(rejected, dict):
            continue
        symbol = str(rejected.get("instId") or "")
        reason = str(rejected.get("reason") or "unknown")
        rows.append(
            {
                "releaseId": release_id,
                "strategyId": strategy_id,
                "strategyFamilyId": family_id,
                "timestamp": observed_at,
                "symbol": symbol,
                "direction": direction,
                "timeframe": timeframe,
                "signalMatched": False,
                "passOrReject": "reject",
                "reasonZh": _REASON_ZH.get(reason, reason),
                "featureSnapshot": {},
                "marketRegime": "unknown",
                "publicUniverseIncluded": True,
                "demoUniverseIncluded": symbol in demo_instrument_ids,
                "liquidityPassed": rejected.get("liquidityPassed"),
                "dataQualityPassed": reason not in {"insufficient_confirmed_history"},
                "riskGatePassed": None,
                "wouldAttemptDemoOrder": False,
                "sourceDataHashes": hashes,
            }
        )
    try:
        written = [target_store.append(row) for row in rows]
        return {"status": "completed", "writtenCount": len(written)}
    finally:
        if owned_store:
            target_store.close()


def record_shadow_scan_nonblocking(
    contract: dict[str, Any],
    scan: dict[str, Any],
    *,
    observed_at: str,
    source_event_hash: str,
    demo_instrument_ids: set[str],
    writer: Writer = observe_release_scan,
    timeout_seconds: float = 0.05,
) -> dict[str, Any]:
    results: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)

    def run() -> None:
        try:
            results.put_nowait(
                (
                    "completed",
                    writer(
                        contract,
                        scan,
                        observed_at=observed_at,
                        source_event_hash=source_event_hash,
                        demo_instrument_ids=demo_instrument_ids,
                    ),
                )
            )
        except Exception as error:  # warning-only diagnostic boundary
            results.put_nowait(("warning", type(error).__name__))

    thread = threading.Thread(target=run, name="alphapilot-shadow-observer", daemon=True)
    thread.start()
    thread.join(timeout=max(0.001, timeout_seconds))
    if thread.is_alive():
        return {"status": "warning", "reason": "shadow_timeout", "executionUnaffected": True}
    try:
        status, detail = results.get_nowait()
    except queue.Empty:  # pragma: no cover
        return {"status": "warning", "reason": "shadow_no_result", "executionUnaffected": True}
    return {
        "status": status,
        "detail": detail,
        "executionUnaffected": True,
    }
