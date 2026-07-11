# AlphaPilot Unified Demo and Live Auto Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build one restart-safe automatic execution controller that continuously runs eligible immutable strategies in OKX Demo or an explicitly armed OKX Live Canary environment without per-order confirmation.

**Architecture:** A pure UTC candle scheduler and SQLite runtime store feed a shared controller. Environment adapters keep existing Demo and Live clients, release contracts, execution stores, risk profiles, and evidence ledgers separate. A backend runner owns the heartbeat; web and mobile consume one read-only runtime projection.

**Tech Stack:** Python 3 standard library, `unittest`, SQLite, `ThreadingHTTPServer`, vanilla JavaScript/CSS, PowerShell launchers.

## Global Constraints

- Demo and Live share the workflow but never credentials, headers, adapters, releases, profiles, stores, or evidence classes.
- Live requires one process-level ARM and no per-order confirmation afterward.
- Demo private requests require `x-simulated-trading: 1`; Live requests must not contain it.
- Every order must be checksum-bound, idempotent, isolated-margin, risk-approved, and protected by TP/SL with `rewardRiskRatio >= 2`.
- Raw API credentials are process-only and must never enter files, SQLite, browser state, logs, events, or notifications.
- Withdraw, transfer, deposit, and API-key-management endpoints remain absent.
- Browser closure must not stop the runner; process restart must reconcile before new entries.
- Automated tests use fake clients and cannot send real orders.
- Preserve untracked runtime directories under `data/`; never commit or delete them.

---

### Task 1: UTC Candle Scheduler and Persistent Runtime Store

**Files:**
- Create: `alphapilot_control_console/auto_execution_schedule.py`
- Create: `alphapilot_control_console/unified_auto_execution_store.py`
- Test: `tests/test_auto_execution_schedule.py`
- Test: `tests/test_unified_auto_execution_store.py`

**Interfaces:**
- Produces: `parse_timeframe_seconds(timeframe: str) -> int`
- Produces: `closed_candle_key(now: datetime, timeframe: str) -> str`
- Produces: `next_candle_close(now: datetime, timeframe: str) -> datetime`
- Produces: `UnifiedAutoExecutionStore.runtime(environment) -> dict[str, Any]`
- Produces: `set_desired_enabled`, `record_arm`, `disarm`, `save_checkpoint`, `checkpoint`, `append_event`, and `list_events`.

- [x] **Step 1: Write failing scheduler tests**

```python
def test_hourly_strategy_is_due_once_per_closed_candle():
    now = datetime(2026, 7, 12, 10, 37, tzinfo=UTC)
    self.assertEqual(closed_candle_key(now, "1h"), "2026-07-12T10:00:00+00:00")
    self.assertEqual(next_candle_close(now, "1h"), datetime(2026, 7, 12, 11, 0, tzinfo=UTC))

def test_invalid_timeframe_fails_closed():
    with self.assertRaises(ValueError):
        parse_timeframe_seconds("13m")
```

- [x] **Step 2: Run scheduler tests and verify RED**

Run: `python -m unittest tests.test_auto_execution_schedule -v`

Expected: import failure for `auto_execution_schedule`.

- [x] **Step 3: Implement the minimal pure scheduler**

```python
TIMEFRAME_SECONDS = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}

def closed_candle_key(now: datetime, timeframe: str) -> str:
    seconds = parse_timeframe_seconds(timeframe)
    epoch = int(now.astimezone(UTC).timestamp())
    close_epoch = epoch - epoch % seconds
    return datetime.fromtimestamp(close_epoch, UTC).isoformat()
```

- [x] **Step 4: Write failing store tests**

```python
def test_runtime_state_never_persists_credentials():
    store.set_desired_enabled("okx_demo", True)
    store.record_arm("okx_demo", process_id="pid-1")
    state = store.runtime("okx_demo")
    self.assertTrue(state["desiredEnabled"])
    self.assertNotIn("apiKey", json.dumps(state))

def test_checkpoint_is_scoped_by_environment_release_and_timeframe():
    store.save_checkpoint("okx_demo", "release-1", "1h", "2026-07-12T10:00:00+00:00")
    self.assertEqual(store.checkpoint("okx_demo", "release-1", "1h"), "2026-07-12T10:00:00+00:00")
    self.assertIsNone(store.checkpoint("okx_live", "release-1", "1h"))
```

