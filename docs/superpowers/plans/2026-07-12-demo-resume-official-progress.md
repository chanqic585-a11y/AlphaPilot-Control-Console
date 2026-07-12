# V13.27.6 Demo Resume and Official Download Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resume an ordinary OKX Demo pause from the start action and expose durable page-level progress for long official-history downloads.

**Architecture:** Keep Demo resume in the existing runner/service boundary so start remains explicit and Kill Switch remains closed. Add an optional page callback to the public OKX client, persist throttled active-partition metadata in the existing contract checkpoint, and project it read-only to the Console.

**Tech Stack:** Python 3, SQLite, pandas, stdlib HTTP server, vanilla JavaScript, unittest.

## Global Constraints

- No raw API key storage.
- No Withdraw capability.
- No Live auto-resume change.
- No database migration.
- No partial official partition may count as formal evidence.
- Existing running worker remains active until its current partition is durable.

---

### Task 1: Demo ordinary-pause resume

**Files:**
- Modify: `alphapilot_control_console/evolution_demo_service.py`
- Modify: `alphapilot_control_console/unified_auto_execution_runner.py`
- Test: `tests/test_unified_auto_execution_runner.py`
- Test: `tests/test_demo_execution_engine.py`

**Interfaces:**
- Produces: `resume_evolution_demo_runtime() -> None`
- Consumes: `UnifiedAutoExecutionRunner(..., demo_resume=callable)`

- [ ] **Step 1: Write failing tests**

```python
def test_demo_start_resumes_before_arm_and_start(self):
    events = []
    runner = UnifiedAutoExecutionRunner(
        controller=FakeController(),
        demo_resume=lambda: events.append("resume"),
    )
    runner.action("okx_demo", "start", {})
    self.assertEqual(events, ["resume"])

def test_demo_resume_rejects_active_kill_switch(self):
    store.set_runtime_flag("killSwitch", True)
    with self.assertRaises(RuntimeError):
        resume_evolution_demo_runtime(store_path)
```

- [ ] **Step 2: Run tests and verify RED**

Run:
`python -m unittest tests.test_unified_auto_execution_runner tests.test_demo_execution_engine -v`

Expected: failure because `demo_resume` and `resume_evolution_demo_runtime` do not exist.

- [ ] **Step 3: Implement minimal resume**

```python
def resume_evolution_demo_runtime(store_path=STORE_PATH):
    store = DemoExecutionStore(store_path)
    try:
        if store.get_runtime_flag("killSwitch", False):
            raise RuntimeError("Demo kill switch requires separate reviewed clearing")
        store.set_runtime_flag("paused", False)
        store.set_runtime_flag("pauseReason", None)
        store.append_event(None, "demo_resumed", {})
    finally:
        store.close()
```

Call `demo_resume()` before Demo ARM/start. Do not call it for Live.

- [ ] **Step 4: Run targeted tests and commit**

Expected: targeted tests pass.

---

### Task 2: Page-level official download checkpoint

**Files:**
- Modify: `alphapilot/data_foundation/okx_public.py`
- Modify: `alphapilot/data_foundation/official_history.py`
- Test: `tests/data_foundation/test_okx_public.py`
- Test: `tests/data_foundation/test_official_history.py`

**Interfaces:**
- Produces: optional `page_progress: Callable[[dict[str, Any]], None]`
- Persists: checkpoint `inProgress` object; completed partitions remain under `completed`.

- [ ] **Step 1: Write failing callback and checkpoint tests**

Assert callbacks contain `requestCount`, `rowCount`, `oldestTimestampMs`, and
`maxPages`; assert collector checkpoint contains active instrument/timeframe
during page callbacks and removes it after successful partition completion.

- [ ] **Step 2: Run tests and verify RED**

Run:
`python -m unittest tests.data_foundation.test_okx_public tests.data_foundation.test_official_history -v`

- [ ] **Step 3: Implement callback and throttled persistence**

Call the callback after each valid page. Persist on page 1, every 25 pages and
the final page. Never persist partial rows as a completed partition.

- [ ] **Step 4: Run targeted tests and commit**

Expected: data-foundation tests pass.

---

### Task 3: Projection and Console rendering

**Files:**
- Modify: `alphapilot/evolution/workflow/projection.py`
- Test: `tests/evolution/test_workflow_projection.py`
- Modify: `web/app.js`
- Test: `tests/test_workflow_ui_contract.py`

**Interfaces:**
- Consumes: `downloadProgress.active`
- Produces: active partition label and subordinate progress bar.

- [ ] **Step 1: Write failing projection and UI contract tests**

Assert projection safely exposes active progress and malformed metadata is
ignored. Assert JS contains the active-partition progress renderer and page/row
labels.

- [ ] **Step 2: Run tests and verify RED**

Run the two targeted test modules and confirm expected failures.

- [ ] **Step 3: Implement read-only projection and UI**

Render a subordinate progress row without replacing the existing phase bar.
Use `requestCount / maxPages` for the sub-bar and show instrument, timeframe,
pages and rows.

- [ ] **Step 4: Run targeted tests and commit**

Expected: projection and UI tests pass.

---

### Task 4: Version, validation and deployment

**Files:**
- Modify: both repositories' `README.md`
- Modify: Console/Quant version constants where currently `V13.27.5`

- [ ] **Step 1: Update V13.27.6 notes and version labels**
- [ ] **Step 2: Run Quant and Console full unittest suites**
- [ ] **Step 3: Run compileall, Node `--check`, `git diff --check`, and changed-line safety scans**
- [ ] **Step 4: Wait for the active old worker to finish its current partition, then pause it at the durable boundary**
- [ ] **Step 5: Merge and push both repositories**
- [ ] **Step 6: Restart Demo Console with process-only credentials, resume the queue and verify**

Expected live checks:

- Demo runtime leaves `demo_runtime_paused` after start.
- Step 4 passes unless a real preflight/reconciliation/risk blocker exists.
- The running backtest shows changing page-level progress.
- Kill Switch remains closed and no raw credential is stored.
