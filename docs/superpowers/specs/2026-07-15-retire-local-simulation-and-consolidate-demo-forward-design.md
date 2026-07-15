# AlphaPilot Revised Demo Universe, Shadow Observer, and Backtest-First Consolidation Design

## Status

Revision 2 for review. This revision combines the approved local-simulation retirement direction with the V13.27.1.10 revised Demo-universe and backtest-first proposal. No business code is changed by this document.

## Executive Decision

AlphaPilot will use one research path and one engineering path, with separate releases, ledgers, statistics, and acceptance criteria.

~~~text
Research path
  Data availability audit
  -> immutable preregistration
  -> bounded event prefilter
  -> full cost-aware backtest
  -> formal backtest pass
  -> immutable strategy-validation release
  -> explicit enable approval
  -> shadow diagnostics + OKX Demo strategy validation
  -> Demo closed-trade review
  -> future Live Canary decision in a separate version

Engineering path
  Demo account instrument discovery
  -> public Top100 intersection
  -> dedicated engineering-smoke release
  -> minimum Demo order lifecycle rehearsal
  -> reconciliation and recovery checks
~~~

The full local simulation page, virtual account, virtual positions, equity curve, PnL lifecycle, and promotion stage are retired. Historical records remain immutable and readable for audit.

## Why This Is the Final Combined Direction

The earlier design correctly removed a duplicated forward stage, but it needed three stricter boundaries from the revised proposal:

1. OKX Demo connectivity must be proven with the Demo account's actual tradeable contracts, not with a public-only universe.
2. Engineering-smoke Demo and strategy-validation Demo are different experiments and cannot share evidence or statistics.
3. The retained shadow observer is signal diagnostics only. It must not calculate MFE, MAE, virtual PnL, 2R outcomes, positions, equity, or promotion decisions.

This avoids two opposite errors: delaying every strategy behind a duplicate virtual portfolio, and sending unqualified research strategies into Demo merely to prove that the order API works.

## Information Architecture

Primary navigation remains intentionally small:

~~~text
Strategy
Demo
Live
Mobile Console
~~~

- Remove the Local Simulation navigation item and page.
- Redirect legacy #localLab links to Strategy with a one-time retirement message.
- Do not add a replacement shadow page.
- Show shadow diagnostics only in an advanced, read-only section when incident review requires them.
- Keep historical local-simulation exports and audit reads, but do not load them in the primary workflow.

## Lifecycle Model

### Active research and execution states

~~~text
research_candidate
data_audit
preregistered
event_prefilter
backtest_queued
backtest_running
basic_backtest_passed
formal_backtest_passed
immutable_release_ready
demo_waiting_approval
demo_validation_running
demo_validated
live_candidate
archived
~~~

### Retired local-simulation states

~~~text
local_simulation_running
local_simulation_passed
local_forward
local_sandbox
~~~

Legacy rows keep their original stored state. Read projections label them legacy_local_observation; no new object may enter a retired state.

## Evidence Model

Every record has an explicit evidenceSource:

| Evidence source | What it proves | What it cannot prove |
| --- | --- | --- |
| historical_backtest | Historical, reproducible strategy screening | Future execution or profitability |
| shadow_observation | A frozen release emitted or rejected a signal in live public data | Fill, PnL, position, or promotion evidence |
| demo_engineering_smoke | Demo connectivity and order lifecycle plumbing | Strategy quality, PF, win rate, or promotion |
| demo_strategy_validation | Exchange-facing forward closed-trade evidence | Guaranteed future or Live performance |

One market event observed by shadow and Demo is one event, not two independent samples. Only closed trades in the strategy-validation Demo ledger count as forward execution evidence.

## Phase 1: Repair the OKX Demo Tradeable Universe

### Authoritative sources

Use the existing authenticated Demo client to query:

~~~text
GET /api/v5/account/instruments?instType=SWAP
~~~

The request must use the Demo environment and its existing simulated-trading header. Do not store credentials, log authentication headers, substitute a Live response, or share caches between Demo and Live.

### Universe construction

The executable Demo universe is:

