# V13.27.6 Demo Resume and Official Download Progress Design

## Goal

Fix two runtime-state gaps without changing strategy definitions or execution
permissions:

1. `启动/保持自动运行` must explicitly resume a normally paused OKX Demo
   runtime before rerunning preflight and reconciliation.
2. A long OKX official-history partition must expose durable page-level progress
   instead of leaving the workflow card at a static phase percentage.

## Demo resume semantics

The Demo start action is an explicit operator resume. It clears the ordinary
`paused` flag, records a resume event, arms the current process, and wakes the
existing heartbeat. The next heartbeat still runs credentials, read-only,
reconciliation, account and risk checks. Any failed gate pauses entries again.

The start action must never clear `killSwitch`. A set kill switch returns a
closed failure and remains set until a separate reviewed operation clears it.
Live behavior is unchanged by this patch.

## Official download progress

`OkxPublicClient.history_candles` reports page progress through an optional
callback after every accepted page. `OfficialHistoryCollector` persists a
throttled `inProgress` record in the existing contract checkpoint, including:

- instrument ID and timeframe;
- requested page count and estimated maximum pages;
- collected confirmed-row count;
- oldest downloaded candle timestamp;
- update time.

The callback writes on page 1, every 25 pages, and the final page. Completed
partitions remove `inProgress` and continue using the existing immutable
partition record. No partial partition becomes formal evidence.

The workflow projection exposes this record under `downloadProgress.active`.
The Console shows a second, subordinate progress bar and text such as
`BTC-USDT-SWAP · 5m · 1,250 / 6,800 页 · 124,972 根 K 线`. The existing workflow
phase bar remains an overall phase indicator and no longer appears to be the
only measure of activity.

## Failure and restart behavior

- Pause/cancel checks remain page-level.
- A stopped process may lose only pages from the current incomplete partition;
  completed partitions remain reusable.
- Restart reads the durable `inProgress` record for visibility, then safely
  restarts that incomplete partition; it never treats partial rows as complete.
- Missing or malformed progress metadata is ignored and cannot block a run.

## Safety boundary

- OKX Demo only for automatic resume.
- No raw credential storage.
- No Withdraw capability.
- No Live permission or Live auto-resume change.
- No database migration.
- No change to strategy, target R, formal evidence or promotion gates.

## Validation

- Test that Demo start resumes an ordinary pause before ARM/start.
- Test that a kill switch prevents resume.
- Test page callbacks and throttled checkpoint persistence.
- Test projection and UI rendering of active partition progress.
- Run full Quant and Console suites, compileall, Node syntax, diff checks and
  changed-line safety scans.
