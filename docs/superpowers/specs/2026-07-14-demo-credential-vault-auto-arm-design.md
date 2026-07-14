# OKX Demo Credential Vault and Automatic ARM Recovery Design

## Objective

Persist one confirmed OKX Demo credential set in Windows Credential Manager so the local AlphaPilot Control Console can recover Demo automation after a process restart without repeatedly asking the user to paste credentials.

This is a Demo-only convenience and reliability feature. It does not apply to OKX Live, does not add Withdraw support, and does not weaken immutable Demo Release, order, position, or risk gates.

## Confirmed User Decision

The user confirmed that the credential set is an OKX Demo Trading API key and approved persistent storage for Demo only.

The user accepts that the credential survives console restarts and Windows sign-in sessions on this computer. Live credentials remain outside this mechanism.

## Current Failure Mode

Demo ARM is intentionally bound to the process that received the process-only credentials. When that process exits or is replaced, the database still records the previous process id and the new listener enters `disarmed/process_arm_required`.

The observed incident had an ARM record for PID `11708`, while the replacement listener used PID `31920`. The most recent completed batch was at 14:00 Beijing time, and later heartbeats were blocked. The safety behavior was correct, but recovery required the user to notice the condition and manually reopen the launcher.

## Considered Approaches

### A. One-time automatic prompt with process-only credentials

This preserves the current no-storage boundary and opens the existing PowerShell prompt once per disarmed process. It is safe but still requires manual entry after every process restart.

### B. Persistent supervisor process

A supervisor can restart the console, but it cannot transfer secrets to the replacement process after logout or reboot without storing them. It adds lifecycle complexity without solving the credential problem.

### C. Windows Credential Manager for Demo only

This is the approved approach. It uses a generic credential scoped to the current Windows user and this computer. The console can retrieve the Demo bundle at startup, validate it against OKX Demo read-only endpoints, and restore the existing process gates.

## Security Boundary

1. The vault target is fixed and namespaced: `AlphaPilot/OKX/Demo/v1`.
2. Persistence uses `CRED_PERSIST_LOCAL_MACHINE`, not enterprise or roaming persistence.
3. Only the OKX Demo API key, secret, and passphrase are stored.
4. Credentials are accepted only after a read-only OKX Demo validation request succeeds with `x-simulated-trading: 1`.
5. Credentials are never placed in SQLite, project files, logs, HTTP responses, browser storage, Git, command-line arguments, or exception text.
6. Live credentials are never read from or written to the Demo vault target.
7. Withdraw APIs remain absent.
8. The vault does not create or modify a Demo Release and cannot bypass immutable release, strategy, market, order, position, or risk gates.
9. Deleting the vault entry immediately returns the next process to the existing `process_arm_required` behavior.
10. Tests use an in-memory vault double and never access the user's real Windows Credential Manager.

Windows Credential Manager protects credentials at rest but cannot protect them from malware or an administrator running under the same Windows account. The UI must state this residual risk without exposing credential values.

## Components

### `WindowsDemoCredentialVault`

A focused Windows adapter around `CredWriteW`, `CredReadW`, and `CredDeleteW`.

It provides:

- `store(bundle)`
- `load()`
- `delete()`
- `metadata()`

The adapter returns typed status codes and redacted metadata only. The generic credential blob contains a compact versioned JSON document. API key material is never included in `repr`, logs, or returned metadata.

### `DemoCredentialBootstrap`

Runs before the OKX Demo provider and unified auto-execution controller are created.

If a vault entry exists, it:

1. loads the credential bundle into process memory;
2. validates it using Demo read-only requests only;
3. sets the existing Demo environment gates in the current process;
4. marks the launcher confirmation as coming from an approved Demo vault enrollment;
5. allows the existing controller to ARM this process normally.

It does not directly write ARM state or bypass the controller.

### `DemoCredentialPromptSupervisor`

If the vault is missing or validation fails while Demo automation is desired and at least one immutable Demo Release exists, the supervisor opens the fixed PowerShell launcher once for the current listener process.

The one-time key is based on the listener PID and failure class. It prevents a window storm on every heartbeat. Closing or cancelling the prompt does not reopen it automatically in the same process; the existing manual launcher action remains available.

### Launcher enrollment mode

`start_okx_demo_console.ps1` gains an explicit Demo vault enrollment switch used by the automatic prompt and the manual update action.

The launcher:

1. collects all three values through secure prompts;
2. validates the credential against OKX Demo read-only endpoints;
3. stores it in the fixed local-machine vault target only after successful validation;
4. verifies the current listener PID before stopping it;
5. starts the replacement console, which retrieves the new vault entry and ARM-restores through the normal controller.