~~~text
public point-in-time Top100 USDT perpetual universe
AND
current Demo-account tradeable SWAP instruments
AND
available instrument state
AND
data-quality, liquidity, depth, and portfolio-risk filters
~~~

Normalize exact instrument identity across BTC-USDT-SWAP and BTC/USDT:USDT, case, separators, and settlement currency. Never use fuzzy base-symbol matching; never map spot or USDC instruments to USDT SWAP.

The builder reports:

~~~text
publicUniverseCount
demoAccountInstrumentCount
intersectionCount
liquidityEligibleCount
excludedNotInDemoAccount
excludedUnavailableState
excludedDataMissing
excludedLiquidity
generatedAt
cacheAge
~~~

Cache results with an explicit Demo environment key, TTL, generated timestamp, and stale status. A missing, stale beyond policy, malformed, or empty authenticated response fails closed and must not fall back to the public universe.

### Read-only endpoint

Add GET /api/demo-instrument-universe. Return counts, status, and small included/excluded samples. Never return credentials, private headers, or a raw private response.

## Phase 2: Engineering-Smoke Demo

Engineering smoke validates only:

- scan and signal-object construction;
- risk checks;
- minimum-size Demo order submission;
- order, fill or open-order status;
- position reads;
- stop/target and exit or cancellation handling;
- restart recovery;
- local-to-exchange reconciliation.

It uses a dedicated release and ledger:

~~~text
demoPurpose = engineering_smoke
strategyQualification = false
promotionEligible = false
forwardPerformanceEligible = false
evidenceClass = demo_engineering_smoke
ledger = engineering_smoke_ledger
~~~

It may use a deterministic test trigger instead of waiting for a research signal. It is limited to one minimum-size Demo position, no concurrent entries, no adding, no martingale, and bounded retries.

Engineering smoke passes only when:

~~~text
Demo/public intersection > 0
orderAttemptCount > 0
no demo_instrument_unavailable inside the intersection
order status can be read
position status can be read
exit or cancellation completes where supported
reconciliation is consistent
duplicate orders = 0
orphan positions = 0
~~~

Real OKX errors remain errors and are recorded; success must never be fabricated.

## Current Ten Demo Releases

The current ten releases become legacy_diagnostic releases:

~~~text
releasePurpose = legacy_diagnostic
strategyQualification = false
promotionEligible = false
forwardPerformanceEligible = false
demoPerformanceEligible = false
~~~

They may support engineering diagnosis, signal audits, and historical comparison. They may not count as independent hypotheses, strategy-validation Demo candidates, promotion evidence, or Live candidates. Historical scans, orders, and records are preserved without mutation.

The UI labels variants from one family as: 同源变体，不是独立假设.

## Phase 3: Retire Full Local Simulation

The following capabilities are permanently false in this version and cannot be re-enabled by frontend controls, hidden endpoints, or environment variables:

~~~text
fullLocalSimulationEnabled=false
localVirtualPositionEnabled=false
localVirtualEquityEnabled=false
localSimulationLifecycleEnabled=false
simulationLearningEnabled=false
~~~

Bootstrap must not start the local sandbox runner. Restart recovery must not revive it. No new virtual order, fill, position, equity snapshot, PnL, daily report, learning sample, or lifecycle transition may be written.

Legacy write endpoints return 410 Gone:

~~~json
{
  "status": "retired",
  "code": "local_simulation_retired",
  "historicalDataPreserved": true,
  "nextAction": "Use formal backtest and OKX Demo validation."
}
~~~

Read-only audit and export compatibility may remain deprecated. No existing SQLite table, report, snapshot, order, fill, position, or history is deleted.

## Phase 4: Lightweight Shadow Observer

Shadow observation records only whether a frozen release produced a candidate signal and why it passed or failed:

~~~text
shadowObservationId
releaseId
strategyId
strategyFamilyId
timestamp
symbol
direction
timeframe
signalMatched
passOrReject
reasonZh
featureSnapshot
marketRegime
publicUniverseIncluded
demoUniverseIncluded
liquidityPassed
dataQualityPassed
riskGatePassed
wouldAttemptDemoOrder
sourceDataHashes
~~~

