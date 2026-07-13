# AlphaPilot Control Console

Current version:

```text
Control Console runtime: AlphaPilot V13.27.9
Quant workflow compatibility: V13.27.11 formal-backtest progress semantics
```

AlphaPilot Control Console is a local desktop web console for reviewing
AlphaPilot Quant Engine research outputs and preparing a mobile-safe control
status bridge.

## Current Demo ARM and Evaluation Audit Patch

The secure Demo launcher now hands its explicit process-only automation
confirmation to the newly started Console process. After the listener, market
runtime, and runner are ready, startup performs the existing fail-closed Demo
ARM action for the current PID. A stale PID is never treated as armed, and the
browser cannot arm Demo by itself.

Every confirmed-close batch now exposes a redacted evaluation audit: evaluated
Release count, market/liquidity/deep-screen counts, matched signals, bounded
near misses, rejection and failed-check counts, order attempts/results,
exchange response-code counts, close sequence, PID, and stage timings. The
same bounded payload is stored with `heartbeat_completed`; it contains no API
credentials or private account values.

Historical evidence explains the previous ten-strategy zero-order period: the
recorded batches evaluated the older five hourly Releases (and all ten only at
daily boundaries), produced zero matches, and predated a completed Top100
close batch. The patch does not claim a trade retroactively. The next
credential-bearing runtime must complete a real confirmed-close Top100 batch;
the audit will then show whether the blocker is no signal, arbitration,
latency, risk, or exchange submission.

No raw key is persisted, Withdraw remains absent, immutable Demo Releases are
not mutated, and Live stays locked.

## V13.27.11 Quant Workflow Compatibility

- Distinguishes a first official-data download from a shared-warehouse tail
  refresh, an existing contract checkpoint check, and fully ready shared data.
- Shows how many historical K-lines were reused when only the latest public OKX
  tail is being collected.
- Separates official-data partition progress from formal backtest computation;
  a 100% data counter no longer implies that the formal result is complete.
- Matches the Quant Engine bounded pipeline: one formal compute worker and one
  next-strategy official-data prefetch worker.
- Does not change immutable research evidence, OKX Demo gates, Live gates,
  process-only credential handling, or the Withdraw boundary.

## What AlphaPilot V13.27.9 Adds

- Replaces immutable Top20 Demo releases with rollback-safe Top100 successor
  releases. Strategy rules, direction, target R, and risk envelopes are
  preserved; predecessor files are archived byte-for-byte.
- Keeps the OKX USDT perpetual Top100 public market state prewarmed in memory
  through separate public ticker and public candle WebSocket connections.
- Wakes the Demo execution controller from a confirmed close event instead of
  reconstructing an order cycle from the 15-second health heartbeat.
- Shares one frozen market snapshot per timeframe across every due release,
  arbitrates duplicate symbols, and still applies immutable release and risk
  gates before an OKX Demo order can be submitted.
- Targets five seconds from confirmed close to order send. Entries after ten
  seconds require fresh quotes, acceptable liquidity, limited adverse drift,
  and recalculated net reward/risk of at least 2R; signals expire after thirty
  seconds.
- Shows compact warm/synchronized status, last confirmed close, Top100 pool,
  and redacted latency stages in the Demo console without rendering all quotes.
- Adds a public-only no-order latency rehearsal and a separate successor
  activation command. Runtime credentials remain process-only.
- Does not add Withdraw, raw credential storage, or any new Live permission.

See `docs/V13.27.9-top100-demo-release.md`.

## What V13.27.7 Adds

- Makes OKX instrument normalization idempotent for symbols such as
  `ETH-USDT-SWAP`.
- Prevents full-market Demo scans from accidentally requesting malformed IDs
  such as `ETH-USDT-SWAP-USDT-SWAP`.
- Restores real ticker, candle, spread, metadata, strategy-rule, sizing, and
  risk evaluation before a Demo signal can be created.
- Does not relax any strategy rule or risk gate and does not persist raw
  credentials.

See `docs/V13.27.7-canonical-okx-instrument-fix.md`.

## What V13.27.6 Adds

- Lets an explicit Demo start clear an ordinary paused state while preserving a
  separate kill switch.
- Re-runs credentials, read-only reconciliation, account, and risk gates after
  the resume; any real blocker pauses Demo again.
- Shows the active OKX official-data partition, downloaded page count, K-line
  count, and partition percentage below the workflow phase progress.
- Keeps page progress in a durable checkpoint so restarts preserve operator
  visibility without treating partial rows as completed data.
- Keeps raw credentials process-only and does not add Withdraw or Live resume.

See `docs/V13.27.6-runtime-resume-official-progress.md`.

## What V13.27.5 Adds

- Replaces terminal Cancel Queue with reversible Pause Queue.
- Adds Restart From Checkpoint for cancelled backtest attempts.
- Keeps cancelled attempts immutable while creating one audited successor.
- Routes restart actions through the serial batch worker instead of a competing
  one-off worker.
- Confirms before a running attempt is permanently cancelled.
- Keeps process-only credentials, Live gates, and Withdraw boundaries unchanged.

See docs/V13.27.5-cancelled-attempt-resume.md.

## What V13.27.4 Adds

- Restarts incomplete backtests as one deterministic serial batch instead of
  spawning competing workers.
- Shows every selected strategy as queued before the first heavy backtest
  begins.
- Adds `人工放行到 Demo` to eligible local-forward cards using the immutable
  `strategyCandidateId`.
- Records the missing local-forward evidence, reason, actor, confirmation, and
  `postDemoPromotionPolicy` in the Demo-only release audit.
- Keeps the local-forward result unchanged: a manual release does not mark it
  passed and does not create an order.
- Treats complete OKX Demo validation as the final strategy-performance gate
  before live-candidate review. The override itself cannot directly enable
  Live execution.
- Continues to keep raw credentials process-only and Withdraw absent.

See `docs/V13.27.4-workflow-recovery-demo-release.md`.

## What V13.27.3 Adds

- Registers five 5-minute and five 15-minute executable research candidates in
  the Quant Engine. Registration is idempotent and never creates a Demo or Live
  release.
- Uses historical point-in-time dynamic Top50 OKX USDT perpetual universes for
  formal backtests. A single-symbol run is smoke/debug evidence only and cannot
  promote a strategy.
- Keeps `targetR >= 2`, fees, slippage, funding, delay, purged walk-forward,
  locked OOS, and unseen-symbol validation as formal promotion requirements.
- Adds `启动这一条`, checkbox selection, `启动选中`, and `启动全部待运行`
  controls to Strategy, formal Local Forward, and Demo workflow pages.
- Runs selected historical backtests and public local-forward cycles serially,
  so one click cannot start competing heavy workers.
- Lets Demo batch controls execute only each card's current legal step. They do
  not authorize a controlled override, bypass an immutable release, enable
  Live, or store credentials. OKX Demo credentials remain process-only.

See `docs/V13.27.3-short-cycle-workflow.md` for the Short-Cycle Workflow
contracts, page controls, and safety boundary.

## What V13.27.2 Adds

- Adds one restart-safe backend controller for Demo and Live automatic
  execution. Closing the browser does not stop the runner.
- Evaluates each immutable strategy only once per newly closed candle, while a
  15-second heartbeat continues order, position, and reconciliation checks.
- Lets eligible Demo releases scan the full configured OKX USDT perpetual
  universe, arbitrate competing signals, and place protected Demo orders
  without per-order confirmation.
- Gives Live the same operational controls, but keeps its credentials, request
  headers, adapter, releases, RiskProfile, ledger, ARM state, and kill switch
  isolated from Demo. Live remains disabled until all five runtime gates and a
  current-process ARM pass.
- Adds shared Chinese controls for start, pause new entries, stop, and emergency
  stop on desktop and mobile-width layouts. The mobile page is read-only and
  cannot initiate an order.
- Persists only runtime state, closed-candle checkpoints, and redacted events.
  Raw credentials remain process-only; Withdraw and key-management endpoints
  remain absent.
- Keeps immutable release checks, idempotency, isolated margin, attached TP/SL,
  and `rewardRiskRatio >= 2` as hard execution requirements.

See `docs/V13.27.2-unified-auto-execution.md` for the Unified Automatic
Execution lifecycle, launch gates, restart behavior, and safety boundary.

## What V13.27.1.8 Adds

- Converts OKX Demo read-only response code `50110` into an explicit blocker
  instead of leaving the operator-facing blocker list empty.
- Shows a one-time `OKX Demo 前检查失败` dialog with the current state, completed
  safety checks, and concrete API-key type, IP allowlist, and regional-domain
  review steps. Closing the dialog acknowledges the Demo page guidance version,
  so lower-priority Demo evidence notices do not immediately open a second
  dialog. Inline guidance remains available.
- Keeps the same guidance visible in the Demo status, read-only details, and
  recent-event list after the dialog is closed.
- Updates the workflow action status as soon as preflight returns, before the
  background workflow refresh completes.
- Prevents a duplicate resume attempt from rewriting an active backtest worker
  as `queued`, and reads official-data checkpoint counts so collection progress
  is displayed as real partitions such as `27/150`.
- Does not place orders, persist credentials, loosen risk gates, or enable Live
  or Withdraw capabilities.

See `docs/V13.27.1.8-demo-preflight-guidance.md` for the Read-only preflight,
50110, one-time guidance, and process-only credential contracts.

## What V13.27.1.7 Adds

- Makes the Demo workflow runtime-preflight step complete only after runtime
  gates are ready and the OKX Demo read-only check has passed.
- Corrects a preflight-pending strategy from the misleading 4/6 display to
  3/6 (50%) and exposes `运行 Demo 前检查` directly on its card.
- Hides legacy single-symbol fallbacks until an actual OKX USDT perpetual
  full-market scan produces a ranked candidate.
- Adds a frontend compatibility normalization so the current process-only
  credential session renders the corrected state without a forced restart.
- Does not place orders, start a Demo cycle automatically, persist credentials,
  or change portfolio and per-strategy risk limits.

See `docs/V13.27.1.7-demo-state-accuracy.md` for the projection, compatibility,
and safety contracts.

## What V13.27.1.6 Adds

- Restarts interrupted `queued` and `running` backtest workers when the Control
  Console starts, reusing the same workflow run and persisted checkpoint.
- Keeps an explicit user pause paused. The existing `继续运行` action resumes
  that same run only when the user requests it.
- Adds a cross-process run lock so a restarted Console cannot create duplicate
  workers for the same workflow run.
- Exposes startup recovery state through `/api/health` and clarifies the resume
  behavior on the Strategy page.
- Does not delete historical data, create a new strategy version, or repeat
  completed official-data partitions.

See `docs/V13.27.1.6-workflow-checkpoint-resume.md` for the restart, pause,
checkpoint, and duplicate-worker contracts.

## What V13.27.1.5 Adds

- Adds one-time, stage-aware issue guidance to Strategy, Local Simulation, Demo
  Simulation, and Live pages. The highest-priority unresolved issue opens once;
  users can reopen it explicitly with `查看处理办法`.
- Collapses the permanent Demo evidence checklist by default, preserving the
  evidence without crowding the main execution view.
- Adds a loopback-only `启动 OKX Demo` action. The browser requests only a fixed
  local launcher; it never reads, transmits, or stores API credentials.
