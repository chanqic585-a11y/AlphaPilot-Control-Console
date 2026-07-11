# AlphaPilot V13.27.2 - Unified Auto Execution for Demo and Live

## 中文执行摘要

- Demo 与实盘采用同一套自动运行体验：启动一次后持续扫描、仲裁、下单、止盈止损、对账和复盘，不逐笔确认。
- 两个环境底层强隔离：分别使用凭据、请求 adapter、Release、RiskProfile、状态库、证据账本和紧急停止开关。
- 实盘每次启动只做一次进程级 ARM；通过后自动下单，手机和网页只负责同步状态与异常提醒。
- 策略只在对应周期的新 K 线闭合后重新判断，持仓和订单使用更快的独立心跳，避免重复信号。
- 每笔订单必须经过不可变版本、数据新鲜度、组合仲裁和风险检查，并附带满足 `>= 2R` 的交易所止盈止损。
- 实盘默认关闭；只有 Live 凭据、不可变候选、版本化风险配置、只读对账和一次 ARM 全部通过后才可启动。
- 永不保存 raw API Key，永不接 Withdraw；浏览器关闭不停止后台运行，进程重启后先对账再恢复。

## 1. Decision

AlphaPilot will provide the same automatic execution experience in OKX Demo and
OKX Live:

```text
start once -> scan -> arbitrate -> risk check -> place protected order ->
reconcile -> close -> review -> continue
```

There is no per-order confirmation after the user starts and arms an eligible
runtime. Web and mobile notifications report state and exceptions; they are not
order approval tickets.

The user experience is shared, but Demo and Live remain hard-separated below the
controller. They use different credentials, request semantics, adapters,
release contracts, risk profiles, state stores, ledgers, and kill switches.

## 2. Goals

1. Replace the manual `run_demo_cycle` workflow with a persistent automatic
   controller.
2. Let an immutable eligible strategy place an OKX Demo order automatically
   when a valid signal survives arbitration and risk checks.
3. Reuse the same controller for OKX Live after one explicit process-level ARM.
4. Keep every order protected by exchange-hosted take-profit and stop-loss
   instructions satisfying the active RiskProfile and `rewardRiskRatio >= 2`.
5. Reconcile orders, fills, positions, fees, slippage, realized PnL, and closed
   outcomes without relying on the browser remaining open.
6. Present identical operational concepts on web and mobile while making the
   active environment unmistakable.

## 3. Non-Goals

- No guarantee of profitability or strategy validity.
- No automatic promotion of an unapproved strategy into Live.
- No mutation of a running immutable strategy release.
- No raw API key storage in browser, files, SQLite, logs, or notifications.
- No Withdraw API, transfer API, deposit API, or sub-account key management.
- No bypass of portfolio risk, reconciliation, data freshness, or account
  checks.
- No real order submission from automated tests.

## 4. Product Semantics

### 4.1 Shared experience

Both pages use one operational model:

- `启动自动运行`
- `自动运行中`
- `暂停新开仓`
- `停止自动运行`
- `紧急停止`

Once started, the controller does not ask for per-signal or per-order approval.

### 4.2 Hard environment separation

The shared controller must receive an explicit environment:

```text
okx_demo
okx_live
```

It then resolves exactly one environment adapter. The adapter cannot be changed
while the controller is armed.

Demo requirements:

- OKX Demo Read + Trade credentials;
- `x-simulated-trading: 1` on every private request;
- an immutable Demo Release;
- an active OKX Demo RiskProfile;
- the Demo execution store and outcome evidence class.

Live requirements:

- a separate OKX Live Read + Trade key;
- no simulated-trading header;
- an immutable Live Canary Release with matching checksum;
- an active Live RiskProfile;
- the Live execution store and outcome evidence class;
- one explicit process-level ARM before automatic execution begins.

Demo credentials can never authorize Live, and Live credentials can never be
used by the Demo adapter.

## 5. Architecture

### 5.1 Shared AutoExecutionController

Add a controller responsible only for orchestration:

```text
AutoExecutionController
  -> StrategySchedule
  -> MarketScanner
  -> SignalEvaluator
  -> PortfolioArbiter
  -> RiskProfile evaluator
  -> EnvironmentExecutionAdapter
  -> ReconciliationLoop
  -> OutcomeLedger
  -> NotificationPublisher
```

It must not construct OKX signatures or issue HTTP requests directly.

### 5.2 Existing adapters remain authoritative

Demo execution continues through the existing Demo client and
`DemoExecutionEngine`.

Live execution continues through the existing Live client and
`LiveExecutionEngine`.

