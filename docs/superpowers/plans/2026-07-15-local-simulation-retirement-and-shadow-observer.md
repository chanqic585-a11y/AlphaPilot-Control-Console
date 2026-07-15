# AlphaPilot Local Simulation Retirement and Shadow Observer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove local simulation from the active product lifecycle without deleting its history, classify the existing ten Demo releases as legacy diagnostics, and retain only a lightweight public-market shadow observer that records signal decisions without positions or performance.

**Architecture:** Retirement is enforced in both repositories: the Quant workflow can no longer create a local-forward transition, while the Console cannot start, recover, or write local-sandbox state. Historical tables remain readable through deprecated audit projections. A separate release-classification overlay preserves signed release files, and a new append-only shadow database stores only signal/rejection diagnostics.

**Tech Stack:** Python 3.12, SQLite, existing workflow registry, unittest/pytest, vanilla JavaScript.

## Global Constraints

- Preserve every existing local-simulation database, row, report, fill, position, equity snapshot, and export.
- Do not mutate the signed JSON or hash of any existing Demo release.
- No new object may enter `local_simulation_running`, `local_simulation_passed`, `local_forward`, or `local_sandbox`.
- No frontend flag, environment variable, restart recovery, compatibility route, or hidden action may re-enable local writes.
- Shadow records contain no order, fill, virtual capital, position, PnL, MFE, MAE, R outcome, equity, or promotion fields.
- Shadow failures are warnings and cannot block an approved strategy-validation Demo release.
- The existing ten releases are diagnostic history, not ten independent hypotheses.
- No Live or Withdraw capability is added.

---

### Task 1: Snapshot local history and define retirement invariants

**Files:**
- Create during execution: `data/backups/local_simulation_retirement_<timestamp>/manifest.json`
- Create: `tests/test_local_simulation_retirement_invariants.py`

**Snapshot counts:**

```text
local runs
virtual orders
virtual fills
virtual positions
equity snapshots
closed samples
learning samples
daily reports
workflow rows in retired states
```

- [ ] Use SQLite online backup for every actively written database before changing startup behavior.
- [ ] Record pre-retirement table counts and SHA-256 hashes without dumping row payloads.
- [ ] Write a failing invariant test that captures counts, restarts the Console, waits one scheduler interval, and expects all counts to remain unchanged.
- [ ] Write a failing invariant test that invokes every legacy write route and expects no count changes.
- [ ] Stop if a source database cannot be backed up or counted consistently.

### Task 2: Replace the active workflow state model

**Repository:** `D:\Codex-Workspace\AlphaPilot-Quant-Engine`

**Files:**
- Modify: `alphapilot/evolution/workflow/states.py`
- Modify: `alphapilot/evolution/workflow/dual_layer.py`
- Modify: `alphapilot/evolution/workflow/local_forward_bridge.py`
- Modify: `alphapilot/evolution/registry/types.py`
- Modify: `alphapilot/evolution/registry/repositories.py`
- Test: `tests/evolution/test_dual_layer_workflow.py`
- Test: `tests/evolution/test_workflow_local_forward_bridge.py`
- Create: `tests/evolution/test_retired_local_workflow_states.py`

**Active lifecycle:**

```text
research_candidate
data_audit
preregistered
event_prefilter
backtest_queued
backtest_running
basic_backtest_passed
formal_backtest_passed
immutable_release_ready
demo_waiting_approval
demo_validation_running
demo_validated
live_candidate
archived
```

- [ ] Write failing tests proving historical retired values deserialize but cannot be transition targets.
- [ ] Change `run_dual_layer_backtest_workflow` so a pass ends at the applicable backtest state and never starts local forward.
- [ ] Change `local_forward_bridge` into audit-only compatibility: reads return `legacy_local_observation`; all create/advance methods raise a typed retirement error.
- [ ] Preserve old row values in storage; translate only in read projections.
- [ ] Add registry methods for the active lifecycle without rewriting old migrations or deleting old enum strings.
- [ ] Run `python -m pytest tests/evolution/test_dual_layer_workflow.py tests/evolution/test_workflow_local_forward_bridge.py tests/evolution/test_retired_local_workflow_states.py -q`; expect all tests to pass.
- [ ] Commit only Quant files: `git commit -m "Retire local forward from the active strategy workflow"`.

### Task 3: Stop local-sandbox startup and recovery

**Repository:** `D:\Codex-Workspace\AlphaPilot-Control-Console`