- Prompts once per Demo runtime for API Key, Secret Key, and Passphrase. That
  one process-level Demo account connection is shared by all eligible
  strategies, while orders, positions, PnL, risk gates, and evidence remain
  isolated by strategy and immutable Release.
- Keeps the Live boundary distinct: account credentials are entered once, but
  every strategy must still be approved individually before activation. This
  patch does not enable Live trading.
- Replaces an existing Console listener only after exact PID, command-line,
  port, and confirmation checks. Mobile and LAN clients cannot launch a local
  process.

See `docs/V13.27.1.5-one-time-guidance-demo-launcher.md` for the launcher,
credential-sharing, one-time guidance, and safety contracts.

## What V13.27.1.4 Adds

- Keeps a permanent evidence checklist on every Demo strategy card. Formal
  backtest, target R, strategy definition, local-forward samples, immutable
  candidate/release, process-only Demo runtime, and closed Demo trades remain
  visible before and after they are satisfied.
- Adds a controlled `Demo-only` override for the local-forward sample gate. It
  requires a reason and the exact phrase `仅放行到OKX DEMO`; it cannot bypass
  formal backtest evidence, a complete strategy definition, or the `>= 2R`
  target, and it can never form a Live Candidate.
- Replaces single-symbol presentation with an OKX public full-market universe:
  all live USDT linear perpetual contracts are filtered by market metadata,
  public ticker availability, liquidity, and spread before a capped deep
  strategy scan. Missing public values are rejected rather than synthesized.
- Adds a per-strategy `1..10` simultaneous-symbol preference. The effective
  limit is always the lower of that preference, the active Demo RiskProfile,
  remaining portfolio slots, duplicate-symbol rules, and current risk budget.
- Shows separate `current top candidate` and `actual position instrument`
  fields, plus a compact multi-position view shared by Demo and Live pages.
- Adds visible progress tracks to running, queued, and paused dual-layer
  backtests. Download partition counts are shown when known; otherwise the UI
  displays honest workflow-phase progress instead of inventing elapsed time.
- Keeps Live and Withdraw boundaries unchanged. Public market scanning requires
  no credentials; Demo credentials remain process-only and are never persisted.

See `docs/V13.27.1.4-demo-evidence-full-market-progress.md` for the evidence,
override, universe, concurrency, and UI contracts.

## What V13.27.1.3 Adds

- Replaces the ambiguous Demo observation list with four exclusive queues:
  `待 Demo 模拟`, `Demo 验证中`, `Demo 模拟通过`, and `实盘候选`.
- Shows a six-step progress path for every Demo strategy: strategy load, public
  market check, immutable release, runtime preflight, Demo execution, and
  closed-trade review.
- Shows actual instrument, position status, entry/mark/TP/SL prices, quantity,
  realized/unrealized PnL, fees, slippage, and reconciliation state when those
  values exist in OKX Demo or the immutable execution ledger. Missing values
  stay empty and are never synthesized from backtest results.
- Adds `GET /api/demo-workflow` and gated `POST /api/demo-workflow/action`.
  The action endpoint can run the public scan, report release-readiness gaps,
  run the existing read-only preflight, or invoke the existing immutable
  Release Demo cycle. It cannot bypass a missing Release.
- Persists only redacted public candidate scan status so a page refresh does
  not erase the visible step. Raw API credentials remain process-only.
- Adds visible local-forward sample progress. `30` closed samples is still only
  a review starting point, never an automatic promotion.

The ten strategies currently assigned to `demo_trial` are therefore displayed
under `待 Demo 模拟`, not `Demo 验证中`: there is no formal StrategyCandidate,
immutable DemoRelease, or OKX Demo execution record for them yet.

### How a waiting strategy starts OKX Demo validation

1. Open `Demo模拟` and click the card's current primary action.
2. `检查 Demo 行情` scans OKX public market data only.
3. `检查 Demo Release 条件` lists missing backtest, local-forward, candidate,
   checksum, or immutable-release evidence.
4. Only a strategy with an immutable eligible Release can advance to runtime
   preflight.
5. Start the Console with process-only Demo credentials and explicit Demo
   order/automation gates, then run the preflight.
6. `运行一次 Demo 验证` reads signals only from the frozen Release and writes
   real Demo order/position/outcome evidence. Live and Withdraw remain locked.

## What V13.26.2 Fixes

- Uses persisted strategy-stage assignments as the lifecycle display source of
  truth, so a promoted strategy no longer reappears on the local simulation
  page because of retained historical evidence.
- Separates Demo Trial observation from formal Demo Release validation while
  counting both under the Demo page.
- Gives the strategy, local simulation, Demo, and Live pages distinct summary
  cards and stage-specific lists.
- Preserves all historical backtest and local sample data; this patch only
  corrects stage visibility and labels.

## What V13.26.1 Adds

- Restores the local sandbox scheduler to a 5-minute default with a 288-run
  daily ceiling.
- Adds explicit strategy-stage assignments so promotion moves a strategy from
  the local sandbox list into the Demo observation pool without deleting its
  historical reports or local samples.
- Promotes the current ten reviewed strategies into Demo Trial observation and
  shows historical sample count, win rate, profit factor, 2R target, score, and
  preserved local sample count on the Demo page.
- Keeps immutable formal Demo Release and Live gates unchanged. Demo Trial is
  an observation stage and does not by itself authorize an exchange order.

It can mechanically execute immutable eligible releases in OKX Demo Trading.
It also contains a default-off, checksum-gated OKX Live Canary adapter.

## What V13.26.0 Adds

- An immutable local ledger for fully closed and reconciled Demo/Live outcomes.
- Gross PnL, fee, slippage, net PnL, risk, and R-multiple reconciliation.
- Internal Demo/Live engine hooks that require an existing filled entry plus
  explicit exit evidence; no browser endpoint can submit arbitrary outcomes.
- A checksummed JSON export for the Quant Engine offline importer.
- A Chinese Live-page evidence panel showing formal Demo/Live results,
  quarantined incomplete executions, and the latest export path.

An opening order marked `filled` is not treated as a closed trade. V13.26.0
does not update models online, promote releases, read or persist account
values, expose Withdraw, or create an order through the feedback path.

## What V13.25.0 Adds

- A separate process-only OKX Live credential path and allowlisted REST client.
- An immutable LiveRelease contract with one-time manual release approval.
- Restart-safe idempotent Live intent, order, event, and runtime ledgers.
- Required isolated margin, attached TP/SL, at least 2R, account reconciliation,
  RiskProfile hash matching, circuit breakers, and emergency stop.
- Independent master, read, Canary, order, and manual ARM gates.
- A Chinese Live page showing every blocker without exposing account values.

All Live gates are off by default. The repository stores no raw credentials,
the Live client contains no Withdraw endpoint, tests use fake transports, and
this release places no real order.

## What V13.24.0 Adds

V13.24 introduces immutable, checksummed, bounded RiskProfile versions. See
the detailed V13.24 section below for configuration, activation, rollback, and
portfolio concentration controls.

## What V13.21.0 Adds

V13.21 adds a fail-closed, local-only Live safety preflight without adding a
Live exchange adapter.

- Every preflight is bound to the exact Live candidate package, Demo release,
  risk-budget hashes, instrument state, price snapshot, request expiry, and
  idempotency key.
- Private-state reconciliation, restart recovery, circuit breaker, and kill
  switch are explicit gates.
- Decisions are persisted in an append-only SQLite audit ledger.
- Manual approval only clears the review check. A fully valid request ends as
  `validated_execution_disabled`, never as executable.
- `attempt_live_execution()` always raises because Live execution approval and
  the Live adapter do not exist.
- `GET /api/live-safety` provides operator/mobile-safe status; the only write
  endpoint activates the local kill switch.

The real environment currently has no Live candidate package and no Live
request. No credentials are read or stored, and Live/Withdraw remain locked.

## What V13.20.0 Adds

V13.20 closes the remaining trust gaps around automatic OKX Demo execution.

- Automatic Demo cycles ignore externally supplied `signals` and `portfolio`.
- Signals come only from a checksum-verified immutable release, confirmed OKX
  public candles, frozen factor thresholds, spread checks, and public SWAP
  sizing metadata.
- Contract validation enforces the exact 1000 USDT / 250 USDT order-notional /
  0.25% risk / three-position envelope.
- A private Demo-only read reconciles balance and positions before new entries.
- Runtime guard pauses on unresolved order state, reconciliation mismatch,
  daily loss, drawdown, rolling profit-factor, consecutive-loss, checksum, or
  slippage drift.
- Existing idempotent order IDs, attached `>=2R` protective exits, restart
  recovery, partial-fill reconciliation, pause, and kill switch are reused.

The real Quant registry currently exports no eligible DemoRelease. With no
release, the console stops before public scanning, private credentials, or
orders. Runtime credentials remain process-only; Live and Withdraw remain
locked.

## What V13.15.1 Adds

V13.15.1 gives the desktop console one consistent strategy lifecycle:

```text
候选待测 -> 回测通过 -> 本地模拟中 -> 本地模拟通过
-> Demo 验证中 -> Demo 通过 -> 实盘候选
```

- Adds read-only `GET /api/strategy-lifecycle`.
- Every strategy has one current stage and appears on only one main page.
- The Strategy page only shows research candidates and backtest-passed rows.
- The Local Simulation page only shows local simulation stages.
- The Demo page only shows strategies backed by immutable `DemoRelease`
  contracts.
- The Live page only shows immutable `LiveCandidatePackage` rows.
- Reaching 30 closed local samples is a review starting point, not a promotion.
- Reports, benchmarks, failed rows, and duplicate research assets are kept in a
  collapsed archive and do not count as active strategies.
- Legacy research and rehearsal tools remain available in collapsed advanced
  sections instead of crowding the main workflow.
- No database migration is added and no old data is deleted.

This patch does not add API key storage, Trade API, Withdraw API, account or
position access, order creation, automatic Live promotion, or live execution.

## What V13.15.0 Adds

V13.15.0 adds a local, append-only manual approval state machine for immutable
`LiveCandidatePackage` exports from Quant Engine.

- The console verifies package schema and SHA-256 checksum before display.
- Approval requires the exact `APPROVE_LIVE_CANDIDATE_REVIEW` phrase and the
  fixed `user_manual` actor.
- Approval binds the package checksum and proposed risk budget.
- Revocation appends a new audit action; it does not delete history.
- A changed checksum invalidates the prior approval.
- AI, Bandit, ML, and automation actors cannot write approval.
- Approval only means `approved_for_future_release_review`; execution remains
  false.

The Live page shows Demo evidence, risk limits, checksum, approval state, and
revoke controls. The current registry has no qualifying package, so the page
correctly shows zero candidates and remains blocked.

There is no live execution adapter, no live key input, no live account access,
no live order endpoint, and no Withdraw path. OKX Demo remains isolated from
this future-release review boundary.

## What V13.14.0 Adds

V13.14.0 adds the isolated execution half of the Factor Evolution Research
Kernel. It discovers checksum-verified `DemoRelease` contracts from Quant
Engine, arbitrates conflicting signals, applies a fixed 1000 USDT Demo risk
envelope, and records every intent and lifecycle transition in a restart-safe
local SQLite ledger before contacting OKX Demo.

Key controls:

