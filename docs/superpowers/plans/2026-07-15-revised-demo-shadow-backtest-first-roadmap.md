# AlphaPilot Revised Demo, Shadow, and Backtest-First Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the duplicated local-simulation stage with an auditable backtest-first research path, an isolated no-PnL shadow observer, an authenticated OKX Demo engineering path, and a separately approved strategy-validation Demo path.

**Architecture:** Work is divided into four independently testable phases across `AlphaPilot-Control-Console` and `AlphaPilot-Quant-Engine`. Each phase has a hard exit gate and a separate commit. Engineering-smoke evidence, shadow diagnostics, historical backtests, and strategy-validation Demo outcomes remain separate by purpose, ledger, API projection, and UI section.

**Tech Stack:** Python 3.12, SQLite, pandas, NumPy, PyArrow, PowerShell, vanilla JavaScript, unittest/pytest, OKX Demo REST API with `x-simulated-trading: 1`.

## Global Constraints

- All work stays under `D:\Codex-Workspace`.
- Preserve the pre-existing Quant change in `reports/archived_failed_strategy_failure_attribution_summary.md`; do not stage, amend, or overwrite it.
- Never store or print raw API key, secret, passphrase, private headers, or signed private responses.
- Do not add Withdraw, Live order access, Live account reads, Live positions, automatic Live activation, or Live Canary behavior.
- Keep Demo and Live clients, caches, releases, ledgers, and approvals isolated.
- Preserve all historical local-simulation data; retirement means no new writes, not deletion.
- Shadow observation is signal diagnostics only: no virtual capital, position, fill, PnL, MFE, MAE, 2R outcome, or promotion evidence.
- Engineering smoke proves plumbing only; it never qualifies a strategy.
- Only a formal backtest pass may produce a strategy-validation Demo release, and explicit approval is still required before execution.
- Risk remains expressed in R; initial target is at least 2R; the initial stop may never be widened.
- Missing data remains null or unavailable. Never synthesize evidence to satisfy a gate.
- Experiment budgets are finite. A failed bounded campaign is archived; thresholds are not weakened to manufacture a pass.

---

## Stage Map

| Stage | Repository | Deliverable | Exit gate |
| --- | --- | --- | --- |
| 0. Baseline freeze | Both | Backups, hashes, Runtime inventory, dirty-worktree record | Every mutable SQLite file and active release set is inventoried without exposing credentials |
| 1. Demo engineering foundation | Control Console | Authenticated Demo universe and isolated engineering smoke | Non-empty public/Demo intersection; minimum Demo lifecycle completes; zero duplicate/orphan state |
| 2. Workflow consolidation | Both | Local simulation retired, ten releases classified legacy, no-PnL shadow observer | No new local writes after restart; legacy history readable; shadow schema contains no performance fields |
| 3. Backtest-first research factory | Quant Engine | Data audit, preregistration, event prefilter, formal campaign | Real bounded run completes; holdout isolation, five folds, costs, FDR, and budget evidence are present |
| 4. Strategy-validation Demo cutover | Both | Immutable release admission, explicit approval, separate strategy ledger, concise UI | Only approved formal-pass releases can execute; only closed strategy-Demo trades count as forward evidence |

## Phase Documents

1. `docs/superpowers/plans/2026-07-15-demo-universe-and-engineering-smoke.md`
2. `docs/superpowers/plans/2026-07-15-local-simulation-retirement-and-shadow-observer.md`
3. `D:\Codex-Workspace\AlphaPilot-Quant-Engine\docs\superpowers\plans\2026-07-15-backtest-first-research-factory.md`
4. `docs/superpowers/plans/2026-07-15-strategy-validation-demo-admission-and-cutover.md`

---

### Task 1: Freeze the baseline before implementation

**Files:**
- Create during execution: `data/backups/revised_demo_backtest_first_<timestamp>/manifest.json`
- Create during execution: `data/backups/revised_demo_backtest_first_<timestamp>/*.sqlite`
- Create during execution in Quant: `data/backups/revised_demo_backtest_first_<timestamp>/manifest.json`
- Modify only at closeout: `D:\Codex-Workspace\踩坑日志.txt`

**Interfaces:**
- Input: current Git status, SQLite files, active Demo contract files, Runtime read-only status.
- Output: SHA-256 manifest with file path, size, hash, copy path, Git HEAD, and pre-existing dirty files.

- [ ] Run `git status --short` and `git rev-parse HEAD` in both repositories; record the Quant report file as pre-existing and out of scope.
- [ ] Use SQLite online backup APIs or a read-only copy process; do not copy an actively written database with a plain unlocked file copy.
- [ ] Hash active files under `data/demo_release_contracts` and record the ten current release IDs without modifying them.
- [ ] Query `/api/auto-execution/runtime?fresh=1` only if the Runtime is already online; record boolean/status fields, never credentials or full private payloads.
- [ ] Verify every manifest path resolves inside `D:\Codex-Workspace`.
- [ ] Stop immediately if backup verification fails.

