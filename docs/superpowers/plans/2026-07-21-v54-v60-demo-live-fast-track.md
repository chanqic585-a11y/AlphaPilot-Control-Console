# V54-V60 Demo Activation and Live Fast-Track Implementation Plan

> **For Codex:** Execute this plan sequentially with TDD and commit checkpoints. Do not cross an exact approval gate without the required immutable identity and user authorization.

**Goal:** Activate the frozen TOP200 Demo Release through exact approval and audited ARM, harden its low-latency execution and versioned controls, then build an isolated Live canary path up to the exact Live approval gate.

**Architecture:** Add narrowly scoped services around the V53 immutable artifacts. Reuse the existing Demo execution, TOP200, engineering-smoke, risk-profile, Live isolation, and minimal projection modules. Keep every write append-only and environment-bound. Project one source of truth into the UI and evidence bundle.

**Tech Stack:** Python 3.12, stdlib HTTP/SQLite/JSON, pytest, vanilla HTML/CSS/JavaScript, PowerShell launchers, SHA-256 canonical JSON artifacts.

---

## Task 1: Freeze and verify the V53 baseline

**Files:**
- Create: `alphapilot_control_console/v54_baseline_audit.py`
- Create: `scripts/build_v54_baseline_audit.py`
- Test: `tests/test_v54_baseline_audit.py`
- Read: `data/top200_minimal_ui/**`

- [ ] Add failing tests for evidence ZIP hash/CRC/manifest verification.
- [ ] Add failing tests for Release-to-final-HEAD execution-path diff classification.
- [ ] Add failing tests for strategy-order count scope reconciliation.
- [ ] Implement deterministic read-only auditors and redacted artifacts.
- [ ] Generate `baseline_evidence_verification.json`, `release_to_final_head_execution_diff_audit.json`, and `strategy_order_scope_reconciliation.json`.
- [ ] Run targeted tests and commit the baseline audit.

## Task 2: Build signal matchability readiness

**Files:**
- Create: `alphapilot_control_console/demo_matchability_readiness.py`
- Create: `scripts/build_demo_matchability_readiness.py`
- Test: `tests/test_demo_matchability_readiness.py`
- Modify: `alphapilot_control_console/top200_minimal_ui_projection.py`

- [ ] Add failing tests for component universe compatibility and deterministic 30/90-day read-only rehearsal summaries.
- [ ] Assert no order client or private endpoint is reachable from the rehearsal path.
- [ ] Implement component-level candidate counts, blocker attribution, and pre-ARM funnel counts.
- [ ] Generate `component_signal_matchability.csv`, `signal_matchability_30d.json`, `signal_matchability_90d.json`, and `pre_arm_scan_funnel.json`.
- [ ] Project only four headline readiness values into the Demo page; keep details collapsed.
- [ ] Run targeted tests and commit V54 readiness.

## Task 3: Add exact Demo approval and ARM overlays

**Files:**
- Create: `alphapilot_control_console/exact_release_approval.py`
- Create: `alphapilot_control_console/demo_activation_service.py`
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `alphapilot_control_console/top200_minimal_ui_projection.py`
- Modify: `web/top200-minimal-ui.js`
- Test: `tests/test_exact_release_approval.py`
- Test: `tests/test_demo_activation_service.py`
- Test: `tests/test_top200_minimal_ui_http.py`

- [ ] Add failing tests that reject any Release/Risk/Intersection/Request hash mismatch.
- [ ] Add failing tests that prove approval and ARM are separate append-only events.
- [ ] Add failing tests for missing credentials, stale snapshot, risk blocker, and unapproved Release.
- [ ] Implement exact approval overlay storage with no artifact mutation.
- [ ] Implement ARM service that delegates to the existing Demo runtime only after all gates pass.
- [ ] Add minimal approval and ARM endpoints and UI actions.
- [ ] Record the user-approved frozen TOP200 identity only after all exact checks pass.
- [ ] Back up runtime SQLite stores before any operational write.
- [ ] Run targeted tests, perform read-only checks, then commit V54 activation.

## Task 4: Run approved TOP200 Demo and expose the full funnel

