# Adaptive Learning Live Governance Split Design

## Status

Approved by the user on 2026-07-21. This is a governance and safety correction. It does not change strategy results, frozen Demo identities, model parameters, or trading risk values.

## Goal

Remove the circular dependency between adaptive-learning technical readiness and exact human approval, keep the current observer model out of Live, and make Live approval and ARM mechanically impossible until truthful technical evidence is complete.

## Chosen Design

Use three independent, fail-closed gates:

1. `AdaptiveLearningTechnicalReadinessGate` evaluates only technical evidence and a decision-participating model policy. It never reads human approval.
2. `ExactLiveReleaseApprovalGate` evaluates an actionable approval request against a technically ready, hash-bound Live Release and draft Risk Overlay.
3. `LiveArmGate` evaluates the approved identity plus runtime credentials, reconciliation, environment gates, and zero-state safety checks. It never changes technical readiness.

`AdaptiveLearningLiveReadinessGate` remains only as a compatibility facade for old imports and delegates to the technical gate. New production code must import the three explicit gates.

## Alternatives Considered

- Keep one gate and rename `exactHumanApproval`: rejected because it preserves the circular dependency.
- Build a new orchestration state machine: rejected for this patch because it would expand scope and risk changing runtime behavior.
- Split the three gates and keep a compatibility facade: selected because it gives clear ownership while preserving existing imports.

## Technical Readiness Contract

Technical readiness requires production factors, real Factor Bench, Alpha101 and Alpha191 compatibility, a validated crypto subset, bounded factor mining, a frozen learning dataset, training, Purged Walk-forward, Qlib evidence, model validation and registration, Demo outcome lineage, shadow inference, decision-participating Demo validation, drift monitoring, rollback rehearsal, online latency evidence, feature-pipeline parity, and deterministic Live inference.

It does not require `exactHumanApproval`. Observer and `observer_only` policies always fail technical readiness. A successful technical snapshot may say `ready_for_release_construction`; it does not grant approval, ARM, order, or Live authority.

## Current Draft Disposition

The existing V59/V60 Experimental Live identity is preserved as historical evidence. A versioned governance disposition must reference its exact hashes and project:

- `status=draft_blocked_adaptive_learning_not_ready`
- `approvalRequestActionable=false`
- `mechanicalExecutionAllowedAfterExactApproval=false`

The current observer Model Hash and Model Policy Hash remain Demo observer-only. No exact Live approval challenge may be actionable for this identity.

After all technical evidence passes, the system must generate a new decision-participating Model Hash, Model Policy Hash, Live Release Hash, draft Risk Overlay Hash, and actionable Approval Request. Existing hashes are never silently mutated.

## Latency Semantics

`execution_latency_profile_v1` is the sole authority for target latency, maximum signal age, order request expiry, exchange Ack timeout, and the critical latency boundary. The profile is versioned and hash-bound.

- `criticalLatencyFailureMs=20000` means only `critical_latency_failure`.
- `maximumSignalAgeMs` must be strictly less than 20000 and is the actual order-submission freshness deadline.
- Target latency and Ack timeout remain independently configurable and enter the policy hash.
- Experimental Live Release and Risk evidence bind the latency-policy hash instead of duplicating a 20-second signal-age field.

## Risk Governance

The current Live Experiment Profile and Risk Overlay remain `draft`. Before final approval, the user may adjust every exposed risk field. Any adjustment produces a new Profile Hash and Risk Overlay Hash. Risk cannot increase automatically.

## Artifact Policy

Historical immutable artifacts are not overwritten. The patch writes a new versioned governance bundle containing technical-gate output, current-draft disposition, approval-gate output, ARM-gate output, latency-policy binding, risk draft status, manifest, tests, and closeout.

## Safety Invariants

- No Live approval request while technical readiness is false.
- No ARM while exact approval or runtime gates are false.
- No strategy Live order creation.
- Current Demo runtime is not restarted.
- Live and Withdraw remain disabled.
- No API credentials are read, stored, or emitted by this patch.

## Verification

Run focused gate, release, latency, snapshot, and auto-execution tests; then full Console tests, `compileall`, configuration validation, safety scan, and `git diff --check`. Generated artifacts must contain no credential field names or values.