- Official Demo REST endpoint and mandatory `x-simulated-trading: 1` header.
- Process-only credentials with redacted representations and responses.
- Exact private endpoint allowlist; Withdraw and transfer paths are rejected
  before network access.
- 250 USDT maximum order notional, 0.25% risk per trade, 1% total open risk,
  maximum three positions, default maximum 2x leverage.
- Local idempotency keys and OKX `clOrdId`, partial-fill reconciliation,
  attached TP/SL fields, restart recovery, pause and kill switch.
- Automatic Demo execution requires all three startup gates: Demo private,
  Demo order, and Demo automation. It does not require a per-order ticket.
- The normal page clearly separates Research, Shadow, OKX Demo and Live Locked;
  the legacy manual ticket is only shown in advanced mode.

Start read-only Demo mode:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_okx_demo_console.ps1
```

Enable an already eligible immutable release for automatic Demo execution:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_okx_demo_console.ps1 -EnableOrder -EnableAutomation
```

The current registry has no eligible formal Demo release, so automatic orders
remain blocked even when runtime credentials are present. Live execution,
automatic Live promotion, Withdraw API, and raw key storage remain disabled.

Official API assumptions and endpoint limits are recorded in
`docs/V13.14.0-okx-demo-api-contract.md`.

## What V13.10.5 Adds

V13.10.5 turns active local lifecycle records into traceable observation
samples using OKX public ticker and confirmed OHLCV data.

What changed:

- Adds `POST /api/auto-execution-lifecycle/advance`.
- Adds `GET /api/auto-execution-learning`.
- Adds an append-only `autoExecutionLifecycleEvents` state collection. Original
  `autoExecutionRecords` remain unchanged for audit compatibility.
- Establishes a clearly labelled local reference price. It is a public market
  observation reference, not a historical fill or exchange execution price.
- Calculates ATR14 from confirmed public candles and uses the strategy ATR
  multiplier as the 1R price unit. A missing multiplier falls back to 1.0 and
  is explicitly recorded.
- Advances long and short observations toward 2R, -1R, or a timeframe-based
  expiry and records current R, MFE, MAE, and close reason.
- Uses confirmed post-reference candles to detect barriers crossed between
  manual advances. If one candle touches both barriers, the result is recorded
  conservatively as a stop; candle details remain transient and are not saved.
- Adds a Chinese `推进本地生命周期` action plus a closed-sample learning
  summary on the Demo page.
- Splits learning summaries by strategy, symbol, and direction.
- Keeps learning descriptive below 30 closed samples. It does not train a
  model or automatically promote or eliminate a strategy.

The lifecycle advancer uses public market endpoints only. It requires no API
key, does not read accounts or positions, does not create Demo or live orders,
does not run exchange Dry-run, and does not enable automatic trading.

## What V13.10.4 Adds

V13.10.4 turns the V13.10.3 local lifecycle records into a Chinese review
queue for explanation and manual strategy research.

What changed:

- Adds `GET /api/auto-execution-review`.
- Adds Chinese review summaries for lifecycle records, active local holdings,
  blocked records, closed results, and waiting triggers.
- Standardizes user-facing blocker reasons and recommended review actions in
  Chinese without changing the original local records.
- Adds blocker-reason distribution, strategy lifecycle aggregation, symbol and
  direction breakdowns, active holding review, closed result review, and a
  blocked-review queue.
- Adds review priority and blocker-reason standardization coverage so missing
  or ambiguous data can be reviewed before strategy comparisons.
- Keeps unavailable entry price, current price, and R values as null instead of
  inventing results.
- Adds a Chinese `本地自动执行复核队列` panel to the Demo page.

This version only reads local lifecycle and audit records. It does not require
or store API keys, does not connect Trade API or Withdraw API, does not read
real accounts or positions, does not create Demo or live orders, does not run
exchange Dry-run, and does not enable automatic trading or automatic strategy
promotion.

## What V13.10.3 Adds

V13.10.3 adds a local lifecycle monitor for the no-ticket auto execution
records created by V13.10.2.

What changed:

- Adds `GET /api/auto-execution-lifecycle`.
- Adds a visual lifecycle board on the Demo page.
- Groups local auto-execution records into: waiting trigger, local simulated
  holding, 2R take-profit, -1R stop-loss, expired exit, and blocked.
- Shows blockers from the strategy router and local risk gate in a user-facing
  way.
- Keeps the existing no-ticket auto execution engine intact.

This version only reads local simulation and audit records. It does not require
API keys, does not store raw API keys, does not connect private exchange
endpoints, does not read accounts or positions, does not submit Demo or live
orders, and does not enable live automatic trading.

## What V13.10.2 Adds

V13.10.2 combines the auto-execution lifecycle work and the no-ticket execution
boundary into one local-only patch.

What changed:

- Adds `GET /api/auto-execution-engine`.
- Adds `POST /api/auto-execution-engine/run`.
- Removes the user-facing no-key observation ticket action from the main Demo
  page flow.
- Adds a strategy router that resolves same-symbol conflicts, caps each run to
  five local lifecycle records, applies a cooldown, and keeps the 1000 USDT
  local notional cap.
- Adds local risk gates for public-market readiness, 2R target, score, sample
  count, profit factor, and notional size.
- Saves immutable local auto-execution records for review, including TP/SL
  lifecycle policy, route status, risk status, blockers, and safety flags.
- Keeps all exchange order paths locked. The records are local simulation and
  audit records only.

This version still does not require API keys, does not store raw API keys, does
not connect private exchange endpoints, does not read accounts or positions,
does not submit Demo or live orders, and does not enable live automatic trading.

## What V13.10.1 Adds

V13.10.1 makes the no-key pre-live workbench easier to understand before OKX
Demo credentials are available.

What changed:

- Separates old local sandbox samples from new no-key pre-live candidates.
- Shows local sandbox sample counts, daily reports, health snapshots, and
  learning snapshots so existing samples do not look lost.
- Shows long/short direction balance for both the strategy catalog and current
  public-market candidates.
- Changes no-key candidate generation from score-only ordering to a
  balanced-strategy-first order so long research strategies can enter the public
  candidate list.
- Clarifies that current scans use historical `selectedPairs`, not a full OKX
  market-wide scanner yet.
- Adds a long-candidate lane for mean reversion, breakout, and squeeze-breakout
  research candidates.

This version still does not require API keys, does not store raw API keys, does
not connect private exchange endpoints, does not read accounts or positions,
does not submit Demo or live orders, and does not enable automatic trading.

## What V13.10.0 Adds

V13.10.0 adds a no-key pre-live workbench for the waiting period before OKX
Demo credentials are available.

What changed:

- Adds `GET /api/no-key-pre-live`.
- Adds `POST /api/no-key-pre-live/scan`.
- Adds `POST /api/no-key-pre-live/create-ticket`.
- Shows a Chinese desktop panel that explains usable strategies in plain
  language.
- Uses public OKX market data only to screen candidate strategy/symbol pairs.
- Saves local observation tickets with a 1000 USDT maximum notional reference.
- Keeps OKX Demo private connection, Demo order rehearsal, and live trading as
  separate gated stages.

This version does not require API keys, does not store raw API keys, does not
connect private exchange endpoints, does not read accounts or positions, does
not submit Demo or live orders, and does not enable automatic trading.

When OKX Demo credentials are ready, start the console with:

```text
powershell -ExecutionPolicy Bypass -File scripts\start_okx_demo_console.ps1
```

Enter credentials only in the local PowerShell prompt. Do not paste them into
chat. The V13.10.0 no-key tickets can then be used as review context before
running the OKX Demo read-only check.

## What V13.8.5 Adds

V13.8.5 adds a local Sandbox Quality Center to make the ongoing paper-observation
loop easier to judge from the first screen.

What changed:

- Adds `GET /api/local-sandbox/quality-center`.
- Aggregates local sandbox daily reports, simulation review rows, auto-runner
  state, replay cursor state, and readonly testnet-preparation blockers.
- Shows a one-screen quality panel with:
  - closed sample count
  - average quality score
  - continue-observing count
  - testnet-preparation candidate count
  - insufficient-sample count
  - data-gap count
- Adds a clickable strategy quality detail pane showing:
  - what the strategy is
  - latest sandbox trigger context
  - sample performance
  - main risk points
  - next recommended review action
- Clarifies the sandbox run button state and readonly preparation stage.

This version still does not add API key input, API key storage, Trade API,
Withdraw API, real account reads, real position reads, order creation, exchange
Dry-run, live trading, or automatic trading. Testnet preparation remains a
readonly checklist only.

## Start After Reboot

After Windows shutdown, restart, or sleep, the local web console process may be
gone. Run this helper from the repository root:

```text
Start-Control-Console.cmd
```

It will stop any old AlphaPilot Control Console Python process, start the local
server on `http://127.0.0.1:8766/`, run `/api/health`, and open the browser.

## What V13.8.4 Adds

V13.8.4 improves the local sandbox sample path after real console testing showed
that repeated five-minute checks were correctly skipped as duplicate samples.

What changed:

- Adds a local replay cursor to the sandbox auto-runner state.
- Maps each run to a rolling OHLCV replay window when local public OHLCV cache
  exists.
- Includes replay window metadata in sandbox sample keys, logs, run summaries,
  and the auto-runner event stream.
- Prefers actual OHLCV futures/spot files over funding-rate or mark-price files
  when selecting local cache.
- Shows the replay cursor in the desktop console so duplicate skips are easier
  to understand.

This is still local historical replay and paper observation only. It does not
add API key input, API key storage, Trade API, Withdraw API, real account reads,
real position reads, order creation, exchange Dry-run, live trading, or
automatic trading.

## What V13.8.3 Adds

V13.8.3 turns the V13.8.2 local lifecycle preview into a local pre-live
operational closure pack.

New local endpoint:

- `POST /api/pre-live-order-lifecycle/rehearse`

The console now saves local rehearsal records and shows:

- total local rehearsals
- passed local rehearsal paths
- rejected local rehearsal paths
- latest rehearsal state
- pre-live closure checks
- recent rehearsal records
- a local runbook for the next safe steps

Saved rehearsals are local audit records only. They do not create exchange
orders, do not connect private exchange endpoints, do not store credentials, do
not read accounts, do not read positions, and do not run exchange Dry-run.

Even if the local rehearsal paths are complete, execution remains disabled until
a separate future testnet design implements credential isolation, permission
switches, manual confirmation, and kill-switch controls.

This release does not add API key input, API key storage, Trade API, Withdraw
API, real account reads, real position reads, order creation, exchange Dry-run,
live trading, or automatic trading.

## What V13.8.2 Adds

V13.8.2 adds a local pre-live preparation pack before any future testnet or
live integration.

New local endpoints:

- `GET /api/pre-live-preparation-pack`
- `POST /api/pre-live-order-lifecycle/simulate`

The console now shows:

- a local order lifecycle rehearsal
- risk limit and kill-switch design
- credential-vault design requirements
- reference-only lessons from alpha101, CryptoAgentPro.beta, TradingAgents, and
  QuantDigger
- disabled pre-live actions for API keys, private exchange connection, orders,
  cancels, emergency close, and automatic execution

The lifecycle simulation endpoint returns a local status path only. It does not
persist an order, contact an exchange, store credentials, read accounts, read
positions, or run exchange Dry-run.

