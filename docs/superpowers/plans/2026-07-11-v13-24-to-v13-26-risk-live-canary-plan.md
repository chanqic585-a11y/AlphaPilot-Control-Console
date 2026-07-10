# AlphaPilot V13.24-V13.26 Implementation Plan

1. Add a shared immutable RiskProfile schema, validation, defaults, registry
   persistence, activations, and rollback lineage in Quant Engine.
2. Bind Forward, Demo, and Live candidate packages to RiskProfile identity and
   hash while retaining compatibility defaults.
3. Add the Control Console RiskProfile store, API, presets, activation history,
   and portfolio-risk evaluation.
4. Add a compact Chinese RiskProfile control panel to the Live page.
5. Validate, document, commit, tag, and push V13.24.
6. Add process-only OKX Live credentials and an allowlisted Live client with no
   Withdraw support.
7. Add a restart-safe Live Canary store and engine with idempotency,
   reconciliation, attached protection, circuit breakers, and kill switch.
8. Add fail-closed Live Canary API/status UI and a separate secure launcher.
9. Validate, document, commit, tag, and push V13.25 without placing an order.
10. Add terminal Demo/Live execution outcome capture and checksum exports.
11. Add Quant Engine import, quarantine, attribution, and offline feedback
    reporting for those outcomes.
12. Add the Console evidence summary, complete end-to-end validation, then
    commit, tag, and push V13.26.
