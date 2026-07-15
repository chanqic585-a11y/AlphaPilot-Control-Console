# Local Simulation Retirement and No-PnL Shadow Diagnostics

AlphaPilot has retired Local Simulation from the active product lifecycle. The
active path is now:

```text
formal backtest
-> immutable Demo Release
-> OKX Demo validation
-> Live Candidate
```

## Retirement boundary

- Historical local-simulation databases, rows, reports, fills, positions,
  equity snapshots, closed samples, learning samples, and exports remain
  preserved for read-only audit.
- Legacy write routes return HTTP `410 Gone` with
  `code=local_simulation_retired`.
- Console startup, restart recovery, timers, bridges, learning jobs, and UI
  actions cannot create new local-simulation state.
- Historical workflow values still deserialize, but they cannot be selected as
  active transition targets.
- The retired Local Simulation page is absent from primary navigation. An old
  `#localLab` link redirects to Strategy and shows one retirement notice per
  browser session.

## Existing Demo release classification

The ten releases that predate this retirement are preserved byte-for-byte and
classified in a separate SQLite overlay as `legacy_diagnostic`. The overlay
does not edit a signed release file or its hash.

Each classification has these fixed properties:

```text
strategyQualification=false
promotionEligible=false
forwardPerformanceEligible=false
demoPerformanceEligible=false
```

Active strategy-validation discovery excludes these diagnostic releases.

## No-PnL shadow observer

The lightweight observer records only public-market signal diagnostics such as
the frozen release identity, market event, matched/rejected decision, bounded
feature snapshot, data and liquidity checks, and source hashes.

It does not create or store:

```text
orders, fills, positions, capital, equity, PnL, profit/loss, MFE/MAE,
returns, outcomes, promotion decisions
```

Shadow persistence is a non-blocking side effect. A warning, timeout, or
storage failure cannot change candidate ranking, risk checks, an order payload,
idempotency, or Demo eligibility.

Read-only diagnostics are available from:

```http
GET /api/shadow-observation?releaseId=<id>&limit=100
```

The UI exposes this only under advanced diagnostics.

## Safety boundary

This retirement adds no Live connector, Withdraw capability, raw credential
storage, account read, position read, order creation, or automatic trading.
Only a formally passed, immutable and eligible release may proceed to OKX Demo
validation under the existing runtime and risk gates.