This release does not add API key input, API key storage, Trade API, Withdraw
API, real account reads, real position reads, order creation, exchange Dry-run,
live trading, or automatic trading.

## What V13.8.1 Adds

V13.8.1 adds a disabled Testnet readiness center to the web console.

New local read-only endpoint:

- `GET /api/testnet-design-boundary`

The console now shows:

- missing Testnet safety controls
- future connection sequence
- disabled API Key / Testnet / order / exchange Dry-run actions
- clear copy that Testnet is not enabled

This release does not add API key input, API key storage, Trade API, Withdraw
API, real account reads, real position reads, order creation, exchange Dry-run,
live trading, or automatic trading.

## What V13.8 Adds

V13.8 completes the four-step research workflow after V13.7.49:

1. `V13.7.50` Research Action Executor
2. `V13.7.51` Candidate Promotion Gate
3. `V13.7.52` Simulation Command Center
4. `V13.8` Testnet Readiness Pack

New local research endpoints:

- `GET /api/research-action-executor`
- `POST /api/research-action-executor/run`
- `GET /api/candidate-promotion-gate`
- `GET /api/simulation-command-center`
- `GET /api/testnet-readiness-pack`
- `GET /api/research-execution-pipeline`
- `POST /api/research-execution-pipeline/run`

The web console adds a "Research Execution Pipeline" panel that shows:

- research action execution results
- task statuses written back to local weakness action tasks
- sandbox review candidates
- Testnet readiness candidates
- Testnet blockers
- the next local research action

The executor can update only local research task status in
`data/console_state.json`. It does not change strategy code, does not connect to
an exchange, does not run exchange Dry-run, and does not create orders.

The Testnet Readiness Pack is a design checklist only. V13.8 keeps
`testnetEnabled=false`, `apiKeyInputEnabled=false`, and
`orderCreationEnabled=false`.

V13.8 does not add API key storage, Trade API, Withdraw API, exchange testnet
orders, real account reads, real position reads, order creation, exchange
Dry-run, live trading, or automatic trading.

## What V13.7.49 Adds

- Adds local task tracking for weakness action items.
- Stores action task state in the local `console_state.json` file under
  `weaknessActionTasks`.
- Adds `GET /api/weakness-action-board/tasks`.
- Adds `POST /api/weakness-action-task`.
- Adds task statuses:
  - todo
  - in progress
  - needs more samples
  - resolved
  - archived
- Updates the web console action board with:
  - task status counters
  - status and priority filters
  - buttons to start, pause for more samples, resolve, or archive an action
  - local notes for each action

This turns replay weaknesses into a repair workflow. It still does not modify
strategy logic automatically, does not start testnet or Dry-run, and does not
create orders.

V13.7.49 does not add API key storage, Trade API, Withdraw API, exchange
testnet orders, real account reads, real position reads, order creation,
exchange Dry-run, live trading, or automatic trading.

## What V13.7.48 Adds

- Adds `GET /api/weakness-action-board`.
- Converts replay weakness labels into research action items.
- Groups action items by strategy, weakness type, severity, sample count, and
  average replay score.
- Adds priority scoring for research repair work:
  - high priority
  - medium priority
  - observe
- Adds blocked-upgrade reasons when a weakness should prevent testnet, Dry-run,
  or live escalation.
- Updates the web console with a Strategy Weakness Action Board directly after
  the closed-sample replay panel.

The action board is a deterministic research layer. It does not change strategy
parameters, does not generate trading advice, does not start Dry-run or testnet,
and does not create orders.

V13.7.48 does not add API key storage, Trade API, Withdraw API, exchange
testnet orders, real account reads, real position reads, order creation,
exchange Dry-run, live trading, or automatic trading.

## What V13.7.47 Adds

- Adds replay scoring for local sandbox closed samples.
- Adds explainable weakness labels for each estimated replay sample:
  - profit not captured
  - deep adverse excursion
  - stop-like loss
  - weak favorable path
  - cost drag
  - holding window too long
  - clean entry path
- Adds strategy-level replay score summaries:
  - average review score
  - strong / usable / weak / poor sample counts
  - top warning and danger labels
- Updates the closed-sample replay panel to show:
  - average replay score
  - primary weakness
  - per-sample review score
  - per-sample weakness tags

The scoring layer is deterministic and explainable. It reads local estimated
sample paths and turns them into review labels. It does not produce trading
advice, does not promote a strategy automatically, and does not create orders.

V13.7.47 does not add API key storage, Trade API, Withdraw API, exchange
testnet orders, real account reads, real position reads, order creation,
exchange Dry-run, live trading, or automatic trading.

## What V13.7.46 Adds

- Adds local sandbox sample path instrumentation for the closed-sample replay
  view.
- Uses local public OHLCV cache files to estimate a replay path when an older
  sandbox log has only an R outcome.
- Adds estimated fields for closed-sample review:
  - entry / exit time
  - entry / exit price
  - direction
  - market regime
  - MFE / MAE in R
  - path outcome in R
  - fee and slippage estimates
  - holding time
  - replay candle window
- Writes the same estimated fields into newly generated local sandbox samples
  without changing the existing sample de-duplication schema.
- Updates `GET /api/closed-sample-replay` so old representative samples can be
  dynamically enriched for review.
- Updates the web console to show `estimated path`, `actualExchangeFill=false`,
  path R, fee R, slippage R, and holding time.

V13.7.46 does not claim that estimated paths are real fills. The path fields
are derived from local public OHLCV cache for research review only. This version
does not add API key storage, Trade API, Withdraw API, exchange testnet orders,
real account reads, real position reads, order creation, exchange Dry-run, live
trading, or automatic trading.

## What V13.7.45 Adds

- Adds `GET /api/closed-sample-replay`.
- Adds `GET /api/closed-sample-replay/strategies`.
- Adds `GET /api/closed-sample-replay/samples`.
- Adds `GET /api/closed-sample-replay/strategies/{strategyId}`.
- Adds a closed-sample replay panel in the advanced research area.
- Uses local sandbox daily-report `closedPaperSampleCount` as the de-duplicated
  sample source instead of raw repeated auto-run logs.
- Shows representative sample details:
  - pair and timeframe
  - run id
  - outcome in R
  - outcome reason
  - virtual capital and virtual equity
  - data status and source path
  - missing replay fields
- Marks incomplete trade-path fields as `pending` instead of fabricating them:
  - entry / exit time
  - entry / exit price
  - direction
  - market regime
  - MFE / MAE
  - fee and slippage estimates
  - holding time
- Keeps the view read-only. It does not promote strategies automatically and
  does not create tickets, orders, Dry-run jobs, or exchange requests.

V13.7.45 does not add API key storage, Trade API, Withdraw API, exchange
testnet orders, real account reads, real position reads, order creation,
exchange Dry-run, live trading, or automatic trading. The replay view is a
local research and instrumentation gap panel only.

## What V13.7.44 Adds

- Adds `GET /api/simulation-review`.
- Adds `GET /api/simulation-review/strategies`.
- Adds `GET /api/simulation-review/queue`.
- Adds `GET /api/simulation-review/strategies/{strategyId}`.
- Builds a local simulation review queue from:
  - usable strategy catalog
  - local sandbox daily reports
  - paper observation logs
  - local sandbox auto-runner state
- Shows a strategy review queue on the simple home page:
  - collecting strategies
  - review-ready strategies
  - promoted-candidate suggestions
  - demoted/reference suggestions
- Adds a detailed simulation review panel in the learning section:
  - closed sample count
  - win rate
  - profit factor
  - average win / average loss in R
  - max consecutive losses
  - max drawdown in R
  - pair / direction / market-regime breakdown when available
  - warning flags such as sample-size, concentration, inactive, risk, and invalidated-sample warnings
- Keeps state transitions as suggestions only. The console does not write
  promoted/demoted status automatically.

V13.7.44 does not add API key storage, Trade API, Withdraw API, exchange
testnet orders, real account reads, real position reads, order creation,
exchange Dry-run, live trading, or automatic trading. The review queue is a
local research triage panel only.

## What V13.7.43 Adds

- Adds `GET /api/simulation-bridge`.
- Builds a local simulation bridge from:
  - usable strategy catalog
  - local sandbox daily reports
  - paper observation logs
  - local sandbox auto-runner state
  - learning snapshots
- Shows a simple simulation status block on the default console home page:
  - local simulation stage
  - simulation-review candidate count
  - closed sample count
  - virtual capital / equity
  - learning sample progress
- Separates three concepts:
  - local sandbox simulation is available now
  - exchange testnet remains disabled in this version
  - real trading remains disabled
- Defines minimum review gates before a strategy can be considered for later
  exchange testnet review:
  - at least 30 closed samples
  - at least 12 rule-matched samples
  - health score at least 65
  - no unresolved risk warnings or invalidated samples
- Defines learning fields and labels for future research models without
  allowing any model to create orders.

V13.7.43 does not add API key storage, Trade API, Withdraw API, exchange
testnet orders, real account reads, real position reads, order creation,
exchange Dry-run, live trading, or automatic trading. It makes the local
simulation loop observable and learnable before any future testnet design.

## What V13.7.42 Adds

- Adds a simplified default desktop console home page.
- Shows only the most important operating state first:
  - safety mode
  - usable strategy count
  - local sandbox state
  - virtual sandbox equity and closed samples
- Adds one clear action row:
  - start or stop local sandbox observation
  - refresh data
  - import reports
  - expand advanced research panels
- Hides complex research sections by default while keeping all old panels and
  code available behind "展开高级研究".
- Keeps strategy detail drawers closed by default so the first screen is easier
  to read.
- Keeps the local sandbox button state explicit: when running, it shows
  "沙盒运行中 · 点击停止".

V13.7.42 is a UI simplification patch only. It does not change strategy logic,
does not add API key input, does not connect Trade API or Withdraw API, does
not read accounts or positions, does not create orders, does not run exchange
Dry-run, and does not enable automatic trading.

## What V13.7.41 Adds

- Adds a unified usable strategy catalog for the local sandbox.
- Merges:
  - the V13.7.21 low-frequency paper-observation task pack
  - the V13.7.40 strict short-cycle selected candidates
- Adds `GET /api/usable-strategy-catalog`.
- Updates the local sandbox runner so the default task pack includes both
  low-frequency and short-cycle research candidates.
- Keeps virtual capital at `1000 USDT` per strategy.
- Keeps the fixed `2R` target requirement visible in the catalog.
- Keeps sandbox sample de-duplication stable so version bumps do not inflate
  closed samples.
- Shows a Chinese usable-strategy catalog panel before the sandbox lane in the
  desktop console.

V13.7.41 does not add API key input, Trade API, Withdraw API, account reads,
position reads, exchange Dry-run, order creation, live trading, or automatic
trading. "Usable" means local-sandbox observable, not tradable.

## What V13.7.39 Adds

- Adds a local Strategy Promotion Gate to separate strategy assets into:
  - survivors
  - lightweight watchlist
  - needs-evidence candidates
  - archived or rejected candidates
  - negative samples
- Adds `GET /api/strategy-promotion-gate`.
- Reads the V13.7.38 Top50 short-cycle backtest report when available and
  turns failed expanded-backtest candidates into negative samples instead of
  letting them keep occupying forward-review attention.
- Keeps the July 10 forward-review blockers visible: real manual forward logs
  and manual closed samples are still required before any manual-review ticket
  can become meaningful.
