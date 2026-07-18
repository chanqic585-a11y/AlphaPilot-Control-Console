# V37A Execution Function Core Design

## Status

Approved for implementation on 2026-07-19 as the execution-track companion to V35.

## Product decision

Function precedes visual polish. The Console first exposes truthful, tested runtime contracts; the Chinese operator UI then renders those contracts without inventing state.

Research and execution remain isolated. The Console consumes immutable Releases and read-only research receipts. It cannot edit candidates, gates, preregistrations, Formal evidence, or Locked OOS results.

## Scope

V37A strengthens the existing execution stack rather than replacing it:

- one consolidated execution-control status projection;
- explicit Demo and Live environment identity;
- persisted desired state separated from process-local credential/ARM state;
- idempotent action requests and deterministic blocker codes;
- startup and crash recovery without duplicate submission;
- order lifecycle and reconciliation health summaries;
- risk and kill-switch readiness summaries;
- Workflow Validation Demo support that remains statistically isolated;
- Live readiness only, default OFF and fail closed.

## Alternatives

1. Redesign the current execution engine. Rejected because the repository already has tested Demo, Live, reconciliation, and unified controller modules.
2. Add UI-specific aggregation in JavaScript. Rejected because duplicated state derivation would drift from backend truth.
3. Add a backend read model over existing stores/controllers, then a thin UI. Selected.

## Consolidated read model

`GET /api/execution-control/status` returns redacted, operational state only:

- generatedAt and schemaVersion;
- researchTrack receipt summary;
- Demo: process, desiredEnabled, armedForCurrentProcess, credentialReady, releaseCount, market feed, last heartbeat, next evaluation, last error, blockers, orders, positions, reconciliation, risk and kill switch;
- Live: same categories but always reports default-disabled readiness until separately authorized;
- cross-track: exact Release/Approval hashes and mismatch blockers;
- nextActions: deterministic Chinese action codes/labels without secrets.

No raw credential, request signature, passphrase, account secret, or full exchange payload can enter this projection.

## Action contract

`POST /api/execution-control/action` accepts an idempotency key and one bounded action. Existing environment-specific actions remain compatible. V37A only adds orchestration around safe existing actions.

Demo may start/arm only when process-local Demo credentials, immutable Release, environment identity, risk profile, and reconciliation preflight pass. Live cannot start or arm through V37A unless the existing exact manual approval path and separate process gates pass; tests use fakes only.

## Recovery semantics

- Desired enabled state may persist.
- Credentials and ARM are process-local.
- Restart never silently restores ARM.
- Unknown in-flight orders reconcile before retry.
- A network timeout queries by deterministic `clOrdId` before any resubmission.
- Reconciliation failure, stale market/account data, environment mismatch, or unknown position triggers fail-closed pause/kill-switch status.

## Workflow Validation Demo

A diagnostic-only immutable Release can exercise discover, authorize, submit, inspect, exit/cancel, reconcile, and report. Its ledger is separate and it cannot contribute to strategy PF, Formal evidence, or Live promotion.

## UI boundary

The first UI slice is a compact Chinese operations panel with stable dimensions and five sections:

1. 双轨总览
2. Demo 运行
3. 实盘就绪（默认关闭）
4. 订单与持仓
5. 阻塞与下一步

Advanced evidence is collapsed. UI actions map one-to-one to backend action codes. No API key form is added to the page.

## Verification

- projection tests with complete, missing, stale, blocked, and mismatch states;
- redaction tests;
- idempotency tests;
- startup recovery and unknown-order reconciliation tests;
- Demo/Live ledger and process isolation tests;
- Live default-OFF and fail-closed tests;
- existing Console full regression;
- browser DOM, screenshot, narrow viewport, and console-error checks after UI implementation.
