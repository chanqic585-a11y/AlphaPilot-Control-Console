# V13.27.1.5 One-Time Guidance and OKX Demo Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one-time actionable blocker guidance, collapsed evidence lists, and a loopback-only one-click OKX Demo launcher that collects one account credential set for every eligible Demo strategy.

**Architecture:** A small Python launcher service owns loopback validation, fixed-command construction, and launcher concurrency. The existing HTTP server exposes one fixed local-control endpoint, while the existing PowerShell script securely collects credentials and replaces only the exact server PID that opened it. A focused browser module owns issue fingerprints and acknowledgement state; `app.js` maps Strategy, Local, Demo, and Live blockers into that module and keeps evidence compact.

**Tech Stack:** Python 3 standard library, `unittest`, PowerShell 5+, plain HTML/CSS/JavaScript, Windows process APIs, existing AlphaPilot HTTP server.

## Global Constraints

- Version is `V13.27.1.5` and tag is `v13.27.1.5`.
- Raw API Key, Secret Key, and Passphrase never enter browser fields, JSON payloads, logs, command-line arguments, SQLite, or files.
- The launcher endpoint accepts loopback clients only and accepts no user-selected command, path, or argument.
- Demo credentials are entered once per runtime and shared by all eligible Demo strategies; attribution remains per strategy and immutable Release.
- Live credentials are account-level, but Live strategy activation remains individually approved; this patch must not enable Live.
- Withdrawal capability remains absent.
- Unknown processes on port 8766 must never be terminated.
- Existing runtime directories `data/demo_release_contracts/` and `data/workflow_jobs/` remain untracked and untouched.
- Same issue fingerprint auto-opens once; manual `查看处理办法` always remains available.
- Evidence is collapsed by default on desktop and mobile.
- Completion-triggered shutdown is scheduled only after implementation, tests, safety scan, commit, merge, tag, push, and final runtime verification are complete. No fixed-time idle waiting is allowed.

---

### Task 1: Loopback-only local Demo launcher service and HTTP endpoint

**Files:**
- Create: `alphapilot_control_console/local_demo_launcher.py`
- Create: `tests/test_local_demo_launcher.py`
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `tests/test_workflow_ui_contract.py`

**Interfaces:**
- Produces: `LocalDemoLauncher.open(client_host: str, current_pid: int, port: int, mobile: bool = False) -> dict[str, object]`.
- Produces: module singleton `LOCAL_DEMO_LAUNCHER`.
- Produces: `POST /api/local-control/open-okx-demo-launcher` with `202`, `403`, `409`, or `500` JSON responses.
- Consumes: repository-owned `scripts/start_okx_demo_console.ps1` only.

- [ ] **Step 1: Write failing launcher unit tests**

Add tests that instantiate the service with a fake `popen_factory` and assert:

```python
def test_loopback_request_opens_fixed_visible_launcher(self):
    result = launcher.open("127.0.0.1", current_pid=4321, port=8766)
    self.assertTrue(result["ok"])
    self.assertEqual(result["status"], "launcher_opened")
    command = calls[0][0]
    self.assertIn("start_okx_demo_console.ps1", " ".join(map(str, command)))
    self.assertIn("-EnableOrder", command)
    self.assertIn("-EnableAutomation", command)
    self.assertIn("-ReplaceExistingConsole", command)
    self.assertEqual(command[command.index("-ExpectedConsoleProcessId") + 1], "4321")
    self.assertNotIn("apiKey", " ".join(map(str, command)).lower())

def test_non_loopback_request_is_rejected_without_starting_process(self):
    result = launcher.open("192.168.1.20", current_pid=4321, port=8766)
    self.assertFalse(result["ok"])
    self.assertEqual(result["error"], "local_host_required")
    self.assertEqual(calls, [])

def test_second_click_does_not_open_duplicate_launcher(self):
    first = launcher.open("::1", current_pid=4321, port=8766)
    second = launcher.open("::1", current_pid=4321, port=8766)
    self.assertTrue(first["ok"])
    self.assertEqual(second["error"], "launcher_already_open")
    self.assertEqual(len(calls), 1)
```