- Shows the promotion gate in the desktop console so failed short-cycle
  candidates are visibly separated from surviving low-frequency or factor
  candidates.

V13.7.39 does not modify strategy code, run exchange Dry-run, connect API keys,
read accounts or positions, create orders, enable paper execution, enable live
trading, or enable automatic trading. The gate is a read-only research triage
layer.

## What V13.7.37 Adds

- Adds a dedicated Short Cycle Candidate Pool to the desktop console.
- Selects five 15m / 30m / 1h short-cycle research candidates from existing strategy assets and derived templates:
  - 15m Volume Rebound
  - 1h Trend Pullback
  - 1h Short Rejection
  - 30m Volatility Compression Breakout
  - 30m Bollinger Mean Reversion
- Separates candidates with existing short-cycle reports from candidates derived from higher-timeframe strategy assets.
- Adds `GET /api/short-cycle-candidates`.
- Shows each candidate's target timeframe, source asset, short-cycle score, missing metrics, research idea, risk focus, and next validation action.
- Keeps the wording explicit: these are short-cycle research candidates, not tick-level HFT strategies and not execution signals.
- Keeps all execution capability disabled: no API key input, no Trade API, no Withdraw API, no account access, no position access, no real orders, no exchange Dry-run, no live trading, and no automatic trading.

V13.7.37 does not promote these candidates into simulation, testnet, or live
trading automatically. The next engineering step is to backtest the short-cycle
pool on public OHLCV with fees, slippage, liquidity gates, BTC regime filters,
and market-state breakdowns.

## What V13.7.36 Adds

- Adds a "Forward Review Workbench" panel for the July 10 forward-review window.
- Separates real manual forward logs from local virtual sandbox replay logs so sandbox samples cannot be mistaken for real forward evidence.
- Shows each of the five current observation strategies with blockers, rule matches, risk warnings, invalidations, latest logs, and next review action.
- Adds a candidate expansion pool from the existing 60-strategy candidate queue. Expansion candidates remain research candidates only; they are not automatically promoted to live trading.
- Adds `GET /api/forward-review` and `POST /api/forward-review/refresh`.
- Keeps all execution capability disabled: no API key input, no Trade API, no Withdraw API, no account access, no position access, no real orders, no exchange Dry-run, no live trading, and no automatic trading.

V13.7.36 answers the strategy-candidate question directly: yes, more
strategies can be nominated, but only through the research queue, backtest
evidence, forward observation, and the same pre-live review gate. It does not
auto-add candidates to a live list.

## What V13.7.35 Adds

- Adds a local "Live Readiness Gate" panel to the desktop console.
- Checks candidate strategies against local observation quality, rule matches, closed samples, historical sample count, profit factor, reward/risk, drawdown, risk warnings, and invalidation records.
- Uses `2026-07-10` Beijing time as the first forward-review gate; before that date, candidates stay in shadow observation even if local metrics look good.
- Adds local manual execution tickets as review records only. They are not exchange orders and do not connect to any trading endpoint.
- Adds `GET /api/live-readiness`, `GET /api/manual-execution-tickets`, and `POST /api/manual-execution-ticket`.
- Keeps the console read-only toward exchanges: no API key input, no Trade API, no Withdraw API, no account access, no position access, no real orders, no exchange Dry-run, no live trading, and no automatic trading.

V13.7.35 is a pre-live engineering gate, not a live trading release. Passing the
gate only means the console can save a local manual-review ticket; the user must
still make any future external exchange decision manually outside this system.

## What V13.7.34 Adds

- Changes the main "Run Local Sandbox" action into a continuous local observation starter.
- When clicked, the console enables the local auto runner, runs one round immediately, and schedules checks every 5 minutes while the console process is open.
- Raises the local daily auto-run limit to 288 so 5-minute checks can run for a full Beijing day.
- Adds sandbox sample keys so repeated runs against the same task, pair, timeframe, data file, and metrics window are skipped instead of counted as new closed samples.
- Deduplicates closed-sample reporting so existing repeated logs do not inflate strategy health and learning readiness.
- Shows skipped duplicate samples in the run status.

V13.7.34 does not make 5-minute checks equal to 5-minute valid samples. A new
closed sample still requires a new data fingerprint or a genuinely new sandbox
observation window. It also does not add API key input, private exchange access,
account access, position access, order creation, exchange Dry-run, live trading,
or automatic trading.

## What V13.7.33 Adds

- Adds a local auto observation runner for the sandbox lane.
- The runner works only while this desktop control-console process is open.
- Adds configurable interval minutes and max auto-runs per Beijing day.
- Adds `GET /api/local-sandbox/auto-runner`, `POST /api/local-sandbox/auto-runner`, and `POST /api/local-sandbox/auto-runner/run-now`.
- Adds a learning snapshot after each auto run so future ML can use structured local sandbox samples.
- Keeps ML in data-collection mode until enough closed sandbox samples exist; it does not train a trading model in this version.
- Updates the learning-loop panel with auto runner status, next run time, run history, and ML data readiness.

V13.7.33 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automatic
trading. The auto runner only creates local virtual observation logs and
research summaries.

## What V13.7.32 Adds

- Adds a local sandbox daily report builder.
- Summarizes today's virtual observation logs, closed samples, daily `R`, cumulative `R`, wins, losses, and virtual equity.
- Adds per-strategy health scores and health trend deltas from saved local snapshots.
- Adds `POST /api/local-sandbox/build-daily-report` and `GET /api/local-sandbox/daily-report`.
- Updates the learning-loop panel with a "Sandbox Daily Review" section.
- Keeps reports as local review artifacts only; they do not change strategy rules, create signals, or move strategies to testnet/live execution.

V13.7.32 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.31 Adds

- Adds a local sandbox runner for the five paper-observation candidate strategies.
- Generates local virtual observation logs from the V13.7.21 task pack and available public OHLCV cache.
- Uses 1,000 USDT virtual capital per strategy and a 1% virtual risk unit for replayable `R` outcomes.
- Records pair, timeframe, local data status, virtual equity, and reference-only safety metadata on each generated log.
- Stores sandbox run summaries in ignored local state under `data/console_state.json`.
- Reuses external repository notes only as reference-only safety metadata: factor context, risk gateway, human confirmation, and audit-first concepts.
- Does not use API keys, exchange accounts, exchange testnet, real positions, real orders, exchange Dry-run, or automation.

V13.7.31 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.30 Adds

- Adds a local sandbox simulation lane to the learning-loop panel.
- Enrolls all five paper-observation candidates into local virtual-capital tracking.
- Uses 1,000 USDT virtual capital per strategy and paper-result `R` logs when available.
- Keeps local sandbox simulation separate from the Testnet Upgrade Gate.
- Lets local sandbox observation run before any strategy qualifies for future testnet review.
- Does not connect an exchange testnet, create orders, run exchange Dry-run, or add automation.

V13.7.30 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.29 Adds

- Renames the local review gate into a Testnet Upgrade Gate.
- Scores every paper-observation strategy against minimum evidence gates:
  quality score, observation logs, rule matches, closed paper samples, risk warnings, and invalidations.
- Separates strategies into future-testnet-review ready, continue observing, and pause-review states.
- Shows exactly which evidence is missing before a strategy can move toward future testnet review.
- Keeps the gate as a read-only local review layer; it does not connect exchanges, start testnet, create orders, or run automation.

V13.7.29 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.28 Adds

- Adds a read-only Strategy Observation Daily Report to the local learning-loop panel.
- Summarizes today's local paper-observation logs by Beijing date.
- Shows today's signal observations, rule matches, risk warnings, invalidations, and strategy coverage.
- Lists per-strategy observation quality, remaining closed-sample work, latest log time, and next observation action.
- Uses existing local observation task data and recent logs only; it does not create new reports or run backtests.
- Keeps all trading execution abilities disabled.

V13.7.28 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.27 Adds

- Adds a quick paper-observation log form inside the Strategy Detail Drawer.
- Lets the user record no-signal days, seen signals, rule matches, missed observations, invalidations, and risk warnings from the currently selected strategy.
- Saves the log through the existing local `/api/paper-observation-log` endpoint with the selected task `taskId`.
- Refreshes the strategy quality and recent-log panels after saving.
- Keeps all trading execution abilities disabled.

V13.7.27 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.26 Adds

- Adds a collapsible Strategy Detail Drawer under the Strategy Playbook.
- Breaks each selected strategy into fit conditions, avoid conditions, entry observation checklist, invalidation and exit checklist, historical weaknesses, and paper log fields.
- Uses existing local paper-observation task fields instead of inferring live trading signals.
- Keeps the strategy explanation readable while preserving strategy, signal, simulated position, backtest evidence, and mobile bridge in one local console.
- Keeps all trading execution abilities disabled.

V13.7.26 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.25 Adds

- Adds a five-strategy switcher inside the Strategy Playbook panel.
- Lets the user click each paper-observation candidate and read its plain-language strategy explanation.
- Shows each strategy's timeframe, sample count, win rate, profit factor, and quality label on the selector cards.
- Keeps the detailed playbook focused on strategy purpose, conditions, execution blocks, next observation records, recommended assets, and backtest evidence.
- Keeps all trading execution abilities disabled.

V13.7.25 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.24 Adds

- Reduces the main cockpit from a dense one-screen matrix into a conclusion-first dashboard.
- Adds a Strategy Playbook panel that translates strategy IDs into readable Chinese strategy explanations.
- Explains what the current strategy waits for, which conditions matter, why execution remains blocked, and what paper-observation logs should be collected next.
- Keeps strategy, signal, simulated position, backtest evidence, and mobile bridge in one local console, but separates summary, explanation, and evidence layers.
- Keeps all trading execution abilities disabled.

V13.7.24 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.23 Adds

- Imports the Quant Engine V13.7.23 paper-observation quality panel baseline.
- Scores each of the five local paper-observation tasks from local logs.
- Shows priority watch, continue observing, needs risk review, pause candidate, and not started states.
- Adds quality score, log coverage, rule-match coverage, closed-sample coverage, risk warnings, invalidations, and next action notes.
- Keeps the score as local observation completeness only, not trade safety or profit probability.

V13.7.23 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.22 Adds

- Imports the Quant Engine V13.7.22 paper-observation logbook baseline.
- Adds local observation-log entry controls to the five-strategy task-pack cards.
- Stores daily observation logs locally in `data/console_state.json`.
- Shows local log count, rule-match count, signal-observed count, closed paper samples, and recent notes.
- Reuses the existing `/api/paper-observation-log` endpoint with task-pack `taskId` keys.

V13.7.22 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.6 Does

- Reads local AlphaPilot Quant Engine reports.
- Builds a compact strategy package list.
- Shows strategy status, gate results, and report summaries.
- Provides a read-only mobile bridge endpoint.
- Stores local console status and audit logs.

## What V13.6.1 Adds

- Adds a public-only exchange connectivity panel.
- Probes OKX, Binance USD-M Futures, and Bybit USDT perpetual public market data.
- Checks public ticker, OHLCV, funding-rate, and open-interest availability when the exchange endpoint supports it.
- Stores the latest public probe result locally in `data/exchange_probe_results.json`.
- Adds a strategy slot registry for active, observer, and backup strategy packages.
- Exposes exchange status and strategy slots through local API endpoints.

