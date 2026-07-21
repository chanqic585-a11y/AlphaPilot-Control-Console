# AlphaPilot V13.27.1.62 Control Plane, Runtime Truth, and Strategy Factory

## Objective

Keep the currently armed OKX Demo process untouched while building the next control-plane release in an isolated worktree. Replace static UI projections with ledger-backed runtime truth, make every business parameter editable through immutable versioned policy objects, and run bounded autonomous research without bypassing research or execution gates.

## Non-Negotiable Safety Boundary

- Withdraw remains absent.
- Raw API credentials remain process-only and are never persisted or returned by an API.
- Exact Release approval and per-process ARM remain mandatory.
- No running Release, exit policy, model, or risk identity may be mutated in place.
- Research may archive failures and publish approval requests, but may not force a pass, approve itself, ARM, or place orders.
- Safety-envelope maxima and environment isolation are hard invariants, not routine UI settings.

## Mutable, Versioned Business Policy

Account and strategy configuration is editable by creating a new immutable version and content hash. Supported fields cover allocation, order notional, per-trade risk, leverage, margin mode, concurrent positions, symbol limits, scan universe, liquidity and depth thresholds, latency limits, cooldown, fees, slippage, stop policy, and exit policy. Risk increases or execution-semantics changes remain inactive until their exact approval route is satisfied.

## Runtime Truth Sources

1. Unified auto-execution runtime: online, desired, ARM, blockers, latest scan funnel.
2. Demo/Live execution ledgers: strategy orders and order lifecycle.
3. Sanitized account snapshots: equity, positions, realized and floating PnL.
4. RiskProfile and StrategyExecutionPolicy stores: active immutable parameter versions.
5. Strategy factory ledger: queued/running/completed/archived campaigns and approval requests.

Static evidence remains audit context only and must not impersonate live runtime state.

## Implementation Phases

1. Add failing tests for immutable strategy policy versions and runtime-truth projections.
2. Add `StrategyExecutionPolicyStore` with validation against the active account RiskProfile and hard SafetyEnvelope.
3. Add a read-only trading-terminal projection for Demo and Live, explicitly distinguishing unavailable credential-bound account data from numeric zero.
4. Add bounded HTTP APIs for reading and proposing policy versions; sensitive fields are rejected and activation stays approval-gated.
5. Rebuild Demo and Live pages around connection, equity, PnL, strategies, positions, orders, and actionable issues. Put hashes and gate detail behind disclosure controls.
6. Start one bounded research campaign at a time. Persist preregistration, budget, results, archive decisions, and approval requests.
7. Add health monitoring for runtime loss, credential expiry, unknown orders/positions, factory stalls, and human approval requests.
8. Run targeted and full tests, compile/config/safety/diff checks, collect evidence, commit/tag/push, then schedule a safe cutover without restarting the currently armed Demo process.

## Cutover Rule

The active Demo process continues on its frozen code and exact Release. V62 is verified separately. Runtime cutover occurs only after the current process reaches a safe zero-order/zero-position checkpoint and the operator can securely restart and ARM the exact Release again.
