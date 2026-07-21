"""Fail-closed Live safety preflight with no exchange execution adapter."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .live_approval_store import LiveApprovalStore


LIVE_SAFETY_STORE_PATH = DATA_DIR / "live_safety_plane.sqlite"
MAX_REQUEST_TTL_SECONDS = 30
MAX_PRICE_DEVIATION_PERCENT = 1.0


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LiveSafetyDecision:
    requestId: str
    idempotencyKey: str
    packageId: str
    packageHash: str
    demoReleaseId: str
    demoReleaseHash: str
    riskBudgetHash: str
    instrumentId: str
    side: str
    referencePrice: float
    observedPrice: float
    instrumentState: str
    requestedAt: str
    expiresAt: str
    reconciliationMatched: bool
    status: str
    passedSafetyChecks: bool
    reasons: list[str]
    executionEnabled: bool
    contentHash: str
    createdAt: str


def evaluate_experimental_live_floors(
    profile: dict[str, Any],
    state: dict[str, Any],
) -> list[str]:
    """Evaluate immutable V59/V60 Live floors without enabling execution."""

    reasons: list[str] = []
    daily_loss = float(state.get("dailyLossUSDT") or 0.0)
    program_loss = float(state.get("programLossUSDT") or 0.0)
    if daily_loss >= float(profile["dailyLossLimit"]):
        reasons.append("live_daily_loss_limit")
    if program_loss >= float(profile["programLossLimit"]):
        reasons.append("live_program_loss_limit")
    if max(daily_loss, program_loss) >= float(profile["hardKillLossLimit"]):
        reasons.append("live_hard_kill_loss_limit")
    if int(state.get("openPositionCount") or 0) >= int(profile["maximumConcurrentPositions"]):
        reasons.append("live_maximum_concurrent_positions")
    if float(state.get("requestedLeverage") or 0.0) > float(profile["maximumLeverage"]):
        reasons.append("live_maximum_leverage")
    maximum_signal_age_seconds = float(profile["maximumSignalAgeMs"]) / 1000.0
    if float(state.get("signalAgeSeconds") or 0.0) > maximum_signal_age_seconds:
        reasons.append("live_signal_stale")
    if state.get("killSwitchActive") is True:
        reasons.append("live_kill_switch_active")
    if state.get("reconciliationMatched") is not True:
        reasons.append("live_reconciliation_not_confirmed")
    return reasons


class LiveSafetyStore:
    """Append-only request ledger plus persistent local safety switches."""

    def __init__(self, path: Path | str = LIVE_SAFETY_STORE_PATH):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS LiveSafetyRequests (
              requestId TEXT PRIMARY KEY,
              idempotencyKey TEXT NOT NULL UNIQUE,
              packageId TEXT NOT NULL,
              packageHash TEXT NOT NULL,
              demoReleaseId TEXT NOT NULL,
              demoReleaseHash TEXT NOT NULL,
              riskBudgetHash TEXT NOT NULL,
              instrumentId TEXT NOT NULL,
              side TEXT NOT NULL,
              referencePrice REAL NOT NULL,
              observedPrice REAL NOT NULL,
              instrumentState TEXT NOT NULL,
              requestedAt TEXT NOT NULL,
              expiresAt TEXT NOT NULL,
              reconciliationMatched INTEGER NOT NULL,
              decisionStatus TEXT NOT NULL,
              passedSafetyChecks INTEGER NOT NULL,
              reasonsJson TEXT NOT NULL,
              executionEnabled INTEGER NOT NULL,
              contentHash TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_live_safety_created
              ON LiveSafetyRequests(createdAt, requestId);
            CREATE TABLE IF NOT EXISTS LiveSafetyRuntime (
              singletonId INTEGER PRIMARY KEY CHECK(singletonId = 1),
              killSwitchActive INTEGER NOT NULL,
              circuitBreakerActive INTEGER NOT NULL,
              reconciliationMatched INTEGER NOT NULL,
              reason TEXT NOT NULL,
              updatedAt TEXT NOT NULL
            );
            INSERT OR IGNORE INTO LiveSafetyRuntime(
              singletonId, killSwitchActive, circuitBreakerActive,
              reconciliationMatched, reason, updatedAt
            ) VALUES (1, 0, 0, 0, 'initial_fail_closed_state', CURRENT_TIMESTAMP);
            """
        )
        self.connection.commit()
        self._recover_pending_requests()

    def close(self) -> None:
        self.connection.close()

    def runtime_state(self) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM LiveSafetyRuntime WHERE singletonId = 1"
        ).fetchone()
        return {
            "killSwitchActive": bool(row["killSwitchActive"]),
            "circuitBreakerActive": bool(row["circuitBreakerActive"]),
            "reconciliationMatched": bool(row["reconciliationMatched"]),
            "reason": row["reason"],
            "updatedAt": row["updatedAt"],
        }

    def update_runtime(
        self,
        *,
        kill_switch: bool | None = None,
        circuit_breaker: bool | None = None,
        reconciliation_matched: bool | None = None,
        reason: str,
    ) -> dict[str, Any]:
        current = self.runtime_state()
        values = (
            int(current["killSwitchActive"] if kill_switch is None else kill_switch),
            int(current["circuitBreakerActive"] if circuit_breaker is None else circuit_breaker),
            int(current["reconciliationMatched"] if reconciliation_matched is None else reconciliation_matched),
            str(reason or "operator_update"),
            _iso(_now()),
        )
        with self.connection:
            self.connection.execute(
                """
                UPDATE LiveSafetyRuntime
                SET killSwitchActive = ?, circuitBreakerActive = ?,
                    reconciliationMatched = ?, reason = ?, updatedAt = ?
                WHERE singletonId = 1
                """,
                values,
            )
        return self.runtime_state()

    def record(self, decision: LiveSafetyDecision) -> LiveSafetyDecision:
        existing = self.connection.execute(
            "SELECT * FROM LiveSafetyRequests WHERE idempotencyKey = ?",
            (decision.idempotencyKey,),
        ).fetchone()
        if existing:
            if existing["contentHash"] != decision.contentHash:
                raise ValueError("Idempotency key was reused with different Live safety content")
            return self._from_row(existing)
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO LiveSafetyRequests(
                  requestId, idempotencyKey, packageId, packageHash,
                  demoReleaseId, demoReleaseHash, riskBudgetHash,
                  instrumentId, side, referencePrice, observedPrice,
                  instrumentState, requestedAt, expiresAt,
                  reconciliationMatched, decisionStatus, passedSafetyChecks,
                  reasonsJson, executionEnabled, contentHash, createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.requestId,
                    decision.idempotencyKey,
                    decision.packageId,
                    decision.packageHash,
                    decision.demoReleaseId,
                    decision.demoReleaseHash,
                    decision.riskBudgetHash,
                    decision.instrumentId,
                    decision.side,
                    decision.referencePrice,
                    decision.observedPrice,
                    decision.instrumentState,
                    decision.requestedAt,
                    decision.expiresAt,
                    int(decision.reconciliationMatched),
                    decision.status,
                    int(decision.passedSafetyChecks),
                    _canonical(decision.reasons),
                    int(decision.executionEnabled),
                    decision.contentHash,
                    decision.createdAt,
                ),
            )
        return decision

    def list_decisions(self, limit: int = 50) -> list[LiveSafetyDecision]:
        rows = self.connection.execute(
            """
            SELECT * FROM LiveSafetyRequests
            ORDER BY createdAt DESC, requestId DESC LIMIT ?
            """,
            (max(1, min(int(limit), 500)),),
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def _recover_pending_requests(self) -> None:
        recovery_reason = _canonical(["restart_recovery_failed_closed", "live_execution_disabled"])
        with self.connection:
            self.connection.execute(
                """
                UPDATE LiveSafetyRequests
                SET decisionStatus = 'rejected_restart_recovery',
                    passedSafetyChecks = 0,
                    reasonsJson = ?, executionEnabled = 0
                WHERE decisionStatus = 'pending'
                """,
                (recovery_reason,),
            )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> LiveSafetyDecision:
        return LiveSafetyDecision(
            requestId=row["requestId"],
            idempotencyKey=row["idempotencyKey"],
            packageId=row["packageId"],
            packageHash=row["packageHash"],
            demoReleaseId=row["demoReleaseId"],
            demoReleaseHash=row["demoReleaseHash"],
            riskBudgetHash=row["riskBudgetHash"],
            instrumentId=row["instrumentId"],
            side=row["side"],
            referencePrice=float(row["referencePrice"]),
            observedPrice=float(row["observedPrice"]),
            instrumentState=row["instrumentState"],
            requestedAt=row["requestedAt"],
            expiresAt=row["expiresAt"],
            reconciliationMatched=bool(row["reconciliationMatched"]),
            status=row["decisionStatus"],
            passedSafetyChecks=bool(row["passedSafetyChecks"]),
            reasons=json.loads(row["reasonsJson"]),
            executionEnabled=bool(row["executionEnabled"]),
            contentHash=row["contentHash"],
            createdAt=row["createdAt"],
        )


def _risk_budget_reasons(risk: dict[str, Any]) -> list[str]:
    limits = {
        "capitalLimitUsdt": 1000.0,
        "riskPerTradePercent": 0.25,
        "maxOpenRiskPercent": 1.0,
        "maxOrderNotionalUsdt": 250.0,
        "maxConcurrentPositions": 3.0,
        "maxLeverage": 2.0,
        "dailyLossStopPercent": 2.0,
        "maxDrawdownStopPercent": 5.0,
    }
    reasons: list[str] = []
    for key, maximum in limits.items():
        value = risk.get(key)
        try:
            number = float(value)
        except (TypeError, ValueError):
            reasons.append(f"risk_budget_missing_or_invalid:{key}")
            continue
        if not math.isfinite(number) or number <= 0 or number > maximum:
            reasons.append(f"risk_budget_exceeds_boundary:{key}")
    return reasons


def evaluate_live_safety_request(
    *,
    request: dict[str, Any],
    package_export: dict[str, Any],
    approval_store_path: Path | str,
    safety_store: LiveSafetyStore,
    now: datetime | None = None,
) -> LiveSafetyDecision:
    """Audit a future Live preflight. It can never return execution permission."""

    evaluated_at = (now or _now()).astimezone(UTC)
    package = package_export.get("package") if isinstance(package_export.get("package"), dict) else {}
    risk = package.get("proposedRiskBudget") if isinstance(package.get("proposedRiskBudget"), dict) else {}
    approval_store = LiveApprovalStore(approval_store_path)
    try:
        approval = approval_store.get_state(
            str(package_export.get("liveCandidatePackageId") or ""),
            str(package_export.get("packageHash") or ""),
        )
    finally:
        approval_store.close()

    reasons: list[str] = []
    package_id = str(request.get("liveCandidatePackageId") or "")
    package_hash = str(request.get("packageHash") or "")
    demo_release_id = str(request.get("demoReleaseId") or "")
    demo_release_hash = str(request.get("demoReleaseHash") or "")
    risk_hash = str(request.get("riskBudgetHash") or "")
    expected_risk_hash = _hash(risk) if risk else ""
    if package_id != str(package_export.get("liveCandidatePackageId") or ""):
        reasons.append("package_id_mismatch")
    if package_hash != str(package_export.get("packageHash") or ""):
        reasons.append("package_hash_mismatch")
    if package_hash and package_hash != _hash(package):
        reasons.append("package_payload_hash_invalid")
    if demo_release_id != str(package_export.get("demoReleaseId") or package.get("demoReleaseId") or ""):
        reasons.append("demo_release_id_mismatch")
    if demo_release_hash != str(package.get("demoReleaseHash") or ""):
        reasons.append("demo_release_hash_mismatch")
    if not expected_risk_hash or risk_hash != expected_risk_hash:
        reasons.append("risk_budget_hash_mismatch")
    package_risk_hash = str(package.get("proposedRiskBudgetHash") or "")
    if package_risk_hash and package_risk_hash != expected_risk_hash:
        reasons.append("candidate_risk_budget_hash_invalid")
    reasons.extend(_risk_budget_reasons(risk))
    if approval.get("status") != "approved_for_future_release_review":
        reasons.append("manual_checksum_bound_approval_missing")
    elif _hash(approval.get("riskBudget") or {}) != expected_risk_hash:
        reasons.append("approved_risk_budget_mismatch")

    requested_at = _parse_time(request.get("requestedAt"))
    expires_at = _parse_time(request.get("expiresAt"))
    if requested_at is None or expires_at is None:
        reasons.append("invalid_request_time")
    else:
        ttl = (expires_at - requested_at).total_seconds()
        if ttl <= 0 or ttl > MAX_REQUEST_TTL_SECONDS:
            reasons.append("request_ttl_invalid")
        if evaluated_at < requested_at - timedelta(seconds=5) or evaluated_at > expires_at:
            reasons.append("request_expired_or_not_yet_valid")

    instrument_id = str(request.get("instrumentId") or "")
    side = str(request.get("side") or "").lower()
    instrument_state = str(request.get("instrumentState") or "").lower()
    if not instrument_id:
        reasons.append("instrument_missing")
    if side not in {"long", "short"}:
        reasons.append("side_invalid")
    if instrument_state != "live":
        reasons.append("instrument_not_live")
    try:
        reference_price = float(request.get("referencePrice"))
        observed_price = float(request.get("observedPrice"))
    except (TypeError, ValueError):
        reference_price = 0.0
        observed_price = 0.0
    if not all(math.isfinite(value) and value > 0 for value in (reference_price, observed_price)):
        reasons.append("price_invalid")
    else:
        deviation = abs(observed_price - reference_price) / reference_price * 100.0
        if deviation > MAX_PRICE_DEVIATION_PERCENT:
            reasons.append("price_deviation_exceeded")

    runtime = safety_store.runtime_state()
    request_reconciled = bool(request.get("reconciliationMatched"))
    if not request_reconciled or not runtime["reconciliationMatched"]:
        reasons.append("private_state_reconciliation_missing")
    if runtime["killSwitchActive"]:
        reasons.append("kill_switch_active")
    if runtime["circuitBreakerActive"]:
        reasons.append("circuit_breaker_active")
    if package.get("liveExecutionAdapterPresent") is not False or package.get("liveExecutionEnabled") is not False:
        reasons.append("candidate_boundary_invalid")

    passed = not reasons
    boundary_reasons = [
        "live_release_execution_approval_not_implemented",
        "live_adapter_absent",
        "live_execution_disabled",
    ]
    final_reasons = [*reasons, *boundary_reasons]
    status = "validated_execution_disabled" if passed else "rejected"
    payload = {
        "idempotencyKey": str(request.get("idempotencyKey") or ""),
        "packageId": package_id,
        "packageHash": package_hash,
        "demoReleaseId": demo_release_id,
        "demoReleaseHash": demo_release_hash,
        "riskBudgetHash": risk_hash,
        "instrumentId": instrument_id,
        "side": side,
        "referencePrice": reference_price,
        "observedPrice": observed_price,
        "instrumentState": instrument_state,
        "requestedAt": str(request.get("requestedAt") or ""),
        "expiresAt": str(request.get("expiresAt") or ""),
        "reconciliationMatched": request_reconciled,
        "status": status,
        "passedSafetyChecks": passed,
        "reasons": final_reasons,
        "executionEnabled": False,
    }
    idempotency_key = payload["idempotencyKey"]
    if not idempotency_key:
        raise ValueError("A non-empty idempotency key is required")
    decision = LiveSafetyDecision(
        requestId=f"live_safety_{uuid.uuid4().hex}",
        idempotencyKey=idempotency_key,
        packageId=package_id,
        packageHash=package_hash,
        demoReleaseId=demo_release_id,
        demoReleaseHash=demo_release_hash,
        riskBudgetHash=risk_hash,
        instrumentId=instrument_id,
        side=side,
        referencePrice=reference_price,
        observedPrice=observed_price,
        instrumentState=instrument_state,
        requestedAt=payload["requestedAt"],
        expiresAt=payload["expiresAt"],
        reconciliationMatched=request_reconciled,
        status=status,
        passedSafetyChecks=passed,
        reasons=final_reasons,
        executionEnabled=False,
        contentHash=_hash(payload),
        createdAt=_iso(evaluated_at),
    )
    return safety_store.record(decision)


def attempt_live_execution(*_: Any, **__: Any) -> None:
    raise PermissionError("Live execution adapter is absent and disabled in V13.21")


def activate_live_kill_switch(
    reason: str = "operator_request",
    *,
    store_path: Path | str = LIVE_SAFETY_STORE_PATH,
) -> dict[str, Any]:
    store = LiveSafetyStore(store_path)
    try:
        state = store.update_runtime(kill_switch=True, reason=reason)
    finally:
        store.close()
    return {"ok": True, "runtime": state, "executionEnabled": False}


def build_live_safety_status(
    *,
    packages: list[dict[str, Any]] | None = None,
    approval_store_path: Path | str | None = None,
    store_path: Path | str = LIVE_SAFETY_STORE_PATH,
) -> dict[str, Any]:
    store = LiveSafetyStore(store_path)
    try:
        runtime = store.runtime_state()
        decisions = store.list_decisions()
    finally:
        store.close()
    rows = packages or []
    approved_count = 0
    if approval_store_path is not None:
        approvals = LiveApprovalStore(approval_store_path)
        try:
            approved_count = sum(
                approvals.get_state(str(item.get("liveCandidatePackageId") or ""), str(item.get("packageHash") or ""))["status"]
                == "approved_for_future_release_review"
                for item in rows
            )
        finally:
            approvals.close()
    return {
        "version": "V13.21.0",
        "source": "live_safety_plane_v1",
        "summary": {
            "packageCount": len(rows),
            "approvedForFutureReviewCount": approved_count,
            "auditedRequestCount": len(decisions),
            "validatedButDisabledCount": sum(item.status == "validated_execution_disabled" for item in decisions),
            "rejectedRequestCount": sum(item.status.startswith("rejected") for item in decisions),
            "liveExecutionEnabledCount": 0,
        },
        "runtime": runtime,
        "recentDecisions": [asdict(item) for item in decisions[:20]],
        "blockers": [
            "live_release_execution_approval_not_implemented",
            "live_adapter_absent",
            "live_execution_disabled",
        ],
        "safetyBoundary": {
            "approvalEnablesExecution": False,
            "liveExecutionAdapterPresent": False,
            "liveExecutionEnabled": False,
            "requestExpiryRequired": True,
            "idempotencyRequired": True,
            "reconciliationRequired": True,
            "killSwitchAvailable": True,
            "withdrawAllowed": False,
            "runtimeCredentialStorageAllowed": False,
        },
    }
