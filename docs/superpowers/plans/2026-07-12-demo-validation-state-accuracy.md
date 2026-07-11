# Demo Validation State Accuracy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Demo workflow progress, market candidates, and the next user action match the actual OKX Demo evidence state.

**Architecture:** Correct the backend projection as the canonical truth and add a narrowly scoped frontend normalization so the already-running process can render accurately without losing process-only credentials.

**Tech Stack:** Python standard library HTTP service, dataclasses/dictionaries, vanilla JavaScript, HTML/CSS, `unittest`.

---

### Task 1: Lock backend projection behavior with failing tests

**Files:**
- Modify: `tests/test_demo_workflow_projection.py`

1. Add a test where runtime readiness is true but read-only status is `not_run`.
2. Assert the runtime-preflight step is pending and progress is 3/6 (50%).
3. Add a test where read-only status is `passed` and assert step 4 completes.
4. Add a test where the market scan is `not_started` and assert no current top candidate is projected.
5. Run `python -m unittest tests.test_demo_workflow_projection` and confirm the new assertions fail before implementation.

### Task 2: Correct backend Demo workflow projection

**Files:**
- Modify: `alphapilot_control_console/demo_workflow_projection.py`

1. Pass `readonly_status` into process-step and progress calculation.
2. Require both runtime readiness and passed read-only status for step 4.
3. Remove the legacy `instId` fallback from full-market current candidate.
4. Run the projection tests and confirm they pass.

### Task 3: Lock frontend action and normalization with failing tests

**Files:**
- Modify: `tests/test_workflow_ui_contract.py`
- Modify or add focused JavaScript source-contract tests if needed.

1. Assert the Demo card can render the `run_demo_preflight` primary action.
2. Assert stale process responses are normalized before card rendering.
3. Assert a not-started scan does not display a legacy candidate.
4. Run the UI contract tests and confirm the new assertions fail before implementation.

### Task 4: Implement frontend defensive normalization and card action

**Files:**
- Modify: `web/app.js`
- Modify: `web/index.html` only if a stable button hook is required.
- Modify: `web/styles.css` only for existing action-row consistency.

1. Normalize pre-patch Demo workflow items at render time.
2. Recompute process progress from normalized steps.
3. Hide stale candidate data while full-market scanning has not started.
4. Route `run_demo_preflight` to the existing read-only-check call.
5. Refresh the Demo workflow after a successful check.
6. Do not trigger order smoke, Demo cycle, or automatic execution.

### Task 5: Version and documentation update

**Files:**
- Modify: `alphapilot_control_console/version.py` or the repository's canonical version source.
- Modify: `README.md`

1. Set the patch version to V13.27.1.7.
2. Document the corrected preflight progress, candidate display, and direct next action.
3. State that credentials remain process-only and no execution permissions changed.

### Task 6: Verification and release

1. Run focused projection and UI contract tests.
2. Run the full Python test suite.
3. Run `python -m compileall alphapilot_control_console`.
4. Run JavaScript syntax validation with bundled Node.
5. Run `git diff --check`.
6. Verify the local page without restarting the current console process.
7. Commit, push, and tag V13.27.1.7 only after all checks pass.