- [x] **Step 5: Run store tests and verify RED**

Run: `python -m unittest tests.test_unified_auto_execution_store -v`

Expected: import failure for `unified_auto_execution_store`.

- [x] **Step 6: Implement SQLite runtime, checkpoint, and event tables**

Use three append-safe tables:

```sql
CREATE TABLE IF NOT EXISTS AutoExecutionRuntime (... environment TEXT PRIMARY KEY ...);
CREATE TABLE IF NOT EXISTS AutoExecutionCheckpoints (... PRIMARY KEY(environment, releaseId, timeframe));
CREATE TABLE IF NOT EXISTS AutoExecutionEvents (... eventId INTEGER PRIMARY KEY AUTOINCREMENT ...);
```

The runtime row contains only booleans, status, timestamps, process ARM identity, and reason codes.

- [x] **Step 7: Run both test files and commit**

Run: `python -m unittest tests.test_auto_execution_schedule tests.test_unified_auto_execution_store -v`

Expected: PASS.

Commit: `git commit -m "Add persistent auto execution schedule state"`

---

### Task 2: Shared Controller and Environment Adapter Contract

**Files:**
- Create: `alphapilot_control_console/unified_auto_execution_controller.py`
- Test: `tests/test_unified_auto_execution_controller.py`

**Interfaces:**
- Consumes: Task 1 scheduler and store.
- Produces: `ReleaseSchedule(releaseId, strategyId, timeframe)`.
- Produces: `ExecutionEnvironmentAdapter` protocol with `preflight`, `reconcile`, `list_releases`, `run_batch`, `pause`, and `emergency_stop`.
- Produces: `UnifiedAutoExecutionController.heartbeat(environment, now=None) -> dict[str, Any]`.

- [x] **Step 1: Write failing controller tests with a fake adapter**

```python
def test_heartbeat_runs_each_release_only_once_per_closed_candle():
    adapter = FakeAdapter([ReleaseSchedule("r1", "s1", "1h")])
    controller.arm("okx_demo", process_id="pid-1")
    first = controller.heartbeat("okx_demo", now=NOW)
    second = controller.heartbeat("okx_demo", now=NOW)
    self.assertEqual(first["evaluatedReleaseCount"], 1)
    self.assertEqual(second["evaluatedReleaseCount"], 0)
    self.assertEqual(adapter.batch_calls, [["r1"]])

def test_live_cannot_run_without_current_process_arm():
    store.set_desired_enabled("okx_live", True)
    result = controller.heartbeat("okx_live", now=NOW)
    self.assertEqual(result["status"], "disarmed")
    self.assertEqual(adapter.batch_calls, [])

def test_preflight_or_reconciliation_failure_pauses_before_batch():
    adapter.preflight_result = {"ok": False, "blockers": ["auth_failed"]}
    result = controller.heartbeat("okx_demo", now=NOW)
    self.assertEqual(result["status"], "paused")
    self.assertEqual(adapter.batch_calls, [])
```

- [x] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.test_unified_auto_execution_controller -v`

Expected: import failure for the controller.

- [x] **Step 3: Implement the controller without exchange logic**

```python
class ExecutionEnvironmentAdapter(Protocol):
    environment: str
    def preflight(self) -> dict[str, Any]: ...
    def reconcile(self) -> dict[str, Any]: ...
    def list_releases(self) -> list[ReleaseSchedule]: ...
    def run_batch(self, releases: list[ReleaseSchedule], candle_keys: dict[str, str]) -> dict[str, Any]: ...
    def pause(self, reason: str) -> None: ...
    def emergency_stop(self, reason: str) -> dict[str, Any]: ...
