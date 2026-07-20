# V47 Demo Runtime Truth Audit Implementation Plan

1. Add tests for redacted credential-source classification and sidecar fields.
2. Add tests for immutable legacy release projection and hash preservation.
3. Add tests for compatibility and scan-funnel artifact generation from fixture SQLite stores.
4. Implement the offline audit generator with explicit input and output paths.
5. Run it against the current local Demo stores in read-only mode.
6. Run targeted and full tests, compile checks, safety scans, and `git diff --check`.

Real Demo private-write smoke is not part of this plan and remains separately gated.