V13.6.1 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.6.3 Adds

- Adds `GET /api/mobile/connection-info`.
- Shows LAN candidate URLs for real phone connection testing.
- Adds `scripts/smoke_mobile_bridge.ps1` to verify health, mobile status, mobile connection info, and execution locks.
- Updates the desktop page Mobile Bridge section with a recommended phone URL and setup notes.

V13.6.3 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.6.5 Adds

- Converts the desktop Control Console UI into a Chinese-first dark quant terminal.
- Adds a left rail, top status bar, portfolio context cards, and a one-screen matrix.
- Places strategy, signal, simulated-position, and backtest-result summaries in one panel.
- Keeps public exchange connectivity, strategy slots, mobile bridge, reports, and audit logs visible.
- Uses a research-terminal style inspired by professional trading dashboards without adding an order panel.

V13.6.5 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.6.6 Adds

- Refines the desktop Control Console into a clearer Chinese quant command terminal.
- Expands the left navigation from icon-only rail to labeled cockpit modules.
- Improves the one-screen command matrix for strategy, signal, simulated position context, and backtest metrics.
- Aligns the mobile app control-console page with the same dark terminal style.
- Keeps mobile focused on current strategy, signal count, simulated PnL context, backtest metrics, public connectivity, and execution locks.

V13.6.6 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.0 Adds

- Adds a "return to cockpit" navigation control and active section status.
- Adds a read-only Strategy Runtime Monitor panel for current strategy, signal samples, health score, execution lock, and next research step.
- Adds a shared `commandSummary` payload for desktop and mobile clients.
- Displays command health and runtime readiness in the one-screen strategy matrix.
- Keeps the desktop and mobile console focused on strategy, signal, simulated research context, and safety locks.

V13.7.0 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.1 Adds

- Reads Quant Engine `reports/runtime_status.json`, `reports/signal_tape.json`, and `reports/paper_observation_ledger.json`.
- Adds `GET /api/runtime` for the full read-only runtime contract payload.
- Extends `GET /api/mobile/status` with compact runtime status, latest signal tape rows, and paper observation rows.
- Displays signal tape and paper observation ledger summaries in the desktop runtime monitor.
- Keeps all runtime data display-only; no signal row can create an order.

V13.7.1 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.

## What V13.7.8 Adds

- Adds local paper-observation logs for strategy artifacts.
- Adds `POST /api/paper-observation-log` and `GET /api/paper-observation-logs`.
- Adds a paper-observation health score based on local observation completeness, risk warnings, invalidations, and missed observations.
- Improves strategy artifact names with readable Chinese display names while preserving original strategy IDs for traceability.
- Shows recent paper-observation logs in the desktop strategy artifact detail panel.
- Extends the mobile status payload with paper-observation health, log counts, latest log time, and recent logs.

V13.7.8 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.
The health score is a local review-completeness score, not a probability of
profit.

## What V13.7.9 Adds

- Adds a forward-validation acceptance summary for the July 10 Beijing-time review window.
- Separates strict active validation from system active tasks and smoke/test-only tasks.
- Adds `GET /api/forward-validation`.
- Extends `/api/mobile/status` with `forwardValidation`.
- Shows formal active validation count, raw active count, test-only active count, candidate pool count, observation-log count, rule-match count, review date, and acceptance gate.
- Defines minimum acceptance checks before a strategy can be reviewed for paper-simulation observation.

V13.7.9 does not add API key input, private exchange access, account access,
position access, order creation, exchange Dry-run, live trading, or automation.
Forward validation is a research acceptance workflow only.

## What V13.6 Does Not Do

```text
no API keys
no Trade API
no Withdraw API
no real account reads
no real position reads
no order creation
no exchange Dry-run
no live trading
no automatic trading
```

## Start

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_console.ps1
```

For real phone testing, start the console on the LAN-visible host:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_console.ps1 -Mobile
```

Default URL:

```text
http://127.0.0.1:8766
```

Smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_console.ps1 -Smoke
```

## API

```text
GET  /api/health
GET  /api/strategies
GET  /api/reports
GET  /api/mobile/status
GET  /api/mobile/connection-info
GET  /api/runtime
GET  /api/strategy-artifacts
GET  /api/audit
GET  /api/exchanges
GET  /api/strategy-slots
GET  /api/pre-live-preparation-pack
GET  /api/testnet-drill
GET  /api/testnet-audit-pack
GET  /api/testnet-permission-check
GET  /api/testnet-small-order-simulation
POST /api/import
POST /api/strategy-status
POST /api/exchanges/probe-public
POST /api/testnet-small-order-simulation/rehearse
POST /api/pre-live-order-lifecycle/simulate
```

The POST endpoints only rescan local files or update local console state. They
cannot place orders or access exchanges.

`POST /api/exchanges/probe-public` only calls public market-data endpoints. It
does not accept, store, or transmit API keys.

## Quant Engine Source

By default the console reads:

```text
D:\Codex-Workspace\AlphaPilot-Quant-Engine
```

Override with:

```powershell
$env:ALPHAPILOT_QUANT_ENGINE_PATH = "D:\Codex-Workspace\AlphaPilot-Quant-Engine"
```

## Mobile Bridge

The mobile bridge is read-only:

```text
http://127.0.0.1:8766/api/mobile/status
```

Real Android phones should use the PC LAN URL rather than `127.0.0.1`.
Use the helper endpoint to see candidates:

```text
http://127.0.0.1:8766/api/mobile/connection-info
```

Smoke test the bridge:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke_mobile_bridge.ps1
```

The mobile App can consume these endpoints to display strategy status.
V13.6 does not add a mobile trading button or execution path.

## Public Exchange Connectivity

The console can probe public market endpoints for a selected symbol, timeframe,
and small candle limit. The probe is meant to verify connectivity and data
availability before later research workflows use these sources.

Supported source profiles:

- OKX public market data
- Binance USD-M Futures public market data
- Bybit USDT perpetual public market data

The probe is deliberately not a trading connector. It does not use credentials,
private endpoints, account data, position data, order endpoints, or emergency
execution paths.

## Strategy Slots

Strategy slots reserve visible places for:

- the active local-paper candidate
- observer research candidates
- future backup candidates

Slots are metadata and review containers only. Empty backup slots do not create
strategy logic, and loaded slots do not execute trades.

## V13.7.4 Strategy Artifact Center

V13.7.4 reads `reports/strategy_artifact_index.json` from the Quant Engine and
shows a Strategy Artifact Center in the desktop console. The same summary is
included in `/api/mobile/status` for the mobile console.

The artifact center shows strategy artifact counts, local paper-observation
candidate counts, research-watchlist counts, review counts, and top artifacts
with sample count, win rate, profit factor, reward-risk ratio, drawdown, and
return.

The endpoint is read-only:

```text
GET /api/strategy-artifacts
```

It cannot place orders, read real accounts, read real positions, use API keys,
run exchange Dry-run, run live trading, or trigger automatic trading.

## V13.7.5 Strategy Artifact Interaction Polish

V13.7.5 turns the Strategy Artifact Center into a faster review console.

What changed:

- Added strategy artifact search by title, report id, version, and source file.
- Added readiness-tier filters for paper-observation candidates, research
  watchlist items, review-needed items, archived/failed reports, and blocked
  reports.
- Added sorting by readiness, research score, return, profit factor, drawdown,
  and source update time.
- Added a selected-artifact detail panel with signal sample count, win rate,
  profit factor, reward/risk, max drawdown, return, paper observation
  eligibility, safety status, recommended action, and readiness reasons.
- Expanded the mobile status payload to include more compact artifact rows for
  phone-side filtering.

Safety boundary:

- This is still a read-only console view.
- It does not add Trade API, Withdraw API, raw API key storage, real account
  reads, real position reads, order creation, dry-run execution, live trading,
  or automatic trading.

## V13.7.6 Strategy Candidate Review Workbench

V13.7.6 adds a local strategy candidate review workbench on top of the Strategy
Artifact Center.

What changed:

- Added local artifact review labels: unreviewed, continue observing, paper
  observation, paused, and rejected.
- Added `POST /api/strategy-artifact-review` for saving desktop-only review
  notes and labels to the local console state.
- Added score explanation fields for win-rate contribution, reward/risk
  contribution, sample-size penalty, drawdown penalty, stability penalty, and
  baseline comparison.
- Added a paper-observation checklist with start time, target sample count,
  current sample count, progress, and required review checks.
- Expanded `/api/mobile/status` so the phone can display review status and
  paper-observation checklist data in read-only mode.

Safety boundary:

- Review labels are local research metadata only.
- Paper observation is a checklist, not an order flow.
- This version does not add Trade API, Withdraw API, raw API key storage, real
  account reads, real position reads, order creation, dry-run execution, live
  trading, or automatic trading.

## V13.7.7 Paper Observation Task Flow

V13.7.7 turns reviewed strategy artifacts into local paper-observation tasks.

What changed:

- Added local paper-observation task state in `data/console_state.json`.
- Added `GET /api/paper-observation-tasks` for the desktop and phone consoles.
- Added `POST /api/paper-observation-task` for desktop-only task updates:
  planned, active, paused, completed, and rejected.
- Selecting `paper_observation` in the artifact review workflow automatically
  creates or refreshes a local observation task.
- Added a desktop `纸面观察任务` panel with task counts, progress, target sample
  counts, observation days, win rate, profit factor, and update time.
- Expanded `/api/mobile/status` with a compact `paperObservationTasks` payload.

Safety boundary:

- Paper-observation tasks are local research workflow records only.
- They do not create orders, read real positions, read real accounts, access
  private exchange endpoints, use API keys, run exchange Dry-run, run live
  trading, or enable automatic trading.

## V13.7.10 ML Coverage Strategy Screening

V13.7.10 adds a strategy ML coverage and candidate-decision layer to the
desktop Strategy Artifact Center.

What changed:

- Each strategy artifact is classified as rule-based, factor-based, ML model,
  benchmark, or report-only.
- Each artifact receives label readiness, walk-forward readiness, ML readiness,
  and a candidate decision such as forward-validation candidate, ML evaluation
  queue, needs backtest, needs labels, research-only, paused, or rejected.
- Added an ML coverage summary card and candidate-decision filter to the web
  console.
- Added `GET /api/ml-coverage` for read-only diagnostics.
- Expanded `/api/mobile/status` so the phone console can show the same ML
  coverage summary.

Safety boundary:

- ML coverage describes research-data readiness only.
- It is not a trading signal and not a profit probability.
- This version does not train a live trading model, does not create orders,
  does not use API keys, does not read accounts or positions, does not run
  exchange Dry-run, and does not enable live or automatic trading.

## V13.7.11 Strategy Candidate Queue

V13.7.11 turns the ML coverage output into a read-only strategy candidate queue.

What changed:

- Added `strategyCandidateQueue` to the imported console payload and mobile
  status payload.
- Added `GET /api/candidate-queue` for desktop and phone diagnostics.
- Ranks existing strategy artifacts into forward-validation priority,
  ML-evaluation queue, needs-backtest, needs-labels, research-watchlist,
  paused, and rejected queues.
- Shows candidate priority score, method type, ML status, label status,
  sample count, win rate, profit factor, reward-risk, drawdown, next action,
  and decision reasons in the web console.