```

Heartbeat order is fixed: desired state -> current-process ARM -> preflight -> reconciliation -> due releases -> one batch -> checkpoints -> projection.

- [x] **Step 4: Add fail-closed exception and process-restart tests**

Verify an exception pauses new entries, and a persisted desired state does not restore a previous process ARM token.

- [x] **Step 5: Run tests and commit**

Run: `python -m unittest tests.test_unified_auto_execution_controller -v`

Expected: PASS.

Commit: `git commit -m "Add shared fail closed auto execution controller"`

---

### Task 3: Demo Batch Adapter and Automatic Cycle

**Files:**
- Create: `alphapilot_control_console/unified_auto_execution_adapters.py`
- Modify: `alphapilot_control_console/evolution_demo_service.py`
- Modify: `alphapilot_control_console/demo_arbitrator.py`
- Test: `tests/test_demo_automatic_batch.py`
- Test: `tests/test_unified_auto_execution_adapters.py`

**Interfaces:**
- Consumes: Task 2 adapter protocol.
- Produces: `run_evolution_demo_batch_cycle(release_ids: list[str]) -> dict[str, Any]`.
- Produces: `OkxDemoAutoExecutionAdapter`.

- [x] **Step 1: Write a failing multi-release Demo test**

```python
def test_batch_scans_all_due_releases_and_arbitrates_before_ordering():
    result = run_evolution_demo_batch_cycle(["release-a", "release-b"])
    self.assertEqual(result["scannedReleaseCount"], 2)
    self.assertEqual(result["selectedSignalCount"], 1)
    self.assertEqual(len(fake_client.orders), 1)
    self.assertEqual(result["rejectedSignals"][0]["reason"], "duplicate_symbol_signal")
```

Patch contract discovery, scanners, risk store, and client construction with deterministic fakes. Do not call OKX.

- [x] **Step 2: Run the test and verify RED**

Run: `python -m unittest tests.test_demo_automatic_batch -v`

Expected: missing batch function.

- [x] **Step 3: Refactor the existing one-release cycle into a batch path**

The batch path must:

1. validate each requested immutable Demo contract;
2. scan each contract and persist its market scan;
3. collect all signals before execution;
4. arbitrate conflicts and concentration once across releases;
5. build one current Demo portfolio snapshot;
6. execute selected signals through `DemoExecutionEngine` using the matching contract and active profile;
7. preserve rejected reasons and never treat no-signal as failure.

Keep `run_evolution_demo_cycle` as a compatibility wrapper calling the batch function with one release ID.

- [x] **Step 4: Write the adapter tests**

Verify release schedule extraction, Demo preflight, reconciliation, pause, emergency stop, and that the adapter cannot expose Live credentials or headers.

- [x] **Step 5: Run Demo regressions and commit**

Run: `python -m unittest tests.test_demo_automatic_batch tests.test_unified_auto_execution_adapters tests.test_evolution_demo_service tests.test_demo_execution_engine tests.test_demo_arbitrator -v`

Expected: PASS.

Commit: `git commit -m "Automate checksum bound Demo execution batches"`

---

### Task 4: Live Scanner Adapter and One-Time ARM Execution

**Files:**
- Create: `alphapilot_control_console/live_auto_execution_service.py`
- Modify: `alphapilot_control_console/unified_auto_execution_adapters.py`
- Modify: `alphapilot_control_console/live_canary_service.py`
- Modify: `alphapilot_control_console/live_execution_engine.py`
- Modify: `scripts/start_okx_live_canary_console.ps1`
- Test: `tests/test_live_auto_execution_service.py`
- Test: `tests/test_live_canary_service.py`
- Test: `tests/test_okx_live_launcher_script.py`

**Interfaces:**
- Produces: `scan_live_release(release, active_profile, loaders=None) -> dict[str, Any]`.
- Produces: `run_live_auto_execution_batch(release_ids, client=None, store_path=...) -> dict[str, Any]`.
- Produces: `OkxLiveAutoExecutionAdapter`.

- [x] **Step 1: Write failing Live scan and execution tests**

```python
def test_live_release_without_frozen_strategy_definition_fails_before_order():
    result = run_live_auto_execution_batch(["release-1"], client=fake_client)
    self.assertIn("live_release_strategy_definition_missing", result["blockers"])
    self.assertEqual(fake_client.orders, [])

