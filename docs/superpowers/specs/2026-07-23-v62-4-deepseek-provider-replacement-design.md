# AlphaPilot V62.4 DeepSeek Provider Replacement Design

## Status

- Date: 2026-07-23
- Decision: approved approach A
- Scope: replace the active OpenAI provider with DeepSeek; retain Gemini as the independent reviewer and batch provider
- Safety state: credential-free development only; Demo and Live order paths remain outside the AI boundary
- Revision: 2026-07-23 Provider change notice adds five DeepSeek capability aliases, controlled `reasoning_content`/research-tool-call retention, disconnect tests, and the explicit DeepSeek/Gemini credential checkpoint

## Context

V62.4 introduced a provider-neutral `AIOrchestrationService` with OpenAI and Gemini adapters. The user has revised the provider decision: DeepSeek must replace OpenAI. A variable-only rename is not acceptable because the existing OpenAI adapter uses the Responses API, OpenAI-specific aliases, an OpenAI Batch endpoint, and OpenAI audit identities. Keeping those internals while pointing at DeepSeek would make routing, evidence, and cost attribution misleading.

DeepSeek's current OpenAI-compatible interface is Chat Completions at `https://api.deepseek.com/chat/completions`. The active registry will use `deepseek-v4-pro` and `deepseek-v4-flash`; the legacy `deepseek-chat` and `deepseek-reasoner` names will not be introduced.

## Goals

1. Replace the active `openai` provider identity with `deepseek` everywhere in the V62.4 AI boundary.
2. Use `DEEPSEEK_API_KEY` and `GEMINI_API_KEY` only from the dedicated AI Worker process environment.
3. Preserve independent dual-model analysis for strategy hypotheses, failure attribution, architecture review, security review, document analysis, and code review.
4. Preserve local redaction, prompt-injection protection, JSON Schema validation, semantic validation, forbidden-task/tool policy, cost budgets, audit ledgers, circuit breakers, and execution-authority denial.
5. Keep credential-free readiness and Mock Provider tests fully runnable without external calls.
6. Preserve historical batch processing without pretending that DeepSeek supports the existing OpenAI Batch protocol.

## Non-Goals

- No API Key collection through Codex chat, UI, JSON, SQLite, logs, reports, or evidence artifacts.
- No Demo or Live Release approval, ARM, order creation, position management, reconciliation, withdrawal, or risk decision through an LLM.
- No trading exchange private credentials in the AI Worker process.
- No live Provider request during the credential-free implementation checkpoint.
- No compatibility alias that labels DeepSeek traffic as OpenAI.

## Selected Architecture

### Provider Set

The active provider set becomes:

| Provider | Primary use | Credential variable | External protocol |
| --- | --- | --- | --- |
| `deepseek` | synchronous research, reasoning, coding review, fast summaries | `DEEPSEEK_API_KEY` | `POST /chat/completions` |
| `gemini` | independent review, multimodal review, fallback, historical batch | `GEMINI_API_KEY` | existing Gemini GenerateContent and Batch APIs |

`openai` is removed from the active composition root, registry allowlist, router aliases, readiness report, smoke sequence, budget provider map, Mock Provider allowlist, and active adapter exports.

### DeepSeek Adapter

`DeepSeekAdapter` implements the existing provider adapter protocol and uses the repository's raw HTTP transport. Business modules remain unable to import a Provider SDK.

Request behavior:

- Endpoint: `https://api.deepseek.com/chat/completions`.
- Authentication: `Authorization: Bearer <process-only credential>`.
- Model ID: resolved only through `AIModelRegistry`.
- Output limit: mapped from `AIRequest.token_ceiling` to `max_tokens`.
- Structured output: `response_format={"type":"json_object"}`.
- Prompt envelope: explicitly requires a JSON object matching the supplied schema and includes the word `JSON`.
- Tool execution: no Provider tools are sent. AlphaPilot's research-tool names remain local policy metadata only.
- Persistence: request payloads and credentials are not persisted; only redacted hashes, status, usage, cost estimate, latency, and provider request identity may enter the audit ledger.

Response behavior:

- Read `choices[0].message.content`.
- Preserve `choices[0].message.reasoning_content` in the in-process `AIResponse` so a caller can return it unchanged for the same bounded research tool-call exchange.
- Preserve returned research `tool_calls` in the in-process response, but do not execute them inside the Provider adapter or orchestration service.
- Persist only the SHA-256 of non-empty `reasoning_content` in the audit ledger. Do not persist raw reasoning text, because it can reflect redacted-but-still-internal research input.
- Reject malformed tool calls and fail closed if a returned tool name is not on the existing research allowlist. Trading, risk, position, reconciliation, Approval, ARM, Live, and Withdraw tools remain forbidden before Provider invocation.
- Parse the content as one JSON object.
- Run the existing local JSON Schema and business-semantic validators before accepting the response.
- Treat disconnects, incomplete streams, empty final content, invalid JSON, schema failure, semantic failure, missing Artifact evidence, or Hash mismatch as non-accepted results.
- Treat missing choices, empty content, malformed JSON, schema violations, and transport errors as fail-closed Provider errors.

### Model Registry

The registry aliases become:

- `deepseek_reasoning_primary` -> `deepseek-v4-pro`
- `deepseek_reasoning_critical` -> `deepseek-v4-pro`
- `deepseek_coding_primary` -> `deepseek-v4-pro`
- `deepseek_fast` -> `deepseek-v4-flash`
- `deepseek_fast_reasoning` -> `deepseek-v4-flash`
- existing Gemini aliases remain

The registry remains the only place containing model names. Conservative cache-miss pricing is used for local budget estimation. No key, endpoint override, or secret-bearing field is allowed in the registry.

### Routing

