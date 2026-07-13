# AlphaPilot V13.27.9 Low-Latency Top100 Demo Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 10 active Top20 OKX Demo releases with immutable Top100 successors and submit eligible Demo orders within a five-second target using prewarmed public market state, with conditional late entry through thirty seconds.

**Architecture:** A public-only OKX WebSocket runtime continuously maintains Top100 quotes and confirmed candles, seeded by REST before automation becomes ready. A confirmed close wakes the existing automatic execution controller, which evaluates all due releases against one immutable in-memory snapshot, applies duplicate arbitration and risk checks, then submits an order without per-order confirmation. A pure latency policy rejects stale or price-drifted entries and preserves net reward/risk of at least 2R.

**Tech Stack:** Python 3, `websocket-client==1.8.0`, standard-library threading/SQLite/JSON/pathlib, unittest, vanilla JavaScript, PowerShell.

## Global Constraints

- Existing Top20 contracts remain byte-for-byte preserved in an archive.
- Active and future Demo releases use `screeningLimit = 100` and `okx_full_market_policy_v2_top100`.
- Existing 1D BTC regime and strategy thresholds are unchanged.
- Confirmed close to order-send target is five seconds; ten seconds begins conditional late-entry checks; thirty seconds is absolute expiry.
- Conditional late entry requires a quote no more than two seconds old, current spread/liquidity gates, dynamic adverse drift within `min(0.20%, 10% of original stop-distance percent)`, and recalculated net reward/risk of at least 2R.
- Demo-only overrides remain ineligible for live promotion.
- No raw API credential storage, no Withdraw, and no new live execution capability.
- No AI, training, historical download, or full-universe REST scan is allowed in the order hot path.
- Activation requires Demo automatic execution to be disabled and is idempotent.

---

### Task 1: Shared Top100 universe policy and future release default

**Files:**
- Create: `alphapilot_control_console/demo_universe_policy.py`
- Modify: `alphapilot_control_console/demo_override_release.py`
- Test: `tests/test_demo_override_release.py`

**Interfaces:**
- Produces: `DEMO_DEEP_SCREENING_LIMIT`, `DEMO_UNIVERSE_POLICY_VERSION`, and `build_demo_universe_policy() -> dict[str, Any]`.
- Consumed by: future release creation, warm runtime, and successor migration.

- [ ] **Step 1: Write failing tests**

Add assertions that a newly authorized release contains:

```python
self.assertEqual(market["universePolicy"]["screeningLimit"], 100)
self.assertEqual(
    market["universePolicy"]["policyVersion"],
    "okx_full_market_policy_v2_top100",
)
```

Add a unit test proving two calls to `build_demo_universe_policy()` return independent dictionaries.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m unittest tests.test_demo_override_release -v
```

Expected: failure because the current default is 20 and the new module is missing.

- [ ] **Step 3: Implement the minimal policy module**

```python
from typing import Any

DEMO_DEEP_SCREENING_LIMIT = 100
DEMO_UNIVERSE_POLICY_VERSION = "okx_full_market_policy_v2_top100"

def build_demo_universe_policy() -> dict[str, Any]:
    return {
        "mode": "okx_usdt_linear_perpetual_full_market",
        "screeningLimit": DEMO_DEEP_SCREENING_LIMIT,
        "ranking": "public_quote_volume_proxy_then_spread",
        "policyVersion": DEMO_UNIVERSE_POLICY_VERSION,
    }
```

Replace the inline Top20 dictionary in `_build_strategy()` with this helper.

- [ ] **Step 4: Run tests and verify GREEN**

Run the same unittest command and expect all tests to pass.

- [ ] **Step 5: Commit**

```powershell
git add alphapilot_control_console/demo_universe_policy.py alphapilot_control_console/demo_override_release.py tests/test_demo_override_release.py
git commit -m "Default Demo releases to Top100 screening"
```

---

### Task 2: Pure latency and conditional late-entry policy

**Files:**
- Create: `alphapilot_control_console/demo_entry_latency_policy.py`
- Create: `tests/test_demo_entry_latency_policy.py`

**Interfaces:**
- Produces: `DemoEntryLatencyDecision` dataclass.
- Produces: `evaluate_demo_entry_latency(signal, quote, *, close_received_at, order_ready_at, fee_rate, slippage_rate) -> DemoEntryLatencyDecision`.
- Consumed by: Demo batch execution immediately before `DemoExecutionEngine.execute()`.

- [ ] **Step 1: Write failing boundary tests**

Cover these exact cases:

```python
self.assertEqual(decision.latencyClass, "on_target")       # 4.999 seconds
self.assertEqual(decision.latencyClass, "delayed")         # 7 seconds
self.assertEqual(decision.latencyClass, "conditional")     # 12 seconds and valid drift
self.assertEqual(decision.reasonCode, "signal_expired")    # 30.001 seconds
```

Add direction-aware tests proving a higher current entry is adverse for long, a lower current entry is adverse for short, and missing stop distance rejects conditional late entry after ten seconds.

Add tests proving conditional entry fails for a quote older than two seconds, excessive spread, adverse drift above the dynamic threshold, or recalculated net R below `2.0` after fees and slippage.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m unittest tests.test_demo_entry_latency_policy -v
```