Safety boundary:

- The queue is research triage only.
- It does not change strategy state automatically, create paper tasks, create
  orders, use API keys, read accounts or positions, run exchange Dry-run, or
  enable live or automatic trading.

## V13.7.12 Research Task Board

V13.7.12 turns the strategy candidate queue into a read-only research task board.

What changed:

- Added `researchTaskBoard` to the imported console payload and mobile status payload.
- Added `GET /api/research-task-board` for desktop and phone diagnostics.
- Splits candidate queue items into forward-observation tasks, backtest-gap tasks, label-gap tasks, and ML-evaluation tasks.
- Shows the forward-observation priority list and needs-backtest task list in the web Strategy Artifact Center.
- Keeps task rows as research scheduling artifacts only; no automatic backtest execution, paper-order creation, dry-run execution, or trading action is triggered.

Safety boundary:

- Research tasks are planning records only.
- They do not run strategy backtests automatically, do not create orders, do not use API keys, do not read accounts or positions, do not run exchange Dry-run, and do not enable live or automatic trading.

## V13.7.13 Backtest Completion Import

V13.7.13 reads the Quant Engine completion report:

```text
reports/v13_7_13_backtest_task_completion_report.json
```

What changed:

- Completed needs-backtest items are marked as `补测完成未通过`.
- The candidate queue no longer counts those items as active needs-backtest tasks.
- The research task board no longer shows the six completed V13.7.12 backtest-gap rows.
- The underlying completion report remains read-only evidence from Quant Engine.

Safety boundary:

- The console only imports local report status.
- It does not run backtests, use API keys, read accounts or positions, create
  orders, execute exchange Dry-run, or enable live or automatic trading.

## V13.7.14 Multi-Agent Strategy Review Import

V13.7.14 imports the Quant Engine research review report:

```text
reports/v13_7_14_multi_agent_strategy_review_report.json
```

What changed:

- The report list now includes the V13.7.14 multi-agent strategy review.
- The report summary shows reviewed subject count, research status counts, and
  whether any paper observation candidate exists.
- The review is based on local Quant Engine artifacts only.

Safety boundary:

- This is a research committee-style review only.
- It does not call LLMs from the console, run backtests, use API keys, read
  accounts or positions, create orders, execute exchange Dry-run, or enable live
  or automatic trading.

## V13.7.18 Strategy Learning Loop Import

V13.7.18 imports the cumulative Quant Engine learning-loop reports:

```text
reports/v13_7_15_strategy_learning_loop_report.json
reports/v13_7_16_strategy_refactor_candidates_report.json
reports/v13_7_17_regime_filtered_experiment_specs_report.json
reports/v13_7_18_paper_observation_rereview_report.json
```

What changed:

- Adds `/api/strategy-learning-loop` for read-only access to the combined
  learning-loop payload.
- Adds a desktop `学习闭环` panel showing failure memory, refactor candidates,
  experiment specs, and paper-observation re-review status.
- Extends the report importer so the V13.7.15-V13.7.18 reports appear in the
  latest report list.
- Keeps all paper observation approvals at zero until deterministic backtest
  evidence exists.

Safety boundary:

- The panel is a research planning view only.
- It does not run backtests, use API keys, read accounts or positions, create
  orders, execute exchange Dry-run, or enable live or automatic trading.

## V13.7.19 LF Factor Confluence Backtest Import

V13.7.19 imports the deterministic Quant Engine backtest report:

```text
reports/v13_7_19_lf_factor_confluence_backtest_report.json
```

What changed:

- Adds the V13.7.19 low-frequency factor-confluence deterministic backtest to
  the local report list.
- Extends `/api/strategy-learning-loop` with deterministic backtest metrics:
  trade count, profit factor, gate status, and paper-observation approval.
- Shows deterministic backtest trade count and PF in the desktop learning-loop
  panel.
- Keeps the candidate in research because the 2023-2024 walk-forward
  validation split is negative.

Current imported result:

- tradeCount: 92
- winRatePct: 39.1304
- profitFactor: 1.1694
- targetRewardRiskRatio: 2.0
- maxDrawdownPct: 18.8774
- paperObservationApproved: false

Safety boundary:

- The console only imports local deterministic backtest evidence.
- It does not run exchange Dry-run, use API keys, read accounts or positions,
  create orders, enable paper execution, enable live trading, or enable
  automatic trading.

## V13.7.20 Five Strategy Candidate Factory Import

V13.7.20 imports the Quant Engine batch candidate factory report:

```text
reports/v13_7_20_five_strategy_candidate_factory_report.json
```

What changed:

- Adds the V13.7.20 five-strategy candidate factory report to the local report
  list.
- Extends `/api/strategy-learning-loop` with candidateCount, approvedCount,
  targetApprovedCount, and paper-observation approval count.
- Imports the five approved candidates into the desktop strategy panel as local
  paper-observation strategy assets.
- Shows five-strategy candidate counts in the learning-loop panel.

Current imported result:

- candidateCount: 120
- approvedCount: 5
- targetApprovedCount: 5
- paperObservationApprovedCount: 5
- targetRewardRiskRatio: 2.0
- dryRunApproved: false
- liveTradingApproved: false

Imported candidate names:

- 1D 趋势突破确认 ATR2.0
- 1D 横盘超卖修复 ATR1.2
- 1D 横盘超卖修复 ATR1.0
- 1D 趋势低波突破 ATR2.0
- 1D 广谱低波突破 ATR2.0

Safety boundary:

- These are local paper-observation candidates, not live strategies.
- The console does not run exchange Dry-run, use API keys, read accounts or
  positions, create orders, enable paper execution, enable live trading, or
  enable automatic trading.

## V13.7.21 Paper Observation Task Pack Import

V13.7.21 imports the Quant Engine paper-observation task pack:

```text
reports/v13_7_21_paper_observation_task_pack_report.json
```

What changed:

- Extends `/api/strategy-learning-loop` with paper-observation task pack
  metrics.
- Shows the five planned paper-observation tasks in the desktop learning-loop
  panel.
- Displays observation days, target closed samples, historical PF, win rate,
  drawdown, and candidate weak points.

Current imported result:

- taskCount: 5
- plannedPaperObservationCount: 5
- targetClosedSamplesTotal: 130
- dryRunApproved: false
- liveTradingApproved: false

Safety boundary:

- The task pack is a local research checklist.
- It does not create orders, run exchange Dry-run, use API keys, read accounts
  or positions, enable live trading, or enable automatic trading.

## V13.8.8 Strategy Asset Playbook and Testnet Gate

V13.8.8 makes the current local sandbox strategy set easier to understand before
any testnet or live-trading work is considered.

What changed:

- Adds `GET /api/strategy-asset-playbook`.
- Adds a Strategy Asset Gate panel to the local web console.
- Groups current candidates into readable strategy families such as 1h upper
  wick rejection, daily oversold repair, daily low-volatility breakout, and
  daily trend confirmation.
- Shows closed samples, win rate, profit factor, total R, next action, and
  blocker status in one place.
- Keeps execution locked: no API key input, no Trade API, no Withdraw API, no
  account or position reads, no order creation, no exchange dry-run, and no
  automatic trading.

The Testnet gate remains blocked until credential isolation, order lifecycle
simulation, kill switch, max-order and max-loss limits, manual confirmation,
and audit trail controls are implemented and reviewed.

## V13.8.9 Local Testnet Drill Panel

V13.8.9 adds a local Testnet Drill layer on top of the Strategy Asset Gate and
the pre-live rehearsal records.

What changed:

- Adds `GET /api/testnet-drill`.
- Adds a Testnet local drill panel to the web console.
- Uses 1,000 USDT virtual account sizing for the drill template.
- Shows review candidates, testnet-drill candidates, rehearsal count, closure
  state, lifecycle steps, and risk template in one place.
- Adds a button that saves one local lifecycle rehearsal record only.
- Alternates the saved rehearsal path toward missing approval/rejection coverage
  so the local lifecycle audit can be reviewed faster.

Safety boundary:

- The drill is local audit rehearsal only.
- It does not add API key input or API key storage.
- It does not connect private exchange endpoints.
- It does not enable Trade API, Withdraw API, real account reads, real position
  reads, order creation, exchange Dry-run, live trading, or automatic trading.

## V13.8.10 Testnet Upgrade Audit Pack

V13.8.10 adds a local Testnet Upgrade Audit layer after the Testnet Drill panel.

What changed:

- Adds `GET /api/testnet-audit-pack`.
- Combines the Strategy Asset Gate, Testnet Drill, Pre-live Preparation Pack,
  Testnet Readiness Pack, and Testnet Design Boundary into one audit result.
- Shows whether the console can enter local design review, whether testnet
  connection is still blocked, and which hard blockers remain.
- Separates safety gates from product gates:
  - local lifecycle rehearsal coverage
  - strategy local review sample coverage
  - API key and credential vault blocker
  - manual unlock blocker
  - public probe evidence
  - order creation and exchange execution lock

Safety boundary:

- This audit pack is local review only.
- It does not enable testnet connection.
- It does not add API key input or API key storage.
- It does not connect private exchange endpoints.
- It does not enable Trade API, Withdraw API, real account reads, real position
  reads, order creation, exchange Dry-run, live trading, or automatic trading.

## V13.9.0 Testnet Read-only Permission Check

V13.9.0 adds a read-only Testnet permission check layer.

What changed:

- Adds `GET /api/testnet-permission-check`.
- Displays public probe status, permission blockers, API key state, private
  connection state, and reference-only design inputs.
- Reuses the previously stored reference lessons from alpha101,
  CryptoAgentPro.beta, TradingAgents, and QuantDigger as design metadata only.
- Keeps API key input, credential storage, private testnet connection, Trade API,
  Withdraw API, and order creation disabled.

## V13.9.1 Testnet Small Order Simulation

V13.9.1 adds a local-only small Testnet order simulation ticket.

What changed:

- Adds `GET /api/testnet-small-order-simulation`.
- Adds `POST /api/testnet-small-order-simulation/rehearse`.
- Uses a 1000 USDT virtual account and a user-entered local ticket size capped at 1000 USDT.
- Saves simulated ticket history to local console state and audit log.
- Shows the simulated lifecycle from candidate selection to audit closeout.

Safety boundary:

- The ticket is not an exchange order.
- It does not connect private testnet endpoints.
- It does not accept, store, or log raw API keys.
- It does not enable Trade API, Withdraw API, real account reads, real position
  reads, exchange orders, exchange Dry-run, live trading, or automatic trading.

## V13.9.5 Mode-separated Console and OKX Demo Simulation

V13.9.5 reorganizes the control console around the real operating path:

1. Local Sandbox and Local Simulation
2. OKX Demo Trading simulation
3. Future live trading, still locked

What changed:

- Adds a first-level Local Lab page that combines local sandbox, local
  simulation equity, closed samples, and strategy review status.
- Adds a separate OKX Demo page designed like an exchange order and observation
  panel.
- Adds `GET /api/exchange-demo/simulation`.
- Adds `POST /api/exchange-demo/read-only-check`.
- Adds `POST /api/exchange-demo/order`.
- Adds `POST /api/exchange-demo/emergency-stop`.
- Hides older detailed observation/testnet panels behind Advanced Research mode
  so the main console is easier to operate.