The controller calls a narrow shared adapter contract:

```python
class ExecutionAdapter(Protocol):
    def preflight(self) -> PreflightResult: ...
    def scan_private_state(self) -> PortfolioState: ...
    def submit_protected_order(self, intent: ExecutionIntent) -> OrderResult: ...
    def reconcile(self) -> ReconciliationResult: ...
    def pause_new_entries(self, reason: str) -> None: ...
    def emergency_stop(self, reason: str) -> EmergencyStopResult: ...
```

### 5.3 Persistent runner

The automatic controller is a backend runner, not a browser timer. Closing the
page must not stop it. State is persisted so a process restart can recover:

- enabled or disabled;
- armed environment;
- active release set and RiskProfile hashes;
- last heartbeat;
- last completed candle per strategy and instrument;
- next evaluation time;
- active signal and idempotency keys;
- pause or kill-switch reason;
- reconciliation checkpoint.

Raw credentials remain process-only and are never persisted. After a restart,
the runner remains paused until credentials are supplied and preflight passes.

## 6. Scheduling

### 6.1 Two clocks

Use two independent loops:

1. Position and order heartbeat: every 15 to 30 seconds while the runtime is
   active.
2. Signal evaluation: only when a new closed candle exists for a strategy's
   timeframe.

Examples:

- `5m`: evaluate once per newly closed 5-minute candle;
- `15m`: evaluate once per newly closed 15-minute candle;
- `1h`: evaluate once per newly closed hourly candle;
- `1d`: evaluate once per newly closed daily candle.

A five-minute heartbeat must not generate duplicate hourly or daily signals.

### 6.2 Catch-up and restart

After restart, the controller compares persisted checkpoints with exchange
candle close times. It may evaluate missed closed candles in order, but it must
never submit an order for an expired signal. The signal freshness limit is part
of the immutable strategy definition.

## 7. Market Scan and Signal Arbitration

Each eligible strategy scans the configured OKX USDT linear perpetual universe,
not a fixed coin.

The sequence is:

1. Read live instruments and exclude suspended or incompatible contracts.
2. Apply liquidity, spread, history, and data freshness gates.
3. Evaluate the immutable strategy definition on the remaining universe.
4. Rank matching signals.
5. Pass matches through portfolio arbitration.

The arbiter enforces:

- maximum active strategies;
- maximum total positions;
- maximum positions per strategy and symbol;
- strategy, symbol, direction, family, and correlated-risk budgets;
- conflicting long and short signals on the same instrument;
- duplicate candle and duplicate intent suppression;
- cooldown and loss-stop rules.

Candidate rank is not risk capacity. Suppressed signals are persisted with a
reason code and never counted as executed evidence.

## 8. Exactly-Once Order Intent

Every intent receives an idempotency key derived from:

```text
environment + release hash + risk profile hash + strategy id + instrument +
direction + closed candle time
```

The same key is used to derive a deterministic OKX client order ID. A retry can
reconcile an existing order but cannot create a second order for the same
signal.

## 9. Protected Order Lifecycle

Before submission, every signal must include:

- instrument and direction;
- entry reference and order type;
- quantity and notional;
- isolated margin and leverage;
- take-profit and stop-loss prices;
- risk amount and risk percent;
- target reward-to-risk ratio;
- source candle time and expiry time;
- immutable release and RiskProfile hashes.

The adapter submits exchange-hosted protection together with, or immediately
after, the entry according to the supported OKX contract API.

If the entry is accepted but protection cannot be confirmed:

1. block all new entries;
2. retry protection within a bounded recovery window;
3. cancel an unfilled entry when possible;
4. reduce or close filled unprotected exposure when recovery fails;
5. activate the environment pause and notify web and mobile.

No position may be represented as safely running until account, order,
position, and protection reconciliation agree.

## 10. Live ARM and Safety

Live does not require per-order confirmation. It requires one explicit ARM for
the current process and configuration.

ARM is allowed only when:

1. Live Read + Trade credentials are present in the process;
2. the key has an IP whitelist and no Withdraw permission;
3. account mode, available equity, open orders, and positions reconcile;
4. at least one checksum-valid Live Canary Release is approved;
5. the active Live RiskProfile hash matches every enabled release;
6. all required TP/SL and order endpoints pass preflight;
7. the persistent kill switch is off and new entries are allowed;
8. web/mobile alert delivery health is visible, though alert failure alone does
   not authorize or duplicate an order.

Changing credentials, environment, active RiskProfile, release set, leverage,
capital limit, or SafetyEnvelope disarms the runtime and requires a new ARM.

## 11. Failure Handling

