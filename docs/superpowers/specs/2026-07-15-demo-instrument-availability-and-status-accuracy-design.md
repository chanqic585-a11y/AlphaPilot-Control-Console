# Demo Instrument Availability and Status Accuracy Design

## Goal

Prevent an OKX Demo-only unavailable instrument from pausing every strategy, and make the console distinguish queued work, active work, current runtime state, and historical failures.

## Confirmed Failure

At 2026-07-15 03:00 Beijing time, a valid public-market signal selected `TRUMP-USDT-SWAP`. OKX Demo rejected the order with `sCode=51001` because the instrument was not available to the Demo account. The generic rejection path paused all new entries. The same condition previously occurred for `BSB-USDT-SWAP`.

The backtest page also grouped `queued`, `running`, and `paused` as “运行中”. The live API state was 28 queued and 2 running, while the page displayed 30 running.

## Design

1. Add the official read-only `GET /api/v5/account/instruments?instType=SWAP` endpoint to the Demo client allowlist.
2. Load the Demo account's available SWAP instrument IDs once per closed-candle execution batch.
3. Remove unavailable instruments before arbitration and order submission. Preserve them in the batch audit as `demo_instrument_unavailable` rejections.
4. Treat an order response whose only exchange rejection code is `51001` as a terminal, non-fatal instrument-availability rejection. Record the rejected order and continue to the next selected signal. Do not increment portfolio exposure or created-order counts.
5. Keep every unknown rejection, network ambiguity, order-state ambiguity, risk failure, and reconciliation mismatch fail-closed. Those conditions still pause new entries.
6. Split the strategy summary into separate queued and actively running counts. Paused items remain visible but do not count as actively running.
7. Label the Demo automatic-execution headline as current state. Show the last blocked heartbeat separately with its timestamp and translated reason so a recovered runtime does not look currently blocked.
8. Keep immutable workflow versions for automation and audit, but use the Quant
   projection's `currentFamilyItems` for user-facing passed/failed/blocked
   counts. Old attempts remain in history and must not accumulate as separate
   failed strategies.

## Safety Boundary

- Demo credentials remain process-only/local-vault controlled and are never rendered or logged.
- Every private request keeps `x-simulated-trading: 1`.
- No Withdraw endpoint is added.
- No live execution gate is changed.
- Immutable Demo Release and risk-envelope checks remain mandatory.
- A `51001` skip never counts as strategy evidence, a successful order, or a closed sample.

## Verification

- Unit test the account-instruments request and Demo header.
- Unit test that `51001` records a rejection without pausing.
- Unit test that another rejection still pauses.
- Batch test that unsupported instruments are filtered and supported signals continue.
- Verify the workflow API reports queued and running separately and the UI uses those separate buckets.
- Run the complete Python test suite and a local HTTP smoke check without exposing credentials.
