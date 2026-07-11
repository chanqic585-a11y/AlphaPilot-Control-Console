# V13.27.1.5 One-Time Guidance and OKX Demo Launcher Design

## Status

Approved product direction, pending written-spec review before implementation.

## Purpose

V13.27.1.5 removes two sources of ambiguity in the workflow console:

1. Blocking states must explain themselves once, with a concrete next action, without repeatedly interrupting the user.
2. Starting the OKX Demo runtime must be a guided local action instead of requiring the user to copy a PowerShell command manually.

This patch does not weaken Demo or Live release gates. It does not store raw credentials and does not add withdrawal capability.

## Confirmed Product Decisions

### Credential ownership

- An API credential belongs to an exchange account runtime, not to an individual strategy.
- One OKX Demo credential set is entered once per console runtime and is shared by all immutable strategies that are eligible for Demo execution.
- Demo orders, positions, fills, fees, slippage, and PnL remain attributed separately by strategy ID, release ID, and symbol.
- A future Live runtime also accepts credentials once per account or subaccount. Live strategies are then approved and enabled one by one.
- If stronger Live isolation is required, the supported model is one API credential per dedicated OKX subaccount, not several duplicate keys for strategies sharing the same account.

### Credential persistence

- API Key, Secret Key, and Passphrase are entered in a visible local PowerShell launcher.
- Raw credentials never pass through browser form fields.
- Raw credentials are never written to SQLite, JSON, logs, browser storage, source files, or command-line arguments.
- Credentials exist only in the launched console process environment and are cleared when that process exits.
- A computer restart or console process restart requires credentials to be entered again.

### Demo versus Live

- The new one-click action starts OKX Demo only.
- Demo may enable the existing order and automation gates, but only immutable eligible Demo Releases can submit Demo orders.
- The button cannot enable Live trading.
- Live strategy activation remains a separate, explicit, per-strategy approval flow with a versioned RiskProfile.
- Withdrawal remains unsupported.

## Approaches Considered

### A. Local-only browser handoff to a secure launcher

The browser calls a loopback-only endpoint. The endpoint opens a visible PowerShell launcher with a fixed script and fixed arguments. The launcher securely asks for the three credentials, replaces only the verified AlphaPilot listener, and starts the Demo runtime.

Advantages:

- One click from the place where the blocker is shown.
- Credentials remain outside the webpage and outside persistent storage.
- Existing process-only credential design is preserved.
- The page can automatically detect when the replacement runtime becomes ready.

Cost and risk:

- Requires a narrowly scoped local endpoint and careful process handoff.
- Must reject phone, LAN, and non-loopback requests.

Decision: selected.

### B. Desktop shortcut only

Keep the secure PowerShell launcher and add a desktop shortcut, but do not let the page open it.

Advantages: simpler and has less backend surface area.

Disadvantages: the user must leave the workflow page and correlate two interfaces. It does not solve the current unclear `人工操作` state as directly.

Decision: retain as a fallback entry, not the primary flow.

### C. Persist credentials for zero-input restart

Store credentials in an encrypted operating-system vault and restore them automatically.

Advantages: fastest restart.

Disadvantages: materially changes the credential threat model, recovery model, and audit surface. It is unnecessary for the current Demo milestone.

Decision: deferred and out of scope.

## User Experience

### One-time issue guidance

When the active page detects a blocking or failed workflow condition, it opens one guidance dialog containing:

- current stage;
- what is blocked;
- what the system has already completed;
- the exact next action;
- the safety boundary for that action.

The dialog opens automatically only once for the same issue fingerprint. The user can always reopen it using `查看处理办法`.

An issue fingerprint contains only non-secret identifiers:

- page or workflow stage;
- strategy or release ID when applicable;
- normalized blocker codes;
- blocker-state version.

The browser stores acknowledged fingerprints locally. Polling, refreshes, and unchanged evidence do not reopen the dialog. A materially changed blocker set produces a new fingerprint and may open one new dialog.

