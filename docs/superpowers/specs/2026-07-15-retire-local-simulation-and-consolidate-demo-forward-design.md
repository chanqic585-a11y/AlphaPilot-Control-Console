# AlphaPilot Local Simulation Retirement and Demo Forward Consolidation Design

## Status

Approved direction. This specification records the implementation boundary before code changes.

## Goal

Remove the standalone local simulation page and retire local simulation as a promotion stage. Preserve all historical records as read-only audit evidence, keep only a lightweight hidden shadow observer, and make OKX Demo the single executable forward-validation stage after formal backtest approval.

## Why This Change

The current lifecycle treats formal backtest, local simulation, and OKX Demo as three visible sequential stages. In practice, local simulation and Demo observe the same future market path, so treating both as independent promotion evidence creates delay without adding independent statistical evidence. It also makes the control console harder to understand.

The correct separation is:

- formal backtest establishes reproducible historical evidence;
- a lightweight shadow observer records signal diagnostics without positions or simulated equity;
- OKX Demo validates exchange-facing execution, fills, positions, exits, costs, and operational reliability;
- Live Canary remains separately gated.

## Approved User Flow

```text
New hypothesis
  -> bounded event prefilter
  -> formal backtest
  -> immutable strategy release
  -> OKX Demo forward validation
  -> Live Canary review
```

After an immutable release is created, the hidden shadow observer and OKX Demo may run in parallel. Shadow output is diagnostic only and never blocks, promotes, or duplicates Demo evidence.

## Information Architecture

The primary navigation becomes:

```text
Strategy
Demo
Live
Mobile Console
```

The `Local Simulation` navigation item and page are removed. The old `#localLab` hash redirects to the Strategy page and shows one one-time message explaining that local simulation was retired and history remains preserved.

No replacement page is added. Historical local simulation information is available only through read-only audit/export interfaces and advanced diagnostics when required for incident review.

## Stage Model

### Active stages

```text
research_candidate
backtest_queued
backtest_running
backtest_passed
demo_waiting
demo_validation_running
demo_validated
live_candidate
live_canary
archived
```

### Retired stages

```text
local_simulation_running
local_simulation_passed
local_forward
local_sandbox
```

Retired stages remain readable for legacy records but cannot be assigned to new work. Projection code maps historical records to a `legacy_local_observation` audit label instead of presenting them as an active lifecycle stage.

## Formal Backtest to Demo Promotion

A strategy may create an immutable Demo Release only when all formal backtest gates pass:

- target risk/reward is at least 2R;
- point-in-time data snapshot is registered and hashed;
- purged walk-forward evidence exists;
- holdout and locked out-of-sample evidence exist;
- fees, funding, slippage, latency, and cost stress are included;
- cross-symbol and cross-regime checks pass;
- immutable strategy definition, risk profile, signal policy, and code/data hashes are complete.

The former local-forward sample threshold is removed from Demo promotion decisions. It must not be silently reintroduced under another name.

## Lightweight Shadow Observer

The retained observer is not a simulation account and has no user-facing page.

It may persist:

- release ID and strategy hash;
- closed-candle timestamp;
- evaluated market universe;
- matching symbol and signal reason;
- veto reason;
- hypothetical entry reference price;
- hypothetical initial stop and 2R target;
- later diagnostic MFE/MAE and outcome labels.

It must not create:

- simulated orders;
- simulated fills;
- simulated positions;
- virtual balances or equity curves;
- promotion decisions;
- Demo or Live orders.

Shadow observations use a distinct evidence class and cannot be counted together with Demo outcomes as two independent forward samples.

## OKX Demo as the Executable Forward Gate

OKX Demo validates the complete forward execution path:

- account-compatible tradeable universe;
- closed-candle signal evaluation;
- strategy arbitration and portfolio risk;
- order submission and exchange response;
- fills, fees, slippage, and latency;
- position monitoring and exit handling;
- reconciliation and closed-trade review.

The scan universe is the intersection of:

```text
public Top100 USDT perpetual universe
AND
current OKX Demo account tradeable SWAP instruments
AND
liquidity/depth/risk filters
```

Publicly visible instruments that the current Demo account cannot trade must be excluded before signal ranking. They may be logged as universe exclusions but must not produce false strategy matches or order failures.

## Engineering Smoke Releases

An engineering smoke release may be used before formal strategy approval only to test connectivity and lifecycle plumbing. It must be explicitly marked:

```text
engineeringSmoke = true
strategyEvidenceEligible = false
liveCandidateEligible = false
```

Smoke orders cannot satisfy strategy evidence, cannot create a Live candidate, and cannot be relabeled as formal evidence later.

## Current Ten Demo Releases

The ten existing releases are relabeled as legacy diagnostic releases until each release proves that its formal backtest evidence, immutable hashes, Demo tradeable-universe binding, and risk profile satisfy the new contract.

This relabeling does not delete, mutate, or recreate their historical orders, scans, or evidence. It changes only how the console describes their validation status.

## API Retirement and Compatibility

### Removed write behavior

The console no longer starts the local sandbox auto-runner during application bootstrap. Local sandbox run, run-now, settings mutation, daily-report creation, and return-to-sandbox actions are retired.

Legacy write endpoints return an explicit retired response and do not modify state:

```json
{
  "status": "retired",
  "code": "local_simulation_retired",
  "nextAction": "Use formal backtest and OKX Demo validation."
}
```

