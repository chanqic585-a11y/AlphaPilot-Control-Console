# AlphaPilot Demo Universe and Engineering Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove that the OKX Demo account can discover, submit, inspect, close or cancel, and reconcile a minimum-size USDT perpetual order using only contracts that are simultaneously in the point-in-time public Top100 and the authenticated Demo account instrument list.

**Architecture:** Add one authoritative Demo-universe service and one isolated engineering-smoke service. The universe service intersects public point-in-time contracts with authenticated Demo instruments by exact canonical identity and fails closed on stale or invalid private data. The smoke service reuses the hardened Demo client and execution engine but writes to its own SQLite ledger and immutable engineering-only contract, so its orders can never qualify a research strategy.

**Tech Stack:** Python 3.12, SQLite, OKX Demo REST API, existing `OkxDemoClient`, `DemoExecutionEngine`, unittest, vanilla JavaScript.

## Global Constraints

- Use only OKX Demo credentials injected into the current process; never persist or return them.
- Every private request must retain `x-simulated-trading: 1` through `OkxDemoClient`.
- Never fall back from an invalid authenticated instrument response to public-only contracts.
- Match exact USDT SWAP identity only; no fuzzy base-symbol, spot, margin, option, USDC, or coin-margined substitution.
- Engineering smoke is limited to one minimum-size position, bounded retries, no adding, no martingale, and no concurrent entry.
- Engineering-smoke records cannot update strategy PF, win rate, PnL summaries, promotion gates, release qualification, or Live state.
- No Live API, Withdraw API, Live account reads, or Live order behavior is added.

---

### Task 1: Lock the Demo instrument identity contract

**Files:**
- Create: `alphapilot_control_console/demo_instrument_identity.py`
- Test: `tests/test_demo_instrument_identity.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class CanonicalDemoInstrument:
    instId: str
    baseCurrency: str
    quoteCurrency: str
    settleCurrency: str
    instrumentType: str

def canonicalize_demo_instrument(value: str | dict[str, Any]) -> CanonicalDemoInstrument
def to_okx_inst_id(value: str | CanonicalDemoInstrument) -> str
def same_demo_contract(left: str | dict[str, Any], right: str | dict[str, Any]) -> bool
```

- [ ] Write failing tests for `BTC-USDT-SWAP`, `btc/usdt:usdt`, case normalization, and separators.
- [ ] Write rejection tests for `BTC-USDT`, `BTC-USDC-SWAP`, `BTC-USD-SWAP`, options, malformed IDs, and missing settlement fields.
- [ ] Implement a single canonical parser; do not duplicate mapping logic in scanners or services.
- [ ] Run `python -m unittest tests.test_demo_instrument_identity -v`; expect all tests to pass.
- [ ] Commit: `git commit -m "Add exact OKX Demo instrument identity mapping"`.

### Task 2: Build the authenticated Demo universe service

**Files:**
- Create: `alphapilot_control_console/demo_instrument_universe.py`
- Create: `alphapilot_control_console/demo_instrument_universe_store.py`
- Modify: `alphapilot_control_console/okx_market_universe.py`
- Modify: `alphapilot_control_console/evolution_demo_service.py`
- Test: `tests/test_demo_instrument_universe.py`
- Test: `tests/test_evolution_demo_service.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class DemoUniversePolicy:
    environment: Literal["demo"]
    cacheTtlSeconds: int = 300
    staleAfterSeconds: int = 900
    maximumIncludedSample: int = 10
    maximumExcludedSample: int = 10

def build_demo_instrument_universe(
    *,
    publicUniverse: dict[str, Any],
    accountInstrumentsResponse: dict[str, Any],
    policy: DemoUniversePolicy,
    now: datetime | None = None,
) -> dict[str, Any]

def load_or_refresh_demo_instrument_universe(
    client: OkxDemoClient,
    *,
    fresh: bool = False,
) -> dict[str, Any]
```

**Required response fields:**

```text
status
environment
publicUniverseCount
demoAccountInstrumentCount
intersectionCount
liquidityEligibleCount
excludedNotInDemoAccount
excludedUnavailableState
excludedDataMissing
excludedLiquidity
generatedAt
cacheAgeSeconds
stale
includedSample
excludedSample
```

