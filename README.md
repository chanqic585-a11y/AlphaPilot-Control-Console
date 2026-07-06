# AlphaPilot Control Console

Current version:

```text
AlphaPilot V13.7.1 - Runtime Contract Signal Tape Bridge
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