**Files:**
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `alphapilot_control_console/sandbox_auto_runner.py`
- Modify: `alphapilot_control_console/local_sandbox_runner.py`
- Modify: `alphapilot_control_console/simulation_bridge.py`
- Test: `tests/test_local_simulation_retirement_invariants.py`
- Modify: existing local-sandbox runner tests to assert retirement behavior

**Permanent capabilities:**

```python
FULL_LOCAL_SIMULATION_ENABLED = False
LOCAL_VIRTUAL_POSITION_ENABLED = False
LOCAL_VIRTUAL_EQUITY_ENABLED = False
LOCAL_SIMULATION_LIFECYCLE_ENABLED = False
SIMULATION_LEARNING_ENABLED = False
```

- [ ] Write failing tests proving `run_server` does not call `start_local_sandbox_auto_runner`.
- [ ] Disable runner recovery, timers, run-now, bridge writes, learning writes, and lifecycle promotion writes.
- [ ] Keep parsers and readers needed for historical exports, clearly marked deprecated.
- [ ] Make any internal direct write call raise `LocalSimulationRetiredError` before opening a write transaction.
- [ ] Run the retirement invariant tests and require zero post-restart count changes.

### Task 4: Retire legacy write APIs while preserving audit reads

**Files:**
- Modify: `alphapilot_control_console/http_app.py`
- Create: `alphapilot_control_console/local_simulation_retirement.py`
- Test: `tests/test_local_simulation_retirement_http.py`

**Write response:**

```json
{
  "status": "retired",
  "code": "local_simulation_retired",
  "historicalDataPreserved": true,
  "nextAction": "Use formal backtest and OKX Demo validation."
}
```

- [ ] Enumerate every existing local-sandbox, simulation-review, stage-return, auto-runner, and learning POST route.
- [ ] Write table-driven failing tests requiring HTTP `410 Gone` and the exact response for each route.
- [ ] Keep only deprecated GET history/export routes; add `deprecated=true`, `readOnly=true`, and `evidenceSource='legacy_local_observation'`.
- [ ] Ensure GET routes never trigger reconciliation, refresh, learning, or lazy writes.
- [ ] Run `python -m unittest tests.test_local_simulation_retirement_http -v`; expect all tests to pass.

### Task 5: Classify the current ten releases without mutation

**Files:**
- Create: `alphapilot_control_console/demo_release_classification_store.py`
- Create: `alphapilot_control_console/demo_release_classification.py`
- Modify: `alphapilot_control_console/evolution_demo_service.py`
- Modify: `alphapilot_control_console/demo_workflow_service.py`
- Test: `tests/test_demo_release_classification.py`

**Overlay record:**

```text
releaseId
releaseHash
releasePurpose=legacy_diagnostic
strategyQualification=false
promotionEligible=false
forwardPerformanceEligible=false
demoPerformanceEligible=false
classifiedAt
classificationReason
```

- [ ] Hash all ten release files before classification.
- [ ] Write failing tests proving overlay classification leaves file contents, names, hashes, and historical execution rows unchanged.
- [ ] Store the overlay in `data/demo_release_classification.sqlite` with a unique `(releaseId, releaseHash)` key.
- [ ] Make active strategy-validation discovery exclude `legacy_diagnostic` releases.
- [ ] Label same-family variants `同源变体，不是独立假设` in projections.
- [ ] Rehash all ten files after classification and require exact equality.

### Task 6: Implement the no-PnL shadow schema

**Files:**
- Create: `alphapilot_control_console/shadow_observation_store.py`
- Create: `alphapilot_control_console/shadow_observer.py`
- Test: `tests/test_shadow_observation_store.py`
- Test: `tests/test_shadow_observer.py`

**Storage:** `data/shadow_observations.sqlite`

**Allowed fields:**

```text
shadowObservationId
releaseId
strategyId
strategyFamilyId
timestamp
symbol
direction
timeframe
signalMatched
passOrReject
reasonZh
featureSnapshot
marketRegime
publicUniverseIncluded
demoUniverseIncluded
liquidityPassed
dataQualityPassed
riskGatePassed
wouldAttemptDemoOrder
sourceDataHashes
```

**Forbidden field fragments:**

```text
order fill position capital equity pnl profit loss mfe mae return outcome targetHit stopHit closedTrade promotion
```

