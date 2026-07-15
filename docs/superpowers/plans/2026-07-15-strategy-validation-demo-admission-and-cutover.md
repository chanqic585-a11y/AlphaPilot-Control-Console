supersededBy: docs/superpowers/plans/2026-07-15-strategy-validation-demo-admission-and-cutover-v2.md
status: superseded

# AlphaPilot Strategy-Validation Demo Admission and Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Admit only formal backtest passes into a separately approved OKX strategy-validation Demo lifecycle, record actual Demo execution in an isolated ledger, and present a concise Strategy/Demo workflow without reintroducing local simulation or enabling Live.

**Architecture:** The Quant Engine creates at most three hash-bound candidate release bundles from formal-pass evidence. The Console imports them as unapproved, stores approval as a separate append-only overlay bound to the exact release hash and frozen risk profile, and exposes only approved releases to the strategy-validation runtime. Strategy Demo orders and closed trades use a dedicated ledger and projections; engineering smoke, shadow, legacy releases, and historical local records remain isolated.

**Tech Stack:** Python 3.12, SQLite, immutable JSON release bundles, existing OKX Demo client/execution engine, pytest/unittest, vanilla JavaScript.

## Global Constraints

- A formal backtest pass is necessary but not sufficient: explicit approval bound to the exact release hash is mandatory.
- Release generation never automatically approves, ARM-enables, or starts execution.
- Admit zero to three releases per campaign; zero is valid.
- Engineering smoke, shadow observation, local history, and `legacy_diagnostic` records never count as strategy-validation evidence.
- Only actual closed trades in the strategy-validation Demo ledger count toward forward review.
- Thirty closed trades means preliminary review; one hundred means serious review. Neither threshold auto-promotes to Live.
- Initial target remains at least 2R, risk is expressed in R, and the initial stop is never widened.
- No Live account, Live position, Live order, automatic Live activation, Withdraw, or API-key persistence is implemented.

---

### Task 1: Replace legacy promotion evidence with formal backtest evidence

**Repository:** `D:\Codex-Workspace\AlphaPilot-Quant-Engine`

**Files:**
- Modify: `alphapilot/evolution/promotion/gate.py`
- Modify: `alphapilot/evolution/promotion/demo_release.py`
- Create: `alphapilot/evolution/promotion/formal_backtest_evidence.py`
- Test: `tests/evolution/test_promotion_gate.py`
- Create: `tests/evolution/test_formal_backtest_evidence.py`

**Required evidence:**

```text
campaignId
candidateId
strategyId
strategyFamilyId
strategyDefinitionHash
dataManifestHash
preregistrationHash
costModelHash
riskConfigHash
backtestReportHash
formalGateHash
holdoutIsolationPassed
walkForwardPassed
baseCostPassed
stress1_5xPassed
```

- [ ] Rewrite failing gate tests so local closed samples, local calendar days, shadow counts, and engineering smoke cannot satisfy admission.
- [ ] Require every formal evidence hash and boolean gate; missing remains failed, not inferred.
- [ ] Preserve old promotion structures only as deprecated readers for historical reports.
- [ ] Require release risk definition to preserve the preregistered >=2R initial target and no-stop-widening rule.
- [ ] Run `python -m pytest tests/evolution/test_promotion_gate.py tests/evolution/test_formal_backtest_evidence.py -q`; expect all tests to pass.

### Task 2: Generate immutable candidate release bundles

**Repository:** `D:\Codex-Workspace\AlphaPilot-Quant-Engine`

**Files:**
- Create: `alphapilot/evolution/promotion/strategy_validation_release.py`
- Create: `alphapilot/scripts/generate_strategy_validation_releases.py`
- Test: `tests/evolution/test_strategy_validation_release.py`
- Create during execution: `reports/backtest_screening/<campaignId>/candidate_releases/*.json`

**Release fields:**

```text
releaseId
releaseHash
campaignId
strategyId
strategyFamilyId
strategyDefinitionHash
dataManifestHash
preregistrationHash
costModelHash
riskConfigHash
backtestReportHash
formalGateHash
releasePurpose=strategy_forward_validation
evidenceClass=demo_strategy_validation
environment=demo
approvalRequired=true
approved=false
createdAt
```

