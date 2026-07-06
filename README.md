# AlphaPilot Control Console

Current version:

```text
AlphaPilot V13.6 - Control Console Bridge
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
GET  /api/audit
POST /api/import
POST /api/strategy-status
```

The POST endpoints only rescan local files or update local console state. They
cannot place orders or access exchanges.

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

Future mobile App work can consume this endpoint to display strategy status.
V13.6 does not add a mobile trading button or execution path.