**Files:**
- Modify: `alphapilot_control_console/unified_auto_execution_runner.py`
- Modify: `alphapilot_control_console/demo_market_scan_service.py`
- Modify: `alphapilot_control_console/demo_prewarmed_market_state.py`
- Modify: `alphapilot_control_console/demo_evaluation_audit.py`
- Modify: `alphapilot_control_console/top200_minimal_ui_projection.py`
- Test: `tests/test_demo_approved_run_all.py`
- Test: `tests/test_demo_evaluation_audit.py`

- [ ] Add failing tests for approved-only run-all behavior and closed-candle scheduling.
- [ ] Add failing tests for the complete funnel: universe, liquidity, depth, component signals, arbitration, risk, order, fill, and position.
- [ ] Preserve zero-natural-signal truth; add only evidence-ineligible engineering fixtures.
- [ ] Implement full funnel ledgers and a first-scan audit.
- [ ] Verify strategy orders remain zero until a natural signal passes every gate.
- [ ] Commit V55 normal Demo operation.

## Task 5: Harden the ultra-low-latency hot path

**Files:**
- Create: `alphapilot_control_console/execution_latency_profile.py`
- Modify: `alphapilot_control_console/demo_entry_latency_policy.py`
- Modify: `alphapilot_control_console/demo_latency_observability.py`
- Modify: `alphapilot_control_console/demo_execution_engine.py`
- Modify: `alphapilot_control_console/exchange_connectors/okx_demo_private_ws.py`
- Test: `tests/test_execution_latency_profile.py`
- Test: `tests/test_demo_entry_latency_policy.py`
- Test: `tests/test_demo_latency_observability.py`

- [ ] Add failing tests for versioned latency profiles and stale-signal fail-closed behavior.
- [ ] Add failing tests for market-state reuse and no public-data download in the order hot path.
- [ ] Instrument candle-close, signal, risk, submit, acknowledge, fill, and reconciliation timestamps.
- [ ] Prefer a healthy private WebSocket order path with bounded REST fallback.
- [ ] Reject critical latency and record every fallback/rejection reason.
- [ ] Generate latency profile, benchmark, ledger, and stale-signal audit artifacts.
- [ ] Commit V55 latency hardening.

## Task 6: Version runtime risk and strategy switching

**Files:**
- Modify: `alphapilot_control_console/risk_profile_service.py`
- Modify: `alphapilot_control_console/risk_profile_store.py`
- Modify: `alphapilot_control_console/demo_strategy_runtime_settings.py`
- Create: `alphapilot_control_console/strategy_version_switch.py`
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `web/top200-minimal-ui.js`
- Test: `tests/test_runtime_risk_versioning.py`
- Test: `tests/test_strategy_version_switch.py`

- [ ] Add failing tests for lower-risk immediate application to new orders.
- [ ] Add failing tests that require a new hash and approval for any risk increase.
- [ ] Add failing tests for pause-new-entry, close-only, rollback, and immutable running positions.
- [ ] Implement hashable runtime risk overlays and append-only history.
- [ ] Implement versioned strategy switch and rollback audits.
- [ ] Expose only concise controls; keep immutable floors non-disableable.
- [ ] Commit V56 policy versioning.

## Task 7: Start the bounded one-click Strategy Factory

**Files:**
- Create: `alphapilot_control_console/strategy_factory_orchestrator.py`
- Modify: `alphapilot_control_console/top200_minimal_ui_projection.py`
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `web/top200-minimal-ui.js`
- Test: `tests/test_strategy_factory_orchestrator.py`

- [ ] Add failing tests for program/campaign identity, budget, checkpoint, pause, resume, and truthful progress.
- [ ] Add failing tests that prevent automatic promotion, forced passes, and OOS leakage.
- [ ] Implement a background orchestration boundary that invokes the Quant factory through explicit artifacts and IDs.
- [ ] Project real status and five result classes into the Strategy page.
- [ ] Commit V56 factory controls.

## Task 8: Establish the isolated Live core

**Files:**
- Create: `alphapilot_control_console/live_environment_contract.py`
- Modify: `alphapilot_control_console/exchange_connectors/okx_live_client.py`
- Modify: `alphapilot_control_console/live_execution_store.py`
- Modify: `alphapilot_control_console/live_release_service.py`
- Modify: `alphapilot_control_console/live_approval_store.py`
- Modify: `alphapilot_control_console/http_app.py`
- Test: `tests/test_live_environment_contract.py`
- Test: `tests/test_live_release_service.py`
- Test: `tests/test_live_approval_store.py`

