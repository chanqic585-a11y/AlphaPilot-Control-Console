# AlphaPilot Control Console

Current version:

```text
AlphaPilot V13.7.27 - Strategy Detail Quick Observation Log
```

AlphaPilot Control Console is a local desktop web console for reviewing
AlphaPilot Quant Engine research outputs and preparing a mobile-safe control
status bridge.

It is not a trading execution system.

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