If several strategies share the same blocker, the page shows one aggregate dialog rather than a sequence of dialogs.

### Evidence checklist

Evidence is displayed in a collapsed disclosure by default:

```text
证据清单  6/8 已满足 · 1 项阻塞
```

Expanding it shows every evidence row, current value, target value, source, blocker reason, and next action. Collapsing evidence never hides the primary status, progress bar, or the `查看处理办法` action.

### OKX Demo Runtime blocker

The old instruction-only state is replaced with:

```text
OKX Demo Runtime 未就绪
需要在本机启动 Demo 运行时。凭据只用于本次进程，不会保存。
[启动 OKX Demo]
```

Selecting `启动 OKX Demo`:

1. asks the local backend to open the fixed launcher;
2. shows `启动器已打开，请在 PowerShell 窗口输入三项 Demo 凭据`;
3. polls runtime health without exposing credentials;
4. changes to `OKX Demo Runtime 已就绪` only after credentials, read access, order gate, automation gate, and risk gate are verified;
5. shows a concrete failure reason and retry action if startup fails.

On a phone or non-loopback browser, the button is disabled and the page says to perform this action on the computer hosting the console.

## Components

### Frontend issue guidance controller

Responsibilities:

- normalize workflow blockers into user-facing issue models;
- select the highest-priority active-page issue;
- calculate non-secret fingerprints;
- open each issue automatically once;
- provide a manual reopen action;
- aggregate repeated strategy issues.

It does not execute workflow actions and does not inspect credential values.

### Evidence disclosure component

Responsibilities:

- show compact satisfied, pending, and blocked totals;
- render full evidence only when expanded;
- preserve mobile single-column layout;
- keep action labels readable at 375 px width.

### Local launcher endpoint

Proposed endpoint:

```text
POST /api/local-control/open-okx-demo-launcher
```

Requirements:

- accept requests only when the TCP client address is `127.0.0.1` or `::1`;
- accept no executable path, script path, credentials, or arbitrary arguments from the request;
- launch only the repository-owned fixed PowerShell script;
- use fixed Demo order and automation arguments;
- return an acknowledgement, not credential or process-environment data;
- prevent repeated clicks from opening several launchers concurrently;
- write only a credential-free audit event such as launcher requested, accepted, rejected, or already open.

### PowerShell runtime handoff

The existing `scripts/start_okx_demo_console.ps1` remains the credential entry point and gains an explicit replacement mode.

Replacement mode must:

1. prompt securely for API Key, Secret Key, and Passphrase before stopping the current console;
2. reject blank values;
3. show that the target is OKX Demo with Read + Trade and no withdrawal;
4. require a short explicit confirmation before enabling Demo automation;
5. inspect the listener on port 8766;
6. stop it only if its command line and repository path identify the AlphaPilot Control Console HTTP application;
7. refuse to stop unknown processes;
8. start the replacement runtime with process-only environment variables;
9. clear those variables in `finally` when the runtime exits.

If credential input or confirmation is cancelled, the existing console stays running.

## Demo Strategy Sharing and Isolation

After runtime readiness:

- all eligible Demo Releases use the same account-level adapter and credential set;
- the workflow orchestrator remains the only route from a strategy Release to execution;
- each order carries strategy ID, strategy version, release ID, symbol, and idempotency key;
- per-strategy maximum concurrent symbols remains configurable from 1 to 10;
- account-level open-risk, daily-loss, exposure, correlation, and kill-switch limits take precedence over strategy limits;
- conflicting or duplicate signals continue through the strategy arbitrator;
- one strategy cannot read another strategy's private configuration or rewrite its immutable Release;
- reports show strategy-level and account-level PnL separately.

Sharing credentials therefore does not mean sharing strategy state or bypassing risk controls.

## Live Boundary

This patch does not implement the Live launcher. It freezes the future contract:

- credentials are entered once per Live account or subaccount runtime;
- each strategy requires an explicit `批准实盘` action;
- approval references an immutable strategy Release and immutable RiskProfile hash;
- activation, pause, and revoke are recorded per strategy;
- account-level kill switch always overrides strategy state;
- no strategy approval can add withdrawal permission;
- a dedicated subaccount is the supported stronger-isolation option.

## Error Handling

- Non-loopback launcher request: reject with `local_host_required`.
- Launcher already open: return `launcher_already_open`; do not open another window.
- Unknown process owns port 8766: leave it untouched and show `端口被非 AlphaPilot 进程占用`.
- Empty or cancelled credential input: keep the existing console alive and show no readiness success.
- Demo authentication failure: show a credential or whitelist troubleshooting message without echoing secrets.
- Read succeeds but order or automation gate is off: report the exact missing gate.
- Runtime restarts but health polling times out: keep the retry button and show the local launcher window as the diagnostic source.
- Browser storage unavailable: suppress repeats for the current page session; do not fail the page.

## Testing

### Unit and integration tests

- identical issue fingerprints open automatically once;
- a changed blocker set may open once again;
- manual reopen always works;
- multiple identical strategy blockers aggregate into one issue;
- evidence disclosure is collapsed by default and has accurate counts;
- loopback launcher requests are accepted;
- non-loopback launcher requests are rejected;
- request payload cannot select commands, paths, or arguments;
- launcher concurrency guard prevents duplicate windows;
- unknown port owner is never terminated;
- cancelled credential entry does not stop the existing console;
- Demo runtime readiness requires credentials plus all required gates;
- strategy order attribution remains separate under one shared Demo adapter;
- Live routes and withdrawal capability remain unavailable.

### Manual verification

1. Open the Demo page on `127.0.0.1` with an ordinary credential-free runtime.
2. Confirm one guidance dialog appears and does not repeat during polling or refresh.
3. Expand and collapse the evidence checklist.
4. Select `启动 OKX Demo` and confirm exactly one visible launcher opens.
5. Enter one Demo credential set once.
6. Confirm the current console is replaced and the page reconnects.
7. Confirm all eligible Demo strategies see the same ready account runtime without further credential prompts.
8. Confirm orders and PnL remain grouped by strategy.
9. Verify the same action is disabled from a phone or LAN URL.
10. Verify no raw secret appears in logs, files, browser storage, process command lines, or API responses.

## Files Expected to Change During Implementation

The implementation plan will identify exact paths, but the expected scope is limited to:

- Control Console HTTP route and fixed launcher service;
- existing OKX Demo PowerShell launcher and a small handoff helper if needed;
- shared page JavaScript/CSS for issue guidance and evidence disclosure;
- Demo workflow rendering and local launcher action;
- focused tests;
- README and runtime safety documentation;
- version metadata.

Runtime data under `data/demo_release_contracts/` and `data/workflow_jobs/` must remain untouched and uncommitted.

## Acceptance Criteria

1. The same unresolved problem opens one automatic dialog only once.
2. Every blocker still has a persistent `查看处理办法` action.
3. Evidence lists are collapsed by default and expandable.
4. The Demo Runtime blocker provides a local `启动 OKX Demo` button.
5. The button never accepts or transports API credentials in the webpage.
6. One launcher collects one Demo credential set for the whole runtime.
7. All eligible Demo strategies share that account connection without repeat credential prompts.
8. Orders, positions, and PnL remain attributable per strategy and Release.
9. The launcher endpoint is loopback-only and cannot execute arbitrary commands.
10. Unknown processes are never stopped during port handoff.
11. Raw credentials are not persisted.
12. Live remains disabled by this patch.
13. Future Live credentials are account-level while strategy activation is approved one by one.
14. Withdrawal capability is not added.
15. Automated tests, syntax checks, safety scans, and desktop/mobile visual checks pass.