- [ ] Add failing tests for Demo/Live credential, release, approval, ledger, and runtime isolation.
- [ ] Add failing tests proving Withdraw/transfer methods are absent.
- [ ] Implement an explicit Live environment contract and private read-only audit path.
- [ ] Add a minimal Live status projection with no ARM or order action before exact approval.
- [ ] Generate `live_environment_contract.json` and `live_private_read_audit.json` with truthful `not_run` states where credentials are absent.
- [ ] Commit V57 Live core.

## Task 9: Build Live engineering smoke without executing it prematurely

**Files:**
- Create: `alphapilot_control_console/live_engineering_smoke_contract.py`
- Create: `alphapilot_control_console/live_engineering_smoke_service.py`
- Modify: `alphapilot_control_console/http_app.py`
- Test: `tests/test_live_engineering_smoke_contract.py`
- Test: `tests/test_live_engineering_smoke_service.py`

- [ ] Add failing tests for exact smoke approval and single minimum-notional order scope.
- [ ] Add failing tests for cancellation/reconciliation and evidence isolation.
- [ ] Implement contract generation and a blocked-by-default execution service.
- [ ] Generate the smoke approval request and stop unless its new exact hash is explicitly approved.
- [ ] Commit V58 Live engineering smoke readiness.

## Task 10: Generate the 1000 USDT experimental Live canary identity

**Files:**
- Create: `alphapilot_control_console/experimental_live_canary_release.py`
- Modify: `alphapilot_control_console/live_canary_service.py`
- Modify: `alphapilot_control_console/live_auto_execution_service.py`
- Modify: `alphapilot_control_console/live_safety_plane.py`
- Test: `tests/test_experimental_live_canary_release.py`
- Test: `tests/test_live_canary_service.py`
- Test: `tests/test_live_safety_plane.py`

- [ ] Add failing tests for versioned, configurable account budget and risk limits.
- [ ] Add failing tests for daily loss, cumulative loss, position, leverage, stale signal, and kill-switch floors.
- [ ] Add failing tests that Live remains unarmed without exact Release/Risk approval.
- [ ] Generate immutable Live Release, Risk Overlay, and approval request identities.
- [ ] Mark all unexecuted order/fill/position outputs `status=not_run`.
- [ ] Stop at `blocked_waiting_exact_live_release_approval`.
- [ ] Commit V59/V60 canary readiness. Do not ARM Live.

## Task 11: Minimal UI and mobile verification

**Files:**
- Modify: `web/index.html`
- Modify: `web/styles.css`
- Modify: `web/top200-minimal-ui.js`
- Modify: `alphapilot_control_console/top200_minimal_ui_projection.py`
- Test: `tests/test_top200_minimal_ui_projection.py`
- Test: `tests/test_top200_minimal_ui_http.py`
- Test: `tests/test_top200_minimal_ui_readonly_server.py`

- [ ] Keep the primary navigation small and preserve the approved Strategy/Demo layout.
- [ ] Add only status, concise controls, positions/orders, latency, and actionable issues required by V54-V60.
- [ ] Hide hashes, gates, and lineage in collapsed audit details.
- [ ] Verify desktop and 390px mobile rendering with browser screenshots and zero console errors.
- [ ] Commit UI changes.

## Task 12: Closeout, evidence, and publication

**Files:**
- Create: `alphapilot_control_console/v54_v60_evidence.py`
- Create: `scripts/build_v54_v60_evidence.py`
- Create: `docs/V13.27.1.54-V13.27.1.60-closeout.md`
- Modify: `README.md`
- Test: `tests/test_v54_v60_evidence.py`

- [ ] Run targeted tests, full Console tests, full Quant tests, compile checks, safety scans, and `git diff --check`.
- [ ] Build every required artifact; use `status=not_run` instead of fake empty execution results.
- [ ] Create one evidence ZIP under `D:/Codex-Workspace/deliveries/` and verify its SHA-256, CRC, manifest count, and sensitive-data scan.
- [ ] Commit Console, Quant, and Docs independently.
- [ ] Tag each repository with the corresponding V54-V60 tag and push branches/tags without force.
- [ ] Report the exact Demo approval/ARM state and the exact blocked Live approval state.