- Dual independent analysis: DeepSeek first, Gemini second.
- Multimodal analysis: Gemini first, DeepSeek second using only the locally extracted/redacted text representation.
- Fast summaries: DeepSeek with Gemini fallback.
- Historical batch: Gemini Batch only.
- Provider smoke order: DeepSeek-only, Gemini-only, then DeepSeek/Gemini dual review.

The system will not implement a fake `DeepSeekBatchAdapter` or point DeepSeek at OpenAI `/v1/files` and `/v1/batches` endpoints. A future DeepSeek Batch adapter requires separately verified official support and a new versioned design.

### Readiness and Worker Identity

Credential readiness requires exactly these external Provider variables:

- `DEEPSEEK_API_KEY`
- `GEMINI_API_KEY`

The report remains value-blind and only emits configured booleans. The fixed redacted smoke input is unchanged, so its hash must remain stable unless the redaction or fixture contract changes. Worker identity changes its allowed-provider projection to `deepseek` and `gemini`, which intentionally produces a new identity hash.

### Budget Policy

- Provider smoke maximum output remains 512 tokens per Provider call.
- The total orchestration request ceiling remains USD 0.05.
- Provider daily limits remain versioned in `config/ai_budget_policy.json` and are renamed from `openai` to `deepseek`.
- DeepSeek cost estimates use registry pricing and remain secondary to the hard request ceiling.

## Migration

1. Add failing tests for DeepSeek request/response behavior, routing, readiness, smoke order, registry, budgets, and boundary scans.
2. Add `DeepSeekAdapter` and update the active composition root.
3. Replace active OpenAI aliases and provider identifiers with DeepSeek identifiers.
4. Remove the OpenAI sync and Batch adapters from active exports and composition. Git history remains the historical record; no runtime compatibility shim is retained.
5. Route historical batch work exclusively to Gemini Batch.
6. Update documentation and CLI descriptions from OpenAI/Gemini to DeepSeek/Gemini.
7. Re-run all AI tests, the full Console suite, compile checks, diff checks, and explicit boundary scans.

## Failure and Rollback Behavior

- Missing either Provider credential: `provider_credentials_required_deepseek_gemini`; no external call.
- DeepSeek unavailable: circuit breaker and configured Gemini fallback apply only to registered research tasks.
- Dual-model disagreement: preserve the existing human-review requirement.
- Batch request: use Gemini Batch; fail closed if Gemini credentials or batch capability are unavailable.
- Rollback: revert the replacement commit. Never relabel DeepSeek traffic as OpenAI to obtain a partial rollback.

## Verification

### Focused tests

- DeepSeek adapter request URL, headers, body, token ceiling, JSON mode, response parsing, usage and cost.
- DeepSeek thinking responses preserve non-empty `reasoning_content` in process, expose its Hash in audit metadata, and never write raw reasoning to SQLite.
- DeepSeek research tool-call responses preserve valid allowlisted tool-call envelopes and reject malformed or forbidden tool calls.
- Provider disconnects, empty choices, missing final content, invalid JSON, and partial responses fail closed.
- Missing `DEEPSEEK_API_KEY` fails before transport.
- DeepSeek model identities reject non-DeepSeek adapters and vice versa.
- Task routes resolve only DeepSeek/Gemini aliases.
- Historical batch resolves only `gemini_batch`.
- Readiness reports only `DEEPSEEK_API_KEY` and `GEMINI_API_KEY` names and never values.
- Smoke order is DeepSeek-only, Gemini-only, dual.
- Fixed smoke input hash stays unchanged.
- Mock Provider supports DeepSeek and Gemini.
- Redaction, prompt injection, forbidden task/tool, cost budget, schema and semantic validation tests remain green.

### Regression and boundary checks

- Full `pytest` suite.
- `python -m compileall alphapilot_control_console`.
- `git diff --check`.
- No business module imports Provider SDKs or concrete adapters.
- No execution, order, risk, position, approval, ARM, reconciliation, Live, or Withdraw module imports AI orchestration.
- No raw Provider or exchange credential values appear in source, logs, SQLite, or generated evidence.
- Credential-free readiness remains `provider_credentials_required_deepseek_gemini` with `externalRequestExecuted=false`, `runtimeArmed=false`, and `withdrawEnabled=false`.

## Acceptance Criteria

1. `OPENAI_API_KEY` is no longer required or reported.
2. `DEEPSEEK_API_KEY` and `GEMINI_API_KEY` are the only external AI Provider credential names.
3. Active routes, aliases, audit provider names, budgets, mocks, and smoke checks use `deepseek` and `gemini`.
4. No active OpenAI adapter or Batch route remains.
5. DeepSeek uses Chat Completions with local structured-output validation.
6. Historical batch remains available through Gemini Batch.
7. All local tests pass without real Provider credentials or external calls.
8. The checkpoint stops at `provider_credentials_required_deepseek_gemini`.
9. Demo and Live order paths remain LLM-free; Live, Withdraw, Approval, and ARM state are unchanged.

## Implementation Result

Implemented on `feature/v13.27.1.62.4-ai-orchestration-core` with these
truthful runtime boundaries:

- synchronous adapters: DeepSeek and Gemini;
- historical provider Batch: Gemini only;
- local bounded queues remain available for non-provider batch orchestration;
- credential variables: `DEEPSEEK_API_KEY` and `GEMINI_API_KEY` only;
- no-credential checkpoint:
  `provider_credentials_required_deepseek_gemini`;
- DeepSeek `reasoning_content` and research tool-call envelopes are validated
  in process; only reasoning hashes may enter the audit ledger;
- external provider smoke has not been run without process credentials;
- Demo, Live, Risk, Order, Position, Approval, ARM, reconciliation, and
  Withdraw behavior was not changed by this provider replacement.
