# AlphaPilot Control Console

Current version:

```text
AlphaPilot V13.7.9 - Forward Validation Acceptance Console
```

AlphaPilot Control Console is a local desktop web console for reviewing
AlphaPilot Quant Engine research outputs and preparing a mobile-safe control
status bridge.

It is not a trading execution system.

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
POST /api/import
POST /api/strategy-status
POST /api/exchanges/probe-public
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
