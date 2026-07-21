"""One shared adaptive-learning core with thin Demo and Live adapters."""

from __future__ import annotations

import math
import time
from typing import Any, Mapping

from .adaptive_learning_contracts import LIVE_DECISION_MODES, stable_hash
from .adaptive_learning_store import AdaptiveLearningStore
from .point_in_time_contract import validate_point_in_time


class AdaptiveLearningCore:
    def __init__(
        self,
        *,
        factor_registry: Mapping[str, Any],
        feature_schema: Mapping[str, Any],
        model_policy: Mapping[str, Any],
        store: AdaptiveLearningStore,
    ) -> None:
        if feature_schema.get("factorRegistryHash") != factor_registry.get("factorRegistryHash"):
            raise ValueError("Adaptive feature schema does not bind the Factor Registry")
        if model_policy.get("featureSchemaHash") != feature_schema.get("featureSchemaHash"):
            raise ValueError("Adaptive Model Policy does not bind the Feature Schema")
        if model_policy.get("factorRegistryHash") != factor_registry.get("factorRegistryHash"):
            raise ValueError("Adaptive Model Policy does not bind the Factor Registry")
        self.factor_registry = dict(factor_registry)
        self.feature_schema = dict(feature_schema)
        self.model_policy = dict(model_policy)
        self.store = store
        self._definitions = {
            str(row["factorId"]): dict(row)
            for row in factor_registry.get("factors", [])
            if isinstance(row, dict) and row.get("pointInTimeReady") is True
        }

    def observe_signal(
        self,
        *,
        environment: str,
        release_id: str,
        release_hash: str,
        strategy_candidate_id: str,
        risk_overlay_hash: str,
        symbol: str,
        timeframe: str,
        signal_at: str,
        observed_at: str,
        available_at: str,
        source_event_hash: str,
        universe_snapshot_hash: str,
        factors: Mapping[str, Any],
        rule_decision: str = "signal_matched",
    ) -> dict[str, Any]:
        validate_point_in_time(
            source_timestamp=signal_at,
            available_at=available_at,
            decision_at=observed_at,
        )
        started = time.perf_counter()
        values: dict[str, float | int | bool | None] = {}
        factor_snapshots: list[dict[str, Any]] = []
        for factor_id in sorted(set(factors) & set(self._definitions)):
            value = factors[factor_id]
            if isinstance(value, float) and not math.isfinite(value):
                value = None
            if value is not None and not isinstance(value, (int, float, bool)):
                continue
            definition = self._definitions[factor_id]
            values[factor_id] = value
            factor_snapshots.append(
                {
                    "factorId": factor_id,
                    "value": value,
                    "availableAt": available_at,
                    "definitionHash": definition["definitionHash"],
                    "implementationHash": definition["implementationHash"],
                    "pointInTimeReady": True,
                }
            )
        missing_factor_ids = sorted(set(self._definitions) - set(values))
        feature_vector_hash = stable_hash(
            {
                "factorRegistryHash": self.factor_registry["factorRegistryHash"],
                "featureSchemaHash": self.feature_schema["featureSchemaHash"],
                "values": values,
                "missingFactorIds": missing_factor_ids,
                "factorImplementations": [
                    {
                        "factorId": row["factorId"],
                        "definitionHash": row["definitionHash"],
                        "implementationHash": row["implementationHash"],
                    }
                    for row in factor_snapshots
                ],
            },
            prefix="feature_vector",
        )
        snapshot = self.store.append_feature_snapshot(
            {
                "environment": environment,
                "releaseId": release_id,
                "releaseHash": release_hash,
                "strategyCandidateId": strategy_candidate_id,
                "riskOverlayHash": risk_overlay_hash,
                "symbol": symbol,
                "timeframe": timeframe,
                "signalAt": signal_at,
                "observedAt": observed_at,
                "availableAt": available_at,
                "sourceEventHash": source_event_hash,
                "universeSnapshotHash": universe_snapshot_hash,
                "factorRegistryHash": self.factor_registry["factorRegistryHash"],
                "featureSchemaHash": self.feature_schema["featureSchemaHash"],
                "featureVectorHash": feature_vector_hash,
                "values": values,
                "factorSnapshots": factor_snapshots,
                "missingFactorIds": missing_factor_ids,
            }
        )
        latency_ms = (time.perf_counter() - started) * 1000.0
        decision = self.store.append_model_decision(
            {
                "featureSnapshotId": snapshot["featureSnapshotId"],
                "environment": environment,
                "modelHash": self.model_policy["modelHash"],
                "modelPolicyHash": self.model_policy["modelPolicyHash"],
                "modelMode": self.model_policy["modelMode"],
                "modelScore": 0.5,
                "calibratedProbability": 0.5,
                "modelSuggestedAction": "observe",
                "modelRank": None,
                "modelVeto": False,
                "modelRiskSuggestion": None,
                "modelLatencyMs": round(latency_ms, 6),
                "ruleDecision": rule_decision,
                "decisionAuthority": "none" if self.model_policy["modelMode"] == "observer" else "release_bound",
            }
        )
        return {
            "featureSnapshotId": snapshot["featureSnapshotId"],
            "featureVectorHash": snapshot["featureVectorHash"],
            "modelDecisionId": decision["modelDecisionId"],
            "modelMode": self.model_policy["modelMode"],
            "modelScore": decision["modelScore"],
            "modelLatencyMs": decision["modelLatencyMs"],
        }

    def observe_scan(
        self,
        contract: Mapping[str, Any],
        scan: Mapping[str, Any],
        *,
        environment: str,
        observed_at: str,
        source_event_hash: str,
        universe_snapshot_hash: str,
    ) -> dict[str, Any]:
        strategy = contract.get("strategy") if isinstance(contract.get("strategy"), dict) else {}
        market = strategy.get("marketDefinition") if isinstance(strategy.get("marketDefinition"), dict) else {}
        rows = []
        for signal in scan.get("signals", []):
            if not isinstance(signal, dict):
                continue
            factor_context = signal.get("factorContext") if isinstance(signal.get("factorContext"), dict) else {}
            factors = factor_context.get("factors") if isinstance(factor_context.get("factors"), dict) else {}
            rows.append(
                self.observe_signal(
                    environment=environment,
                    release_id=str(contract.get("demoReleaseId") or contract.get("liveReleaseId") or ""),
                    release_hash=str(contract.get("releaseContentHash") or contract.get("liveReleaseHash") or ""),
                    strategy_candidate_id=str(contract.get("strategyCandidateId") or signal.get("candidateId") or ""),
                    risk_overlay_hash=str(contract.get("riskOverlayHash") or contract.get("riskProfileHash") or ""),
                    symbol=str(signal.get("instId") or ""),
                    timeframe=str(market.get("timeframe") or scan.get("timeframe") or "unknown"),
                    signal_at=str(signal.get("signalTime") or observed_at),
                    observed_at=observed_at,
                    available_at=str(signal.get("signalTime") or observed_at),
                    source_event_hash=source_event_hash,
                    universe_snapshot_hash=universe_snapshot_hash,
                    factors=factors,
                )
            )
        return {
            "status": "completed",
            "environment": environment,
            "modelMode": self.model_policy["modelMode"],
            "featureSnapshotCount": len(rows),
            "modelDecisionCount": len(rows),
            "records": rows,
            "executionUnaffected": self.model_policy["modelMode"] == "observer",
        }

    def record_closed_trade(
        self,
        outcome: Mapping[str, Any],
        *,
        feature_snapshot_id: str,
        model_decision_id: str,
        market_state: str,
        funding: float | None,
        mfe: float | None,
        mae: float | None,
        manually_intervened: bool,
    ) -> dict[str, Any]:
        if outcome.get("status") != "closed":
            raise ValueError("Only closed reconciled trades can become learning samples")
        if any(bool(outcome.get(key)) for key in ("engineeringOnly", "fixture", "shadowVirtual")):
            raise PermissionError("Non-strategy outcomes cannot become learning samples")
        trade = outcome.get("trade") if isinstance(outcome.get("trade"), dict) else {}
        decision = self.store.get_model_decision(model_decision_id)
        return self.store.append_learning_sample(
            {
                "sourceEnvironment": str(outcome.get("environment") or ""),
                "sourceEntityId": str(outcome.get("sourceEntityId") or ""),
                "releaseId": str(outcome.get("releaseId") or ""),
                "releaseHash": str(outcome.get("releaseHash") or ""),
                "modelHash": str(decision.get("modelHash") or ""),
                "modelPolicyHash": str(decision.get("modelPolicyHash") or ""),
                "factorRegistryHash": self.factor_registry["factorRegistryHash"],
                "featureSchemaHash": self.feature_schema["featureSchemaHash"],
                "riskOverlayHash": str(outcome.get("riskProfileHash") or outcome.get("riskOverlayHash") or ""),
                "universeSnapshotHash": str(
                    self.store.get_feature_snapshot(feature_snapshot_id).get("universeSnapshotHash") or ""
                ),
                "featureSnapshotId": feature_snapshot_id,
                "modelDecisionId": model_decision_id,
                "strategyCandidateId": str(outcome.get("strategyCandidateId") or ""),
                "instrumentId": str(outcome.get("instrumentId") or ""),
                "timeframe": str(outcome.get("timeframe") or ""),
                "direction": str(outcome.get("direction") or ""),
                "decisionAt": str(outcome.get("decisionAt") or ""),
                "entryAt": str(outcome.get("entryAt") or ""),
                "exitAt": str(outcome.get("exitAt") or ""),
                "modelScore": decision.get("modelScore"),
                "modelSuggestedAction": decision.get("modelSuggestedAction"),
                "ruleDecision": decision.get("ruleDecision"),
                "feePaid": float(trade["feePaid"]) if trade.get("feePaid") is not None else None,
                "funding": float(funding) if funding is not None else None,
                "slippagePaid": float(trade["slippagePaid"]) if trade.get("slippagePaid") is not None else None,
                "mfe": float(mfe) if mfe is not None else None,
                "mae": float(mae) if mae is not None else None,
                "exitReason": str(trade.get("exitReason") or ""),
                "netR": float(trade["netR"]) if trade.get("netR") is not None else None,
                "accountPnl": float(trade["netPnl"]) if trade.get("netPnl") is not None else None,
                "marketState": str(market_state),
                "metricAvailability": {
                    "feePaid": trade.get("feePaid") is not None,
                    "funding": funding is not None,
                    "slippagePaid": trade.get("slippagePaid") is not None,
                    "mfe": mfe is not None,
                    "mae": mae is not None,
                    "netR": trade.get("netR") is not None,
                    "accountPnl": trade.get("netPnl") is not None,
                },
                "manuallyIntervened": bool(manually_intervened),
                "engineeringOnly": False,
                "fixture": False,
                "shadowVirtual": False,
            }
        )


