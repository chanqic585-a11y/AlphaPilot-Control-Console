# OKX Demo Credential Vault and Automatic ARM Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist one verified OKX Demo credential bundle in Windows Credential Manager and restore the existing Demo automation gates after a console process restart without exposing credentials or weakening execution controls.

**Architecture:** A small WinCred adapter owns the fixed `AlphaPilot/OKX/Demo/v1` target and returns only redacted metadata. Enrollment validates the bundle through the existing allowlisted OKX Demo read-only client before writing; startup bootstrap loads and validates it into the current process environment, after which the existing startup ARM controller remains the only component allowed to ARM execution. Loopback-only HTTP actions expose status, prompt enrollment, and explicit deletion, while a once-per-PID supervisor prevents repeated prompt windows.

**Tech Stack:** Python 3.11 standard library (`ctypes`, `dataclasses`, `json`), Windows Credential Manager Win32 APIs, existing OKX Demo REST client, PowerShell launcher, built-in HTTP server, vanilla HTML/CSS/JavaScript, `pytest`/`unittest`.

## Global Constraints

- Store only confirmed OKX Demo credentials; never store or load OKX Live credentials.
- Use the fixed target `AlphaPilot/OKX/Demo/v1` and `CRED_PERSIST_LOCAL_MACHINE`.
- Validate with an allowlisted OKX Demo read-only request carrying `x-simulated-trading: 1` before storing or startup ARM.
- Never expose credentials through files, SQLite, logs, HTTP, browser storage, Git, command-line arguments, or exception text.
- Keep Withdraw absent and preserve immutable Demo Release, order, position, latency, and risk gates.
- Missing, unsupported, or rejected credentials remain fail-closed.
- Do not restart the listener currently bound to port `8766` while implementing or testing.
- Tests use fake backends and never touch the user's real Windows Credential Manager.

---

### Task 1: Windows Demo Credential Vault

**Files:**
- Create: `alphapilot_control_console/windows_demo_credential_vault.py`
- Test: `tests/test_windows_demo_credential_vault.py`

**Interfaces:**
- Produces: `DemoCredentialBundle`, `DemoCredentialVaultError`, `WindowsDemoCredentialVault.store()`, `.load()`, `.delete()`, and `.metadata()`.
- Produces: an injectable backend contract with `write(target_name, blob, persistence)`, `read(target_name)`, and `delete(target_name)` so tests never call Win32.

- [ ] **Step 1: Write failing vault contract tests**

  Cover a redacted round trip, compact versioned JSON, exact target name, persistence value `2`, missing entry metadata, deletion, malformed payload rejection, non-Windows fail-closed behavior, and secret absence from `repr` and metadata.

- [ ] **Step 2: Verify the tests fail for the missing module**

  Run:

  ```powershell
  D:\Codex-Workspace\AlphaPilot-Quant-Engine\.venv\Scripts\python.exe -m pytest -q tests\test_windows_demo_credential_vault.py
  ```

  Expected: collection fails because `windows_demo_credential_vault` does not exist.

- [ ] **Step 3: Implement the minimal vault and Win32 backend**

  Implement a frozen bundle whose secret fields use `repr=False`, a safe error carrying only a category, and a native `CredWriteW`/`CredReadW`/`CredDeleteW` adapter loaded only on Windows. Serialize exactly `{\"v\":1,\"apiKey\":...,\"secretKey\":...,\"passphrase\":...}` as UTF-8; reject incomplete, oversized, malformed, or wrong-version records without returning the blob.

- [ ] **Step 4: Run the focused tests until green**

  Run the Task 1 command and expect all tests to pass.

- [ ] **Step 5: Commit Task 1**

  ```powershell
  git add alphapilot_control_console/windows_demo_credential_vault.py tests/test_windows_demo_credential_vault.py
  git commit -m "feat: add Windows vault for OKX Demo credentials"
  ```

### Task 2: Read-only Validation and Enrollment CLI

**Files:**
- Create: `alphapilot_control_console/demo_credential_enrollment.py`
- Create: `alphapilot_control_console/demo_credential_vault_cli.py`
- Modify: `scripts/start_okx_demo_console.ps1`
- Modify: `tests/test_okx_demo_launcher_script.py`
- Test: `tests/test_demo_credential_enrollment.py`

**Interfaces:**
- Consumes: `DemoCredentialBundle` and `WindowsDemoCredentialVault` from Task 1.
- Produces: `validate_demo_credentials(bundle, client_factory=...) -> dict`, `enroll_demo_credentials(environment=..., vault=..., validator=..., audit_writer=...) -> dict`, and CLI exit codes `0` success / `2` rejected.

