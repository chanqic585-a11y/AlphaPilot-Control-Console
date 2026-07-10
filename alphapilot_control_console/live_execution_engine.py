"""Fail-closed OKX Live Canary order lifecycle for immutable Live releases."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .execution_outcome_store import ExecutionOutcomeStore, FormalExecutionOutcome
from .live_execution_store import LiveExecutionRecord, LiveExecutionStore
from .portfolio_risk import evaluate_portfolio_risk


_TERMINAL = {"filled", "canceled", "rejected", "mmp_canceled"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _first(response: dict[str, Any]) -> dict[str, Any]:
    rows = response.get("data") if isinstance(response.get("data"), list) else []
    return rows[0] if rows and isinstance(rows[0], dict) else {}


class LiveExecutionEngine:
    def __init__(
        self,
        *,
        client: Any,
        store: LiveExecutionStore,
        outcomeStore: ExecutionOutcomeStore | None = None,
    ):
        self.client = client
        self.store = store
        self.outcomeStore = outcomeStore

    def execute(
        self,
        *,
        contract: dict[str, Any],
        activeProfile: dict[str, Any],
        signal: dict[str, Any],
        portfolio: dict[str, Any],
    ) -> LiveExecutionRecord:
        release = self._validate_contract(contract, activeProfile)
        if self.store.get_runtime_flag("killSwitch", True):
            raise RuntimeError("OKX Live kill switch is active")
        if self.store.get_runtime_flag("paused", True):
            raise RuntimeError("OKX Live new entries are paused")
        if portfolio.get("reconciliationMatched") is not True:
            self.pause("private_state_reconciliation_mismatch")
            raise RuntimeError("OKX Live private state reconciliation is required")
        portfolio = self._verify_private_state(portfolio)
        self._validate_signal(signal, release, activeProfile)
        decision = evaluate_portfolio_risk(
            profile=dict(activeProfile.get("profile") or {}),
            intent=signal,
            portfolio=portfolio,
        )
        if not decision.passed:
            raise RuntimeError("OKX Live risk gate blocked: " + ",".join(decision.reasonCodes))

        idempotency_key = hashlib.sha256(
            _canonical({
                "liveReleaseId": contract["liveReleaseId"],
                "liveReleaseHash": contract["liveReleaseHash"],
                "riskProfileId": activeProfile["riskProfileId"],
                "riskProfileHash": activeProfile["contentHash"],
                "strategyCandidateId": signal["candidateId"],
                "instrumentId": signal["instId"],
                "side": signal["side"],
                "signalTime": signal["signalTime"],
            }).encode("utf-8")
        ).hexdigest()
        order_payload = self._build_order_payload(signal, "ap" + idempotency_key[:28])
        record = self.store.create_intent(
            idempotencyKey=idempotency_key,
            liveReleaseId=str(contract["liveReleaseId"]),
            liveReleaseHash=str(contract["liveReleaseHash"]),
            riskProfileId=str(activeProfile["riskProfileId"]),
            riskProfileHash=str(activeProfile["contentHash"]),
            strategyCandidateId=str(signal["candidateId"]),
            instrumentId=str(signal["instId"]),
            signal=signal,
            orderPayload=order_payload,
        )
        if record.status != "prepared":
            return record
        try:
            response = self.client.place_protected_order(order_payload)
            order = _first(response)
            accepted = str(response.get("code")) == "0" and str(order.get("sCode", "0")) == "0"
            updated = self.store.update_record(
                record.recordId,
                status="submitted" if accepted else "rejected",
                exchangeOrderId=str(order.get("ordId") or "") or None,
                exchangeResponse=response,
            )
            if not accepted:
                self.pause("live_order_rejected")
            return updated
        except Exception as error:
            self.store.update_record(
                record.recordId,
                status="unknown",
                exchangeResponse={"errorType": type(error).__name__, "message": "Live order state is unknown"},
            )
            self.pause("live_order_state_unknown")
            raise

    def _verify_private_state(self, portfolio: dict[str, Any]) -> dict[str, Any]:
        balance = self.client.get_balance("USDT")
        positions = self.client.get_positions()
        open_orders = self.client.get_open_orders()
        if any(str(response.get("code") or "") != "0" for response in (balance, positions, open_orders)):
            self.pause("live_private_state_endpoint_failed")
            raise RuntimeError("OKX Live private state endpoint failed")
        position_rows = positions.get("data") if isinstance(positions.get("data"), list) else []
        active_positions = [
            row for row in position_rows
            if isinstance(row, dict) and abs(float(row.get("pos") or 0)) > 0
        ]
        order_rows = open_orders.get("data") if isinstance(open_orders.get("data"), list) else []
        tracked_client_ids = {
            str(row.orderPayload.get("clOrdId") or "")
            for row in self.store.list_records({"prepared", "submitted", "live", "partially_filled", "unknown"})
        }
        untracked_orders = [
            row for row in order_rows
            if isinstance(row, dict) and str(row.get("clOrdId") or "") not in tracked_client_ids
        ]
        if len(active_positions) != int(portfolio.get("openPositionCount") or 0) or untracked_orders:
            self.pause("live_private_state_reconciliation_mismatch")
            raise RuntimeError("OKX Live private state changed before order submission")
        balance_rows = balance.get("data") if isinstance(balance.get("data"), list) else []
        first_balance = balance_rows[0] if balance_rows and isinstance(balance_rows[0], dict) else {}
        details = first_balance.get("details") if isinstance(first_balance.get("details"), list) else []
        usdt = next((row for row in details if isinstance(row, dict) and row.get("ccy") == "USDT"), {})
        actual_equity = float(usdt.get("availEq") or usdt.get("availBal") or first_balance.get("availEq") or 0)
        if actual_equity <= 0:
            self.pause("live_available_equity_unknown")
            raise RuntimeError("OKX Live available equity is unavailable")
        return {**portfolio, "availableEquityUsdt": min(float(portfolio.get("availableEquityUsdt") or 0), actual_equity)}

    def reconcile_record(self, recordId: str) -> LiveExecutionRecord:
        record = self.store.get_record(recordId)
        if record.status in _TERMINAL:
            return record
        response = self.client.get_order(
            instId=record.instrumentId,
            ordId=record.exchangeOrderId,
            clOrdId=str(record.orderPayload.get("clOrdId") or "") or None,
        )
        order = _first(response)
        state = str(order.get("state") or "unknown")
        if str(response.get("code")) != "0" or state == "unknown":
            self.pause("live_order_query_unknown")
            state = "unknown"
        return self.store.update_record(
            recordId,
            status=state,
            exchangeOrderId=str(order.get("ordId") or record.exchangeOrderId or "") or None,
            exchangeResponse=response,
        )

    def recover_open_records(self) -> list[LiveExecutionRecord]:
        recoverable = self.store.list_records({"prepared", "submitted", "live", "partially_filled", "unknown"})
        recovered: list[LiveExecutionRecord] = []
        for record in recoverable:
            if record.status == "prepared":
                self.pause("prepared_live_intent_requires_manual_reconciliation")
                recovered.append(record)
            else:
                recovered.append(self.reconcile_record(record.recordId))
        return recovered

    def pause(self, reason: str) -> None:
        self.store.set_runtime_flag("paused", True)
        self.store.set_runtime_flag("pauseReason", reason)
        self.store.append_event(None, "live_paused", {"reason": reason})

    def activate_kill_switch(self, reason: str) -> dict[str, Any]:
        self.store.set_runtime_flag("killSwitch", True)
        self.pause(reason)
        response = self.client.cancel_all_after(10)
        self.store.append_event(None, "live_kill_switch_activated", {
            "reason": reason,
            "cancelAllAfterCode": str(response.get("code") or ""),
        })
        return response

    def record_closed_outcome(
        self,
        *,
        recordId: str,
        dataSnapshotId: str,
        closeEvidence: dict[str, Any],
    ) -> FormalExecutionOutcome:
        if self.outcomeStore is None:
            raise RuntimeError("Formal execution outcome store is not configured")
        record = self.store.get_record(recordId)
        if record.status != "filled":
            raise RuntimeError("Live entry must be filled before a closed outcome can be recorded")
        expected_direction = "long" if str(record.signal.get("side") or "").lower() in {"buy", "long"} else "short"
        if str(closeEvidence.get("direction") or "") != expected_direction:
            raise ValueError("Live closed outcome direction does not match the opening execution")
        return self.outcomeStore.record_closed({
            **closeEvidence,
            "environment": "live",
            "sourceRecordId": record.recordId,
            "releaseId": record.liveReleaseId,
            "releaseHash": record.liveReleaseHash,
            "riskProfileId": record.riskProfileId,
            "riskProfileHash": record.riskProfileHash,
            "strategyCandidateId": record.strategyCandidateId,
            "dataSnapshotId": str(dataSnapshotId),
            "instrumentId": record.instrumentId,
            "decisionAt": str(record.signal.get("signalTime") or ""),
        })

    @staticmethod
    def _validate_contract(contract: dict[str, Any], active_profile: dict[str, Any]) -> dict[str, Any]:
        if contract.get("schemaVersion") != "alphapilot_live_release_v1":
            raise ValueError("Unsupported Live release export")
        if contract.get("status") != "live_canary_approved":
            raise ValueError("Live release is not Canary-approved")
        release = contract.get("release") if isinstance(contract.get("release"), dict) else {}
        expected_hash = hashlib.sha256(_canonical(release).encode("utf-8")).hexdigest()
        if contract.get("liveReleaseHash") != expected_hash:
            raise ValueError("Live release checksum mismatch")
        boundary = release.get("executionBoundary") if isinstance(release.get("executionBoundary"), dict) else {}
        if boundary.get("environment") != "okx_live_canary_only":
            raise PermissionError("Live release is not bound to OKX Live Canary")
        if boundary.get("mechanicalExecutionAllowed") is not True or boundary.get("withdrawAllowed") is not False:
            raise PermissionError("Live release execution boundary is invalid")
        if release.get("riskProfileId") != active_profile.get("riskProfileId"):
            raise PermissionError("Active Live RiskProfile id mismatch")
        if release.get("riskProfileHash") != active_profile.get("contentHash"):
            raise PermissionError("Active Live RiskProfile checksum mismatch")
        return release

    @staticmethod
    def _validate_signal(signal: dict[str, Any], release: dict[str, Any], active_profile: dict[str, Any]) -> None:
        required = (
            "candidateId", "signalTime", "instId", "side", "tdMode", "ordType", "sz",
            "entryPrice", "takeProfitPrice", "stopLossPrice", "notionalUsdt", "leverage", "riskPercent",
        )
        missing = [key for key in required if signal.get(key) in (None, "")]
        if missing:
            raise ValueError("Live signal is incomplete: " + ",".join(missing))
        if signal["candidateId"] != release.get("strategyCandidateId"):
            raise PermissionError("Live signal candidate does not match release")
        profile = dict(active_profile.get("profile") or {})
        entry = float(signal["entryPrice"])
        take_profit = float(signal["takeProfitPrice"])
        stop_loss = float(signal["stopLossPrice"])
        side = str(signal["side"]).lower()
        reward = take_profit - entry if side in {"buy", "long"} else entry - take_profit
        risk = entry - stop_loss if side in {"buy", "long"} else stop_loss - entry
        if risk <= 0 or reward <= 0 or reward / risk < float(profile.get("rewardRiskRatio") or 2.0):
            raise ValueError("Live signal attached protection does not satisfy the RiskProfile R multiple")

    @staticmethod
    def _build_order_payload(signal: dict[str, Any], cl_ord_id: str) -> dict[str, Any]:
        return {
            "instId": str(signal["instId"]),
            "side": str(signal["side"]),
            "posSide": str(signal.get("posSide") or "net"),
            "tdMode": "isolated",
            "ordType": str(signal["ordType"]),
            "sz": str(signal["sz"]),
            "clOrdId": cl_ord_id,
            "tag": "alphapilot",
            "attachAlgoOrds": [{
                "tpTriggerPx": str(signal["takeProfitPrice"]),
                "tpOrdPx": "-1",
                "tpTriggerPxType": "mark",
                "slTriggerPx": str(signal["stopLossPrice"]),
                "slOrdPx": "-1",
                "slTriggerPxType": "mark",
            }],
        }