Expected: import failure because the policy module does not exist.

- [ ] **Step 3: Implement the immutable decision model**

```python
@dataclass(frozen=True)
class DemoEntryLatencyDecision:
    passed: bool
    latencyClass: str
    reasonCode: str | None
    closeToReadyMs: int
    quoteAgeMs: int | None
    adverseDriftPercent: float | None
    allowedAdverseDriftPercent: float | None
    recalculatedNetRewardRisk: float | None
```

Use UTC-aware timestamps, finite positive prices, and `Decimal` or controlled floating-point comparisons. Recalculate reward/risk from current executable ask for long or bid for short. Fees and slippage reduce reward and increase risk; the result must remain at least `2.0`.

- [ ] **Step 4: Run tests and verify GREEN**

Run the same unittest command and expect all tests to pass.

- [ ] **Step 5: Commit**

```powershell
git add alphapilot_control_console/demo_entry_latency_policy.py tests/test_demo_entry_latency_policy.py
git commit -m "Enforce Demo signal latency and entry drift policy"
```

---

### Task 3: Transport-independent prewarmed market state

**Files:**
- Create: `alphapilot_control_console/demo_prewarmed_market_state.py`
- Create: `tests/test_demo_prewarmed_market_state.py`
- Modify: `alphapilot_control_console/demo_release_scanner.py`
- Modify: `tests/test_demo_release_scanner.py`

**Interfaces:**
- Produces: `DemoPrewarmedMarketState` with `seed_universe()`, `seed_snapshot()`, `apply_ticker()`, `apply_candle()`, `freeze_for_timeframe()`, `load_universe()`, `load_snapshot()`, `load_metadata()`, and `status()`.
- Produces: `ConfirmedCloseEvent(timeframe, candleStartMs, receivedAt, sequenceId)`.
- Consumes: normalized public-only ticker, candle, metadata, and universe payloads.

- [ ] **Step 1: Write failing state tests**

Prove that:

- unconfirmed candle updates remain provisional and do not emit a close event;
- the first confirmed version emits exactly one event;
- duplicate confirmed messages do not emit twice;
- a frozen snapshot cannot change after later ticker or candle messages;
- all Top100 instruments and BTC context are available before `warm=True`;
- a missing instrument, stale quote, or missing history makes the state not ready;
- loaders never call REST or accept credentials.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m unittest tests.test_demo_prewarmed_market_state -v
```

Expected: import failure because the state module does not exist.

- [ ] **Step 3: Implement locked in-memory state**

Use `threading.RLock`, bounded deques per `(instrument, timeframe)`, and copy-on-freeze dictionaries. Store `receivedAt` separately from exchange candle timestamps. Keep no API keys or private account data.

- [ ] **Step 4: Write failing scanner tests for precomputed factors**

Add a snapshot containing `_precomputedFactors` and assert strategy evaluation uses it without recomputing indicators. Add a test that an immutable loader miss returns `prewarmed_market_snapshot_missing` instead of falling back to network.

- [ ] **Step 5: Add precomputed-factor support**

In `_factors(snapshot)`, return a defensive copy of `_precomputedFactors` when present and structurally valid. Preserve existing calculation as the REST/replay fallback outside the hot path.

- [ ] **Step 6: Run state and scanner tests**

```powershell
python -m unittest tests.test_demo_prewarmed_market_state tests.test_demo_release_scanner -v
```

- [ ] **Step 7: Commit**

```powershell
git add alphapilot_control_console/demo_prewarmed_market_state.py alphapilot_control_console/demo_release_scanner.py tests/test_demo_prewarmed_market_state.py tests/test_demo_release_scanner.py
git commit -m "Add immutable prewarmed Demo market snapshots"
```

---

### Task 4: OKX public WebSocket runtime and REST seeding

**Files:**
- Create: `requirements.txt`
- Create: `alphapilot_control_console/okx_public_market_runtime.py`
- Create: `tests/test_okx_public_market_runtime.py`
- Modify: `scripts/start_okx_demo_console.ps1`
- Create: `scripts/setup_console_runtime.ps1`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `OkxPublicMarketRuntime(state, universe_loader, snapshot_loader, metadata_loader, websocket_factory)`.
- Produces: `start()`, `stop()`, `refresh_subscriptions(releases)`, `add_close_listener(callback)`, and `status()`.
- Consumes: `websocket-client==1.8.0` only for the public `wss://ws.okx.com:8443/ws/v5/public` connection.

