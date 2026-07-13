# AlphaPilot V13.27.9 Top100 Demo Release Design

## Goal

Upgrade the active OKX Demo release universe from liquidity-ranked Top20 deep screening to Top100 deep screening, while preserving immutable release history and keeping Demo execution isolated from live trading.

This design also makes Top100 the default for every future Demo release.

## Confirmed Product Rules

- Every OKX Demo strategy first discovers the public OKX USDT linear perpetual universe, applies public liquidity and spread gates, and then deep-screens the top 100 eligible contracts.
- Confirmed candle close to Demo order submission has a five-second target. Ten seconds starts conditional late-entry handling, and thirty seconds is the absolute expiry.
- A signal older than ten seconds may proceed only when current market data is fresh, liquidity and spread gates still pass, adverse entry drift is within the dynamic limit, and net reward/risk recalculated from the current entry remains at least 2R.
- Existing Top20 release files remain unchanged as audit history.
- Existing Top20 releases are replaced by versioned Top100 successor releases, not edited in place.
- The five 1D long strategies retain their current BTC regime rules. A bear regime remains a valid reason for zero 1D signals.
- Demo-only overrides remain ineligible for automatic live promotion.
- Reward/risk remains at least 2R.
- Raw API credentials are process-only. No credential is written to JSON, SQLite, logs, reports, or the browser.
- Withdraw remains absent. This change adds no live execution capability.

## Approaches Considered

### 1. Edit the existing Top20 contracts

Rejected. Editing `screeningLimit` would invalidate the contract checksum and violate immutable release semantics.

### 2. Keep Top20 and add parallel Top100 releases

Rejected. Both generations would remain active, double-scan the same strategy, and increase duplicate signal and duplicate order risk.

### 3. Versioned Top100 successors with archived predecessors

Selected. Each active Top20 contract is copied unchanged into an archive, a checksum-valid Top100 successor is generated with a new release identity, and only successors remain in the active contract directory. A migration manifest records every predecessor-successor mapping.

## Architecture

### Demo Universe Policy

Define shared constants:

- `DEMO_DEEP_SCREENING_LIMIT = 100`
- `DEMO_UNIVERSE_POLICY_VERSION = "okx_full_market_policy_v2_top100"`

`authorize_demo_override()` uses these values for every future release. A release that does not contain the Top100 policy cannot be silently upgraded during scanning.

### Successor Contract Builder

Add a focused successor module that:

1. validates the predecessor contract;
2. deep-copies it without mutating the source object;
3. changes only the universe policy and explicit successor metadata;
4. computes a new `releaseContentHash`, `demoReleaseId`, and `contractHash`;
5. preserves strategy content, risk envelope, Demo-only boundary, 2R target, and `livePromotionAllowed = false`;
6. records `supersedesDemoReleaseId` and migration reason.

### Transactional Activation

Activation uses staging and rollback-safe ordering:

1. validate exactly the intended active predecessor files;
2. generate and validate all successor files in a staging directory;
3. copy predecessor files unchanged into a timestamped archive directory;
4. create a migration manifest containing source and successor hashes;
5. atomically replace active predecessor files with successor files;
6. online-backup `unified_auto_execution.sqlite`;
7. remove only predecessor checkpoints and append a `demo_top100_successors_activated` audit event;
8. verify discovery returns only Top100 successors.

Activation is idempotent. Re-running it returns the existing successor set without creating another generation.

### Prewarmed Top100 Market Runtime

On-demand REST scanning after a candle closes cannot reliably meet the latency target. Add a process-local public market runtime that continuously maintains the active Top100 universe, instrument metadata, confirmed candles, current quotes, spread, liquidity state, and incremental indicator inputs for every active Demo timeframe.

The runtime uses two unauthenticated OKX WebSocket connections: ticker subscriptions use `wss://ws.okx.com:8443/ws/v5/public`, while candlestick subscriptions use `wss://ws.okx.com:8443/ws/v5/business`. Neither connection accepts a login payload or credential fields.

The runtime has four responsibilities:

1. refresh the public OKX USDT perpetual universe and liquidity ranking before a strategy is due;
2. consume public candle updates and retain unconfirmed updates only as provisional state;
3. publish an immutable evaluation snapshot when OKX marks a candle confirmed;
4. wake all releases due for the same timeframe so they evaluate one shared snapshot in one batch.

No AI, model training, historical download, or full indicator recomputation is allowed in the order hot path. Those operations remain outside automatic execution.

The runtime retains a REST recovery loader keyed by universe limit, instrument, timeframe, and candle limit. REST recovery can rebuild warm state after startup or reconnect, but it cannot submit an order from a missed or stale close event.