The HTTP status is `410 Gone` for direct legacy callers.

### Preserved read behavior

Read-only history endpoints remain temporarily available for audit/export compatibility. They must be marked deprecated and must not appear in primary page loading.

No SQLite table, report, snapshot, fill, position, or strategy history is deleted by this change.

## Console Projection

The Strategy page shows:

- awaiting backtest;
- backtest running;
- formal pass;
- failed/blocked with reasons;
- archived history.

The Demo page shows:

- waiting for Demo;
- Demo validating;
- Demo passed;
- Live candidates;
- current positions, orders, PnL, fees, slippage, blockers, and next action.

No stage summary includes an active local-simulation count. Legacy local records appear only in audit metadata.

## Finite Research Budget

Strategy generation remains bounded:

- at most 8 hypothesis families per research campaign;
- at most 2 initial variants per family;
- at most 16 candidates per campaign;
- at most 48 full formal backtests per campaign;
- event prefilter before expensive full backtest;
- bounded optimization, then archive without forced promotion.

The system must never optimize toward a forced pass or weaken the 2R target merely to create Demo activity.

## Data Migration and Recovery

This change requires no destructive migration.

- Existing stage assignments remain immutable history.
- New assignments cannot target retired stages.
- A compatibility projection translates legacy local stages at read time.
- Existing local runner enabled state is force-disabled once, with an audit event.
- Restart recovery must not restart the retired runner.
- Active OKX Demo runtime, process-only credentials, immutable releases, and positions are not restarted or mutated by the migration.

## Error Handling

- Old bookmarks redirect safely instead of rendering a blank page.
- Retired API callers receive `410` and a clear next action.
- Missing Demo credentials leave releases in `demo_waiting`; they do not fall back to local simulation.
- A Demo-incompatible instrument is excluded before ranking and is recorded as an availability exclusion.
- Shadow observer failure is warning-only and cannot stop Demo.
- Demo execution failure remains fail-closed and visible with an actionable blocker.

## Security Boundaries

- No Withdraw API.
- No raw API key storage in browser or SQLite.
- Demo credentials remain process-only or in the existing approved Windows credential vault.
- Live trading remains separately gated.
- No historical local record is presented as a real trade or real PnL.
- No shadow observation is presented as a Demo fill or Live result.
- Immutable releases, risk limits, and audit trails remain mandatory.

## Testing Strategy

Implementation follows test-first development.

### Frontend contract tests

- navigation has no Local Simulation item;
- `#localLab` redirects to Strategy;
- local page markup and active controls are absent;
- Strategy and Demo summaries contain no active local stage;
- historical audit wording remains available where appropriate.

### HTTP tests

- local simulation writes return `410` with `local_simulation_retired`;
- read-only history remains accessible;
- bootstrap never starts the local sandbox auto-runner;
- application shutdown does not assume the runner was started.

### Workflow tests

- formal backtest pass creates or queues an immutable Demo Release without local-forward evidence;
- failed formal backtest cannot enter Demo;
- retired stages cannot be assigned to new strategies;
- legacy records remain readable and are projected as audit-only;
- shadow observations cannot satisfy promotion gates;
- engineering smoke releases can never become Live candidates.

### Demo universe tests

- public Top100 is intersected with account-tradeable Demo instruments;
- unavailable instruments are excluded before signal ranking;
- one account-instrument request is shared for all releases in a scan cycle;
- no raw credential or private payload appears in logs.

### Regression checks

- full Python test suite;
- compileall;
- JavaScript syntax check;
- `git diff --check`;
- local console health endpoint;
- Strategy, Demo, Live, and Mobile pages open normally;
- active Demo runtime remains unchanged unless a restart is explicitly required.

## Rollout Order

1. Remove the Local Simulation page and navigation, add legacy redirect, and stop primary-page API loading.
2. Disable local sandbox bootstrap and retire its write endpoints while preserving read-only history.
3. Replace active local stages in lifecycle projection with direct formal-backtest-to-Demo flow.
4. Add hidden shadow-observation evidence with no promotion authority.
5. Bind Demo scans to the account-compatible tradeable universe.
6. Relabel existing ten releases as legacy diagnostics without mutating evidence.
7. Update AlphaPilot Docs and operator instructions.
8. Run full regression and verify the active Demo runtime separately.

## Acceptance Criteria

1. The Local Simulation navigation item and page no longer exist.
2. Old `#localLab` links redirect to Strategy with a one-time explanation.
3. No local sandbox runner starts automatically.
4. Legacy local write APIs are retired and cannot mutate data.
5. Historical local records remain readable and unchanged.
6. New strategies cannot enter a local simulation stage.
7. Formal backtest pass can proceed directly to an immutable Demo Release.
8. Shadow observations are hidden, diagnostic, and non-promotional.
9. Demo and shadow evidence are never double-counted.
10. Demo scan candidates are restricted to account-tradeable instruments before ranking.
11. Current ten releases are clearly labeled legacy diagnostic until requalified.
12. Live remains separately gated and no security boundary is weakened.
13. All targeted and full regression checks pass.

## Non-Goals

- deleting historical local simulation tables or reports;
- converting old local samples into Demo evidence;
- weakening formal backtest or 2R requirements;
- enabling Live automatically;
- storing raw API credentials;
- adding Withdraw support;
- claiming that Demo or Live Canary guarantees profitability.