class DemoAdaptiveRuntimeAdapter:
    def __init__(self, core: AdaptiveLearningCore) -> None:
        self.core = core

    def observe_scan(self, contract: Mapping[str, Any], scan: Mapping[str, Any], **context: Any) -> dict[str, Any]:
        return self.core.observe_scan(contract, scan, environment="okx_demo", **context)

    def record_closed_outcome(self, outcome: Mapping[str, Any], *, signal: Mapping[str, Any]) -> dict[str, Any]:
        observation = self.core.store.find_observation(
            environment="okx_demo",
            release_id=str(outcome.get("releaseId") or ""),
            symbol=str(signal.get("instId") or outcome.get("instrumentId") or ""),
            signal_at=str(signal.get("signalTime") or outcome.get("decisionAt") or ""),
        )
        return self.core.record_closed_trade(
            outcome,
            feature_snapshot_id=observation["featureSnapshot"]["featureSnapshotId"],
            model_decision_id=observation["modelDecision"]["modelDecisionId"],
            market_state=str(outcome.get("marketState") or "unknown"),
            funding=_optional_number(outcome.get("funding")),
            mfe=_optional_number(outcome.get("mfe")),
            mae=_optional_number(outcome.get("mae")),
            manually_intervened=bool(outcome.get("manuallyIntervened", False)),
        )


