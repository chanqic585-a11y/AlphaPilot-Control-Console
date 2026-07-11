# Targeted Strategy Optimization Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give failed or blocked backtests the actions `重新回测 / 改善优化 / 归档`, and make the same targeted optimization flow available from local-forward and Demo strategy cards.

**Architecture:** The Quant Engine remains the authority for immutable `StrategyVersion` records and workflow stage transitions. The Control Console derives explainable parameter suggestions from the current strategy parameters plus stage evidence, then either creates a canonical challenger or imports an optimized legacy strategy into the canonical workflow; every changed strategy restarts at backtesting and keeps its source record intact.

**Tech Stack:** Python 3.12, SQLite workflow registry, stdlib HTTP server, vanilla JavaScript/CSS/HTML, `unittest`.

## Global Constraints

- `targetR` and `targetRMultiple` must remain greater than or equal to `2.0`.
- A parameter or strategy-definition change creates a new immutable strategy version and starts again at backtesting.
- Data-integrity blockers must recommend data repair and same-version rerun; they must not fabricate parameter improvements.
- Existing backtest, local-forward, Demo, archive, and sample records must not be deleted or rewritten.
- No Trade API, Withdraw API, API key persistence, real order creation, or automatic live trading is added.

---

### Task 1: Quant Optimization Boundary

**Files:**
- Modify: `D:/Codex-Workspace/AlphaPilot-Quant-Engine/alphapilot/evolution/workflow/projection.py`
- Modify: `D:/Codex-Workspace/AlphaPilot-Quant-Engine/alphapilot/evolution/workflow/cli.py`
- Modify: `D:/Codex-Workspace/AlphaPilot-Quant-Engine/alphapilot/evolution/workflow/bootstrap.py`
- Test: `D:/Codex-Workspace/AlphaPilot-Quant-Engine/tests/evolution/test_workflow_orchestrator.py`
- Test: `D:/Codex-Workspace/AlphaPilot-Quant-Engine/tests/evolution/test_workflow_cli.py`

**Interfaces:**
- Produces projection field `optimizationContext` with immutable source definition and parameters.
- Produces CLI command `import-optimized` for legacy strategy lineage, with changed-parameter and `targetR >= 2` validation.

- [ ] Write projection and CLI failure tests.
- [ ] Run the focused tests and verify failures are caused by missing optimization context/import support.
- [ ] Add the minimal projection and legacy import implementation.
- [ ] Run focused and full Quant tests.

### Task 2: Control Console Optimization Service

**Files:**
- Create: `alphapilot_control_console/strategy_optimization.py`
- Modify: `alphapilot_control_console/usable_strategy_catalog.py`
- Modify: `alphapilot_control_console/strategy_lifecycle_projection.py`
- Modify: `alphapilot_control_console/workflow_client.py`
- Test: `tests/test_strategy_optimization.py`
- Test: `tests/test_strategy_lifecycle_projection.py`
- Test: `tests/test_workflow_client.py`

**Interfaces:**
- Produces `build_optimization_context(...)` and deterministic `proposedParameters` plus per-field reasons.
- Extends legacy lifecycle rows with a safe `optimizationContext` sourced from existing research specs.
- Supports `challenger` and `import-optimized` actions with optional immediate backtest start.

- [ ] Write failure tests for parameter recommendations, unchanged-content rejection, `2R` enforcement, and legacy action command construction.
- [ ] Run focused tests and verify RED.
- [ ] Implement the minimum service, catalog enrichment, projection enrichment, and action routing.
- [ ] Run focused and full Console tests.

### Task 3: Three-Page Actions and Parameter Dialog

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Test: `tests/test_workflow_ui_contract.py`

**Interfaces:**
- Failed/blocked backtest actions: `重新回测`, `改善优化`, `归档`.
- Local-forward and Demo cards expose `改善优化`.
- Dialog shows diagnosis, current values, proposed values, reasons, and creates an immutable version that restarts at backtest.

- [ ] Write DOM/source contract tests for all three stages and the parameter dialog.
- [ ] Run focused tests and verify RED.
- [ ] Add the dialog, action mapping, validation copy, and responsive styles.
- [ ] Update JS/CSS cachebusters and run Node syntax plus focused tests.

### Task 4: Integration and Release Verification

**Files:**
- Modify: `README.md`
- Modify: `D:/Codex-Workspace/踩坑日志.txt`

- [ ] Run Quant and Console full test suites, compile checks, Node syntax check, `git diff --check`, and safety scan.
- [ ] Merge the isolated branches into clean main branches without touching runtime evidence.
- [ ] Verify process-only Demo credentials are absent before restarting port `8766`.
- [ ] Test the real browser at `http://127.0.0.1:8766/`, including the Alpha191 blocked card and local/Demo optimization dialogs.
- [ ] Commit and push the verified patch; report hashes, runtime status, and any residual limitation.
