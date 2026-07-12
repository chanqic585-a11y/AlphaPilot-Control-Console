# AlphaPilot V13.27.9 Top100 Demo Release Design

## Goal

Upgrade the active OKX Demo release universe from liquidity-ranked Top20 deep screening to Top100 deep screening, while preserving immutable release history and keeping Demo execution isolated from live trading.

This design also makes Top100 the default for every future Demo release.

## Confirmed Product Rules

- Every OKX Demo strategy first discovers the public OKX USDT linear perpetual universe, applies public liquidity and spread gates, and then deep-screens the top 100 eligible contracts.
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

### Batch-Scoped Public Market Cache

Top100 would otherwise request the same public universe, metadata, and OHLCV repeatedly for similar releases. Introduce a batch-scoped context with cached loaders keyed by:

- universe: `screeningLimit`;
- snapshot: `instrumentId + timeframe + limit`;
- metadata: `instrumentId`.

`run_evolution_demo_batch_cycle()` creates one context and passes its loaders to every release scan in that batch. The cache exists only in memory for that batch and stores no credentials.

At an hourly boundary, five 1h releases should share roughly 100 snapshots instead of requesting roughly 500. At the Beijing midnight boundary, 1h and 1D releases share metadata and universe discovery while retaining timeframe-specific snapshots.

### Arbitration

Existing global arbitration already rejects duplicate symbols after per-strategy selection. Add a regression test proving that multiple successor releases matching the same symbol create at most one Demo order. Top100 changes candidate discovery, not portfolio risk limits.

### Runtime Deployment

Source code can be tested and committed while the current V13.27.7 credential-bearing process continues running. Successor activation must not occur until the V13.27.9 runtime is loaded, because the old process does not have the shared cache.

Deployment sequence:

1. finish and verify V13.27.9 code;
2. stop the current Demo automatic runner without exposing credentials;
3. restart through the secure Demo launcher so credentials remain process-only;
4. activate the Top100 successor migration;
5. arm Demo automation;
6. verify 10 active Top100 releases, zero active Top20 releases, shared cache metrics, no blockers, and no duplicate symbol order.

If secure restart needs user credential input, automation stops at that boundary and asks only for process input. It never reads credentials from another process.

## UI and Observability

Demo workflow cards should use accurate wording:

- market universe: OKX USDT perpetual public universe;
- liquidity eligible count;
- deep screening: Top100;
- strategy matched count;
- unique matched symbol count;
- duplicate signals rejected by arbitration.

The page must not label Top20 or Top100 deep screening as evaluating strategy rules on every listed exchange contract.

## Validation

- Unit tests for the Top100 default in future Demo releases.
- Unit tests for immutable successor generation and checksum validation.
- Unit tests for idempotent transactional activation and predecessor archive preservation.
- Unit tests proving batch loaders cache universe, snapshot, and metadata calls.
- Batch execution test proving duplicate symbols create at most one order.
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
