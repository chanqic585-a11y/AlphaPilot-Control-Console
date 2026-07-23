"""Idempotent no-ticket OKX Demo order lifecycle for immutable releases."""

from __future__ import annotations

import hashlib
import inspect
import json
import time
from datetime import UTC, datetime
from typing import Any
from typing import Callable

from .demo_execution_store import DemoExecutionRecord, DemoExecutionStore
from .demo_risk_envelope import evaluate_demo_order_risk
from .execution_outcome_store import ExecutionOutcomeStore, FormalExecutionOutcome
from .execution_latency_profile import build_execution_latency_profile
from .runtime_identity import RuntimeIdentity, assert_runtime_identity
from .exchange_connectors.okx_demo_private_ws import (
    OkxPrivateWsOrderUnknown,
    OkxPrivateWsUnavailable,
)


_TERMINAL = {"filled", "canceled", "rejected", "mmp_canceled"}
_NON_FATAL_REJECTION_CODES = {"51001"}
_SENSITIVE_KEY_PARTS = ("apikey", "secretkey", "passphrase", "password", "credential", "accesstoken")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _first_order(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data") if isinstance(response.get("data"), list) else []
    return data[0] if data and isinstance(data[0], dict) else {}


def _rejection_code(response: dict[str, Any], order: dict[str, Any]) -> str:
    return str(order.get("sCode") or response.get("code") or "")


def _exchange_timestamp(value: Any) -> str | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric <= 0:
        return None
    if numeric >= 1_000_000_000_000_000:
        numeric /= 1_000_000.0
    elif numeric >= 1_000_000_000_000:
        numeric /= 1_000.0
    try:
        return datetime.fromtimestamp(numeric, tz=UTC).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _accepts_keyword(callable_value: Any, keyword: str) -> bool:
    try:
        parameters = inspect.signature(callable_value).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD or parameter.name == keyword
        for parameter in parameters
    )