- [ ] Write a schema test that fails if a table column or serialized key contains a forbidden fragment, case-insensitive.
- [ ] Write append/idempotency tests keyed by release, symbol, timeframe, closed-candle timestamp, and definition hash.
- [ ] Reuse frozen release signal evaluation but stop before order sizing or execution intent creation.
- [ ] Store bounded feature snapshots and source hashes; do not store full candle arrays.
- [ ] Treat observer exceptions as `warning` records and return control to the Demo execution path.
- [ ] Run `python -m unittest tests.test_shadow_observation_store tests.test_shadow_observer -v`; expect all tests to pass.

### Task 7: Attach shadow observation without coupling it to execution

**Files:**
- Modify: `alphapilot_control_console/demo_release_scanner.py`
- Modify: `alphapilot_control_console/demo_market_scan_service.py`
- Modify: `alphapilot_control_console/unified_auto_execution_runner.py`
- Create: `tests/test_shadow_observer_execution_isolation.py`

- [ ] Write tests where shadow persistence succeeds, fails, and times out while the same qualified Demo scan result remains unchanged.
- [ ] Call the observer after signal evaluation and before order dispatch only as a non-blocking side effect.
- [ ] Do not let shadow records alter candidate ranking, risk results, order payloads, idempotency keys, or release eligibility.
- [ ] Assert one market event observed by both paths has one shared source-event hash but only a Demo closed trade can become forward evidence.

### Task 8: Add the read-only shadow endpoint

**Files:**
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `web/app.js`
- Test: `tests/test_shadow_observation_http.py`

**Endpoint:**

```http
GET /api/shadow-observation?releaseId=<id>&limit=100
```

**Response summaries:**

```text
observationCount
matchedCount
rejectedCount
warningCount
reasonCounts
familyCounts
symbolCounts
directionCounts
demoUniverseHitRate
latestObservedAt
```

- [ ] Write failing tests for filters, bounded limit, empty state, and absence of forbidden performance keys.
- [ ] Expose only aggregate diagnostics and a bounded recent row sample.
- [ ] Put the UI behind `高级诊断`; do not create a primary shadow navigation item.

### Task 9: Remove Local Simulation from primary UI

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Test: `tests/test_primary_navigation.py`

- [ ] Write a failing DOM/static test requiring exactly `策略`, `Demo模拟`, `实盘交易`, and `手机控制台` as primary destinations.
- [ ] Remove the Local Simulation nav button and page mount from the active render path.
- [ ] Redirect `#localLab` to Strategy with a once-per-browser-session retirement notice.
- [ ] Remove local equity, virtual positions, local PnL, sample-progress, and promotion cards from active workflow projections.
- [ ] Keep a small audit link under advanced diagnostics only if historical export is still needed.

### Task 10: Phase 2 integrated proof

**Files:**
- Modify: `README.md` in both repositories
- Create: `docs/local-simulation-retirement-and-shadow.md`

- [x] Run Console: `python -m unittest discover -s tests -v`.
- [x] Run Console: `python -m compileall alphapilot_control_console`.
- [x] Run Quant: `python -m pytest tests -q`.
- [x] Run Quant: `python -m compileall alphapilot`.
- [x] Run `git diff --check` in both repositories.
- [x] Restart the Console twice and observe at least one former scheduler interval; require every local history count to remain at its baseline.
- [x] Verify deprecated reads still return the same historical counts and hashes.
- [x] Verify the ten release file hashes are unchanged and all classification overlays are `legacy_diagnostic`.
- [x] Generate shadow matches and rejects, then scan its SQLite schema and JSON values for forbidden performance fields.
- [x] Confirm a forced shadow storage failure does not block a qualified mocked Demo order path.
- [x] Commit Console: `git commit -m "Retire local simulation and add no-PnL shadow diagnostics"`.
- [x] Commit Quant without staging the pre-existing report: `git commit -m "Consolidate strategy workflow around backtest and Demo"`.
- [x] Push both commits and require both intended scopes clean before Phase 3.

## Phase Exit Gate

Phase 2 passes only when Local Simulation is absent from primary navigation, every legacy write route returns `410`, restart cannot produce new local records, historical hashes and counts remain readable, all ten releases are non-mutating legacy diagnostics, and shadow observation records signal diagnostics with no order or performance semantics. Any local count increase or forbidden shadow field is a hard stop.

## Reserved Phase 3 (Single Stage)

Phase 3 remains one top-level implementation stage. It must not be split into
3A, 3B, or other implementation sub-stages in the active roadmap.

The detailed Phase 3 specification is intentionally pending a user-supplied
update. Completing and pushing Phase 2 does not authorize any Phase 3 code,
data collection, factor research, backtest campaign, Demo action, or Live
action. Stop after the Phase 2 exit gate until the replacement Phase 3 document
is confirmed.
