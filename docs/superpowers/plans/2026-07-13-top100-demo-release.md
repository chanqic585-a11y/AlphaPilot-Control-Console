# AlphaPilot V13.27.9 Top100 Demo Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 10 active Top20 OKX Demo releases with immutable Top100 successors and make Top100 the default for all future Demo releases without expanding live-trading permissions.

**Architecture:** A shared universe-policy module defines the Top100 contract. A successor migration module generates checksum-valid replacements, archives predecessors unchanged, backs up execution state, and retires predecessor checkpoints. A batch-scoped scan context caches public universe, OHLCV, and metadata across all due releases before existing arbitration enforces symbol and portfolio limits.

**Tech Stack:** Python 3, standard-library SQLite/JSON/pathlib, unittest, vanilla JavaScript, PowerShell launch scripts.

## Global Constraints

- Existing Top20 contracts remain byte-for-byte preserved in an archive.
- Active and future Demo releases use `screeningLimit = 100` and `okx_full_market_policy_v2_top100`.
- Existing 1D BTC regime and strategy thresholds are unchanged.
- Reward/risk remains at least 2R.
- Demo-only overrides remain ineligible for live promotion.
- No raw API credential storage, no Withdraw, and no new live execution capability.
- Activation requires Demo automatic execution to be disabled and is idempotent.

---

### Task 1: Shared Top100 universe policy and future release default

**Files:**
- Create: `alphapilot_control_console/demo_universe_policy.py`
- Modify: `alphapilot_control_console/demo_override_release.py`
- Test: `tests/test_demo_override_release.py`

**Interfaces:**
- Produces: `DEMO_DEEP_SCREENING_LIMIT`, `DEMO_UNIVERSE_POLICY_VERSION`, and `build_demo_universe_policy() -> dict[str, Any]`.
- Consumed by: future release creation and successor migration.

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

Run:

```powershell
python -m unittest tests.test_demo_override_release -v
```

Expected: failure because the current default is 20 and the new module is missing.

- [ ] **Step 3: Implement the minimal policy module**