def _reject_sensitive_fields(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            compact = str(key).replace("_", "").replace("-", "").lower()
            safe_disabled_marker = child is False or child is None or child == ""
            if any(part in compact for part in _SENSITIVE_KEY_PARTS) and not safe_disabled_marker:
                raise ValueError(f"Credential-like field is forbidden in Demo execution input: {path}.{key}")
            _reject_sensitive_fields(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_sensitive_fields(child, f"{path}[{index}]")


class DemoExecutionEngine:
    def __init__(
        self,
        *,
        client: Any,
        store: DemoExecutionStore,
        outcomeStore: ExecutionOutcomeStore | None = None,
        adaptiveAdapter: Any | None = None,
        clock: Callable[[], datetime] = _utc_now,
        monotonicClock: Callable[[], float] = time.perf_counter,
        orderTransport: Any | None = None,
        latencyProfile: dict[str, Any] | None = None,
        runtimeIdentity: RuntimeIdentity | None = None,
    ):
        self.client = client
        self.store = store
        self.outcomeStore = outcomeStore
        self.adaptiveAdapter = adaptiveAdapter
        self.clock = clock
        self.monotonicClock = monotonicClock
        self.orderTransport = orderTransport
        self.latencyProfile = build_execution_latency_profile(latencyProfile)
        self.runtimeIdentity = runtimeIdentity

    def execute(
        self,
        *,
        contract: dict[str, Any],
        signal: dict[str, Any],
        portfolio: dict[str, Any],
    ) -> DemoExecutionRecord:
        _reject_sensitive_fields(contract, "contract")
        _reject_sensitive_fields(signal, "signal")
        _reject_sensitive_fields(portfolio, "portfolio")
        self._validate_contract(contract)
        expected_identity: dict[str, Any] = {
            "environment": "okx_demo",
            "releaseId": str(contract["demoReleaseId"]),
            "releaseHash": str(contract["releaseContentHash"]),
        }
        binding = contract.get("portfolioRuntimeBinding")
        if isinstance(binding, dict) and str(binding.get("riskOverlayHash") or ""):
            expected_identity["riskOverlayHash"] = str(binding["riskOverlayHash"])
        assert_runtime_identity(self.runtimeIdentity, expected=expected_identity)
        if self.store.get_runtime_flag("killSwitch", False):
            raise RuntimeError("OKX Demo kill switch is active")
        if self.store.get_runtime_flag("paused", False):
            raise RuntimeError("OKX Demo new entries are paused")
        risk = evaluate_demo_order_risk(
            notionalUsdt=float(signal.get("notionalUsdt") or 0),
            leverage=int(signal.get("leverage") or 0),
            riskPercent=float(signal.get("riskPercent") or 0),
            openRiskPercent=float(portfolio.get("openRiskPercent") or 0),
            openPositionCount=int(portfolio.get("openPositionCount") or 0),
            dailyLossPercent=float(portfolio.get("dailyLossPercent") or 0),
            drawdownPercent=float(portfolio.get("drawdownPercent") or 0),
            dataFresh=bool(portfolio.get("dataFresh", True)),
            liquidityPassed=bool(portfolio.get("liquidityPassed", True)),
            envelope=contract.get("riskEnvelope") if isinstance(contract.get("riskEnvelope"), dict) else None,
            availableEquityUsdt=float(
                portfolio.get("availableEquityUsdt")
                or (contract.get("riskEnvelope") or {}).get("initialEquityUsdt")
                or 0
            ),
            strategyId=str(signal.get("candidateId") or ""),
            instrumentId=str(signal.get("instId") or ""),
            side=str(signal.get("side") or ""),
            correlationGroup=str(signal.get("correlationGroup") or ""),
            positionsByStrategy=dict(portfolio.get("positionsByStrategy") or {}),
            positionsBySymbol=dict(portfolio.get("positionsBySymbol") or {}),
            openRiskByStrategy=dict(portfolio.get("openRiskByStrategy") or {}),
            openRiskBySymbol=dict(portfolio.get("openRiskBySymbol") or {}),
            openRiskByDirection=dict(portfolio.get("openRiskByDirection") or {}),
            openRiskByCorrelationGroup=dict(portfolio.get("openRiskByCorrelationGroup") or {}),
            activeStrategyIds=list(portfolio.get("activeStrategyIds") or []),
            canaryLossUsdt=float(portfolio.get("canaryLossUsdt") or 0),
            cooldownActive=bool(portfolio.get("cooldownActive", False)),
        )
        if not risk.passed:
            raise RuntimeError("OKX Demo risk gate blocked: " + ",".join(risk.reasonCodes))
        risk_completed_at = self.clock().astimezone(UTC)
        if not str(signal.get("candidateId") or "").strip() or not str(signal.get("signalTime") or "").strip():
            raise ValueError("Demo signal requires candidateId and signalTime for idempotency")
        idempotency_key = hashlib.sha256(
            _canonical(
                {
                    "release": contract["demoReleaseId"],
                    "releaseHash": contract["releaseContentHash"],
                    "candidate": signal["candidateId"],
                    "instrument": signal.get("instId"),
                    "side": signal.get("side"),
                    "signalTime": signal["signalTime"],
                }
            ).encode("utf-8")
        ).hexdigest()
        cl_ord_id = "ap" + idempotency_key[:28]
        order_payload = self._build_order_payload(signal, cl_ord_id)
        record = self.store.create_intent(
            idempotencyKey=idempotency_key,
            demoReleaseId=str(contract["demoReleaseId"]),
            signal=signal,
            orderPayload=order_payload,
        )
        order_intent_durable_at = self.clock().astimezone(UTC)
        if record.status != "prepared":
            return record
        order_sent_at = self.clock().astimezone(UTC)
        request_expiry_epoch_ms = (
            int(order_sent_at.timestamp() * 1000)
            + int(self.latencyProfile["orderRequestExpiryMs"])
        )
        transport_mode = "rest"
        fallback_reason: str | None = None
        monotonic_started = self.monotonicClock()
        try:
            response, transport_mode, fallback_reason = self._place_order(
                order_payload,
                request_expiry_epoch_ms=request_expiry_epoch_ms,
            )
            response_received_at = self.clock().astimezone(UTC)
            gateway_elapsed_ms = round(
                max(0.0, self.monotonicClock() - monotonic_started) * 1000.0,
                3,
            )
            order = _first_order(response)
            accepted = str(response.get("code")) == "0" and str(order.get("sCode", "0")) == "0"
            status = "submitted" if accepted else "rejected"
            latency_audit = signal.get("latencyAudit") if isinstance(signal.get("latencyAudit"), dict) else {}
            exchange_created_at = (
                _exchange_timestamp(order.get("ts"))
                or _exchange_timestamp(response.get("ts"))
                or response_received_at.isoformat()
            )
            first_fill_at = _exchange_timestamp(order.get("fillTime"))
            updated = self.store.update_record(
                record.recordId,
                status=status,
                exchangeOrderId=str(order.get("ordId") or "") or None,
                exchangeResponse={
                    **response,
                    "_alphaPilotTiming": {
                        "orderSentAt": order_sent_at.isoformat(),
                        "exchangeResponseReceivedAt": response_received_at.isoformat(),
                        "barCloseExchangeTs": latency_audit.get("barCloseExchangeTs") or latency_audit.get("closeReceivedAt"),
                        "marketEventReceivedTs": latency_audit.get("marketEventReceivedTs") or latency_audit.get("closeReceivedAt"),
                        "signalCompletedTs": latency_audit.get("signalCompletedTs") or latency_audit.get("orderReadyAt"),
                        "riskCompletedTs": risk_completed_at.isoformat(),
                        "orderIntentDurableTs": order_intent_durable_at.isoformat(),
                        "orderSendTs": order_sent_at.isoformat(),
                        "gatewayInTime": _exchange_timestamp(response.get("inTime")) or order_sent_at.isoformat(),
                        "gatewayOutTime": _exchange_timestamp(response.get("outTime")) or response_received_at.isoformat(),
                        "exchangeOrderCreatedTs": exchange_created_at,
                        "firstFillTs": first_fill_at,
                        "finalFillTs": first_fill_at if status == "filled" else None,
                        "gatewayRoundTripMonotonicMs": gateway_elapsed_ms,
                        "orderTransportMode": transport_mode,
                        "orderTransportFallbackReason": fallback_reason,
                        "orderRequestExpiryEpochMs": request_expiry_epoch_ms,
                        "executionLatencyProfileVersion": self.latencyProfile["executionLatencyProfileVersion"],
                        "executionLatencyProfileHash": self.latencyProfile["executionLatencyProfileHash"],
                    },
                },
            )
            if not accepted:
                rejection_code = _rejection_code(response, order)
                if rejection_code not in _NON_FATAL_REJECTION_CODES:
                    self.pause("order_rejected")
            return updated
        except Exception as error:
            response_received_at = self.clock().astimezone(UTC)
            self.store.update_record(
                record.recordId,
                status="unknown",
                exchangeResponse={
                    "errorType": type(error).__name__,
                    "message": "Demo order state is unknown",
                    "_alphaPilotTiming": {
                        "orderSentAt": order_sent_at.isoformat(),
                        "exchangeResponseReceivedAt": response_received_at.isoformat(),
                        "riskCompletedTs": risk_completed_at.isoformat(),
                        "orderIntentDurableTs": order_intent_durable_at.isoformat(),
                        "orderSendTs": order_sent_at.isoformat(),
                        "orderTransportMode": transport_mode,
                        "orderTransportFallbackReason": fallback_reason,
                        "orderRequestExpiryEpochMs": request_expiry_epoch_ms,
                        "executionLatencyProfileVersion": self.latencyProfile["executionLatencyProfileVersion"],
                        "executionLatencyProfileHash": self.latencyProfile["executionLatencyProfileHash"],
                    },
                },
            )
            self.pause("order_state_unknown")
            raise

    def _place_order(
        self,
        payload: dict[str, Any],
        *,
        request_expiry_epoch_ms: int,
    ) -> tuple[dict[str, Any], str, str | None]:
        mode = str(self.latencyProfile["orderTransportMode"])
        if mode in {"auto", "websocket"}:
            transport = self.orderTransport
            if transport is not None and bool(transport.is_order_ready()):
                try:
                    return (
                        transport.place_order(
                            payload,
                            timeoutSeconds=(
                                int(self.latencyProfile["exchangeAckTimeoutMs"]) / 1000.0
                            ),
                        ),
                        "websocket",
                        None,
                    )
                except OkxPrivateWsUnavailable:
                    if mode == "websocket":
                        raise
                    fallback_reason = "private_ws_unavailable_before_send"
            elif mode == "websocket":
                raise OkxPrivateWsUnavailable("private_ws_order_channel_not_ready")
            else:
                fallback_reason = (
                    "private_ws_not_configured"
                    if transport is None
                    else "private_ws_not_ready"
                )
        else:
            fallback_reason = None
        place_order = self.client.place_order
        if _accepts_keyword(place_order, "expireAtEpochMs"):
            response = place_order(
                payload,
                expireAtEpochMs=request_expiry_epoch_ms,
            )
        else:
            response = place_order(payload)
        return response, "rest", fallback_reason

    def reconcile(self, recordId: str) -> DemoExecutionRecord:
        record = self.store.get_record(recordId)
        if record.status in _TERMINAL:
            return record
        response = self.client.get_order(
            instId=str(record.orderPayload["instId"]),
            ordId=record.exchangeOrderId,
            clOrdId=str(record.orderPayload.get("clOrdId") or "") or None,
        )
        order = _first_order(response)
        state = str(order.get("state") or "unknown")
        if str(response.get("code")) != "0" or state == "unknown":
            self.pause("order_query_unknown")
            state = "unknown"
        previous_timing = (
            record.exchangeResponse.get("_alphaPilotTiming")
            if isinstance(record.exchangeResponse, dict)
            and isinstance(record.exchangeResponse.get("_alphaPilotTiming"), dict)
            else {}
        )
        reconciliation_at = self.clock().astimezone(UTC).isoformat()
        fill_at = _exchange_timestamp(order.get("fillTime"))
        return self.store.update_record(
            recordId,
            status=state,
            exchangeOrderId=str(order.get("ordId") or record.exchangeOrderId or "") or None,
            exchangeResponse={
                **response,
                "_alphaPilotTiming": {
                    **previous_timing,
                    "firstFillTs": previous_timing.get("firstFillTs") or fill_at,
                    "finalFillTs": fill_at if state == "filled" else previous_timing.get("finalFillTs"),
                    "reconciliationCompletedTs": reconciliation_at,
                },
            },
        )

    def recover_open_records(self) -> list[DemoExecutionRecord]:
        recoverable = self.store.list_records({"prepared", "submitted", "live", "partially_filled", "unknown"})
        recovered: list[DemoExecutionRecord] = []
        for record in recoverable:
            if record.status == "prepared":
                self.pause("prepared_intent_requires_reconciliation")
                recovered.append(record)
                continue
            recovered.append(self.reconcile(record.recordId))
        return recovered

    def pause(self, reason: str) -> None:
        self.store.set_runtime_flag("paused", True)
        self.store.append_event(None, "demo_paused", {"reason": reason})

    def resume(self) -> None:
        if self.store.get_runtime_flag("killSwitch", False):
            raise RuntimeError("Kill switch must be cleared by a separate reviewed operation")
        self.store.set_runtime_flag("paused", False)
        self.store.append_event(None, "demo_resumed", {})

    def activate_kill_switch(self, reason: str) -> dict[str, Any]:
        self.store.set_runtime_flag("killSwitch", True)
        self.store.set_runtime_flag("paused", True)
        response = self.client.cancel_all_after(10)
        self.store.append_event(None, "kill_switch_activated", {"reason": reason, "cancelAllAfter": response})
        return response

    def record_closed_outcome(
        self,
        *,
        recordId: str,
        contract: dict[str, Any],
        dataSnapshotId: str,
        closeEvidence: dict[str, Any],
    ) -> FormalExecutionOutcome:
        if self.outcomeStore is None:
            raise RuntimeError("Formal execution outcome store is not configured")
        self._validate_contract(contract)
        record = self.store.get_record(recordId)
        if record.status != "filled":
            raise RuntimeError("Demo entry must be filled before a closed outcome can be recorded")
        if record.demoReleaseId != str(contract["demoReleaseId"]):
            raise PermissionError("Demo execution record does not match the release contract")
        expected_direction = "long" if str(record.signal.get("side") or "").lower() in {"buy", "long"} else "short"
        if str(closeEvidence.get("direction") or "") != expected_direction:
            raise ValueError("Demo closed outcome direction does not match the opening execution")
        outcome = self.outcomeStore.record_closed({
            **closeEvidence,
            "environment": "okx_demo",
            "sourceRecordId": record.recordId,
            "releaseId": record.demoReleaseId,
            "releaseHash": str(contract["releaseContentHash"]),
            "strategyCandidateId": str(record.signal.get("candidateId") or ""),
            "dataSnapshotId": str(dataSnapshotId),
            "instrumentId": str(record.orderPayload.get("instId") or ""),
            "decisionAt": str(record.signal.get("signalTime") or ""),
        })
        if self.adaptiveAdapter is not None:
            self.adaptiveAdapter.record_closed_outcome(outcome.outcome, signal=record.signal)
        return outcome

    @staticmethod
    def _validate_contract(contract: dict[str, Any]) -> None:
        boundary = contract.get("executionBoundary") if isinstance(contract.get("executionBoundary"), dict) else {}
        if contract.get("schemaVersion") != "alphapilot_control_console_demo_v1":
            raise ValueError("Unsupported Demo release contract")
        if contract.get("releaseMode") == "experimental_override":
            raise PermissionError("legacy experimental override cannot execute")
        if contract.get("status") not in {"demo_eligible", "demo_active"}:
            raise ValueError("Demo release is not eligible")
        if not contract.get("demoReleaseId") or not contract.get("releaseContentHash"):
            raise ValueError("Demo release identity is incomplete")
        if boundary.get("environment") != "okx_demo_only":
            raise PermissionError("Release is not bound to OKX Demo")
        if boundary.get("automaticDemoExecutionAllowed") is not True:
            raise PermissionError("Automatic Demo execution is not enabled by the release")
        if boundary.get("liveExecutionAllowed") is not False or boundary.get("withdrawAllowed") is not False:
            raise PermissionError("Live or withdraw capability is forbidden")

    @staticmethod
    def _build_order_payload(signal: dict[str, Any], cl_ord_id: str) -> dict[str, Any]:
        required = ("instId", "side", "tdMode", "ordType", "sz")
        missing = [key for key in required if not str(signal.get(key, "")).strip()]
        if missing:
            raise ValueError("Demo signal is incomplete: " + ",".join(missing))
        payload = {
            "instId": str(signal["instId"]),
            "side": str(signal["side"]),
            "posSide": str(signal.get("posSide") or "net"),
            "tdMode": str(signal["tdMode"]),
            "ordType": str(signal["ordType"]),
            "sz": str(signal["sz"]),
            "clOrdId": cl_ord_id,
            "tag": "alphapilot",
        }
        if signal.get("px") is not None:
            payload["px"] = str(signal["px"])
        if signal.get("takeProfitPrice") is not None or signal.get("stopLossPrice") is not None:
            attached: dict[str, str] = {}
            if signal.get("takeProfitPrice") is not None:
                attached.update({"tpTriggerPx": str(signal["takeProfitPrice"]), "tpOrdPx": "-1", "tpTriggerPxType": "mark"})
            if signal.get("stopLossPrice") is not None:
                attached.update({"slTriggerPx": str(signal["stopLossPrice"]), "slOrdPx": "-1", "slTriggerPxType": "mark"})
            payload["attachAlgoOrds"] = [attached]
        return payload