- [ ] Write tests proving only formal passes produce bundles.
- [ ] Write tests enforcing at most three bundles per campaign using the documented ranking, with deterministic tie-breaking.
- [ ] Write tests proving generation does not mutate the source strategy or report and does not write an approval.
- [ ] Canonicalize JSON, calculate SHA-256, and make existing hash-addressed bundles immutable.
- [ ] Reject any bundle referencing a changed preregistration, holdout, cost model, strategy definition, or risk config.
- [ ] Run the generator against the completed real campaign; create zero bundles if there are zero formal passes.
- [ ] Commit: `git commit -m "Generate formal-pass strategy-validation release bundles"`.

### Task 3: Import releases into Console without automatic enablement

**Repository:** `D:\Codex-Workspace\AlphaPilot-Control-Console`

**Files:**
- Create: `alphapilot_control_console/strategy_validation_release_store.py`
- Create: `alphapilot_control_console/strategy_validation_release_service.py`
- Modify: `alphapilot_control_console/demo_workflow_service.py`
- Test: `tests/test_strategy_validation_release_store.py`
- Test: `tests/test_strategy_validation_release_service.py`

**Storage:** `data/strategy_validation_releases.sqlite`

- [ ] Write failing import tests for valid formal bundles, duplicate import, changed bytes, missing hash, wrong purpose, wrong environment, legacy purpose, and more than three from one campaign.
- [ ] Copy accepted canonical bundles to `data/strategy_validation_release_contracts/<releaseHash>.json`; preserve bytes and source hash.
- [ ] Store import metadata and approval state separately from immutable bundle bytes.
- [ ] Default every imported release to `demo_waiting_approval`; never add it to Runtime discovery at import time.
- [ ] Exclude `legacy_diagnostic`, `engineering_smoke`, and unknown release purposes.

### Task 4: Add explicit hash-bound approval and revocation

**Files:**
- Create: `alphapilot_control_console/strategy_validation_approval_store.py`
- Create: `alphapilot_control_console/strategy_validation_approval_service.py`
- Modify: `alphapilot_control_console/http_app.py`
- Test: `tests/test_strategy_validation_approval.py`
- Test: `tests/test_strategy_validation_approval_http.py`

**Approval record:**

```text
approvalId
releaseId
releaseHash
riskConfigHash
action=approve|revoke
actor=human_local_operator
reason
createdAt
previousApprovalHash
recordHash
```

**Endpoints:**

```http
POST /api/strategy-validation-releases/approve
POST /api/strategy-validation-releases/revoke
```

- [ ] Write tests requiring loopback, explicit release ID/hash, frozen risk hash, reason, and append-only history.
- [ ] Reject stale hash approval, changed risk config, revoked release, legacy release, missing formal evidence, and browser-supplied credentials.
- [ ] Make approval idempotent only when the exact request already exists; conflicting duplicate actions return `409`.
- [ ] Ensure approval changes eligibility but does not directly ARM or place an order.

### Task 5: Restrict Runtime discovery to approved strategy releases

**Files:**
- Modify: `alphapilot_control_console/evolution_demo_service.py`
- Modify: `alphapilot_control_console/unified_auto_execution_runner.py`
- Modify: `alphapilot_control_console/unified_auto_execution_controller.py`
- Modify: `alphapilot_control_console/demo_release_scanner.py`
- Test: `tests/test_strategy_validation_runtime_admission.py`

- [ ] Write table-driven tests for formal/unapproved, formal/approved, revoked, legacy, engineering, changed-hash, wrong-environment, and missing-risk-profile releases.
- [ ] Discover only releases whose immutable hash, formal evidence, current approval, frozen risk profile, and Demo environment all verify.
- [ ] Keep Runtime ARM a separate process-level action; an approved release still cannot execute while Runtime is disarmed.
- [ ] Recheck approval and hashes immediately before order intent creation.
- [ ] Fail closed on release-store or approval-store errors and surface an exact blocker.

### Task 6: Create the strategy-validation Demo ledger

**Files:**
- Create: `alphapilot_control_console/strategy_validation_demo_store.py`
- Create: `alphapilot_control_console/strategy_validation_demo_models.py`
- Test: `tests/test_strategy_validation_demo_store.py`

**Storage:** `data/strategy_validation_demo.sqlite`

**Ledger records:**

```text
strategy releases
order intents
exchange orders
partial fills
position snapshots
fees
funding
slippage/reference-price evidence
stop and target state
exit or cancel actions
reconciliation events
closed trades
runtime checkpoints
```

