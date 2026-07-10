# AlphaPilot V13.15.2 OKX Demo Secure Integration Implementation Plan

## Objective

Implement the approved secure OKX Demo integration using one process-only Read + Trade Demo key for the global OKX site. Consolidate all private requests through one allowlisted client, complete a redacted read-only connection check, and prepare a separate connectivity smoke path without bypassing immutable `DemoRelease` requirements for strategy automation.

## Safety Boundary

- Demo Trading only.
- Global REST domain only: `https://openapi.okx.com`.
- Mandatory `x-simulated-trading: 1`.
- No Withdraw, transfer, deposit, live domain, or live credentials.
- Raw credentials remain process-only.
- Default startup keeps order, automation, and cancel gates off.
- Connectivity smoke is not strategy evidence.
- Strategy automation requires an immutable eligible `DemoRelease`.
- Current `DemoRelease=0` must remain an honest blocker.

## Task 1: Lock Expected Behavior With Tests

Files:

- Modify `tests/test_okx_demo_client.py`
- Add `tests/test_exchange_demo_secure_integration.py`
- Modify `tests/test_evolution_demo_service.py` if release-gate coverage needs extension

Tests:

1. Global site resolves to `https://openapi.okx.com`.
2. Unknown site and non-allowlisted base URL fail locally.
3. Every private request includes the Demo header.
4. Read-only check calls account config, balance, and SWAP positions.
5. Read-only event stores codes and status only.
6. Raw credentials, signature headers, full balances, and full positions are absent from returned/persisted audit data.
7. Default startup status keeps order, automation, and cancel disabled.
8. Connectivity smoke requires its own gate and marker.
9. Automatic strategy execution without eligible `DemoRelease` remains blocked.
10. Withdraw and live endpoints remain rejected.

Run the focused tests first and confirm that new expectations fail before implementation.

## Task 2: Add Explicit OKX Site Mapping

Files:

- Modify `alphapilot_control_console/exchange_connectors/okx_demo_client.py`
- Modify `alphapilot_control_console/credential_runtime.py` only if status needs the selected site

Implementation:

1. Define an immutable site-to-REST-domain map.
2. Add `resolve_okx_rest_url(site)`.
3. Keep `global` as the explicit default for backward compatibility.
4. Reject unknown sites and mismatched custom base URLs.
5. Expose selected site and redacted connection metadata without exposing credentials.

## Task 3: Consolidate Private Requests

Files:

- Modify `alphapilot_control_console/exchange_demo_simulation.py`

Implementation:

1. Remove duplicate HMAC, timestamp, urllib, and raw environment credential code.
2. Load credentials only through `load_okx_demo_credentials()`.
3. Resolve the site through the allowlist.
4. Route all private calls through `OkxDemoClient`.
5. Keep a small response adapter only for existing UI contracts.
6. Normalize network, permission, credential, and OKX response failures.
7. Never include full private payloads in persisted events.

## Task 4: Strengthen Read-only Connection Check

Files:

- Modify `alphapilot_control_console/exchange_demo_simulation.py`
- Modify `web/app.js`
- Modify `web/index.html` if new status fields are needed

Implementation:

1. Call account config before balance and positions.
2. Require top-level OKX `code == "0"` for all three calls.
3. Return a redacted summary:
   - site
   - base URL
   - account config status/code
   - balance status/code and currency presence only
   - position status/code and row count only
   - Demo header used
   - checked time
4. Persist only status/code/blocker metadata.
5. Render connection, credential, smoke, and automation states separately.

## Task 5: Harden Connectivity Smoke And Automation Gates

Files:

- Modify `alphapilot_control_console/exchange_demo_simulation.py`
- Modify `alphapilot_control_console/evolution_demo_service.py`
- Modify `alphapilot_control_console/http_app.py` only if a separate smoke endpoint is required
- Modify `scripts/start_okx_demo_console.ps1`

Implementation:

1. Keep default launcher gates off.
2. Set `ALPHAPILOT_OKX_SITE=global` in the launcher.
3. Require `-EnableOrder` for connectivity smoke.
4. Mark smoke events `connectivity_smoke_only`.
5. Exclude smoke events from strategy metrics and promotion evidence.
6. Require `-EnableOrder -EnableAutomation` plus eligible immutable release for strategy automation.
7. Keep cancel separately gated.
8. Preserve idempotency, unknown-state pause, and kill-switch behavior.

## Task 6: Documentation And Operator Flow

Files:

- Modify `README.md`
- Modify the Demo runbook returned by `exchange_demo_simulation.py`

Document:

1. Create a global-site OKX Demo API key with Read + Trade only.
2. Do not enable Withdraw.
3. Prefer an IP whitelist.
4. Start the secure launcher without order flags first.
5. Run read-only check.
6. Restart with `-EnableOrder` for connectivity smoke only.
7. Use `-EnableOrder -EnableAutomation` only when a formal Demo release exists.
8. Credentials are never stored.

## Task 7: Verification

Run:

```powershell
python -m compileall alphapilot_control_console
python -m unittest discover -s tests
python -m alphapilot_control_console.http_app --smoke
node --check web\app.js
git diff --check
```

Also verify:

1. HTML tag balance.
2. Safety scan for credential leakage and forbidden private endpoints.
3. Desktop and mobile Demo-page layout.
4. Default console startup remains safe with no credentials.
5. Secure launcher prompts without echoing values.
6. Runtime status reports global site and all gates accurately.
7. No raw credentials appear in files, SQLite, browser state, process command line, or logs.

## Task 8: Commit And Secure Launch

1. Commit the implementation separately from this plan.
2. Push `origin/main`.
3. Verify local HEAD equals `origin/main` and worktree is clean.
4. Start a visible secure PowerShell launcher for the user to type the three Demo credential values locally.
5. Run the read-only check first.
6. Report exact OKX result codes and blockers without exposing account-private payloads.
7. Do not proceed to a smoke order if the read-only check fails.