It must not create or calculate:

~~~text
orders or fills
virtual positions
virtual capital or equity
realized or unrealized PnL
MFE or MAE outcome scoring
2R / -1R lifecycle outcomes
local closed trades
automatic promotion or rejection
~~~

Shadow failure is warning-only and cannot stop a qualified Demo release. Add a read-only GET /api/shadow-observation endpoint for signal counts, rejection reasons, families, symbols, directions, and Demo-universe hit rates.

## Phase 5: Backtest-First Research Factory

### Data availability audit

Audit OHLCV, funding, open interest, liquidation, spot and perpetual prices, basis, volume, point-in-time universe, and market breadth before selecting hypotheses. Missing evidence remains null and unavailable; it is never fabricated. Continue with other families, but do not claim a complete campaign unless at least three genuinely testable independent families remain.

Candidate families should begin with market mechanisms that previous indicator stacks underused, such as funding/OI crowding, price/OI continuation, liquidation exhaustion, basis deviation, breadth, liquid cross-sectional momentum, idiosyncratic shock reversion, and volatility compression confirmed by OI/volume. Simple EMA/RSI/MACD/Bollinger stacking is not an independent hypothesis.

### Immutable preregistration

Before reading screening results, commit immutable preregistration files containing hypotheses, variants, data range, split, folds, embargo, final holdout, thresholds, costs, experiment budget, and stop rules. The preregistration commit and hash are audit evidence and cannot be edited after results are known.

### Data split

Use the default split unless a hypothesis preregisters a better justified one:

~~~text
development = 55%
walk-forward = 25%
final locked holdout = 20%
embargo between development and validation
~~~

Thresholds are chosen only in development. The final holdout is not used for parameter choice, model selection, or rescue attempts.

### Event prefilter

Run a cheap event-level prefilter before implementing a full Freqtrade strategy. Each event stores hypothesis, variant, timestamp, symbol, direction, timeframe, entry/stop/target references, maximum hold, split, fold, and data hash. Same-bar stop/target collisions use the conservative stop-first rule.

Only variants meeting all of the following proceed:

~~~text
development base-cost PF >= 1.08
development average net R >= 0.03
at least 60% of development months have average net R > 0
minimum effective event count and coverage pass
~~~

Minimums from the revised proposal are:

~~~text
15m: >= 300 events and >= 12 months
1h: >= 150 events and >= 12 months
4h: >= 80 events and >= 18 months
1d: >= 40 events and >= 24 months
~~~

The proposal does not define a 5m minimum. A 5m campaign must preregister a separate, stricter noise- and cost-aware minimum before it can claim a formal pass; it must not silently borrow the 15m threshold.

### Full backtest and cost stress

Only prefilter survivors receive a full implementation. Signal definitions and hashes must match the event study. Long and short variants remain distinguishable.

Run base, 1.5x, and 2x cost scenarios covering fees, slippage, funding, and a spread proxy. Missing real cost data stays explicit and receives a separately labeled conservative proxy.

Use at least five real purged walk-forward folds with an embargo, preserving foldId on every event/trade. Apply Benjamini-Hochberg FDR; Deflated Sharpe and PBO may be added when valid and otherwise remain null.

### Two pass levels

Basic research pass:

~~~text
OOS PF >= 1.05
OOS average net R > 0
OOS total net R > 0
maximum drawdown <= 25%
at least 3/5 folds have average net R > 0
base costs included
minimum samples pass
no look-ahead
~~~

A basic pass permits further research only. It cannot enter strategy-validation Demo.

Formal pass:

~~~text
OOS PF >= 1.15
OOS average net R >= 0.05
OOS total net R > 0
maximum drawdown <= 20%
at least 4/5 folds have average net R > 0
1.5x-cost PF >= 1.05
1.5x-cost average net R > 0
single-symbol positive contribution <= 35%
single-month positive contribution <= 35%
locked holdout was not used for selection
~~~