### Task 2: Execute Phase 1 and stop at its gate

**Plan:** `2026-07-15-demo-universe-and-engineering-smoke.md`

- [ ] Implement authenticated Demo-universe discovery and exact instrument identity normalization test-first.
- [ ] Implement isolated engineering-smoke release, ledger, status API, and reconciliation test-first.
- [ ] Run all Phase 1 focused and full Console tests.
- [ ] Perform one credentialed Demo smoke only after tests pass and the user has supplied process-only Demo credentials.
- [ ] Confirm no strategy metrics, promotion decision, or Live artifact changed.
- [ ] Commit and push Phase 1 before starting Phase 2.

### Task 3: Execute Phase 2 and stop at its gate

**Plan:** `2026-07-15-local-simulation-retirement-and-shadow-observer.md`

- [ ] Classify the current ten immutable releases through a separate overlay as `legacy_diagnostic`.
- [ ] Retire local-simulation startup, writes, transitions, page, and navigation while retaining audit reads.
- [ ] Add the no-PnL shadow observer and read-only diagnostics.
- [ ] Restart the Console and prove local history counts do not increase.
- [ ] Commit and push each repository separately before starting Phase 3.

### Task 4: Execute Phase 3 and stop at its gate

**Plan:** `D:\Codex-Workspace\AlphaPilot-Quant-Engine\docs\superpowers\plans\2026-07-15-backtest-first-research-factory.md`

- [ ] Audit real data availability before choosing families.
- [ ] Lock the preregistration and experiment budget before reading candidate results.
- [ ] Run event prefilter, full backtests, cost stress, purged walk-forward, FDR, and formal gates.
- [ ] Preserve zero formal passes as a valid result; do not rescue the campaign from the holdout.
- [ ] Commit code and immutable preregistration before the result-producing run; commit generated report manifests separately.

### Task 5: Execute Phase 4 and stop at its gate

**Plan:** `2026-07-15-strategy-validation-demo-admission-and-cutover.md`

- [ ] Generate zero to three immutable releases only from formal passes.
- [ ] Require an approval record bound to the release hash before Runtime ARM can include a release.
- [ ] Keep engineering-smoke, legacy, shadow, and strategy-validation records in separate ledgers/statistics.
- [ ] Update Strategy and Demo pages to show only decision-useful status.
- [ ] Run credentialed strategy Demo only if at least one formal release exists and has explicit approval.
- [ ] Do not implement Live Canary even if Demo evidence is positive.

### Task 6: Final integrated acceptance

**Files:**
- Modify: `README.md` in both repositories
- Modify: relevant operator docs under `docs/`
- Modify: `D:\Codex-Workspace\踩坑日志.txt`

- [ ] Run Console tests: `python -m unittest discover -s tests -v`.
- [ ] Run Console compile check: `python -m compileall alphapilot_control_console`.
- [ ] Run Quant tests: `python -m pytest tests -q`.
- [ ] Run Quant compile check: `python -m compileall alphapilot`.
- [ ] Run `powershell -ExecutionPolicy Bypass -File scripts\check_safety.ps1` in Quant.
- [ ] Run `git diff --check` in both repositories.
- [ ] Scan for credential persistence, Withdraw, Live-order enablement, local-simulation writes, and shadow performance fields.
- [ ] Confirm the four required read-only APIs return schemas documented by the approved design.
- [ ] Confirm engineering smoke has `orderAttemptCount > 0`, readable order/position state, and zero duplicate/orphan records.
- [ ] Confirm local virtual equity and record counts are unchanged across a restart and observation interval.
- [ ] Confirm the screening report is generated from real data and includes the preregistration hash and experiment-budget counters.
- [ ] Confirm at most three strategy-validation releases exist and none is automatically approved or armed.
- [ ] Tag only after all acceptance evidence is written and both intended worktrees are clean.

## Execution Order and Stop Policy

- A phase may not begin until the previous phase is committed, pushed, and clean.
- A failed gate blocks later phases; it does not authorize a threshold reduction.
- Missing process-only Demo credentials block credentialed runtime proof only. Continue offline tests and documentation, then stop at the credential boundary.
- If the research campaign yields zero formal passes, Phase 4 still implements admission and UI contracts but creates zero strategy-validation releases.
- Any unexpected Live or Withdraw capability is a hard stop.

## Completion Definition

This roadmap is complete only when the product has one visible research path (`Strategy -> approved strategy-validation Demo`) and one visible engineering path (`Demo engineering status`), with local simulation removed from the active workflow, historical records preserved, and no evidence class able to masquerade as another.
