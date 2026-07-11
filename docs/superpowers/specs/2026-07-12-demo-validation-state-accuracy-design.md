# V13.27.1.7 Demo Validation State Accuracy Design

## Context

The Demo workflow card currently reports a strategy as 4/6 complete even when
the OKX Demo read-only preflight has never run. It can also display a legacy
single-symbol candidate while the full-market scan is still `not_started`.
Both values make the card look farther along than the underlying evidence.

The running console holds OKX Demo credentials in process memory only. A fix
must not restart that process or persist credentials.

## Goals

- Count the runtime preflight step as complete only after the console is ready
  and the read-only check has passed.
- Show 3/6 (50%) while the next action is `run_demo_preflight`.
- Hide a stale candidate until a real full-market scan produces candidates.
- Put a clear `运行 Demo 前检查` action directly on the strategy card.
- Preserve all existing execution gates, position limits, and credential rules.

## Non-goals

- No automatic order placement.
- No automatic Demo cycle triggered by the read-only check.
- No credential persistence or API-key UI storage.
- No change to the requested/effective concurrent-position safety calculation.
- No change to strategy selection, order sizing, or live-trading permissions.

## Considered Approaches

### Frontend-only correction

This would update the visible card immediately without restarting the console,
but the API projection would remain inaccurate for other consumers.

### Backend-only correction

This would establish a correct source of truth, but the currently running
process would need a restart and would lose its process-only credentials.

### Dual correction (selected)

Fix the backend projection and add a narrow frontend normalization for stale
responses from a pre-patch process. The backend becomes correct on the next
normal restart, while the current credential-bearing session renders correctly
after a page refresh.

## Backend Projection Rules

The runtime preflight process step is complete only when both conditions hold:

1. Runtime readiness is true.
2. `readonlyStatus` equals `passed`.

When credentials exist but the read-only check has not run, the step remains
pending and the workflow action remains `run_demo_preflight`.

The full-market candidate projection must not fall back to a release's legacy
`instId`. `currentTopCandidate` is populated only from a completed scan result.
When the scan is `not_started`, has zero instruments, or has no ranked result,
the projected candidate is null.

## Frontend Normalization Rules

Before rendering a Demo workflow card:

- If the next action is `run_demo_preflight`, force the runtime-preflight step
  to pending and recompute completed steps and percentage.
- If the market scan is `not_started` with zero instruments, hide any stale
  candidate and show `待扫描` instead.

This normalization is deliberately limited to these known stale-response
conditions and does not synthesize passed evidence.

## Card Interaction

The card shows a primary `运行 Demo 前检查` button when that is the next action.
The button calls the existing read-only-check endpoint. On success, it refreshes
the Demo workflow projection. It does not place, cancel, or automate orders.

## Safety

- Demo credentials remain process-only.
- The patch does not restart the current console.
- Order smoke and cancellation gates remain unchanged.
- The effective concurrent-position cap remains the minimum of strategy,
  portfolio, and risk-profile limits.
- No live or withdrawal capability is added.

## Verification

- Unit tests cover preflight pending/passed progress and candidate hiding.
- UI contract tests cover the visible preflight action and stale-response
  normalization.
- The full test suite, compile checks, JavaScript syntax checks, and
  `git diff --check` must pass.
- The current local page is verified without restarting the credential-bearing
  console process.
