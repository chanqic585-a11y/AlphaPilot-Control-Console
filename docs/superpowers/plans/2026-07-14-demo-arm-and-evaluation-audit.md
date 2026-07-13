# AlphaPilot Demo ARM and Evaluation Audit Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `executing-plans` and complete each task with RED-GREEN-REFACTOR.

**Goal:** Make an explicitly confirmed OKX Demo launcher arm the current Console PID on startup, and persist enough redacted batch evidence to distinguish no evaluation, no match, risk rejection, order submission, and order failure.

**Architecture:** The PowerShell launcher emits a process-only confirmation flag only after the existing exact phrase. `http_app.run_server` starts market and runner services, then a small fail-closed startup helper invokes the existing `okx_demo/start` action for the current PID. A pure batch-audit projector summarizes scanner, arbitration, latency, risk, and order outcomes without credentials or account values; the controller persists that summary in `heartbeat_completed`, and the Demo UI renders the latest state.

**Tech Stack:** Python 3, `unittest`/`pytest`, SQLite append-only event store, vanilla JavaScript, PowerShell.

---

## Task 1: Restore the existing version-contract baseline

**Files:**
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `alphapilot_control_console/unified_auto_execution_runner.py`
- Modify: `web/app.js`
- Test: `tests/test_workflow_ui_contract.py`

1. Update the runtime/UI version strings to `V13.27.11` and matching source identifiers so the existing README contract is consistent.
2. Run `python -m pytest tests/test_workflow_ui_contract.py -q` and confirm the pre-existing failure is green.
3. Commit as `Fix Console version contract baseline`.

## Task 2: Arm only an explicitly confirmed launcher process

**Files:**
- Create: `alphapilot_control_console/demo_startup_arm.py`
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `scripts/start_okx_demo_console.ps1`
- Modify: `tests/test_workflow_startup_recovery.py`
- Modify: `tests/test_okx_demo_launcher_script.py`

1. Add failing tests proving startup does not call the Demo start action without all four conditions: launcher confirmation, Demo enabled, order enabled, and automation enabled.
2. Add a failing test proving startup calls `run_unified_auto_execution_action({"environment": "okx_demo", "action": "start"})` exactly once after the unified runner starts when all conditions are true.
3. Add a launcher contract test requiring `ALPHAPILOT_OKX_DEMO_LAUNCHER_CONFIRMED=1` only after the existing exact confirmation phrase and requiring cleanup in `finally`.
4. Run the focused tests and observe the expected failures.
5. Implement `start_confirmed_demo_automation(action_runner=...)` as a fail-closed helper returning a redacted result. It must never log environment values, credentials, balances, or positions.
6. Call the helper from `run_server` after `start_unified_auto_execution_runner`; print only state/blocker codes. Do not auto-arm Live.
7. Run focused tests and the full Console suite.
8. Commit as `Fix current-process Demo ARM startup`.

## Task 3: Build a redacted Demo evaluation audit

**Files:**
- Create: `alphapilot_control_console/demo_evaluation_audit.py`
- Create: `tests/test_demo_evaluation_audit.py`
- Modify: `alphapilot_control_console/evolution_demo_service.py`
- Modify: `alphapilot_control_console/unified_auto_execution_controller.py`
- Modify: `tests/test_evolution_demo_service.py`
- Modify: `tests/test_unified_auto_execution_controller.py`

1. Add failing pure-function tests for these outcomes: zero signals after real evaluation; signals rejected by arbitration/risk/latency; successful order; exchange order failure.
2. Require the audit schema to include evaluated release count, market/liquidity/deep-screen counts, matched signals, bounded near misses, rejection reason counts, failed-check counts, order attempts/success/failure, exchange code counts, close sequence, PID, and stage timings.
3. Require a recursive redaction assertion that rejects keys containing API key, secret, passphrase, raw headers, balance values, or credential payloads.
4. Implement the pure projector with bounded lists and stable integer counters.
5. Attach `evaluationAudit` to every successful Demo batch return, including zero-signal returns.
6. Persist the same audit under the `heartbeat_completed` event; do not advance checkpoints when a batch fails.
7. Run focused and full tests.
8. Commit as `Add redacted Demo evaluation audit`.

## Task 4: Expose honest Demo operating states in the UI

**Files:**
- Modify: `alphapilot_control_console/demo_workflow_projection.py`
- Modify: `web/app.js`
- Modify: `tests/test_demo_workflow_projection.py`
- Modify: `tests/test_workflow_ui_contract.py`
- Modify: `README.md`

1. Add failing projection tests for `not_armed`, `waiting_for_close`, `evaluated_zero_matches`, `matched_rejected`, `order_submitted`, and `order_failed`.
2. Project the latest redacted audit and one concrete next action; do not infer a match from candidate ranking.
3. Render compact Chinese labels with evaluated strategies, Top100/deep-screen counts, matched signals, order attempts, result, and next close. Keep details collapsible.
4. Document the startup ARM handoff and audit states.
5. Run JS syntax validation, focused tests, full tests, and `git diff --check`.
6. Commit as `Show auditable Demo evaluation states`.

## Task 5: Validate without touching the active Demo process

1. Run `python -m pytest tests -q` from the worktree.
2. Run `python -m compileall alphapilot_control_console`.
3. Run `node --check web/app.js` using the bundled Node runtime.
4. Run `git diff --check` and the repository safety scan.
5. Use temporary files and fake transports only; do not point tests at the user's live `data/*.sqlite`.
6. Do not restart port 8766. Report that the current process keeps its process-only credentials and that the fix becomes active on the next explicit secure launcher start.