def test_armed_live_batch_uses_same_signal_rules_and_submits_protected_order():
    result = run_live_auto_execution_batch(["release-1"], client=fake_client)
    self.assertTrue(result["ok"])
    self.assertEqual(len(fake_client.orders), 1)
    self.assertTrue(fake_client.orders[0]["attachAlgoOrds"][0]["slTriggerPx"])
```

The valid fixture includes strategy definition, `>= 2R`, matching RiskProfile hashes, current-process ARM, and successful reconciliation.

- [x] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.test_live_auto_execution_service -v`

Expected: import failure.

- [x] **Step 3: Implement a Live scanner wrapper and portfolio snapshot**

Map only checksum-validated Live release strategy fields into the existing immutable strategy-family scanner. Replace Demo identity fields with Live identities before execution. Reject missing strategy, profile, data freshness, sizing, or protection evidence before calling the Live client.

- [x] **Step 4: Add an explicit Live automation process gate**

Add `ALPHAPILOT_OKX_LIVE_AUTOMATION_ENABLED`. It requires read, canary, and order gates. The launcher requires the exact existing process confirmation and never writes credentials.

- [x] **Step 5: Bind ARM to the current process, not persisted startup state**

`arm_live_canary` keeps its manual once-per-process confirmation. The controller receives the current process ID after successful reconciliation and ARM. Restart clears effective ARM even when desired automatic execution remains persisted.

- [x] **Step 6: Run Live regressions and commit**

Run: `python -m unittest tests.test_live_auto_execution_service tests.test_live_canary_service tests.test_live_execution_engine tests.test_okx_live_client tests.test_okx_live_launcher_script -v`

Expected: PASS with fake clients only.

Commit: `git commit -m "Add armed automatic Live Canary execution"`

---

### Task 5: Backend Runner, Startup Recovery, and HTTP Contract

**Files:**
- Create: `alphapilot_control_console/unified_auto_execution_runner.py`
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `alphapilot_control_console/demo_workflow_service.py`
- Test: `tests/test_unified_auto_execution_runner.py`
- Test: `tests/test_unified_auto_execution_http.py`

**Interfaces:**
- Produces: `start_unified_auto_execution_runner()`, `stop_unified_auto_execution_runner()`, `get_unified_auto_execution_status()`.
- Adds: `GET /api/auto-execution/runtime`.
- Adds: `POST /api/auto-execution/action` with `start`, `pause`, `stop`, `arm`, and `emergency_stop`.

- [x] **Step 1: Write failing runner tests**

Verify a daemon runner wakes immediately on start, uses a 15-second position heartbeat, does not create duplicate worker threads, and stops cleanly.