The strategy definition keeps an initial target of at least 2R, expresses risk in R, and never widens the initial stop after entry. Adaptive exits or trailing logic must be bounded, preregistered, versioned, and hashed; they cannot be invented after seeing the holdout.

### Finite experiment budget

Per campaign:

~~~text
hypothesis families <= 8
initial variants per family <= 2
initial candidates <= 16
structural revisions per family <= 1
full backtests <= 48
~~~

No unlimited generation, genetic search, broad parameter grid, holdout-driven editing, forced passing, or threshold weakening is allowed. A bounded failure is archived with attribution and informs a genuinely new hypothesis batch.

## Strategy-Validation Demo Admission

Only a formal pass may generate an immutable candidate release with:

~~~text
releaseId
strategyId
strategyFamilyId
strategyDefinitionHash
dataManifestHash
costModelHash
riskConfigHash
backtestReportHash
releasePurpose = strategy_forward_validation
~~~

Admission additionally requires traceable hashes, untouched holdout, base and 1.5x cost passes, walk-forward pass, a frozen execution-risk profile, and explicit enable approval. Generating a release does not automatically arm it.

The strategy-validation ledger is separate:

~~~text
demoPurpose = strategy_forward_validation
ledger = strategy_forward_validation_ledger
~~~

It records actual Demo orders, partial fills, fees, funding, slippage proxy, exits, reconciliation, and closed trades. Only these closed trades count as forward execution evidence.

Future review policy, not an automatic promotion rule in this version:

~~~text
>= 30 closed Demo trades: preliminary review
>= 100 closed Demo trades: serious review
~~~

Shadow observations and engineering-smoke records never count toward these thresholds.

## Console Projection

### Strategy page

Show only decision-useful research status:

- data audit and preregistration;
- event prefilter progress;
- full backtests;
- basic passes;
- formal passes;
- failure attribution;
- experiment budget used;
- immutable candidate releases awaiting approval.

Rank by formal status, OOS PF, average net R, 1.5x-cost PF, positive-fold ratio, drawdown, symbol/month concentration, sample size, and evidence completeness, not by raw return alone.

### Demo page

Use two visibly separated sections:

1. Demo 工程状态: Runtime, Demo account instruments, Top100 intersection, latest order attempt, reconciliation, duplicate/orphan counts.
2. 策略验证 Demo: approved immutable releases, current orders/positions, fees, funding, slippage, PnL, closed trades, blockers, and next action.

Never merge engineering-smoke metrics into strategy PF, win rate, PnL, or promotion counts.

### Advanced diagnostics

The hidden shadow section shows signal counts, pass/reject counts, and reasons only. It never shows virtual equity, virtual positions, or virtual PnL.

## Read-Only APIs

Add or consolidate:

~~~text
GET /api/demo-instrument-universe
GET /api/demo-engineering-smoke
GET /api/shadow-observation
GET /api/backtest-screening
~~~

Legacy simulation write APIs are retired. Deprecated simulation history reads remain audit-only.

## Failure and Stop Rules

- Empty or invalid Demo-account instruments: fail closed and expose the exact blocker.
- Public/Demo intersection empty: engineering smoke and strategy Demo do not place orders.
- Engineering smoke failure: keep strategy evidence unchanged.
- Shadow failure: warning only; never block qualified Demo execution.
- Formal pass count equals zero: keep full local simulation off, keep shadow and engineering smoke, stop the current batch, and propose a new independent hypothesis batch from failure attribution.
- Formal pass count is positive: freeze at most one to three releases and wait for explicit enable approval before strategy-validation Demo.
- No forced pass, resurrection of old candidates, post-hoc coin deletion, or extra trials beyond budget.

## Live Boundary

This version does not implement or enable Live Canary. A future, separately approved version may define:

~~~text
separate subaccount
no withdraw permission
IP allowlist
maximum one position initially
fixed absolute loss budget
no adding
immediate stop at the budget
~~~

No Demo result guarantees profitability or Live safety.

## Security Boundaries