Add a UI contract assertion for the exact route string and use of `self.client_address[0]`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
D:\Codex-Workspace\AlphaPilot-Quant-Engine\.venv\Scripts\python.exe -m unittest tests.test_local_demo_launcher tests.test_workflow_ui_contract -v
```

Expected: FAIL because `local_demo_launcher` and the endpoint do not exist.

- [ ] **Step 3: Implement the minimal launcher service**

Use `ipaddress.ip_address(host.split("%", 1)[0]).is_loopback`, a `threading.Lock`, and an injected process factory. Build this fixed command only:

```python
command = [
    "powershell.exe",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", str(script_path),
    "-HostName", "127.0.0.1",
    "-Port", str(port),
    "-EnableOrder",
    "-EnableAutomation",
    "-ReplaceExistingConsole",
    "-ExpectedConsoleProcessId", str(current_pid),
]
if mobile:
    command.append("-Mobile")
```

Use `subprocess.CREATE_NEW_CONSOLE`, `cwd=repo_root`, and `close_fds=True`. Return credential-free state only. If the existing child has `poll() is None`, return `launcher_already_open`.

- [ ] **Step 4: Wire the loopback endpoint**

In `ConsoleHandler.do_POST`, ignore request body content, derive all values from the server, and call:

```python
result = LOCAL_DEMO_LAUNCHER.open(
    str(self.client_address[0]),
    current_pid=os.getpid(),
    port=int(self.server.server_address[1]),
    mobile=str(self.server.server_address[0]) in {"0.0.0.0", "::"},
)
```

Map `local_host_required` to 403, `launcher_already_open` to 409, successful open to 202, and an unexpected launch failure to 500. Do not echo exception command lines or environment values.

- [ ] **Step 5: Run focused and full Python tests**

Run the focused command from Step 2, then:

```powershell
D:\Codex-Workspace\AlphaPilot-Quant-Engine\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add alphapilot_control_console/local_demo_launcher.py alphapilot_control_console/http_app.py tests/test_local_demo_launcher.py tests/test_workflow_ui_contract.py
git commit -m "Add loopback-only OKX Demo launcher endpoint"
```

---

### Task 2: Safe PowerShell credential collection and exact process handoff

**Files:**
- Modify: `scripts/start_okx_demo_console.ps1`
- Create: `tests/test_okx_demo_launcher_script.py`

**Interfaces:**
- Consumes: fixed arguments `-ReplaceExistingConsole` and `-ExpectedConsoleProcessId` from Task 1.
- Preserves: existing manual launcher behavior when replacement mode is absent.
- Produces: exact-PID handoff after credentials and explicit Demo automation confirmation.

- [ ] **Step 1: Write failing script contract tests**

Read the PowerShell file as UTF-8 and assert it contains:

```python
self.assertIn("[switch]$ReplaceExistingConsole", script)
self.assertIn("[int]$ExpectedConsoleProcessId", script)
self.assertIn('ENABLE_OKX_DEMO_AUTOMATION', script)
self.assertIn('Get-NetTCPConnection', script)
self.assertIn('OwningProcess', script)
self.assertIn('alphapilot_control_console.http_app', script)
self.assertIn('Stop-Process -Id $listenerProcessId', script)
self.assertIn('if ($listenerProcessId -ne $ExpectedConsoleProcessId)', script)
self.assertLess(script.index('$apiKey = Read-SecretText'), script.index('Stop-Process -Id $listenerProcessId'))
self.assertNotIn('apiKey = "', script)
```

Also assert the script uses `$listenerProcessId`, never assigns to the PowerShell reserved `$PID`, and still clears all three credential environment variables in `finally`.

- [ ] **Step 2: Run the script contract test and verify RED**

Run:

```powershell
D:\Codex-Workspace\AlphaPilot-Quant-Engine\.venv\Scripts\python.exe -m unittest tests.test_okx_demo_launcher_script -v
```

Expected: FAIL because replacement parameters and exact handoff are absent.

- [ ] **Step 3: Add replacement parameters and explicit confirmation**

Add parameters:

```powershell
[switch]$ReplaceExistingConsole,
[int]$ExpectedConsoleProcessId = 0
```

After the three secure inputs are non-empty, require this exact confirmation only when `-EnableAutomation` is present:

```powershell
$automationConfirmation = Read-Host "Type ENABLE_OKX_DEMO_AUTOMATION to continue"
if ($automationConfirmation -cne "ENABLE_OKX_DEMO_AUTOMATION") {
  Write-Host "OKX Demo automation launch cancelled. Existing console remains running." -ForegroundColor Yellow
  exit 2
}
```

- [ ] **Step 4: Implement exact listener ownership verification**

Before setting credential environment variables, replacement mode must:

```powershell
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $listener) { throw "No listener exists on the requested AlphaPilot port." }
$listenerProcessId = [int]$listener.OwningProcess
if ($listenerProcessId -ne $ExpectedConsoleProcessId) { throw "The port owner changed; refusing to stop an unverified process." }
$processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $listenerProcessId"
if ($null -eq $processInfo -or $processInfo.CommandLine -notmatch "alphapilot_control_console\.http_app") {
  throw "The listener is not the AlphaPilot Control Console; refusing process handoff."
}
Stop-Process -Id $listenerProcessId
```

Wait up to 10 seconds for the port to be released. Throw without starting a second server if release fails. Credential cancellation or failed ownership checks happen before the existing console is stopped.

- [ ] **Step 5: Run tests and PowerShell parser check**

Run the focused test, then:

```powershell
$errors = $null
[System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path 'scripts\start_okx_demo_console.ps1'), [ref]$null, [ref]$errors) | Out-Null
if ($errors.Count -gt 0) { $errors | Format-List; exit 1 }
```

Expected: focused test passes and parser error count is zero.

- [ ] **Step 6: Commit Task 2**

```powershell
git add scripts/start_okx_demo_console.ps1 tests/test_okx_demo_launcher_script.py
git commit -m "Add safe OKX Demo runtime handoff"
```

---

### Task 3: One-time issue guidance module and collapsed evidence disclosure

**Files:**
- Create: `web/issue-guidance.js`
- Modify: `web/index.html`
- Modify: `web/styles.css`
- Modify: `web/app.js`
- Modify: `tests/test_workflow_ui_contract.py`

**Interfaces:**
- Produces: `window.AlphaPilotIssueGuidance.createController(options)`.
- Produces controller methods: `register(issue)`, `presentHighestPriority(pageId)`, `open(issueKey)`, and `acknowledgeCurrent()`.
- Consumes issue objects with `key`, `pageId`, `priority`, `title`, `summary`, `completed`, `nextAction`, and `safety`.

- [ ] **Step 1: Add failing UI contract tests**

Assert all of these contracts:

```python
self.assertIn('id="issueGuidanceDialog"', self.html)
self.assertIn('id="issueGuidanceNextAction"', self.html)
self.assertIn('/issue-guidance.js?v=20260711-v13-27-1-5-guidance', self.html)
self.assertIn('ALPHAPILOT_ISSUE_ACK_V1', issue_js)
self.assertIn('function issueFingerprint', issue_js)
self.assertIn('localStorage', issue_js)
self.assertIn('sessionStorage', issue_js)
self.assertIn('查看处理办法', self.js)
self.assertIn('<details class="demo-evidence-section"', self.js)
self.assertIn('<summary class="demo-section-head">', self.js)
self.assertIn('evidenceChecklist.items', self.js)
```

The test setup must read `web/issue-guidance.js` separately.

- [ ] **Step 2: Run UI contract tests and verify RED**

Run:

```powershell
D:\Codex-Workspace\AlphaPilot-Quant-Engine\.venv\Scripts\python.exe -m unittest tests.test_workflow_ui_contract -v
```

Expected: FAIL because the module, dialog, and disclosure are absent.

- [ ] **Step 3: Implement the focused issue controller**

The module must:

```javascript
const ACK_PREFIX = "ALPHAPILOT_ISSUE_ACK_V1";
function issueFingerprint(issue) {
  const blockers = [...new Set(issue.blockers || [])].sort();
  return [issue.pageId, issue.strategyId || "global", issue.stage || "unknown", blockers.join("|"), issue.version || "1"].join("::");
}
```

Use `localStorage` first and fall back to `sessionStorage`, then an in-memory `Set`. Mark a fingerprint acknowledged when its automatic dialog closes. Register issues in a `Map`, aggregate keys that share page, stage, and blockers, and auto-open only the highest-priority issue for the current location hash. Manual open ignores acknowledgement state.

- [ ] **Step 4: Add the accessible dialog and styles**

Add one global `<dialog id="issueGuidanceDialog">` containing:

- title and current-stage text;
- blocker summary;
- completed work list;
- exact next action;
- safety boundary;
- `知道了` and icon close buttons.

Use the existing dialog visual language, 8 px or smaller corner radius, mobile-safe width, no nested cards, and no horizontal overflow at 375 px.

- [ ] **Step 5: Convert Demo evidence to a native disclosure**

Change `renderDemoEvidence` to return:

```javascript
<details class="demo-evidence-section">
  <summary class="demo-section-head">
    <strong>证据清单</strong>
    <small>6/8 已满足 · 1 项阻塞</small>
  </summary>
  <div class="demo-evidence-list">...</div>