- [ ] **Step 1: Write failing enrollment tests**

  Assert that `get_account_config()` with OKX code `0` is the sole validation request, validation failure writes nothing, success stores once, audit payloads contain only target/category/PID, raw test secrets never appear in results or exceptions, and the script enrolls before verifying/stopping the existing listener.

- [ ] **Step 2: Verify RED**

  ```powershell
  D:\Codex-Workspace\AlphaPilot-Quant-Engine\.venv\Scripts\python.exe -m pytest -q tests\test_demo_credential_enrollment.py tests\test_okx_demo_launcher_script.py
  ```

  Expected: missing enrollment module and missing `-EnrollCredentialVault` behavior.

- [ ] **Step 3: Implement validation and CLI**

  Build `OkxDemoCredentials` from the three existing Demo environment variables, call `OkxDemoClient(..., site="global").get_account_config()`, accept only code `0`, and map failures to redacted categories such as `demo_validation_rejected`, `demo_validation_unavailable`, or `vault_write_failed`. The CLI prints only a safe status line and never prints returned payloads.

- [ ] **Step 4: Extend the PowerShell launcher**

  Add `[switch]$EnrollCredentialVault`. When set, temporarily inject only the three Demo values plus the fixed site, invoke `python -m alphapilot_control_console.demo_credential_vault_cli enroll`, clear those variables in `finally`, and proceed to listener replacement only when enrollment succeeds. Keep the current explicit automation confirmation and final environment cleanup.

- [ ] **Step 5: Verify GREEN and commit**

  Run the Task 2 tests, then:

  ```powershell
  git add alphapilot_control_console/demo_credential_enrollment.py alphapilot_control_console/demo_credential_vault_cli.py scripts/start_okx_demo_console.ps1 tests/test_demo_credential_enrollment.py tests/test_okx_demo_launcher_script.py
  git commit -m "feat: validate and enroll OKX Demo vault credentials"
  ```

### Task 3: Startup Bootstrap and Once-per-process Prompt

**Files:**
- Create: `alphapilot_control_console/demo_credential_bootstrap.py`
- Modify: `alphapilot_control_console/local_demo_launcher.py`
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `tests/test_local_demo_launcher.py`
- Modify: `tests/test_workflow_startup_recovery.py`
- Test: `tests/test_demo_credential_bootstrap.py`

**Interfaces:**
- Consumes: vault load and validation APIs from Tasks 1-2.
- Produces: `bootstrap_demo_credentials(environment, vault, validator, audit_writer) -> dict` and `LocalDemoLauncher.open_once_for_failure(..., failure_class) -> dict`.

- [ ] **Step 1: Write failing bootstrap and prompt tests**

  Assert valid stored credentials populate only the current process Demo variables and fixed gates, then allow the existing `arm_okx_demo_runtime_on_startup()` call. Missing/rejected credentials do not set gates, do not delete the vault, and request one prompt for the same PID/failure class. A second call is suppressed; a new PID or failure class may prompt once.

- [ ] **Step 2: Verify RED**

  ```powershell
  D:\Codex-Workspace\AlphaPilot-Quant-Engine\.venv\Scripts\python.exe -m pytest -q tests\test_demo_credential_bootstrap.py tests\test_local_demo_launcher.py tests\test_workflow_startup_recovery.py
  ```

- [ ] **Step 3: Implement bootstrap and launcher supervision**

  Bootstrap before market runtime and unified runner startup. On valid vault data set `ALPHAPILOT_OKX_DEMO_ENABLED`, `ALPHAPILOT_OKX_DEMO_ORDER_ENABLED`, `ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED`, and `ALPHAPILOT_OKX_DEMO_LAUNCHER_CONFIRMED` to `1`, plus the three credential values in process memory. Do not write ARM state. Add `-EnrollCredentialVault` to the fixed launcher command and retain the existing loopback, PID, and duplicate-process checks.

- [ ] **Step 4: Preserve startup ordering**

  In `run_server`, execute bootstrap first, then construct/start market runtime and unified runner, then call the existing startup ARM function. If bootstrap is missing/rejected and Demo is desired, invoke the once-per-PID prompt supervisor after the listener object exists but before `serve_forever`; do not stop or replace the listener from Python.

- [ ] **Step 5: Verify GREEN and commit**

  Run the Task 3 tests, then:

  ```powershell
  git add alphapilot_control_console/demo_credential_bootstrap.py alphapilot_control_console/local_demo_launcher.py alphapilot_control_console/http_app.py tests/test_demo_credential_bootstrap.py tests/test_local_demo_launcher.py tests/test_workflow_startup_recovery.py
  git commit -m "feat: restore Demo ARM from the local credential vault"
  ```