OKX Demo credentials are environment-variable only:

```powershell
$env:ALPHAPILOT_OKX_DEMO_ENABLED="1"
$env:ALPHAPILOT_OKX_DEMO_API_KEY="your-demo-key"
$env:ALPHAPILOT_OKX_DEMO_SECRET_KEY="your-demo-secret"
$env:ALPHAPILOT_OKX_DEMO_PASSPHRASE="your-demo-passphrase"
```

Demo order submission is separately locked:

```powershell
$env:ALPHAPILOT_OKX_DEMO_ORDER_ENABLED="1"
```

Demo emergency cancel is also separately locked:

```powershell
$env:ALPHAPILOT_OKX_DEMO_CANCEL_ENABLED="1"
```

Safety boundary:

- Use OKX Demo credentials only, never live API credentials.
- Raw API keys are not stored in the browser, SQLite, or console state.
- OKX Demo requests require the `x-simulated-trading: 1` header.
- Demo order requests require a user-entered `OKX_DEMO_ORDER_APPROVED`
  confirmation phrase.
- Demo order notional is capped at 1000 USDT.
- Live trading, Withdraw API, real account trading, real order creation, and
  automatic trading remain disabled.

## V13.9.6 OKX Demo Runbook and Launcher

V13.9.6 makes OKX Demo startup safer and easier to operate.

What changed:

- Adds `scripts/start_okx_demo_console.ps1`.
- Adds an OKX Demo runbook strip to the Demo page.
- Adds a latest read-only check result panel showing balance endpoint status,
  position endpoint status, OKX return codes, blockers, and next action.
- Updates `/api/exchange-demo/simulation` to include `readonlySummary`,
  `runbook`, and `launcher` metadata.

Read-only Demo startup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_okx_demo_console.ps1
```

Mobile Demo startup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_okx_demo_console.ps1 -Mobile
```

Manual Demo order rehearsal startup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_okx_demo_console.ps1 -EnableOrder
```

Emergency cancel rehearsal startup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_okx_demo_console.ps1 -EnableCancel
```

Safety boundary:

- The launcher prompts for OKX Demo credentials and injects them into the
  current PowerShell process environment only.
- The launcher does not write raw API keys to files.
- `-EnableOrder` is not enabled by default.
- `-EnableCancel` is not enabled by default.
- OKX Demo order submission still requires the page-level
  `OKX_DEMO_ORDER_APPROVED` phrase, explicit OKX `sz`, and the 1000 USDT cap.
- Live trading, Withdraw API, live API keys, real account trading, and automatic
  trading remain disabled.

## V13.9.7 Page-separated Control Console and Demo Candidate Pipeline

V13.9.7 makes the desktop control console easier to operate by separating the
main workflow into four pages:

1. `策略`
2. `本地模拟`
3. `Demo模拟`
4. `实盘交易`

Updated in this patch:

- The left navigation now switches pages instead of forcing all modules into one
  long scrolling page.
- `本地模拟` now shows real simulation bridge, review queue, and learning-loop
  status instead of empty placeholder cards.
- The old advanced `运行本地沙盒` entry remains available only in advanced
  research mode; the main flow has one clear local sandbox button.
- `Demo模拟` now loads usable and candidate strategies, builds an automatic
  candidate list, and can scan OKX public market data before filling the Demo
  ticket.
- The Demo candidate pipeline only uses local strategy data and public market
  data. It does not use API keys, private endpoints, account data, positions,
  or orders.
- Filling a Demo ticket is not order execution. OKX Demo order submission still
  requires environment-only Demo credentials, the order gate, explicit `sz`, and
  the manual confirmation phrase.
- `实盘交易` is a locked page that documents the future live gate. Live trading,
  Withdraw API, raw API key storage, real account access, real position access,
  real order creation, and auto trading remain disabled.

## V13.9.8 Navigation Simplification and Mobile Console Page

V13.9.8 removes duplicated research/debug entries from the main navigation and
keeps the console focused on five operator-facing pages:

1. `策略`
2. `本地模拟`
3. `Demo模拟`
4. `实盘交易`
5. `手机控制台`

Updated in this patch:

- The left navigation now only shows the five main workflow pages.
- The former `手机端连接` panel is promoted to a standalone `手机控制台` page.
- Advanced research, audit, public probe, strategy slots, and debug JSON remain
  in the codebase but stay behind the `展开高级研究` control instead of crowding
  the primary navigation.
- The `#mobile` legacy hash redirects to `#mobileConsole` for compatibility.
- No trading capability is added. Live trading, Withdraw API, raw API key
  storage, real account access, real position access, real order creation, and
  auto trading remain disabled.

## V13.9.9 Control Console Performance Patch

V13.9.9 improves the local desktop console loading path after diagnosing that
the slow page load was caused by local report scanning and large JSON payloads,
not by internet speed.

Updated in this patch:

- The first screen loads only the core five-page console summaries.
- Local sandbox result review, quality review, simulation review, and learning
  loop data are loaded after the first render or when the relevant page is
  opened.
- Full mobile status JSON is loaded only on the `鎵嬫満鎺у埗鍙癭 page.
- Advanced research and debug panels are loaded only after `灞曞紑楂樼骇鐮旂┒`
  is enabled.
- Slow read-only GET endpoints use short in-process TTL caches. POST actions
  still run live and are not cached.
- No trading capability is added. Live trading, Withdraw API, raw API key
  storage, real account access, real position access, real order creation, and
  auto trading remain disabled.

## V13.15.2 Secure OKX Demo Integration

V13.15.2 hardens the existing OKX Demo connection before any formal strategy
automation is enabled.

Updated in this patch:

- Uses one allowlisted `OkxDemoClient` for signing and all OKX Demo private
  requests.
- Fixes the selected account site to Global and the REST origin to
  `https://openapi.okx.com`.
- Requires `x-simulated-trading: 1` on every private Demo request.
- The first check reads only account configuration, the USDT Demo balance, and
  SWAP Demo positions.
- Persisted check events contain only endpoint status, OKX return code, site,
  timestamp, and redacted metadata. Account values and credentials are not
  written to console state.
- `-EnableOrder` opens a `connectivity_smoke_only` lane. A smoke order is not
  strategy evidence and cannot create a Demo Release or Live Candidate.
- Connectivity smoke events retain the OKX `ordId`/`clOrdId`, expose a scoped
  order-status check, and allow cancellation by either identifier so a pending
  smoke order can always be traced and cleaned up.
- Formal automated strategy execution remains locked until an immutable,
  eligible Demo Release passes every release and runtime gate.
- Raw API key, secret, and passphrase values exist only in the launcher process
  environment and are removed when that process exits.

Global-site read-only startup:

```powershell
cd D:\Codex-Workspace\AlphaPilot-Control-Console
powershell -ExecutionPolicy Bypass -File scripts\start_okx_demo_console.ps1
```

Connectivity smoke startup, only after the read-only check passes:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_okx_demo_console.ps1 -EnableOrder
```

Safety boundary:

- Use only an OKX Demo Trading Read+Trade key. Do not use a live key and do not
  enable Withdraw permission.
- Connectivity smoke results do not promote strategies.
- A missing Demo Release always blocks formal strategy automation.
- Live trading and Withdraw API remain disabled.

## V13.24.0 Versioned Risk Profile Console

V13.24.0 makes the conservative account assumptions configurable without
turning them into mutable runtime globals.

Updated in this version:

- Adds immutable Local Forward, OKX Demo, Live Canary, and Live Standard risk
  profiles with checksums and append-only activation history.
- Adds a Chinese Live-page panel to save a new version, activate it with an
  exact confirmation phrase, or roll back to a previous version.
- Adds portfolio-wide strategy, position, symbol, direction, and correlation
  exposure checks, plus daily-loss, drawdown, Canary-loss, cooldown, data, and
  liquidity gates.
- Binds the active profile id/hash to release checks; a mismatch fails closed.
- Keeps the reviewed `SafetyEnvelope` outside routine UI control.

Saving or activating a profile does not grant order permission. V13.24.0 adds
no Live exchange adapter, stores no raw API credentials, exposes no Withdraw
capability, and keeps Live execution disabled.

## V13.26.0 Formal Execution Outcome Export

The Control Console exports only fully closed, reconciled, checksum-bound
OKX Demo and Live Canary outcomes. Entry fills without exit evidence remain in
the quarantine list and cannot enter Quant Engine learning.

Use the `闭环执行证据` panel on the Live page, or call the local-only endpoint:

```text
POST /api/execution-outcomes/export
```

The export contains no raw credentials or account balances and does not place
orders. It is consumed only by the Quant Engine offline feedback importer.

## V13.27.1 Workflow Strategy Page

V13.27.1 gives the Strategy page one clear Quant Engine workflow projection.

- Each immutable strategy version appears in exactly one current lane:
  `待回测`, `回测中`, `回测通过`, or `未通过 / 阻塞`.
- The page can request a real local backtest worker, pause/cancel/retry work,
  archive a version, or advance a passed version. The UI cannot write a pass or
  fail decision itself.
- Progress and final gate results come from the Quant Engine registry through
  `GET /api/workflow`.
- Legacy research summaries remain collapsed and do not count as active
  workflow strategies.
- Mobile layout uses one-column, full-width controls with no horizontal
  overflow.

The current Alpha191 observer remains visibly waiting for formal data lineage;
the console does not fabricate a successful backtest. This release adds no
credential persistence, exchange order creation, automatic promotion, or Live
activation. See `docs/V13.27.1-workflow-strategy-page.md`.

## V13.27.1.1 Dual-Data Backtest Action

V13.27.1.1 keeps the Strategy page concise while exposing the real dual-layer
workflow state from Quant Engine.

- `一键回测` first inspects the existing read-only local research warehouse,
  then prepares official OKX public data required by the immutable strategy
  contract.
- The card shows the current phase, research/formal evidence class, public-data
  download progress, coverage, and the only permitted automatic next stage:
  Local Forward.
- A local research smoke result cannot promote a strategy. Only a checksum-bound
  formal backtest pass may create an awaiting Local Forward run.
- The UI never creates a pass result, Demo release, Live candidate, or order.

Release checks passed with 76 Console tests and Node syntax validation. The
bounded public-data integration result is documented in
`docs/V13.27.1.1-dual-data-one-click-backtest.md`.

## V13.27.1.2 Targeted Strategy Optimization Actions

V13.27.1.2 completes the actionable failure path on the Strategy, Local
Simulation, and Demo pages.

- Failed or blocked backtests now show `重新回测`, `改善优化`, and `归档`.
- Data-integrity blockers use the same immutable strategy version and restart
  the official-data preparation path; strategy-performance failures require a
  changed version.
- `改善优化` shows the recorded current parameters, stage evidence, proposed
  values, and a reason for each suggested change. It adjusts only existing
  parameters and keeps all target-R fields locked at `2R` or higher.
- Local Simulation and Demo cards expose the same optimization dialog. An
  optimized legacy strategy is imported into the canonical workflow, while its
  original samples remain attached to the original strategy.
- Confirming an optimization creates an immutable version and starts it again
  at backtesting. It never edits a running Local/Demo strategy in place.

The suggestions are deterministic research heuristics, not AI promises or
profit guarantees. This patch adds no API key storage, Trade API, Withdraw API,
Demo order, real order, or automatic Live activation.