</details>
```

Do not add `open`; the checklist is collapsed by default. Keep counts and every evidence row unchanged.

- [ ] **Step 6: Run contract tests and JavaScript syntax checks**

Run the focused Python test, then:

```powershell
C:\Users\阿俊\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe --check web\issue-guidance.js
C:\Users\阿俊\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe --check web\app.js
```

Expected: all pass.

- [ ] **Step 7: Commit Task 3**

```powershell
git add web/issue-guidance.js web/index.html web/styles.css web/app.js tests/test_workflow_ui_contract.py
git commit -m "Add one-time workflow issue guidance"
```

---

### Task 4: Wire actionable guidance and one-click Demo startup across primary pages

**Files:**
- Modify: `web/app.js`
- Modify: `web/index.html`
- Modify: `web/styles.css`
- Modify: `tests/test_workflow_ui_contract.py`

**Interfaces:**
- Consumes: `window.AlphaPilotIssueGuidance` from Task 3.
- Consumes: `POST /api/local-control/open-okx-demo-launcher` from Task 1.
- Produces: `launchOkxDemoRuntime()`, `collectStrategyIssues()`, `collectLocalIssues()`, `collectDemoIssues()`, and `collectLiveIssues()`.

- [ ] **Step 1: Add failing integration contract tests**

Assert the UI contains:

```python
for name in ("collectStrategyIssues", "collectLocalIssues", "collectDemoIssues", "collectLiveIssues"):
    self.assertIn(f"function {name}", self.js)