- [ ] Write failing tests for exact intersection, unavailable-state exclusion, duplicate private rows, liquidity exclusion, and stable ordering.
- [ ] Write fail-closed tests for private code not equal to `0`, empty data, malformed rows, wrong environment key, expired cache, and unavailable credentials.
- [ ] Store only normalized IDs, counts, exclusion reasons, timestamps, and hashes in `data/demo_instrument_universe.sqlite`; never store the raw private response.
- [ ] Key cache rows by `environment='demo'`, public manifest hash, and authenticated-instrument hash.
- [ ] Replace `_demo_account_instrument_ids` in `evolution_demo_service.py` with the shared service; preserve existing error semantics where compatible.
- [ ] Ensure `scan_demo_strategy_public_universe` receives the eligible intersection, not a public-only set.
- [ ] Run `python -m unittest tests.test_demo_instrument_universe tests.test_evolution_demo_service -v`; expect all tests to pass.
- [ ] Commit: `git commit -m "Build authenticated OKX Demo tradeable universe"`.

### Task 3: Expose a compact read-only universe API

**Files:**
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `web/app.js`
- Test: `tests/test_demo_instrument_universe_http.py`

**Endpoint:**

```http
GET /api/demo-instrument-universe?fresh=1
```

- [ ] Write a failing loopback HTTP test for the documented schema and a non-loopback rejection test if the existing server guard applies.
- [ ] Add the GET route using the shared service; do not add credential input or private raw payload fields.
- [ ] Return `503` with `status='blocked'` and an exact blocker for invalid/empty/stale authenticated data; return `200` only for a usable or explicitly cached-fresh result.
- [ ] Add a compact Demo engineering status row showing public, authenticated, intersection, eligible, cache age, and blocker counts.
- [ ] Run `python -m unittest tests.test_demo_instrument_universe_http -v`; expect all tests to pass.

### Task 4: Define an immutable engineering-smoke contract

**Files:**
- Create: `alphapilot_control_console/demo_engineering_smoke_contract.py`
- Create: `data/demo_engineering_smoke_contracts/.gitkeep`
- Test: `tests/test_demo_engineering_smoke_contract.py`

**Contract fields:**

```text
releaseId
releaseHash
createdAt
demoPurpose=engineering_smoke
evidenceClass=demo_engineering_smoke
strategyQualification=false
promotionEligible=false
forwardPerformanceEligible=false
environment=demo
maximumConcurrentPositions=1
maximumAttempts=3
minimumOrderOnly=true
```

- [ ] Write failing tests that reject any contract enabling qualification, promotion, forward evidence, Live, multiple positions, or unbounded retry.
- [ ] Generate the deterministic contract from canonical JSON and SHA-256; never mutate an existing hash-addressed file.
- [ ] Keep its release directory separate from `data/demo_release_contracts` used by strategies.
- [ ] Run `python -m unittest tests.test_demo_engineering_smoke_contract -v`; expect all tests to pass.
- [ ] Commit: `git commit -m "Add isolated Demo engineering smoke contract"`.

### Task 5: Add the isolated smoke ledger and lifecycle service

**Files:**
- Create: `alphapilot_control_console/demo_engineering_smoke_store.py`
- Create: `alphapilot_control_console/demo_engineering_smoke_service.py`
- Modify: `alphapilot_control_console/demo_execution_engine.py`
- Test: `tests/test_demo_engineering_smoke_store.py`
- Test: `tests/test_demo_engineering_smoke_service.py`

**Storage:** `data/demo_engineering_smoke.sqlite`

**Interfaces:**

```python
def run_demo_engineering_smoke(
    *,
    client: OkxDemoClient,
    contract: dict[str, Any],
    universe: dict[str, Any],
    deterministicTrigger: bool,
) -> dict[str, Any]

def reconcile_demo_engineering_smoke(*, client: OkxDemoClient) -> dict[str, Any]
def build_demo_engineering_smoke_status() -> dict[str, Any]
```