- [ ] Write idempotent migration tests and unique constraints for release hash, client order ID, exchange order ID, fill ID, and closed-trade identity.
- [ ] Store monetary values with explicit currency and timestamps with UTC source plus Beijing display projection.
- [ ] Store sanitized exchange responses only; recursively reject API key, secret, passphrase, signed headers, and raw private response dumps.
- [ ] Keep this database separate from `demo_engineering_smoke.sqlite`, historical Demo ledgers, and shadow observations.
- [ ] Make closed-trade insertion require reconciled entry fills and reconciled exit fills.

### Task 7: Connect the strategy runtime to its isolated ledger

**Files:**
- Create: `alphapilot_control_console/strategy_validation_demo_service.py`
- Modify: `alphapilot_control_console/demo_execution_engine.py`
- Modify: `alphapilot_control_console/evolution_demo_service.py`
- Test: `tests/test_strategy_validation_demo_service.py`
- Test: `tests/test_strategy_validation_demo_recovery.py`

**Interfaces:**

```python
def run_strategy_validation_cycle(
    *,
    approvedReleases: Sequence[dict[str, Any]],
    universe: dict[str, Any],
    client: OkxDemoClient,
) -> dict[str, Any]

def reconcile_strategy_validation_demo(*, client: OkxDemoClient) -> dict[str, Any]
def recover_strategy_validation_runtime(*, client: OkxDemoClient) -> dict[str, Any]
```

- [ ] Write tests for matched/no-match scans, risk rejection, accepted order, partial fill, full fill, open position, stop/target exit, funding update, closed trade, and no duplicate on restart.
- [ ] Use only the authenticated Demo/public eligible universe from Phase 1.
- [ ] Preserve existing order idempotency and low-latency policy, while binding every intent to release hash and source-candle hash.
- [ ] Ensure shadow write failure and engineering-smoke state cannot block or alter a qualified strategy order.
- [ ] Reconcile local order/position/fill state with exchange state before accepting new risk after restart.
- [ ] Keep real OKX rejection codes as failures; never synthesize a successful trade.

### Task 8: Calculate forward review evidence from closed trades only

**Files:**
- Create: `alphapilot_control_console/strategy_validation_forward_review.py`
- Test: `tests/test_strategy_validation_forward_review.py`

**Review statuses:**

```text
0-29 closed trades: collecting
30-99 closed trades: preliminary_review_ready
>=100 closed trades: serious_review_ready
```

- [ ] Write tests proving open orders, open positions, shadow observations, engineering smoke, legacy trades, and local history do not increment counts.
- [ ] Report actual fees, funding, slippage, net PnL, drawdown, symbol/month concentration, and reconciliation exceptions from closed strategy-Demo trades.
- [ ] Preserve one market event hash across shadow and Demo so it cannot be counted as two independent samples.
- [ ] Do not create `live_candidate` or approval automatically at either review threshold.

### Task 9: Expose the backtest-screening projection

**Files:**
- Create: `alphapilot_control_console/backtest_screening_projection.py`
- Modify: `alphapilot_control_console/http_app.py`
- Test: `tests/test_backtest_screening_projection.py`
- Test: `tests/test_backtest_screening_http.py`

**Endpoint:**

```http
GET /api/backtest-screening?campaignId=<id>
```

- [ ] Read only hash-verified Quant campaign projection artifacts from the configured workspace path.
- [ ] Return data audit, preregistration, prefilter, running full backtests, basic/formal passes, failures, budget, and candidate releases.
- [ ] Reject path traversal, changed hashes, malformed projections, and reports outside `D:\Codex-Workspace\AlphaPilot-Quant-Engine\reports\backtest_screening`.
- [ ] Do not trigger a backtest, download, release generation, approval, or Demo action from this GET endpoint.

### Task 10: Rebuild the Strategy page around decision status

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Test: `tests/test_strategy_screening_ui.py`

**Visible sections:**

```text
Data audit
Preregistered campaigns
Event prefilter
Full backtest progress
Basic research passes
Formal passes
Failure attribution
Experiment budget
Immutable releases awaiting approval
```

- [ ] Remove duplicated local-forward counts and Demo execution cards from Strategy.
- [ ] Show one primary next action per item: inspect data, inspect failure, approve exact release, or no action.
- [ ] Rank using formal status, OOS PF, average net R, 1.5x PF, fold ratio, drawdown, concentration, sample size, and evidence completeness.
- [ ] Put hashes, fold detail, cost detail, and FDR behind one advanced disclosure.
- [ ] Display `零正式通过也是有效研究结果`; do not offer a bypass button.

### Task 11: Split the Demo page into two evidence classes

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Test: `tests/test_demo_page_evidence_separation.py`

**Section 1 - Demo 工程状态:**

