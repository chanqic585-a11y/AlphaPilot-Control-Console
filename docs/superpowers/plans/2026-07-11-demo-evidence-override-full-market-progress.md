# V13.27.1.4 Demo Evidence, Full-Market Scan, and Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add permanent Demo evidence visibility, a fail-closed Demo-only override, OKX full-market candidate screening, and visible progress for every running workflow.

**Architecture:** Pure evidence and universe modules provide deterministic policy decisions. The Demo workflow service performs audited actions, while the projection remains the only UI-facing composition layer. Existing exchange order, runtime, risk, kill-switch, reconciliation, and live gates remain untouched and authoritative.

**Tech Stack:** Python 3.11 standard library, unittest/pytest, vanilla JavaScript, HTML, CSS, local JSON state, OKX public REST endpoints.

## Global Constraints

- Version is `V13.27.1.4`.
- Controlled override is `experimental_override` and only targets OKX Demo.
- Formal backtest, strategy definition, risk envelope, and target `>= 2R` cannot be bypassed.
- Live candidate, live execution, withdraw, raw credential storage, and automatic live promotion remain disabled.
- No APK build is required.

---

### Task 1: Permanent Demo evidence checklist

**Files:**
- Create: `alphapilot_control_console/demo_evidence.py`
- Modify: `alphapilot_control_console/demo_workflow_projection.py`
- Test: `tests/test_demo_evidence.py`
- Test: `tests/test_demo_workflow_projection.py`

**Interfaces:**
- Produces: `build_demo_evidence_checklist(lifecycle_item, contract, runtime) -> dict`
- Produces: `evaluate_demo_override_hard_gates(lifecycle_item) -> dict`

- [ ] Write tests asserting every card contains permanent evidence rows with current, target, source type, blocking state, and next action.
- [ ] Run `python -m pytest tests/test_demo_evidence.py tests/test_demo_workflow_projection.py -q` and verify missing-module or missing-key failures.
- [ ] Implement the minimal evidence builder and projection wiring.
- [ ] Re-run the focused tests and verify they pass.

### Task 2: OKX full-market public universe

**Files:**
- Create: `alphapilot_control_console/okx_market_universe.py`
- Modify: `alphapilot_control_console/exchange_connectors/public_exchange_registry.py`
- Test: `tests/test_okx_market_universe.py`

**Interfaces:**
- Produces: `build_okx_usdt_swap_universe(instruments, tickers, screening_limit=50) -> dict`
- Produces: `fetch_okx_usdt_swap_universe(screening_limit=50) -> dict`

- [ ] Write tests with fixed instruments/tickers payloads covering live USDT linear swaps, invalid price/volume, spread rejection, ranking, and capped deep-screen pool.
- [ ] Run the focused test and verify the new module is missing.
- [ ] Implement payload loading, filtering, ranking, and progress/statistics output using public endpoints only.
- [ ] Re-run the focused tests and verify they pass.

### Task 3: Dynamic release scanner

**Files:**
- Modify: `alphapilot_control_console/demo_release_scanner.py`
- Test: `tests/test_demo_release_scanner.py`

**Interfaces:**
- Consumes: `fetch_okx_usdt_swap_universe(screening_limit)`.
- Produces: scanner output with `universe`, `progress`, ranked `matches`, and rejection reasons.

- [ ] Write failing tests proving a dynamic full-market policy calls the injected universe loader and scans all eligible ranked instruments up to the configured cap.
- [ ] Run the focused test and verify failure because only frozen `eligibleInstruments` are supported.
- [ ] Add an injected `universe_loader`, dynamic policy handling, real completed/required progress, and backward compatibility for old releases.
- [ ] Re-run the focused tests and verify both legacy and dynamic behavior pass.

### Task 4: Audited Demo-only override release

**Files:**
- Create: `alphapilot_control_console/demo_override_release.py`
- Modify: `alphapilot_control_console/demo_workflow_service.py`
- Modify: `alphapilot_control_console/evolution_demo_service.py`
- Test: `tests/test_demo_override_release.py`
- Test: `tests/test_demo_workflow_actions.py`