- [ ] Write store migration tests for idempotent initialization, unique idempotency key, event append, and restart recovery.
- [ ] Write service tests for one selected eligible contract, minimum exchange size, one order attempt, open/fill lookup, position lookup, close-or-cancel, and final reconciliation.
- [ ] Write failure tests for empty universe, unavailable instrument, order rejection, status timeout, retry exhaustion, duplicate attempt, orphan position, and reconciliation mismatch.
- [ ] Reuse `DemoExecutionEngine` only through dependency injection; do not share the strategy ledger path or strategy evidence callbacks.
- [ ] Persist sanitized exchange code/message, IDs, timestamps, quantities, and reconciliation state; reject sensitive fields recursively.
- [ ] Treat a real OKX failure as a failed smoke. Never synthesize a fill or position.
- [ ] Run `python -m unittest tests.test_demo_engineering_smoke_store tests.test_demo_engineering_smoke_service -v`; expect all tests to pass.

### Task 6: Add explicit engineering-smoke controls and status

**Files:**
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Test: `tests/test_demo_engineering_smoke_http.py`

**Endpoints:**

```http
GET  /api/demo-engineering-smoke
POST /api/demo-engineering-smoke/run
POST /api/demo-engineering-smoke/reconcile
```

- [ ] Write failing HTTP tests for status, explicit run, concurrent-run conflict, reconcile, blocked universe, and missing credentials.
- [ ] Require loopback, process-only Demo credentials, the immutable engineering contract, and a usable universe for POST actions.
- [ ] Do not auto-run engineering smoke during Console startup or normal strategy scans.
- [ ] Render it under `Demo 工程状态`, visually separate from `策略验证 Demo`.
- [ ] Display order attempt, order status, position status, close/cancel status, duplicate count, orphan count, reconciliation, and next action.
- [ ] Keep the UI compact; move event detail behind one collapsible diagnostics section.
- [ ] Run `python -m unittest tests.test_demo_engineering_smoke_http -v`; expect all tests to pass.

### Task 7: Prove evidence isolation

**Files:**
- Modify: `tests/test_demo_evidence.py`
- Create: `tests/test_demo_engineering_smoke_isolation.py`

- [ ] Snapshot strategy record counts and promotion inputs before a smoke run.
- [ ] Run a mocked successful engineering lifecycle.
- [ ] Assert strategy ledger counts, closed strategy trades, PF, win rate, promotion evidence, release count, and Live candidates are unchanged.
- [ ] Assert only `demo_engineering_smoke.sqlite` and the engineering status projection change.
- [ ] Run `python -m unittest tests.test_demo_evidence tests.test_demo_engineering_smoke_isolation -v`; expect all tests to pass.

### Task 8: Phase 1 regression and credentialed proof

**Files:**
- Modify: `README.md`
- Create: `docs/demo-engineering-smoke-operator-guide.md`

- [ ] Document the difference between public universe, Demo-account universe, intersection, engineering smoke, and strategy validation.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `python -m compileall alphapilot_control_console`.
- [ ] Run `git diff --check`.
- [ ] Scan source and generated status payloads for API keys, secret, passphrase, private headers, Withdraw, and Live enablement.
- [ ] With user-supplied process-only Demo credentials, call `GET /api/demo-instrument-universe?fresh=1` and require a non-empty intersection.
- [ ] Explicitly run one smoke and require `orderAttemptCount > 0`, readable order state, readable position state, completed exit/cancel where supported, duplicates `0`, and orphans `0`.
- [ ] Back up the smoke SQLite before any corrective migration.
- [ ] Commit and push: `git commit -m "Complete isolated OKX Demo engineering proof"`.

## Phase Exit Gate

Phase 1 passes only when the authenticated/public intersection is non-empty, every selected smoke instrument belongs to that intersection, one real Demo lifecycle has a recorded attempt and reconciliation result, duplicates and orphans are zero, no sensitive value is persisted, and every strategy-performance projection remains unchanged. Missing process-only credentials may defer the credentialed proof, but Phase 2 must not begin until that proof is complete.