```text
Runtime status
authenticated instruments
public Top100 intersection
latest engineering order attempt
order/position/exit state
reconciliation
duplicate/orphan counts
```

**Section 2 - 策略验证 Demo:**

```text
approved immutable releases
scan/match/risk/order progress
current orders and positions
entry, stop, target
fees, funding, slippage
net PnL
closed trades
review status
blocker and next action
```

- [ ] Ensure engineering numbers never appear in strategy PF, win rate, PnL, closed trades, or review progress.
- [ ] Hide legacy diagnostic releases from the active strategy list; expose their history only under advanced diagnostics.
- [ ] Keep evidence lists collapsed by default and show a one-time actionable blocker dialog only when user action is required.
- [ ] Keep responsive layouts readable at desktop and narrow mobile-console widths.

### Task 12: Remove all remaining Local Simulation workflow projections

**Files:**
- Modify: `alphapilot_control_console/strategy_lifecycle_projection.py`
- Modify: `alphapilot_control_console/demo_workflow_projection.py`
- Modify: `web/app.js`
- Test: `tests/test_strategy_lifecycle_projection.py`
- Test: `tests/test_demo_workflow_projection.py`

- [ ] Replace local-simulation stage counts with backtest-screening and approval counts.
- [ ] Keep historical local counts only in deprecated audit payloads.
- [ ] Ensure Strategy, Demo, Live, and Mobile Console never describe local history as an active stage.
- [ ] Ensure zero formal passes results in zero release-ready, zero approved, and zero strategy-Demo entries without an error loop.

### Task 13: End-to-end admission tests

**Files:**
- Create: `tests/test_strategy_validation_end_to_end.py`
- Create: `tests/fixtures/strategy_validation_formal_pass.json`
- Create: `tests/fixtures/strategy_validation_basic_only.json`

- [ ] Test `formal pass -> immutable bundle -> import -> waiting approval -> explicit approval -> Runtime discovery -> matched signal -> Demo order -> fill -> exit -> reconciled closed trade -> preliminary count`.
- [ ] Test basic-only, failed, changed hash, revoked, legacy, engineering, shadow-only, and local-history candidates never enter Runtime discovery.
- [ ] Test approval does not ARM Runtime and ARM does not approve a release.
- [ ] Test thirty and one hundred closed trades change review labels only and never write Live state.
- [ ] Test process restart recovers without duplicate order or orphan position.

### Task 14: Integrated safety and runtime proof

**Files:**
- Modify: `README.md` in both repositories
- Create: `docs/strategy-validation-demo-operator-guide.md`

- [ ] Run Console: `python -m unittest discover -s tests -v`.
- [ ] Run Console: `python -m compileall alphapilot_control_console`.
- [ ] Run Quant: `python -m pytest tests -q`.
- [ ] Run Quant: `python -m compileall alphapilot`.
- [ ] Run Quant: `powershell -ExecutionPolicy Bypass -File scripts\check_safety.ps1`.
- [ ] Run `git diff --check` in both repositories.
- [ ] Scan for raw credentials, browser API-key fields, Withdraw, Live-order access, auto-approval, auto-ARM, local-simulation writes, and cross-ledger aggregation.
- [ ] If there is at least one formal pass, import it, approve it explicitly, ARM with process-only Demo credentials, and verify a no-match or real matched cycle without fabricating an order.
- [ ] If there are zero formal passes, verify the complete zero-release path and do not use an old release as a substitute.
- [ ] Verify engineering smoke still works and leaves strategy review counts unchanged.
- [ ] Verify only reconciled closed strategy-Demo trades change forward review counts.

### Task 15: Commit, push, and cutover audit

- [ ] Commit Quant release work without staging the pre-existing report: `git commit -m "Add formal strategy-validation Demo release admission"`.
- [ ] Commit Console: `git commit -m "Cut over to approved strategy-validation Demo workflow"`.
- [ ] Push each repository only after its full checks pass.
- [ ] Confirm the intended worktrees are clean and release/report hashes verify.
- [ ] Tag only after the roadmap-wide acceptance report is complete.
- [ ] Do not create a Live tag, Live release, or Live approval in this phase.

## Phase Exit Gate

Phase 4 passes only when no non-formal evidence can produce a strategy release, every executable release has an exact current approval and frozen risk hash, engineering and strategy ledgers remain separate, only reconciled closed strategy-Demo trades affect forward review, the UI has no active local-simulation stage, and Live remains completely disabled. A campaign with zero formal passes must finish cleanly with zero Demo strategy releases.