```python
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

### Task 2: Batch-scoped public market cache

**Files:**
- Create: `alphapilot_control_console/demo_batch_scan_context.py`
- Modify: `alphapilot_control_console/evolution_demo_service.py`
- Modify: `tests/test_demo_automatic_batch.py`
- Create: `tests/test_demo_batch_scan_context.py`

**Interfaces:**
- Produces: `DemoBatchScanContext` with `load_universe(limit)`, `load_snapshot(instrument, timeframe, limit)`, `load_metadata(instrument)`, and `metrics()`.
- Consumes: existing public loader functions.

- [ ] **Step 1: Write failing cache tests**

Use counting fake loaders and assert repeated keys call each underlying loader once, while different timeframe or limit keys remain independent.

- [ ] **Step 2: Verify RED**

```powershell
python -m unittest tests.test_demo_batch_scan_context -v
```

Expected: import failure because the context module does not exist.

- [ ] **Step 3: Implement minimal in-memory caches**

Use dictionaries keyed by integer limit, `(instrument, timeframe, limit)`, and instrument. Return loader payloads without writing them to disk.

- [ ] **Step 4: Add a failing batch integration assertion**

Update the scanner mock to accept keyword loaders and assert both release scans receive the same bound context methods.

- [ ] **Step 5: Pass the context to every release scan**

Create one `DemoBatchScanContext` before the contract loop and call:

```python
scan_immutable_demo_release(
    contract,
    snapshot_loader=context.load_snapshot,
    metadata_loader=context.load_metadata,
    universe_loader=context.load_universe,
)
```

Include `marketCacheMetrics` in the batch result for audit visibility.

- [ ] **Step 6: Run both test modules**

```powershell
python -m unittest tests.test_demo_batch_scan_context tests.test_demo_automatic_batch -v
```

Expected: all tests pass and duplicate-symbol arbitration still creates one order.

- [ ] **Step 7: Commit**

```powershell
git add alphapilot_control_console/demo_batch_scan_context.py alphapilot_control_console/evolution_demo_service.py tests/test_demo_batch_scan_context.py tests/test_demo_automatic_batch.py
git commit -m "Share public market data across Demo release scans"
```

---

### Task 3: Immutable Top100 successor migration

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

Assert that the predecessor is unchanged, the successor validates, the IDs and hashes differ, Top100 policy is present, `supersedesDemoReleaseId` points to the predecessor, and all Demo/live/Withdraw boundaries remain unchanged.

- [ ] **Step 2: Verify RED**

```powershell
python -m unittest tests.test_demo_release_successor -v
```

Expected: import failure because the module is missing.

- [ ] **Step 3: Implement deterministic successor generation**

Build a stable release seed from the predecessor's immutable strategy, risk, override, evidence, and boundaries plus successor metadata. Recompute `releaseContentHash`, `demoReleaseId`, and `contractHash`, then call `validate_demo_contract()`.

- [ ] **Step 4: Write failing activation tests**

Using temporary directories and SQLite, assert:

- all predecessors are copied unchanged to a timestamped archive;
- active directory contains only successors;
- a migration manifest records every mapping and hash;
- predecessor checkpoints are retired while unrelated checkpoints remain;
- a second activation is a no-op returning the same successor IDs;
- simulated mid-activation failure restores predecessor files.

- [ ] **Step 5: Implement activation and checkpoint retirement**

Require `desiredEnabled = false`, stage and validate every successor, back up SQLite using `Connection.backup`, perform file swaps with rollback, retire only predecessor checkpoints, and append a credential-free audit event.

- [ ] **Step 6: Run migration tests**

```powershell
python -m unittest tests.test_demo_release_successor tests.test_unified_auto_execution_store -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add alphapilot_control_console/demo_release_successor.py alphapilot_control_console/unified_auto_execution_store.py tests/test_demo_release_successor.py tests/test_unified_auto_execution_store.py
git commit -m "Add immutable Top100 Demo successor migration"
```

---

### Task 4: V13.27.9 observability, docs, and operator command

**Files:**
- Create: `scripts/activate_top100_demo_releases.ps1`
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
- Produces: a PowerShell activation command that invokes the tested Python migration and never accepts credentials.

- [ ] **Step 1: Write failing version and copy tests**

Expect `V13.27.9`, `Top100`, accurate full-market wording, and no claim that every exchange contract receives strategy deep screening.

- [ ] **Step 2: Verify RED**

```powershell
python -m unittest tests.test_workflow_ui_contract tests.test_workflow_startup_recovery tests.test_workflow_client -v
```

- [ ] **Step 3: Update version projections and operator copy**

Change relevant current-mainline version constants from V13.27.7 to V13.27.9. Update Demo wording to show public universe, liquidity-eligible count, and Top100 deep screening.

- [ ] **Step 4: Add the activation script and documentation**

The script resolves bundled/project Python, calls the migration module, prints predecessor/successor counts and archive path, and never prompts for API credentials.

- [ ] **Step 5: Run targeted tests and syntax checks**

```powershell
python -m unittest tests.test_workflow_ui_contract tests.test_workflow_startup_recovery tests.test_workflow_client -v
node --check web/app.js
```

- [ ] **Step 6: Commit**

```powershell
git add scripts/activate_top100_demo_releases.ps1 docs/V13.27.9-top100-demo-release.md README.md alphapilot_control_console web/app.js tests
git commit -m "Expose V13.27.9 Top100 Demo release workflow"
```

---

### Task 5: Full verification and controlled activation

**Files:**
- Runtime output only under `data/backups/`, `data/demo_release_contract_archive/`, `data/demo_release_contracts/`, and `data/ops/`.

**Interfaces:**
- Consumes: tested V13.27.9 source and activation command.
- Produces: 10 active Top100 successor releases and an auditable migration record.

- [ ] **Step 1: Run full verification**

```powershell
python -m unittest discover -s tests -v
python -m compileall alphapilot_control_console
node --check web/app.js
git diff --check
```

Run a targeted safety scan for raw credential writes, Withdraw, live permission expansion, and bypassed release checks.

- [ ] **Step 2: Commit and push source**

Push the V13.27.9 source commits before touching runtime contracts.

- [ ] **Step 3: Disable the current Demo automatic runner**

Use the local control API `stop` action and verify `desiredEnabled = false`. Do not stop the credential-bearing process until the state is persisted.

- [ ] **Step 4: Activate successors**

Run `scripts/activate_top100_demo_releases.ps1`. Verify:

- 10 archived Top20 predecessors;
- 10 active Top100 successors;
- checksum-valid contracts;
- migration manifest and SQLite backup;
- predecessor checkpoints retired;
- zero live releases created.

- [ ] **Step 5: Restart securely**

Run the existing secure OKX Demo launcher. The user enters process-only credentials. Do not read or persist them.

- [ ] **Step 6: Arm and verify Top100 scan**

Verify runtime V13.27.9, 10 active releases, `screeningLimit = 100`, shared cache metrics, zero blockers, and one-order maximum per matched symbol after arbitration.

- [ ] **Step 7: Record operational evidence**

Append the migration result, validation results, commit hash, runtime PID, scan counts, unique matches, orders, and safety confirmation to the project docs and `D:\Codex-Workspace\踩坑日志.txt`.
