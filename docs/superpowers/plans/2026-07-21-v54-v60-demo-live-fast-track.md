# V54-V60 Demo Activation and Live Fast-Track Implementation Plan

> **For Codex:** Execute this plan sequentially with TDD and commit checkpoints. Do not cross an exact approval gate without the required immutable identity and user authorization.

**Goal:** Continue from the authoritative V55.1 TOP200 Demo checkpoint, verify its exact approval overlay before any explicit ARM, harden its low-latency execution and versioned controls, then build an isolated Live canary path up to the exact Live approval gate.

**Architecture:** Add narrowly scoped services around the active V55.1 immutable Release, Risk Overlay, and Observer Sidecar. The superseded V53 hash remains historical-only and must never be approved, armed, or rebound as the active execution identity. Reuse the existing Demo execution, TOP200, engineering-smoke, risk-profile, Live isolation, and minimal projection modules. Keep every write append-only and environment-bound. Project one source of truth into the UI and evidence bundle. Qlib, model training, Factor Bench, drift, rollback, and Live inference remain truthful `not_run` blockers until the AdaptiveLearningLiveReadinessGate proves them complete.

**Tech Stack:** Python 3.12, stdlib HTTP/SQLite/JSON, pytest, vanilla HTML/CSS/JavaScript, PowerShell launchers, SHA-256 canonical JSON artifacts.

---

## Task 1: Freeze and verify the historical baseline and V55.1 authority

**Files:**
- Create: `alphapilot_control_console/v54_baseline_audit.py`
- Create: `scripts/build_v54_baseline_audit.py`
- Test: `tests/test_v54_baseline_audit.py`
- Read: `data/top200_minimal_ui/**`

- [x] Add failing tests for evidence ZIP hash/CRC/manifest verification.
- [x] Add failing tests for Release-to-final-HEAD execution-path diff classification.
- [x] Add failing tests for strategy-order count scope reconciliation.
- [x] Implement deterministic read-only auditors and redacted artifacts.
- [x] Generate `baseline_evidence_verification.json`, `release_to_final_head_execution_diff_audit.json`, and `strategy_order_scope_reconciliation.json`.
- [x] Run targeted tests and commit the baseline audit.

## Task 2: Build signal matchability readiness

**Files:**
- Create: `alphapilot_control_console/demo_matchability_readiness.py`
- Create: `scripts/build_demo_matchability_readiness.py`
- Test: `tests/test_demo_matchability_readiness.py`
- Modify: `alphapilot_control_console/top200_minimal_ui_projection.py`

- [x] Add failing tests for component universe compatibility and deterministic 30/90-day read-only rehearsal summaries.
- [x] Assert no order client or private endpoint is reachable from the rehearsal path.
- [x] Implement component-level candidate counts, blocker attribution, and pre-ARM funnel counts.
- [x] Generate `component_signal_matchability.csv`, `signal_matchability_30d.json`, `signal_matchability_90d.json`, and `pre_arm_scan_funnel.json`.
- [x] Project only four headline readiness values into the Demo page; keep details collapsed.
- [x] Run targeted tests and commit V54 readiness.

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

- [x] Add failing tests that reject any Release/Risk/Intersection/Request hash mismatch.
- [x] Add failing tests that prove approval and ARM are separate append-only events.
- [x] Add failing tests for missing credentials, stale snapshot, risk blocker, and unapproved Release.
- [x] Implement exact approval overlay storage with no artifact mutation.
- [x] Implement ARM service that delegates to the existing Demo runtime only after all gates pass.
- [x] Add minimal approval and ARM endpoints and UI actions.
- [x] Record the user-approved frozen TOP200 identity only after all exact checks pass.
- [x] Back up runtime SQLite stores before any operational write.
- [x] Run targeted tests, perform read-only checks, then commit V54 activation.

## Task 4: Run approved TOP200 Demo and expose the full funnel

**Files:**
- Modify: `alphapilot_control_console/unified_auto_execution_runner.py`
- Modify: `alphapilot_control_console/demo_market_scan_service.py`
- Modify: `alphapilot_control_console/demo_prewarmed_market_state.py`
- Modify: `alphapilot_control_console/demo_evaluation_audit.py`
- Modify: `alphapilot_control_console/top200_minimal_ui_projection.py`
- Test: `tests/test_demo_approved_run_all.py`
- Test: `tests/test_demo_evaluation_audit.py`

- [x] Add failing tests for approved-only run-all behavior and closed-candle scheduling.
- [x] Add failing tests for the complete funnel: universe, liquidity, depth, component signals, arbitration, risk, order, fill, and position.
- [x] Preserve zero-natural-signal truth; add only evidence-ineligible engineering fixtures.
- [x] Implement full funnel ledgers and a first-scan audit.
- [x] Verify strategy orders remain zero until a natural signal passes every gate.
- [x] Commit V55 normal Demo operation.

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

- [x] Add failing tests for versioned latency profiles and stale-signal fail-closed behavior.
- [x] Add failing tests for market-state reuse and no public-data download in the order hot path.
- [x] Instrument candle-close, signal, risk, submit, acknowledge, fill, and reconciliation timestamps.
- [x] Prefer a healthy private WebSocket order path with bounded REST fallback.
- [x] Reject critical latency and record every fallback/rejection reason.
- [x] Generate latency profile, benchmark, ledger, and stale-signal audit artifacts.
- [x] Commit V55 latency hardening.

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

- [x] Add failing tests for lower-risk immediate application to new orders.
- [x] Add failing tests that require a new hash and approval for any risk increase.
- [x] Add failing tests for pause-new-entry, close-only, rollback, and immutable running positions.
- [x] Implement hashable runtime risk overlays and append-only history.
- [x] Implement versioned strategy switch and rollback audits.
- [x] Expose only concise controls; keep immutable floors non-disableable.
- [x] Commit V56 policy versioning.

## Task 7: Start the bounded one-click Strategy Factory

**Files:**
- Create: `alphapilot_control_console/strategy_factory_orchestrator.py`
- Modify: `alphapilot_control_console/top200_minimal_ui_projection.py`
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `web/top200-minimal-ui.js`
- Test: `tests/test_strategy_factory_orchestrator.py`

- [x] Add failing tests for program/campaign identity, budget, checkpoint, pause, resume, and truthful progress.
- [x] Add failing tests that prevent automatic promotion, forced passes, and OOS leakage.
- [x] Implement a background orchestration boundary that invokes the Quant factory through explicit artifacts and IDs.
- [x] Project real status and five result classes into the Strategy page.
- [x] Commit V56 factory controls.

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