self.assertIn('data-issue-guidance-key', self.js)
self.assertIn('启动 OKX Demo', self.js)
self.assertIn('/api/local-control/open-okx-demo-launcher', self.js)
self.assertIn('启动器已打开，请在 PowerShell 窗口输入三项 Demo 凭据', self.js)
self.assertIn('Demo 凭据每次运行只输入一次，全部合格策略共用', self.js)
self.assertIn('实盘账户凭据输入一次；每条策略仍需逐条批准启用', self.js)
self.assertIn('window.location.hostname', self.js)
```

- [ ] **Step 2: Run UI tests and verify RED**

Run `python -m unittest tests.test_workflow_ui_contract -v` with the repository virtual environment. Expected: FAIL on the new contracts.

- [ ] **Step 3: Map blockers into shared issue models**

Implement four collectors:

- Strategy: failed or blocked formal backtests, grouped by normalized failure category.
- Local: local-forward lifecycle cards with blockers or missing evidence.
- Demo: validating/waiting cards with failed evidence or runtime blockers; `okx_demo_runtime` has highest priority.
- Live: Live Canary blockers and pending per-strategy approval, but the action remains review-only and cannot enable Live.

Each rendered blocker area gets `查看处理办法`. Event delegation calls `issueController.open(issueKey)`.

- [ ] **Step 4: Implement one-click Demo launcher UX**

For a loopback hostname only, render:

```text
OKX Demo Runtime 未就绪
Demo 凭据每次运行只输入一次，全部合格策略共用。
[启动 OKX Demo]
```

`launchOkxDemoRuntime()` posts an empty object to the fixed endpoint, reports `launcher_already_open` without opening another window, then polls `/api/exchange-demo/simulation?fresh=1` and `/api/demo-workflow?fresh=1`. Readiness is successful only when credentials, private read, order, automation, and risk gates are all ready. Timeout leaves a retry action and points to the visible PowerShell diagnostic window.

For a LAN or phone hostname, disable the launch action and show `请在运行控制台的电脑上打开 127.0.0.1:8766 完成启动`.

- [ ] **Step 5: Add account-level sharing and Live approval copy**

The Demo page must say that one account runtime serves all eligible strategies while keeping strategy PnL separate. The Live page must say that account credentials are entered once but every immutable strategy is approved separately. Do not add a Live credential form or launcher.

- [ ] **Step 6: Run focused tests and syntax checks**

Run UI contracts and Node checks from Task 3. Expected: all pass.

- [ ] **Step 7: Commit Task 4**

```powershell
git add web/app.js web/index.html web/styles.css tests/test_workflow_ui_contract.py
git commit -m "Wire actionable guidance and Demo startup"
```

---

### Task 5: Version, documentation, complete validation, integration, and completion shutdown

**Files:**
- Create: `docs/V13.27.1.5-one-time-guidance-demo-launcher.md`
- Modify: `README.md`
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `alphapilot_control_console/demo_workflow_projection.py`
- Modify: `alphapilot_control_console/exchange_demo_simulation.py`
- Modify: `alphapilot_control_console/strategy_lifecycle_projection.py`
- Modify: `alphapilot_control_console/workflow_client.py`
- Modify: `tests/test_workflow_ui_contract.py`

**Interfaces:**
- Produces: consistent `V13.27.1.5` version metadata and `v13.27.1.5` tag.
- Produces: verified install-free local web console behavior on desktop and mobile widths.

- [ ] **Step 1: Add failing version and documentation contracts**

Update the UI contract test to require the cachebuster `v13-27-1-5-guidance`, and add assertions that README documents:

- one-time automatic issue guidance;
- collapsible evidence;
- one-click local Demo launcher;
- one Demo credential set per runtime for all eligible strategies;
- Live account credential once with per-strategy approval;
- process-only credentials and no withdrawal.

Run the test and verify it fails against V13.27.1.4 metadata.

- [ ] **Step 2: Update version metadata and documentation**

Replace V13.27.1.4 metadata with V13.27.1.5 in the listed runtime files. Update both CSS and JavaScript cachebusters in `index.html`. Add a focused release document with startup flow, cancellation behavior, loopback restriction, credential boundaries, and recovery steps.

- [ ] **Step 3: Run the complete automated suite**

Run:

```powershell
D:\Codex-Workspace\AlphaPilot-Quant-Engine\.venv\Scripts\python.exe -m unittest discover -s tests -v
D:\Codex-Workspace\AlphaPilot-Quant-Engine\.venv\Scripts\python.exe -m compileall alphapilot_control_console
C:\Users\阿俊\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe --check web\issue-guidance.js
C:\Users\阿俊\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe --check web\app.js
git diff --check
git diff --cached --check
```

Expected: all pass.

- [ ] **Step 4: Run the safety scan**

Scan changed files for credentials, arbitrary command execution, Live enablement, withdrawal, and broad process termination. Confirm every hit is a defensive check, negative statement, fixed local launcher, or existing Demo-only capability. Explicitly verify:

- no raw key values;
- no browser credential fields;
- no `shell=True`;
- no request-controlled executable or arguments;
- no broad `Stop-Process` filter;
- no Live order enablement;
- no Withdraw endpoint.

- [ ] **Step 5: Validate on an isolated test port**

Start the worktree server on port 8877 without credentials. Verify:

- `/api/health` reports V13.27.1.5;
- non-loopback behavior is covered by unit test;
- clicking `启动 OKX Demo` opens exactly one visible launcher;
- cancel the launcher before entering credentials so no account request or order occurs;
- repeated polling does not reopen the same issue dialog;
- manual `查看处理办法` reopens it;
- evidence is collapsed by default;
- desktop and 375 px mobile views have no horizontal overflow.

Stop only the exact 8877 test server PID and verify the port is free.

- [ ] **Step 6: Commit Task 5**

```powershell
git add README.md docs/V13.27.1.5-one-time-guidance-demo-launcher.md web/index.html web/app.js alphapilot_control_console/http_app.py alphapilot_control_console/demo_workflow_projection.py alphapilot_control_console/exchange_demo_simulation.py alphapilot_control_console/strategy_lifecycle_projection.py alphapilot_control_console/workflow_client.py tests/test_workflow_ui_contract.py
git commit -m "Release V13.27.1.5 guided Demo launcher"
```

- [ ] **Step 7: Complete the feature branch**

Use the finishing-a-development-branch skill. Re-run the full suite, merge the feature branch into `main` without staging runtime directories, create tag `v13.27.1.5`, push `main` and the tag, and verify remote refs plus final `git status`.

- [ ] **Step 8: Verify the post-merge runtime path**

If the current 8766 process has no process-only Demo credentials, restart it from merged `main` and verify health and page assets. If it has credentials, do not silently discard them; validate merged code on 8877 and document that the next launcher start will load V13.27.1.5. Because the user requested shutdown after completion, any remaining process-only credentials will be lost at shutdown and must be entered again next boot.

- [ ] **Step 9: Record pitfalls and schedule completion-triggered shutdown**

Append this run's actual errors and user corrections to `D:\Codex-Workspace\踩坑日志.txt`. Only after all prior steps pass, schedule:

```powershell
shutdown.exe /s /t 120 /d p:0:0 /c "AlphaPilot V13.27.1.5 completed and verified"
```

Verify the shutdown request was accepted, then send the final report during the 120-second grace period. Do not schedule shutdown when tests, merge, push, or runtime verification remain incomplete.