- [x] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.test_unified_auto_execution_runner -v`

Expected: import failure.

- [x] **Step 3: Implement the runner with dependency-injected sleep and clock**

The HTTP server starts one runner after binding. It never restarts the current server and never owns credentials. On shutdown, it signals the runner and joins with a bounded timeout.

- [x] **Step 4: Write failing HTTP action tests**

```python
def test_demo_start_enables_and_arms_demo_without_order_confirmation(): ...
def test_live_start_is_rejected_until_live_canary_arm_succeeds(): ...
def test_emergency_stop_routes_only_to_the_selected_environment(): ...
```

- [x] **Step 5: Implement endpoint routing and compatibility actions**

Keep `run_demo_cycle` available as a diagnostic action, but return the automatic runner as the primary `nextAction`. Merge runner status into `/api/demo-workflow`, `/api/live-canary`, and `/api/mobile/status` projections.

- [x] **Step 6: Run startup and HTTP regressions and commit**

Run: `python -m unittest tests.test_unified_auto_execution_runner tests.test_unified_auto_execution_http tests.test_workflow_startup_recovery tests.test_demo_workflow_actions -v`

Expected: PASS.

Commit: `git commit -m "Run automatic execution independently of the browser"`

---

### Task 6: Shared Demo/Live Console and Mobile Status

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Modify: `alphapilot_control_console/http_app.py`
- Test: `tests/test_workflow_ui_contract.py`
- Test: `tests/test_unified_auto_execution_http.py`

**Interfaces:**
- Consumes: Task 5 runtime projection.
- Produces: shared controls and status IDs for Demo and Live pages.

- [x] **Step 1: Add failing static contract tests**

Require the following stable IDs or data attributes:

```text
demoAutoExecutionStatus
demoAutoExecutionToggle
liveAutoExecutionStatus
liveAutoExecutionToggle
autoExecutionLastHeartbeat
autoExecutionNextEvaluation
data-auto-execution-action
```

Also require the Chinese states `等待策略条件匹配`, `自动运行中`, `暂停新开仓`, and `紧急停止`.

- [x] **Step 2: Run UI contract tests and verify RED**

Run: `python -m unittest tests.test_workflow_ui_contract -v`

Expected: missing stable IDs.

- [x] **Step 3: Implement one reusable renderer for both pages**

The first viewport shows environment, runner state, enabled strategies, scan/match counts, current positions, realized/unrealized PnL, last heartbeat, next evaluation, and pause/stop controls. Hide hashes and raw payloads in advanced details.

When match count is zero and no order exists, show `等待策略条件匹配`; never show `正在收集闭合交易` as if execution had begun.

- [x] **Step 4: Merge the same state into the phone read-only payload**

Phone status includes signals, orders, positions, PnL, runner state, and exception events. It cannot submit orders or contain credentials.

- [x] **Step 5: Run Python and JavaScript checks and commit**

Run:

```powershell
python -m unittest tests.test_workflow_ui_contract tests.test_unified_auto_execution_http -v
node --check web/app.js
```

Expected: PASS.

Commit: `git commit -m "Unify automatic Demo and Live console controls"`

---

### Task 7: Full Validation, Documentation, and Release Readiness

**Files:**
- Modify: `README.md`
- Create: `docs/V13.27.2-unified-auto-execution.md`
- Modify: `docs/superpowers/plans/2026-07-12-unified-auto-execution-demo-live.md`

**Interfaces:**
- Documents operator start, ARM, stop, restart, and recovery behavior.

- [x] **Step 1: Document exact operator flows**

Document Demo automatic start, Live launcher plus once-per-process ARM, environment banners, no per-order confirmation, restart recovery, emergency stop, raw-key boundary, and no Withdraw.

- [x] **Step 2: Run the complete test suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass and no real exchange order is attempted.

- [x] **Step 3: Run static and safety checks**

Run:

```powershell
python -m compileall alphapilot_control_console
node --check web/app.js
powershell -NoProfile -Command "[void][scriptblock]::Create((Get-Content -Raw scripts/start_okx_demo_console.ps1)); [void][scriptblock]::Create((Get-Content -Raw scripts/start_okx_live_canary_console.ps1))"
git diff --check
rg -n "withdraw|apiSecret|passphrase|createOrder|automaticTradingAllowed" alphapilot_control_console web scripts
```

Expected: syntax and diff checks pass; safety scan hits are restricted to credential plumbing, explicit negative boundaries, and allowlisted Demo/Live Trade code. No Withdraw client method exists.

- [x] **Step 4: Verify runtime behavior without credentials**

Start a temporary console on an unused port. Confirm both environments fail closed, the runtime endpoint is readable, and no order record is created.

- [x] **Step 5: Commit the completed implementation**

Commit: `git commit -m "Complete V13.27.2 unified automatic execution"`

- [x] **Step 6: Final branch review**

Verify only intended source, tests, docs, and web files are tracked. Preserve `data/demo_release_contracts/` and `data/workflow_jobs/` as untracked runtime data.