If validation or storage fails, the existing console remains running and no partial credential is retained.

### Local management endpoints

Loopback-only endpoints expose operations, never values:

- open or update the Demo credential enrollment prompt;
- delete the Demo credential entry;
- read redacted vault status.

Deletion requires an explicit local confirmation token and writes a non-secret audit event.

## Startup and Recovery Flow

1. The console starts.
2. The bootstrap checks the fixed Demo vault target.
3. If the credential is present and validates, the existing Demo gates are populated in process memory.
4. The unified controller performs its normal ARM checks.
5. If the credential is absent or invalid, the runtime stays disarmed and the prompt supervisor opens one enrollment window.
6. After successful enrollment, the fixed launcher safely replaces the verified listener.
7. The replacement process loads the stored Demo credential and restores ARM through the normal startup path.

No strategy order is submitted merely because credentials were restored. Orders still require an eligible immutable Demo Release, a closed-candle evaluation, a matched signal, and all risk gates.

## Failure Handling

- **Vault unavailable:** stay disarmed, open one prompt, expose a redacted error code.
- **Credential missing:** stay disarmed and offer enrollment.
- **Demo validation rejected:** keep the stored entry until the user updates or deletes it; do not print the exchange response body if it may contain sensitive context.
- **IP whitelist failure:** stay disarmed and show the existing whitelist guidance. Do not delete the credential automatically.
- **Prompt cancelled:** preserve the current listener and do not reopen repeatedly.
- **Listener PID changed during handoff:** refuse replacement.
- **Credential deletion:** clear the vault entry and prevent automatic recovery on the next process.
- **Non-Windows platform:** report vault unsupported and retain process-only behavior.

## UI Behavior

The Demo page shows one compact status line:

- `Demo 凭据已安全保存（仅本机）`
- `Demo 凭据需要更新`
- `尚未保存 Demo 凭据`

Actions:

- `更新 Demo 凭据`
- `删除已保存凭据`

Credential values are never rendered. A prompt-opened notification is shown once, not on every refresh.

## Audit Events

Only non-secret events are recorded:

- `demo_vault_enrollment_opened`
- `demo_vault_validation_succeeded`
- `demo_vault_validation_failed`
- `demo_vault_loaded`
- `demo_vault_deleted`
- `demo_runtime_pid_changed`

Events may include timestamp, current PID, redacted target identifier, and error category. They must not contain API key material or raw exchange responses.

## Testing

1. Vault adapter round-trip against an in-memory WinCred double.
2. Local-machine persistence flag is required.
3. Live or differently namespaced targets are rejected.
4. Bootstrap loads a valid Demo bundle and preserves the existing controller ARM path.
5. Missing or invalid credentials never ARM the process.
6. Prompt opens once per PID and failure class.
7. Prompt cancellation does not stop the current listener.
8. Enrollment validates before writing or stopping the listener.
9. Delete removes the entry and returns redacted status.
10. Logs, API responses, exceptions, and command lines contain no credential values.
11. Existing Demo workflow, transient-network recovery, immutable Release, and Live safety tests remain green.

## Rollout

1. Implement and test in an isolated worktree.
2. Merge without restarting the currently running listener.
3. Open the enrollment prompt once after deployment.
4. The user enters the confirmed Demo credential one final time.
5. Verify read-only Demo connectivity, current-process ARM, 10 immutable Releases, and no last error.
6. Restart the console deliberately and verify automatic vault recovery without another prompt.
7. Confirm no credential material exists in the repository, SQLite, logs, process command lines, or browser storage.

## Non-goals

- Persisting or auto-loading OKX Live credentials.
- Withdraw support.
- Bypassing IP allowlists or exchange permissions.
- Automatically converting a research candidate into a Demo or Live Release.
- Weakening strategy, order, position, latency, or risk controls.
- Guaranteeing uninterrupted operation if Windows, the network, or OKX is unavailable.

## Acceptance Criteria

1. A confirmed Demo credential can be stored under the fixed local-machine vault target.
2. A restarted console can validate and load it without another credential prompt.
3. The controller, not the vault, performs ARM.
4. Missing or invalid credentials remain fail-closed.
5. Automatic prompting occurs at most once per listener PID and failure class.
6. The user can update or delete the stored Demo credential locally.
7. No credential value is persisted outside Windows Credential Manager or exposed through logs, SQLite, HTTP, browser storage, Git, or command lines.
8. Live and Withdraw boundaries are unchanged.
9. Existing Console tests and new security-focused tests pass.