**Interfaces:**
- Produces: `authorize_demo_override(item, reason, confirmation, *, contract_dir=None) -> dict`
- Consumes confirmation phrase `仅放行到OKX DEMO`.
- Produces a contract accepted by `validate_demo_contract` with `releaseMode=experimental_override` and `livePromotionAllowed=false`.

- [ ] Write failing tests for missing reason, wrong confirmation, no formal backtest, target below 2R, incomplete definition, successful idempotent release, audit metadata, and live lock.
- [ ] Run the focused tests and verify the module/action is absent.
- [ ] Implement fail-closed validation, deterministic identity/hash, atomic contract write, and audit append.
- [ ] Add `authorize_demo_override` service action without calling any order function.
- [ ] Re-run focused tests and verify all pass.

### Task 5: Per-strategy concurrent-symbol limits

**Files:**
- Create: `alphapilot_control_console/demo_strategy_runtime_settings.py`
- Modify: `alphapilot_control_console/state_store.py`
- Modify: `alphapilot_control_console/demo_release_scanner.py`
- Modify: `alphapilot_control_console/demo_workflow_service.py`
- Test: `tests/test_demo_strategy_runtime_settings.py`
- Test: `tests/test_demo_release_scanner.py`

**Interfaces:**
- Produces: `get_demo_strategy_runtime_settings(strategy_id) -> dict`
- Produces: `update_demo_strategy_runtime_settings(strategy_id, max_concurrent_symbols) -> dict`
- Produces: `effective_symbol_limit(requested, portfolio_limit, remaining_slots, risk_slots, matched_count) -> int`

- [ ] Write failing tests for default one symbol, bounded settings, audit persistence, and the minimum-of-all-risk-limits rule.
- [ ] Run focused tests and verify the module/action is absent.
- [ ] Implement local audited settings and enforce the effective limit before Demo signal selection.
- [ ] Add an update action that never touches credentials, orders, or live settings.
- [ ] Re-run focused tests and verify all pass.

### Task 6: Workflow UI and universal progress bars

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Test: `tests/test_workflow_ui_contract.py`

**Interfaces:**
- Consumes `item.evidenceChecklist`, `item.marketUniverse`, and normalized progress.
- Produces reason/confirmation dialog payload for `authorize_demo_override`.

- [ ] Extend UI contract tests for the backtest progress track, evidence checklist, automatic/manual source labels, full-market statistics, corrected candidate wording, and Demo-only confirmation dialog.
- [ ] Run the UI contract test and verify it fails on missing elements/functions.
- [ ] Add `dualLayerProgressModel()` and render a progress track for queued/running/paused work.
- [ ] Render evidence and full-market sections on every Demo card, rename the pre-trade symbol field, and add the audited override dialog.
- [ ] Re-run UI tests and `node --check web/app.js`.

### Task 7: Shared Demo/Live monitor structure

**Files:**
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Modify: `web/index.html`
- Test: `tests/test_workflow_ui_contract.py`

**Interfaces:**
- Produces compact execution monitor rows with strategy, symbol, position, PnL, risk, and stop state.

- [ ] Write failing UI contract assertions for concurrent-symbol controls, compact position lists, and shared Demo/Live terminology.
- [ ] Implement the compact Demo view and simplify the Live monitor without changing execution behavior.
- [ ] Re-run the UI contract and JavaScript syntax checks.

### Task 8: Version, documentation, validation, and integration

**Files:**
- Modify: `README.md`
- Modify: `web/index.html`
- Modify: version constants returned by health/workflow modules as found by repository search.
- Modify: `D:/Codex-Workspace/踩坑日志.txt`

**Interfaces:**
- Produces V13.27.1.4 release notes and verifiable runtime version.

- [ ] Update version labels and README with Demo-only override and public full-market boundary.
- [ ] Run the complete Python test suite, Python compile, JavaScript syntax check, and `git diff --check`.
- [ ] Run targeted safety scans and confirm no live/withdraw/raw-key bypass.
- [ ] Start the console without credentials, verify health/runtime gates, and use browser screenshots at desktop and narrow mobile widths.
- [ ] Commit the feature branch, merge into main, tag `v13.27.1.4`, push branch/main/tag, restart the local console, and verify the final URL.