At an hourly boundary, five 1h releases evaluate the same Top100 snapshot rather than requesting roughly 500 separate snapshots. At Beijing midnight, 1h and 1D releases share universe, metadata, quote, spread, and liquidity state while retaining timeframe-specific confirmed candles and indicators.

### Latency and Late-Entry Policy

Latency starts at local receipt of an OKX confirmed-candle event and ends when the order request is sent. Exchange response time is recorded separately.

- `0-5 seconds`: on-target evaluation and submission;
- `>5-10 seconds`: delayed but eligible, with an SLO warning;
- `>10-30 seconds`: conditional late entry;
- `>30 seconds`: hard expiry with `signal_expired` and no order.

Conditional late entry requires all of the following:

- a current quote no more than two seconds old;
- current spread and liquidity gates still passing;
- no duplicate symbol order or conflicting open position;
- no runtime, balance, account, or risk blocker;
- adverse entry drift no greater than `min(0.20%, 10% of the original stop distance percent)`;
- net reward/risk recalculated from the current executable entry, including configured fees and slippage, still at least `2R`.

For a long signal, an increased entry price is adverse drift. For a short signal, a decreased entry price is adverse drift. A favorable price change does not bypass spread, liquidity, freshness, risk, or recalculated-2R checks. If the signal lacks a valid stop distance, it cannot use conditional late entry and expires after ten seconds.

WebSocket disconnect, sequence loss, missing candle confirmation, stale quote, stale private account state, or inability to prove the latency timestamps fails closed. The system records the reason and waits for a later confirmed candle instead of reconstructing and chasing the missed entry.

### Arbitration

Existing global arbitration already rejects duplicate symbols after per-strategy selection. Add a regression test proving that multiple successor releases matching the same symbol create at most one Demo order. Top100 changes candidate discovery, not portfolio risk limits.

### Runtime Deployment

Source code can be tested and committed while the current V13.27.7 credential-bearing process continues running. Successor activation must not occur until the V13.27.9 runtime is loaded and the prewarmed Top100 runtime passes latency rehearsal, because the old process does not have the shared market state or late-entry policy.

Deployment sequence:

1. finish and verify V13.27.9 code;
2. rehearse Top100 confirmed-close evaluation with recorded public data and prove timing/audit output without placing orders;
3. stop the current Demo automatic runner without exposing credentials;
4. restart through the secure Demo launcher so credentials remain process-only;
5. wait until the public Top100 runtime reports warm, synchronized, and current;
6. activate the Top100 successor migration;
7. arm Demo automation;
8. verify 10 active Top100 releases, zero active Top20 releases, latency metrics, no blockers, and no duplicate symbol order.

If secure restart needs user credential input, automation stops at that boundary and asks only for process input. It never reads credentials from another process.

## UI and Observability

Demo workflow cards should use accurate wording:

- market universe: OKX USDT perpetual public universe;
- liquidity eligible count;
- deep screening: Top100;
- strategy matched count;
- unique matched symbol count;
- duplicate signals rejected by arbitration.
- latest confirmed close received time;
- evaluation, arbitration, risk, order-send, and exchange-response durations;
- latency class: on target, delayed, conditional late entry, or expired;
- current-entry drift and recalculated net R when late-entry handling runs.

The page must not label Top20 or Top100 deep screening as evaluating strategy rules on every listed exchange contract.

## Validation

- Unit tests for the Top100 default in future Demo releases.
- Unit tests for immutable successor generation and checksum validation.
- Unit tests for idempotent transactional activation and predecessor archive preservation.
- Unit tests proving all releases for one timeframe share one prewarmed immutable snapshot.
- Unit tests for provisional versus confirmed candle handling and close-event wake-up.
- Unit tests for 5-second target classification, 10-second conditional late entry, and 30-second hard expiry.
- Unit tests for direction-aware adverse drift and recalculated net reward/risk of at least 2R.
- Unit tests proving stale quote, missing stop distance, reconnect recovery, or missing timestamps fail closed.
- Batch execution test proving duplicate symbols create at most one order.
- Recorded-data latency rehearsal covering Top100 with no private order call.
- Full Console test suite.
- Python compileall.
- JavaScript syntax check.
- `git diff --check`.
- Safety scan for credentials, Withdraw, live permission expansion, and order boundary changes.
- Read-only Top100 audit against public OKX data before activation.
- Post-activation verification of release discovery, checkpoints, events, blockers, scans, and Demo execution records.

## Out of Scope

- Changing strategy thresholds or 1D BTC regime rules.
- Promoting a Demo successor to live.
- Adding live credentials, Withdraw, or real-account automation.
- Claiming Top100 produces profitable strategies.
- Treating duplicate matches from related strategy variants as independent opportunities.
- Guaranteeing network latency or exchange acceptance; the system enforces deadlines and records measured outcomes instead.
