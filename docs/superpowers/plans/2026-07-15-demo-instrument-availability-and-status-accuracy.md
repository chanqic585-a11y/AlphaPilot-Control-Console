# Demo Instrument Availability and Status Accuracy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Filter OKX Demo-unavailable instruments before submission, safely continue after exchange code 51001, and correct misleading workflow/runtime labels.

**Architecture:** The authenticated Demo client exposes the account-instruments read endpoint. The closed-candle batch resolves one immutable tradable-instrument set, filters signals before arbitration, and preserves exclusions as audit rows. The execution engine classifies 51001 as a known non-fatal terminal rejection while retaining fail-closed behavior for every other rejection.

**Tech Stack:** Python 3 standard library, SQLite, unittest, vanilla JavaScript, local HTTP console.

## Global Constraints

- All changes stay under `D:\Codex-Workspace`.
- Keep `x-simulated-trading: 1` on Demo private requests.
- Do not add Withdraw, live-order access, credential persistence, or safety-gate bypasses.
- A skipped or rejected instrument is not a successful order and is not strategy evidence.

---

### Task 1: Demo Account Instrument Discovery

**Files:**
- Modify: `alphapilot_control_console/exchange_connectors/okx_demo_client.py`
- Test: `tests/test_okx_demo_client.py`

- [ ] Write a failing test that calls `get_account_instruments("SWAP")` and asserts `GET /api/v5/account/instruments`, `instType=SWAP`, and `x-simulated-trading: 1`.
- [ ] Run `python -m unittest tests.test_okx_demo_client -v` and confirm the missing method/end-point failure.
- [ ] Add the allowlisted endpoint and minimal client method.
- [ ] Re-run the test and confirm it passes.

### Task 2: Non-Fatal 51001 Classification

**Files:**
- Modify: `alphapilot_control_console/demo_execution_engine.py`
- Test: `tests/test_demo_execution_engine.py`

- [ ] Write a failing test where OKX returns `code=1`, `sCode=51001`; assert the record is rejected and `paused` remains false.
- [ ] Write a control test where a different rejection code still pauses entries.
- [ ] Run both tests and confirm the new 51001 behavior fails before implementation.
- [ ] Add a narrowly scoped rejection classifier and retain generic fail-closed behavior.
- [ ] Re-run the engine tests.

### Task 3: Batch Filtering and Accurate Counts

**Files:**
- Modify: `alphapilot_control_console/evolution_demo_service.py`
- Test: `tests/test_demo_automatic_batch.py`

- [ ] Write a failing batch test with one unsupported and one supported signal. Assert only the supported signal reaches the engine and the unsupported row is audited as `demo_instrument_unavailable`.
- [ ] Write a failing test that a late 51001 rejected record does not increment `createdOrderCount` or portfolio exposure and does not stop later supported signals.
- [ ] Load account instruments once per batch, filter before arbitration, and classify returned records before exposure accounting.
- [ ] Re-run the batch tests.

### Task 4: Console Status Accuracy

**Files:**
- Modify: `web/app.js`
- Modify: `web/index.html`
- Test: `tests/test_console_status_copy.py`

- [ ] Write static contract tests asserting separate `queued` and `running` buckets and distinct current versus historical Demo result labels.
- [ ] Run the contract test and verify it fails.
- [ ] Update the strategy summary and Demo runtime renderer without changing workflow actions.
- [ ] Re-run the contract test.

### Task 5: Regression and Runtime Verification

**Files:**
- Modify: `README.md`
- Modify: `D:\Codex-Workspace\踩坑日志.txt`

- [ ] Run all targeted Demo and workflow tests.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `git diff --check`.
- [ ] Query the local runtime read-only and verify current ARM, desired state, pause reason, last error, and next evaluation time without printing credentials.
- [ ] Document the 51001 handling and current/history status distinction.
