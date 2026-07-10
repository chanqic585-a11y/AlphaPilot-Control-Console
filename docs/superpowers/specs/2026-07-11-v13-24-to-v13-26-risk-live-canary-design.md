# AlphaPilot V13.24-V13.26 Risk, Canary, and Feedback Design

## Objective

Move AlphaPilot from fixed risk constants and a disabled Live preflight to an
auditable, versioned risk contract, a fail-closed OKX Live Canary runtime, and a
formal Demo/Live outcome feedback loop. The work does not claim profitability
and does not activate real orders by default.

## V13.24: Versioned Risk Profiles

`RiskProfile` is an immutable contract shared by Local Forward, OKX Demo, and
Live releases. It contains:

- capital and order-notional limits;
- active-strategy and position concurrency limits;
- per-strategy, per-symbol, per-direction, and correlated-group exposure limits;
- per-trade and total-open-risk limits;
- leverage and margin-mode limits;
- daily-loss, drawdown, and Canary-loss circuit breakers;
- cooldown, new-entry, and kill-switch policy.

Profiles are append-only. Editing creates a new version and content hash.
Activation is a separate append-only action. Existing positions remain bound to
their opening profile; only new entries use a newly activated version. The
current conservative values become a preset, not permanent hard-coded values.

An independent `SafetyEnvelope` remains outside the routine UI. It validates
that a profile is internally coherent and prevents accidental unbounded values.
Changing the SafetyEnvelope is a code-reviewed release, not a normal runtime
edit.

## V13.25: OKX Live Canary Runtime

The Live adapter uses process-only `Read + Trade` credentials, an endpoint
allowlist, no Withdraw endpoint, idempotent client order IDs, request expiry,
private-state reconciliation, restart recovery, exchange-hosted TP/SL, and a
persistent kill switch. It is disabled unless all of these are true:

1. a checksum-bound Live Candidate Package is manually approved;
2. its RiskProfile hash matches the active Live profile;
3. the explicit Live read and Canary process gates are enabled;
4. credentials are present only in the running process;
5. account, position, instrument, price, and order reconciliation pass;
6. the active profile allows new entries and all portfolio risk checks pass.

The initial UI exposes status, profile, blockers, reconciliation, recent
intents, and emergency stop. No raw credential is accepted or rendered by the
web app. With no eligible release, the runtime remains blocked even when a key
is present.

## V13.26: Formal Outcome Feedback

Demo and Live terminal orders are mapped to immutable Outcome Ledger exports.
Each outcome carries release, candidate, profile, order, instrument, event-time,
fee, slippage, risk, PnL, and exit-reason lineage. Incomplete or unmatched rows
are quarantined and cannot enter model or factor feedback.

The Quant Engine imports checksum-verified exports as `okx_demo` or `live`
evidence. The offline loop may create research triggers or challengers, but it
cannot mutate a running release, promote a strategy, or place an order.

## Portfolio Arbitration

Multiple strategies and positions are supported, but candidate count alone is
never treated as risk capacity. The arbiter enforces portfolio, strategy,
symbol, direction, family, and correlation-group limits. Conflicting or
suppressed signals are logged with reason codes and are not represented as
executed evidence.

## Compatibility

- Existing V13.19-V13.22 records remain readable.
- Releases without a profile use the conservative compatibility preset.
- Old approval records remain valid only for their original package and risk
  hash.
- No database is rebuilt and no historical record is deleted.

## Acceptance Boundary

- Local Forward, Demo, and Live consume the same profile schema and hash.
- Profile creation, activation, rollback, and mismatch behavior are tested.
- Live credentials are never stored.
- Withdraw is absent from the client allowlist.
- Live order execution remains off without an eligible approved release and
  explicit process gates.
- Demo/Live outcomes remain distinct evidence classes.
- All repositories pass their existing tests plus new V13.24-V13.26 tests.