- Authentication failure: pause new entries and require credentials plus
  preflight again.
- Stale or incomplete market data: skip the signal and record the reason.
- Network timeout with unknown order state: do not retry placement blindly;
  reconcile by client order ID first.
- Private-state mismatch: pause new entries and reconcile.
- Risk limit breach: reject the intent without an exchange request.
- Daily loss, drawdown, or Canary loss stop: block new entries and activate the
  configured stop state.
- Repeated exchange errors: exponential backoff, then pause.
- Process restart: recover open records before evaluating new signals.
- Emergency stop: stop new entries, call the allowlisted cancel-after path, and
  preserve full audit evidence.

## 12. UI and Notifications

Demo and Live use the same reusable control panel structure:

1. Environment banner and account connection state.
2. Automatic runner status, last heartbeat, and next evaluation.
3. Enabled immutable strategies and current release hashes in advanced detail.
4. Market scan progress, matches, suppressed signals, and reason summaries.
5. Orders and positions with entry, mark, TP, SL, size, leverage, fees, and PnL.
6. Closed trades and strategy-level Demo or Live performance.
7. Pause, stop, and emergency-stop actions.

The routine view hides internal IDs, hashes, raw JSON, and low-level payloads.
They remain available in collapsed audit detail.

Web and mobile receive the same event stream:

- runtime started, paused, stopped, or disarmed;
- signal matched or suppressed;
- order accepted, rejected, canceled, or unknown;
- position opened, protected, updated, or closed;
- risk stop, reconciliation mismatch, or credential failure;
- realized PnL and closed-outcome summary.

Notifications are informational and do not require order approval.

## 13. Data and Audit

Use append-only events and keep evidence classes separate:

```text
okx_demo
live
```

Every terminal outcome records environment, release, profile, signal, order,
instrument, timestamps, fees, slippage, PnL, exit reason, and data lineage.

Demo evidence can support research and promotion review but cannot be relabeled
as Live evidence. Live evidence can create offline improvement triggers but
cannot mutate a running release.

## 14. Compatibility

- Existing Demo Release contracts remain readable.
- Existing Live Canary releases remain disabled unless explicitly enabled and
  armed under this controller.
- Existing Demo and Live stores are retained; no historical rows are deleted.
- Existing manual cycle endpoints may remain as administrative diagnostics but
  are no longer the primary user workflow.
- Existing process-only credential launchers remain supported.

## 15. Test Strategy

Implementation follows test-first development.

Required tests include:

- candle-aware scheduling and duplicate suppression;
- restart recovery and expired-signal rejection;
- cross-strategy and cross-symbol arbitration;
- Demo and Live adapter selection cannot cross environments;
- no live adapter call without a valid ARM;
- risk, loss-stop, drawdown, and kill-switch behavior;
- idempotent retry after timeout or unknown order state;
- TP/SL acknowledgement and protection recovery;
- reconciliation before and after every order lifecycle transition;
- append-only Demo and Live outcome separation;
- web/mobile status projection;
- no raw key persistence and no Withdraw endpoint reference;
- all integration tests use fake clients and never place a real order.

## 16. Acceptance Criteria

1. Demo and Live display the same automatic workflow and controls.
2. Demo and Live remain separate adapters, credentials, stores, profiles,
   releases, and evidence classes.
3. Starting an eligible Demo runtime removes per-order confirmation.
4. Starting and arming an eligible Live runtime removes per-order confirmation.
5. Signals are evaluated only on newly closed strategy candles.
6. A matching signal can create at most one exchange order.
7. Every order passes immutable release, data, arbitration, and risk gates.
8. Every opened position has confirmed exchange-hosted TP/SL protection or
   triggers fail-closed recovery.
9. Closing the browser does not stop the backend runner.
10. Restart recovery reconciles existing orders and positions before new
    entries.
11. Mobile and web show the same runtime, signal, order, position, PnL, and
    exception state.
12. Withdraw remains absent.
13. Raw API credentials are never persisted.
14. Live remains disabled by default until valid credentials, release, profile,
    preflight, and one process-level ARM are present.
15. Automated tests cannot submit real OKX orders.

## 17. Rollout Boundary

The implementation can share code immediately, but activation remains staged:

1. prove the shared controller against OKX Demo automatic execution;
2. run the same controller through the Live fake adapter and read-only
   reconciliation;
3. enable one explicitly approved Live Canary release under the configured
   Live RiskProfile;
4. expand strategy or position limits only by activating a new versioned
   RiskProfile.

This rollout does not add per-order approval. It limits the blast radius while
the same automatic lifecycle is validated.