- [ ] **Step 1: Write failing parser and lifecycle tests**

With a fake WebSocket, verify subscription payloads contain only public ticker/candle channels for the active Top100 and active timeframes. Verify `confirm=0` stays provisional, `confirm=1` emits a normalized close, ping/pong keeps the connection alive, reconnect clears readiness until REST seed and subscriptions recover, and payloads containing credential-like fields are rejected.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m unittest tests.test_okx_public_market_runtime -v
```

Expected: import failure because the runtime module does not exist.

- [ ] **Step 3: Add the pinned dependency and workspace setup**

`requirements.txt` contains exactly:

```text
websocket-client==1.8.0
```

`scripts/setup_console_runtime.ps1` creates `.venv` under the repository, installs the pinned dependency, imports `websocket`, and prints its version. The Demo launcher prefers `.venv\Scripts\python.exe` when present and otherwise fails with a clear setup command instead of silently running without WebSocket support.

- [ ] **Step 4: Implement public runtime seeding and subscription**

REST seed runs before automation readiness and may use bounded concurrency. The hot path consumes WebSocket updates only. Subscription refresh never removes the current snapshot until the replacement Top100 set is fully seeded and subscribed.

- [ ] **Step 5: Run tests and PowerShell parse checks**

```powershell
python -m unittest tests.test_okx_public_market_runtime -v
powershell -NoProfile -Command "[scriptblock]::Create((Get-Content -Raw scripts/setup_console_runtime.ps1)) | Out-Null"
powershell -NoProfile -Command "[scriptblock]::Create((Get-Content -Raw scripts/start_okx_demo_console.ps1)) | Out-Null"
```

- [ ] **Step 6: Commit**

```powershell
git add requirements.txt .gitignore alphapilot_control_console/okx_public_market_runtime.py scripts/setup_console_runtime.ps1 scripts/start_okx_demo_console.ps1 tests/test_okx_public_market_runtime.py
git commit -m "Add public OKX prewarmed market runtime"
```

---

### Task 5: Confirmed-close wake-up, shared batch evaluation, and latency gate

**Files:**
- Create: `alphapilot_control_console/demo_market_runtime_registry.py`
- Modify: `alphapilot_control_console/unified_auto_execution_runner.py`
- Modify: `alphapilot_control_console/unified_auto_execution_controller.py`
- Modify: `alphapilot_control_console/unified_auto_execution_adapters.py`
- Modify: `alphapilot_control_console/evolution_demo_service.py`
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `tests/test_unified_auto_execution_runner.py`
- Modify: `tests/test_unified_auto_execution_controller.py`
- Modify: `tests/test_demo_automatic_batch.py`
- Modify: `tests/test_evolution_demo_service.py`

**Interfaces:**
- Produces: process-local `get_demo_market_runtime()` and lifecycle helpers.
- Extends: `UnifiedAutoExecutionRunner.wake(environment, close_event)`.
- Extends: Demo batch result with `latencyMetrics`, `marketRuntimeStatus`, `expiredSignals`, and `conditionalLateEntries`.

- [ ] **Step 1: Write failing runner wake-up tests**

Assert a confirmed close wakes the runner immediately instead of waiting for the 15-second heartbeat. Duplicate close sequence IDs are ignored. The controller still writes one checkpoint per release and closed candle.

- [ ] **Step 2: Verify RED**

```powershell
python -m unittest tests.test_unified_auto_execution_runner tests.test_unified_auto_execution_controller -v
```

- [ ] **Step 3: Implement event-aware wake-up**

Carry `closeReceivedAt` and `closeSequenceId` into the Demo adapter. Keep the 15-second heartbeat for recovery and reconciliation, but event wake-up owns the low-latency path.

- [ ] **Step 4: Write failing shared-snapshot and latency integration tests**

For five releases on one timeframe, assert one frozen Top100 snapshot is used. Produce duplicate signals for one symbol and assert exactly one selected order. Add cases where 4-second, 12-second-valid, 12-second-drifted, and 31-second signals respectively create, create, reject, and reject orders.

- [ ] **Step 5: Integrate strict warm loaders and latency evaluation**

`run_evolution_demo_batch_cycle()` must reject with `demo_market_runtime_not_warm` instead of calling public REST. After arbitration, evaluate latency against a fresh quote immediately before `engine.execute()`. Store order-send and exchange-response timestamps without credential fields.

- [ ] **Step 6: Start and stop the public runtime with the HTTP process**

Start public seeding/subscriptions before the automatic runner. Stop the automatic runner first, then stop the public runtime during shutdown. A runtime startup failure leaves Demo automatic execution disabled but keeps the research UI available.

- [ ] **Step 7: Run integration tests**

```powershell
python -m unittest tests.test_unified_auto_execution_runner tests.test_unified_auto_execution_controller tests.test_demo_automatic_batch tests.test_evolution_demo_service -v
```

- [ ] **Step 8: Commit**

```powershell
git add alphapilot_control_console tests
git commit -m "Wake Demo execution from confirmed Top100 closes"
```

---

### Task 6: Immutable Top100 successor migration

**Files:**
- Create: `alphapilot_control_console/demo_release_successor.py`
- Modify: `alphapilot_control_console/unified_auto_execution_store.py`
- Create: `tests/test_demo_release_successor.py`
- Modify: `tests/test_unified_auto_execution_store.py`

**Interfaces:**
- Produces: `build_top100_successor(predecessor, created_at) -> dict[str, Any]`.
- Produces: `activate_top100_successors(contract_dir, archive_root, auto_execution_db, expected_count=10) -> dict[str, Any]`.
- Produces: `UnifiedAutoExecutionStore.retire_checkpoints(environment, release_ids) -> int`.

- [ ] **Step 1: Write failing successor tests**

Assert that the predecessor is unchanged, the successor validates, IDs and hashes differ, Top100 policy is present, `supersedesDemoReleaseId` points to the predecessor, and Demo/live/Withdraw boundaries remain unchanged.

- [ ] **Step 2: Verify RED**

```powershell
python -m unittest tests.test_demo_release_successor -v
```

- [ ] **Step 3: Implement deterministic successor generation**

Build a stable release seed from the predecessor immutable strategy, risk, override, evidence, boundaries, and successor metadata. Recompute `releaseContentHash`, `demoReleaseId`, and `contractHash`, then call `validate_demo_contract()`.

- [ ] **Step 4: Write failing activation tests**

Using temporary directories and SQLite, assert predecessor byte preservation, active successor-only discovery, manifest hashes, selective checkpoint retirement, idempotency, and rollback after a simulated mid-activation failure.

- [ ] **Step 5: Implement activation and checkpoint retirement**

Require `desiredEnabled = false` and prewarmed runtime code availability. Stage and validate every successor, back up SQLite with `Connection.backup`, perform file swaps with rollback, retire only predecessor checkpoints, and append a credential-free audit event.

- [ ] **Step 6: Run migration tests**

```powershell
python -m unittest tests.test_demo_release_successor tests.test_unified_auto_execution_store -v
```

- [ ] **Step 7: Commit**

```powershell
git add alphapilot_control_console/demo_release_successor.py alphapilot_control_console/unified_auto_execution_store.py tests/test_demo_release_successor.py tests/test_unified_auto_execution_store.py
git commit -m "Add immutable Top100 Demo successor migration"
```

---

### Task 7: V13.27.9 observability, UI, documentation, and operator command

**Files:**
- Create: `scripts/activate_top100_demo_releases.ps1`
- Create: `scripts/rehearse_top100_latency.ps1`
- Create: `docs/V13.27.9-top100-demo-release.md`
- Modify: `README.md`
- Modify: `alphapilot_control_console/exchange_demo_simulation.py`
- Modify: `alphapilot_control_console/demo_workflow_projection.py`
- Modify: `alphapilot_control_console/unified_auto_execution_runner.py`
- Modify: `alphapilot_control_console/workflow_client.py`
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `web/app.js`
- Modify: `tests/test_workflow_ui_contract.py`
- Modify: `tests/test_workflow_startup_recovery.py`
- Modify: `tests/test_workflow_client.py`

**Interfaces:**
- Produces: V13.27.9 runtime/version projection.
- Produces: public runtime readiness and latency-stage metrics without credentials.
- Produces: rehearsal and activation commands that cannot place orders.

- [ ] **Step 1: Write failing version, status, and copy tests**

Expect `V13.27.9`, `Top100`, warm/synchronized state, last confirmed close, close-to-evaluation, arbitration, risk, order-send, response durations, latency class, and accurate full-market wording.

- [ ] **Step 2: Verify RED**

```powershell
python -m unittest tests.test_workflow_ui_contract tests.test_workflow_startup_recovery tests.test_workflow_client -v
```

- [ ] **Step 3: Update projections and UI**

Change current-mainline version constants to V13.27.9. Show compact runtime status and a single actionable blocker. Do not render raw quotes for all Top100 instruments or expose credentials.

- [ ] **Step 4: Add no-order rehearsal and activation commands**

The latency rehearsal replays recorded confirmed-close payloads through warm state, scanner, arbitration, and latency policy with a fake order sink. It reports P50/P95/max and must prove no private endpoint call. The activation script invokes only the tested successor migration.

- [ ] **Step 5: Run targeted checks**

```powershell
python -m unittest tests.test_workflow_ui_contract tests.test_workflow_startup_recovery tests.test_workflow_client -v
node --check web/app.js
```

- [ ] **Step 6: Commit**

```powershell
git add scripts docs README.md alphapilot_control_console web/app.js tests
git commit -m "Expose V13.27.9 low-latency Top100 Demo runtime"
```

---

### Task 8: Full verification and controlled activation

**Files:**
- Runtime output only under ignored `data/backups/`, `data/demo_release_contract_archive/`, `data/demo_release_contracts/`, and `data/ops/`.

**Interfaces:**
- Consumes: tested V13.27.9 source, setup, rehearsal, and activation commands.
- Produces: 10 active Top100 successors and measured latency evidence.

- [ ] **Step 1: Run full source verification**

```powershell
python -m unittest discover -s tests -v
python -m compileall alphapilot_control_console
node --check web/app.js
git diff --check
```

Run a targeted safety scan for credential writes, Withdraw, live permission expansion, network calls in the hot scanner, and bypassed release/risk checks.

- [ ] **Step 2: Create the workspace runtime and rehearse without orders**

Run `scripts/setup_console_runtime.ps1`, then `scripts/rehearse_top100_latency.ps1`. The rehearsal must use recorded/public-only data, make zero private calls, and report P95. Functional correctness is required even if the local machine does not yet achieve the five-second target; measured misses remain blockers for activation.

- [ ] **Step 3: Commit and push source**

Push all V13.27.9 source commits before changing runtime contracts. Verify local/remote refs and keep ignored runtime files out of Git.

- [ ] **Step 4: Disable current Demo automation**

Use the local control API `stop` action and verify `desiredEnabled = false`. Do not stop the credential-bearing process until the state is persisted.

- [ ] **Step 5: Activate successors**

Run `scripts/activate_top100_demo_releases.ps1` and verify 10 archived Top20 predecessors, 10 checksum-valid active Top100 successors, manifest, SQLite backup, predecessor checkpoint retirement, and zero live releases.

- [ ] **Step 6: Restart securely**

Run the secure OKX Demo launcher. The user enters process-only credentials; no tool reads or persists them. Wait for `warm=True`, `synchronized=True`, and current quotes before ARM.

- [ ] **Step 7: Arm and verify a real confirmed-close cycle**

Verify V13.27.9, 10 Top100 releases, one shared snapshot per timeframe, no duplicate-symbol order, latency stage metrics, no blockers, and correct conditional/expired decisions. Do not claim the five-second target from replay alone; record the first real cycle separately.

- [ ] **Step 8: Record evidence**

Append migration results, test totals, commit hash, runtime PID, universe counts, unique matches, orders, latency P50/P95/max, expired signals, conditional entries, and safety confirmation to project docs and `D:\Codex-Workspace\踩坑日志.txt`.