### Task 4: Loopback Management API and Compact Demo UI

**Files:**
- Modify: `alphapilot_control_console/http_app.py`
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Modify: `tests/test_unified_auto_execution_http.py`
- Modify: `tests/test_workflow_ui_contract.py`

**Interfaces:**
- Produces: `GET /api/local-control/okx-demo-credential-vault`, `POST /api/local-control/open-okx-demo-launcher`, and `POST /api/local-control/delete-okx-demo-credential-vault`.
- Delete body: `{\"confirmation\":\"DELETE_OKX_DEMO_CREDENTIAL\"}`; all operations require a loopback client and return metadata only.

- [ ] **Step 1: Write failing HTTP and UI contract tests**

  Assert non-loopback status/delete calls return `403`, deletion rejects a missing confirmation, successful deletion returns redacted metadata and a non-secret audit event, launcher status says local-machine persistence, and UI text/actions contain no credential inputs or browser storage calls.

- [ ] **Step 2: Verify RED**

  ```powershell
  D:\Codex-Workspace\AlphaPilot-Quant-Engine\.venv\Scripts\python.exe -m pytest -q tests\test_unified_auto_execution_http.py tests\test_workflow_ui_contract.py
  ```

- [ ] **Step 3: Implement loopback endpoints**

  Return only `supported`, `stored`, `status`, `targetLabel`, and `persistence`. The update action opens the fixed enrollment launcher. Delete only after the exact confirmation token, writes `demo_vault_deleted`, and never mutates Live state, Release state, or risk settings.

- [ ] **Step 4: Implement compact UI**

  Add a single status row to the Demo toolbar with `Demo 凭据已安全保存（仅本机）`, `Demo 凭据需要更新`, or `尚未保存 Demo 凭据`, plus `更新 Demo 凭据` and `删除已保存凭据`. Confirm deletion in the browser, send only the fixed confirmation token, and never render or request raw values.

- [ ] **Step 5: Verify GREEN and commit**

  Run the Task 4 tests, then:

  ```powershell
  git add alphapilot_control_console/http_app.py web/index.html web/app.js web/styles.css tests/test_unified_auto_execution_http.py tests/test_workflow_ui_contract.py
  git commit -m "feat: add local Demo vault controls"
  ```

### Task 5: Security Regression, Documentation, and Branch Completion

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-07-14-demo-credential-vault-auto-arm-design.md` only if implementation details require an explicit clarification.

**Interfaces:**
- Verifies all previous tasks; introduces no new runtime interface.

- [ ] **Step 1: Update operator documentation**

  Document that Demo credentials are encrypted by Windows Credential Manager for the current Windows user and computer, Live remains process-only, deletion disables next-start recovery, and the first post-deployment enrollment plus deliberate restart test is still required.

- [ ] **Step 2: Run focused security tests and all Console tests**

  ```powershell
  D:\Codex-Workspace\AlphaPilot-Quant-Engine\.venv\Scripts\python.exe -m pytest -q tests
  D:\Codex-Workspace\AlphaPilot-Quant-Engine\.venv\Scripts\python.exe -m compileall alphapilot_control_console
  ```

  Expected baseline: all existing tests plus new tests pass; compileall exits `0`.

- [ ] **Step 3: Run static safety checks**

  ```powershell
  git diff --check
  rg -n "OKX Demo API Key|OKX Demo Secret Key|OKX Demo Passphrase" alphapilot_control_console web tests scripts
  rg -n "localStorage|sessionStorage|withdraw|OKX_LIVE" alphapilot_control_console/windows_demo_credential_vault.py alphapilot_control_console/demo_credential_*.py web/app.js
  ```

  Review matches: prompt labels, negative assertions, and existing safety copy are allowed; no literal credential, browser storage, Withdraw implementation, or Live vault path is allowed.

- [ ] **Step 4: Commit documentation and final verification**

  ```powershell
  git add README.md docs/superpowers/specs/2026-07-14-demo-credential-vault-auto-arm-design.md
  git commit -m "docs: explain Demo credential recovery boundary"
  git status --short --branch
  ```

- [ ] **Step 5: Complete the branch without restarting port 8766**

  Follow `finishing-a-development-branch`: re-run the full suite, inspect the complete diff, fast-forward the approved main branch only after checks pass, push the resulting commits, and leave enrollment/restart verification as an explicit post-merge operator step.
