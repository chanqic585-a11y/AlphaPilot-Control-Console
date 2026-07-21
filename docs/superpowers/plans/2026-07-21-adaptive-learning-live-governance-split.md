# Adaptive Learning Live Governance Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split adaptive-learning technical readiness, exact Live approval, and Live ARM into independent fail-closed gates while blocking the current observer-based Live draft.

**Architecture:** Add three focused gate modules and retain the previous gate name only as a compatibility facade. Bind the existing versioned execution-latency policy into the experimental Live draft, emit a non-mutating governance disposition for historical artifacts, and generate truthful blocked evidence until a new decision-participating model completes every technical gate.

**Tech Stack:** Python 3.11, dataclasses/mappings, JSON artifacts, unittest/pytest, PowerShell validation scripts.

## Global Constraints

- Do not change frozen strategy results, Demo Release identities, model parameters, or existing immutable artifacts.
- `exactHumanApproval` is never technical readiness evidence.
- Observer models never enter Live.
- `criticalLatencyFailureMs=20000` is not an order-submission deadline.
- Risk remains draft and any change creates a new Risk Overlay Hash.
- Do not approve, ARM, create strategy Live orders, enable Live, or enable Withdraw.
- Do not restart the currently running Demo process.

---

### Task 1: Three independent gates

**Files:**
- Create: `alphapilot_control_console/adaptive_learning_technical_readiness.py`
- Create: `alphapilot_control_console/exact_live_release_approval_gate.py`
- Create: `alphapilot_control_console/live_arm_gate.py`
- Modify: `alphapilot_control_console/adaptive_learning_live_readiness.py`
- Test: `tests/test_adaptive_learning_live_readiness.py`

**Interfaces:**
- Produces: `AdaptiveLearningTechnicalReadinessGate.evaluate(model_policy, evidence)`.
- Produces: `ExactLiveReleaseApprovalGate.evaluate(bundle, approval)`.
- Produces: `LiveArmGate.evaluate(bundle, approval_gate, runtime)`.

- [ ] Write failing tests proving technical readiness ignores `exactHumanApproval`, observer mode fails, approval is non-actionable while technical readiness fails, and ARM requires a passed approval gate.
- [ ] Run the focused test and confirm failure on missing classes or old circular behavior.
- [ ] Implement the three gates and compatibility facade.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Draft Release, Approval, latency, and risk semantics

**Files:**
- Modify: `alphapilot_control_console/experimental_live_canary_release.py`
- Modify: `alphapilot_control_console/execution_latency_profile.py`
- Modify: `alphapilot_control_console/live_safety_plane.py`
- Modify: `alphapilot_control_console/live_canary_service.py`
- Modify: `alphapilot_control_console/live_auto_execution_service.py`
- Test: `tests/test_experimental_live_canary_release.py`
- Test: `tests/test_execution_latency_profile.py`

**Interfaces:**
- Consumes: `executionLatencyProfileHash` and distinct target/max-age/Ack/critical fields.
- Produces: blocked draft status, non-actionable approval request, draft Risk Overlay, and three independent gate results.

- [ ] Write failing tests for observer draft status, non-actionable approval, disabled mechanical execution, strict maximum age below 20 seconds, configurable latency hash, and risk hash changes.
- [ ] Run focused tests and confirm the old 20-second duplicate semantics fail.
- [ ] Bind the authoritative latency policy, mark risk as draft, and route approval/ARM through the new gates.
- [ ] Run focused tests and confirm they pass.

### Task 3: Readiness snapshot and current-draft governance evidence

**Files:**
- Modify: `alphapilot_control_console/adaptive_learning_readiness_snapshot.py`
- Modify: `alphapilot_control_console/v55_adaptive_learning_evidence.py`
- Create: `alphapilot_control_console/adaptive_learning_governance_evidence.py`
- Create: `scripts/build_adaptive_learning_governance_evidence.py`
- Test: `tests/test_adaptive_learning_readiness_snapshot.py`
- Create: `tests/test_adaptive_learning_governance_evidence.py`

**Interfaces:**
- Produces: a technical-only readiness matrix and a versioned disposition referencing historical Live draft hashes without overwriting them.

- [ ] Write failing tests proving exact approval is absent from technical capabilities and historical artifacts receive a blocked governance disposition.
- [ ] Run the focused tests and confirm failure.
- [ ] Implement the snapshot migration and artifact generator.
- [ ] Run focused tests and generate the evidence bundle.

### Task 4: Truthful technical-gap campaign status

**Files:**
- Create: `reports/v60_1_adaptive_learning_governance/<runId>/...` through the generator only.
- Modify: `README.md`

**Interfaces:**
- Consumes existing V59 factor, model, Qlib, drift, rollback, Demo, and Live evidence.
- Produces a truthful capability matrix; missing real samples or failed formal evidence remains blocked and is never fabricated.

- [ ] Collect existing evidence by immutable path and hash.
- [ ] Generate technical, approval, ARM, latency, risk, and disposition artifacts.
- [ ] Confirm the current result remains blocked if real evidence is incomplete.
- [ ] Document the new governance boundary and next automatic evidence-producing actions.

### Task 5: Verification and publication

**Files:**
- Modify generated artifact manifest and closeout only through the generator.

**Interfaces:**
- Produces reproducible test, safety, Git, and artifact receipts.

- [ ] Run focused tests.
- [ ] Run the full Console test suite.
- [ ] Run `python -m compileall alphapilot_control_console scripts`.
- [ ] Run configuration validation, safety scan, and `git diff --check`.
- [ ] Confirm Live disabled, Withdraw disabled, no ARM, no strategy Live orders, and no credentials persisted.
- [ ] Commit, tag, and push the governance patch without modifying the running Demo process.