- No Withdraw API.
- No raw API key in browser, SQLite, reports, logs, or commits.
- Demo and Live clients, caches, releases, and ledgers remain isolated.
- No Live account, position, or order access in this version.
- Immutable release hashes and frozen risk profiles are mandatory.
- Historical local records are never presented as real performance.
- Shadow records are never presented as orders or PnL.

## Rollout Order

1. Back up and inventory current databases, active Runtime, process-only credentials boundary, releases, and pre-existing changes.
2. Build and test the authenticated Demo instrument universe and exact ID normalization.
3. Run the isolated engineering-smoke lifecycle and prove attempts, reads, exit/cancel, reconciliation, no duplicates, and no orphans.
4. Relabel the current ten releases as legacy diagnostics without mutating historical evidence.
5. Remove the Local Simulation page and navigation; retire all local simulation writes and bootstrap recovery while preserving history.
6. Add the no-PnL shadow observer and its read-only diagnostics.
7. Audit research data, commit preregistration, and run the bounded event-prefilter/backtest campaign.
8. Generate at most one to three immutable strategy-validation releases only from formal passes; do not auto-arm them.
9. Update Console, Quant, Docs, operator guidance, and audit reports.
10. Run regression, security scans, runtime proof, and git diff --check; tag only after every required result is evidenced.

## Test and Runtime Proof

### Demo universe

- Demo and Live environments never mix.
- Exact contract normalization and intersection are correct.
- Cache freshness and exclusion reasons are correct.
- Credentials and private payloads never enter logs.

### Engineering smoke

- Demo only.
- orderAttemptCount > 0.
- No unavailable-instrument failure inside the intersection.
- Order and position reads work.
- Exit/cancel works where supported.
- Duplicate orders = 0.
- Orphan positions = 0.
- No strategy performance metric changes.

### Local simulation retirement

- No new virtual position, equity, PnL, learning, or lifecycle write.
- History remains unchanged and readable.
- Restart cannot revive the runner.

### Shadow

- Signals and rejection reasons are recorded.
- No PnL, position, equity, lifecycle, or promotion is generated.

### Research screening

- Immutable preregistration exists.
- Locked holdout remains isolated.
- Five real folds exist.
- Costs and stress are correct.
- Basic and formal gates are deterministic.
- FDR is reported.
- Old candidates are not silently restored.
- Trial budget is enforced.

### Required operating result

Before tagging, prove all of the following:

~~~text
Demo account instrument query succeeds
public Top100 intersect Demo instruments is non-empty
intersection contracts do not fail as unavailable
engineering-smoke orderAttemptCount > 0
full local simulation writes no new records
virtual equity no longer changes
shadow records signals and rejection reasons only
legacy releases do not count as strategy performance
bounded screening actually runs
reports are generated from real results
~~~

## Acceptance Criteria

1. Local Simulation is absent from primary navigation and cannot mutate state.
2. Historical local evidence remains intact and audit-only.
3. Shadow observation has no virtual account, PnL, position, outcome, or promotion behavior.
4. OKX Demo scans only the authenticated Demo-account/public-universe intersection.
5. Engineering smoke proves order plumbing without producing strategy evidence.
6. The ten current releases are clearly labeled legacy diagnostics.
7. Research candidates obey immutable preregistration, locked holdout, cost stress, real folds, FDR, and finite trial limits.
8. Only formal passes can produce strategy-validation releases.
9. Strategy-validation releases require explicit enable approval and use a separate ledger.
10. Only strategy-validation Demo closed trades count as forward execution evidence.
11. No automatic Live activation or Live trading capability is added.
12. All targeted tests, complete regressions, safety scans, and runtime proofs pass.

## Non-Goals

- deleting historical local simulation tables or reports;
- converting local, shadow, or smoke evidence into Demo strategy evidence;
- weakening formal backtest, cost stress, locked holdout, or 2R risk rules;
- manufacturing a passing strategy;
- restoring the ten diagnostic releases as candidates without requalification;
- implementing Live Canary;
- storing raw credentials;
- adding Withdraw support;
- claiming that backtest, Demo, or future Canary results guarantee profit.
