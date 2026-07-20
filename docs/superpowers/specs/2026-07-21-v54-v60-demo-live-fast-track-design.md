# V54-V60 Demo Activation and Live Fast-Track Design

## Status

- Design approval: approved by the user on 2026-07-21.
- Authoritative requirements: `AlphaPilot-Docs/prompts/AlphaPilot_V54-V60_Demo_Activation_Low_Latency_Adjustable_Risk_1000USDT_Live_FastTrack_Master_Prompt_CN.md`.
- Baseline Console commit: `6e8026eb0bf87f4f813c6deabd1fd5cf9fcdf4a6`.
- Baseline Quant commit: `7ad720b864d551501a7ba3a07e43019f46b638a7`.
- Baseline evidence ZIP SHA-256: `1bfb99554b57dc1a623d657e23c8f583ed104ed49a8d878e38bb924645076a56`.

## Approval Semantics

The user's approval authorizes implementation of V54-V60 and exact approval of the already frozen TOP200 Demo identity after mechanical verification:

- Release ID: `provisional_research_demo_top200_1fc1e9895d79de78e457bc9c`
- Release hash: `provisional_demo_release_96aa2aa4bdb320e91745474f287dda9e4836b8a901910f252bcf447d718010d0`
- Risk overlay hash: `risk_overlay_7221d23144dcd0a357136f6e9587a505d81c86439e223457d2d7393d287b8218`
- Execution intersection hash: `demo_execution_intersection_4285a3e6dd2155945b6498c130e5a99a9943f7503007b02ccbbed66e1e76960d`
- Approval request hash: `exact_release_approval_request_d3e44900174219d0afaaf2ccf01e6bff97a7f41c72198f175a0ce8a4d2b98091`

Approval is append-only and hash-bound. Demo ARM is a separate audited action and may only occur after exact approval, runtime credentials, universe readiness, and risk checks pass.

Future Live Release and Live Risk Overlay hashes do not exist yet. They cannot be preapproved by this design approval. V59/V60 must stop at `blocked_waiting_exact_live_release_approval` after generating those exact identities.

## Architecture

V54-V60 extends the V53 system additively:

1. **Evidence and identity plane** verifies the V53 ZIP, release-to-HEAD execution diff, order-count scope, component matchability, and all immutable hashes.
2. **Demo control plane** records exact approval and ARM overlays without mutating the frozen Release.
3. **Demo execution plane** uses the dynamic TOP200 universe, prewarmed public market state, closed-candle scheduling, stale-signal fail-closed checks, and isolated Demo ledgers.
4. **Versioned policy plane** treats latency, runtime risk, strategy parameters, capacity, and switching as hashable policy objects. Risk reductions may apply to new orders immediately; risk increases require a new approval identity.
5. **Research factory plane** starts bounded, auditable background campaigns and projects real progress. It never fabricates a pass or promotes a candidate automatically.
6. **Live plane** is physically and logically isolated from Demo. It has separate credentials, environment contracts, approvals, ledgers, kill switches, and release identities. Withdraw and transfers are absent.
7. **Projection plane** keeps Strategy, Demo, and Live pages small. Normal states are terse; errors expose a single actionable next step. Hashes and gates remain collapsed by default.

## Non-Negotiable Boundaries

- No Withdraw or transfer API.
- No raw credential persistence or credential output.
- No mutation of immutable Release artifacts.
- No synthetic signal counted as strategy evidence.
- No automatic Release approval.
- No Live ARM or Live order before exact Live Release and Risk hashes receive a later explicit approval.
- No stale signal order. A signal beyond the active latency profile fails closed.
- No forced strategy pass, no OOS leakage, and no retrospective gate changes.
- Demo and Live ledgers, approvals, keys, and runtime states remain separate.

## Completion State

The implementation may complete Demo activation and Demo operation when all mechanical gates pass. The maximum safe completion state for Live in this approval is:

`blocked_waiting_exact_live_release_approval`

with the exact Live Release hash, Risk Overlay hash, approval request, tests, and evidence package produced.
