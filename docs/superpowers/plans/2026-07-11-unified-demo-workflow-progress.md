# V13.27.1.3 Unified Demo Workflow Progress Implementation Plan

> **For Codex:** Execute this plan with TDD. Preserve the existing immutable release gate and OKX Demo-only safety boundary.

**Goal:** Make Strategy, Local Forward, and OKX Demo stages show real process, progress, blockers, results, and one unambiguous next action. The Demo page must expose four exclusive queues: waiting, validating, passed, and live candidate.

**Architecture:** Add a read-only workflow progress projection in the Control Console. It joins the canonical strategy lifecycle with existing Demo trial candidates, immutable Demo release contracts, execution records, runtime gates, public market scans, and redacted OKX Demo events. UI actions call a narrow stage-action endpoint that performs only the currently legal action; it never bypasses release checks or invents execution data.

**Tech Stack:** Python standard library HTTP service, existing Console services and SQLite stores, vanilla JavaScript/CSS, unittest/pytest.

## Technical Decision

1. **UI-only derivation:** Fast but leaves “start Demo” non-functional and risks presenting guessed progress.
2. **Unified read model plus gated actions (selected):** Reuses existing lifecycle, immutable release, execution, and reconciliation sources. Unknown values stay null and render as “尚未开始”.
3. **Directly submit the ten trial strategies:** Rejected because it bypasses immutable Demo Release and risk gates.

Impact is limited to the Control Console API/read model/UI/tests/docs. No Quant strategy definitions, database migration, credential storage, live order path, or Withdraw API are added.

---

### Task 1: Define the Demo workflow projection contract

**Files:**
- Create: `alphapilot_control_console/demo_workflow_projection.py`
- Test: `tests/test_demo_workflow_projection.py`

1. Write failing tests for the four queue counts and exclusive classification.
2. Verify RED.
3. Implement projection from lifecycle plus exchange Demo payload.
4. Include per-strategy `progress`, `processSteps`, `market`, `position`, `performance`, `failure`, and `nextAction` fields.
5. Unknown execution values must remain `None`, never synthetic zero.
6. Verify targeted tests GREEN.

### Task 2: Expose a safe next-step action

**Files:**
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `alphapilot_control_console/exchange_demo_simulation.py`
- Test: `tests/test_demo_workflow_actions.py`

1. Write failing API/service tests for `preflight`, public scan, and gated cycle behavior.
2. Verify RED.
3. Add a narrow action dispatcher:
   - trial without Release: return preflight blockers and exact required action;
   - release with missing runtime gates: return blockers without execution;
   - eligible release with all gates: reuse `run_evolution_demo_cycle`;
   - operational retry never changes strategy parameters;
   - parameter optimization remains immutable and restarts at backtest.
4. Add GET projection and POST action endpoints.
5. Verify targeted tests GREEN.

### Task 3: Add visible progress to all three active stages

**Files:**
- Modify: `alphapilot_control_console/strategy_lifecycle_projection.py`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Test: `tests/test_strategy_lifecycle_projection.py`
- Test: `tests/test_workflow_ui_contract.py`

1. Write failing tests for progress labels and required UI markers.
2. Verify RED.
3. Add stage progress metadata for backtest and local forward cards.
4. Render a progress bar, current step, completed/required evidence, blocker reason, and next action.
5. Keep advanced identifiers/details collapsed.
6. Verify targeted tests GREEN.

### Task 4: Rebuild the Demo main panel around four queues

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Test: `tests/test_workflow_ui_contract.py`

1. Write failing contract tests for exact labels:
   - `待 Demo 模拟`
   - `Demo 验证中`
   - `Demo 模拟通过`
   - `实盘候选`
2. Verify RED.
3. Render four summary cards and four exclusive lanes.
4. Each strategy card shows actual symbol, prices, position, TP/SL, realized/unrealized PnL, fees, slippage, closed sample progress, and reconciliation status when available.
5. Missing data displays `--` or `尚未开始`.
6. Failed strategies show failure analysis and `重新验证`/`改善优化`/`归档` only when semantically valid.
7. Add the single primary action `执行下一步` with a plain-language explanation.
8. Keep old connectivity-smoke tools under Advanced.
9. Verify targeted tests GREEN.

### Task 5: Documentation and full verification

**Files:**
- Modify: `README.md`
- Create: `docs/V13.27.1.3-unified-demo-workflow-progress.md`

1. Document the exclusive stage model and Demo start sequence.
2. Explain that current trial items do not trade until immutable Release and runtime gates are ready.
3. Run `python -m pytest -q`.
4. Run `git diff --check`.
5. Run focused safety scan for live/withdraw/credential storage regressions.
6. Start the updated Console without raw credentials, verify API/UI in browser, and confirm current ten items appear under `待 Demo 模拟` with a visible blocker and next action.
7. Commit, integrate to `main`, tag `v13.27.1.3`, push, restart the local Console, and verify the final endpoint.