class LiveAdaptiveRuntimeAdapter:
    def __init__(self, core: AdaptiveLearningCore) -> None:
        self.core = core

    def validate_model_mode(self) -> None:
        mode = str(self.core.model_policy.get("modelMode") or "")
        if mode not in LIVE_DECISION_MODES:
            raise PermissionError("Live requires rank_only, veto_only, or meta_label model mode")

    def observe_scan(self, contract: Mapping[str, Any], scan: Mapping[str, Any], **context: Any) -> dict[str, Any]:
        self.validate_model_mode()
        return self.core.observe_scan(contract, scan, environment="live", **context)

    def record_closed_outcome(self, outcome: Mapping[str, Any], *, signal: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_model_mode()
        observation = self.core.store.find_observation(
            environment="live",
            release_id=str(outcome.get("releaseId") or ""),
            symbol=str(signal.get("instId") or outcome.get("instrumentId") or ""),
            signal_at=str(signal.get("signalTime") or outcome.get("decisionAt") or ""),
        )
        return self.core.record_closed_trade(
            outcome,
            feature_snapshot_id=observation["featureSnapshot"]["featureSnapshotId"],
            model_decision_id=observation["modelDecision"]["modelDecisionId"],
            market_state=str(outcome.get("marketState") or "unknown"),
            funding=_optional_number(outcome.get("funding")),
            mfe=_optional_number(outcome.get("mfe")),
            mae=_optional_number(outcome.get("mae")),
            manually_intervened=bool(outcome.get("manuallyIntervened", False)),
        )


def _optional_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    number = float(value)
    return number if math.isfinite(number) else None
