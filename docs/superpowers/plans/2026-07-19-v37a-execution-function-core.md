# V37A Execution Function Core Implementation Plan

> Execute in the isolated Console worktree. Do not connect a real account or submit a real order during implementation or tests.

## Task 1: Baseline and failing contract tests

Run existing unified execution, Demo, Live safety, HTTP, and startup recovery tests. Add failing tests for the consolidated status projection, redaction, stable blocker codes, and Live default-OFF behavior.

## Task 2: Add execution-control read model

Build a small backend projector over existing stores and controllers. Avoid duplicating execution logic. Normalize Demo and Live into one schema while preserving environment-specific source state.

## Task 3: Add idempotent action facade

Wrap existing safe actions with request IDs, bounded action names, conflict handling, and audit metadata. Do not add credential persistence, Withdraw, or a bypass around Release/Approval/ARM gates.

## Task 4: Strengthen recovery and reconciliation summaries

Expose desired-versus-process state, credential readiness, ARM state, last heartbeat, next evaluation, unknown orders, orphan positions, and kill-switch reasons. Add regression tests for restart without auto-ARM and timeout without duplicate submission.

## Task 5: Add Workflow Validation Demo fixture

Use fakes to validate the complete diagnostic lifecycle and statistical isolation. No exchange network call is required for automated tests.

## Task 6: Add minimal Chinese operator UI

Render the consolidated API into compact, scan-friendly bands. Use existing icon library and styles. Keep evidence collapsed and present only actionable blockers and next steps. Do not redesign unrelated pages.

Build Demo and Live from the same original AlphaPilot terminal components and status schema while keeping environment adapters, ledgers, credentials, approvals, ARM state, risk profiles, and kill switches isolated. Demo should expose extra diagnostics; Live should be operationally simpler and default OFF. Use FinceptTerminal only as a high-level information-architecture reference under the documented license boundary. Do not copy or import its code or assets.

## Task 7: Browser and regression verification

Run targeted tests, full Console tests, compileall, safety scan, whitespace checks, and browser checks at desktop and 390 px. Verify no secrets in DOM or JSON and Live remains disabled.

## Task 8: Documentation and publication

Update README and Docs, create closeout artifacts, commit locally, and publish only after all checks pass under the user's explicit long-workflow authorization.
