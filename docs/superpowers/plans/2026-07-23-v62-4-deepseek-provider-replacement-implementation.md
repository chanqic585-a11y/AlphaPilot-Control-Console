# AlphaPilot V62.4 DeepSeek Provider Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the active OpenAI provider in the V62.4 research-only AI orchestration boundary with DeepSeek while preserving Gemini as the independent reviewer and sole batch provider.

**Architecture:** Keep provider-specific HTTP and response parsing behind `AIOrchestrationService`. Add a native DeepSeek Chat Completions adapter, route all synchronous DeepSeek work through versioned registry aliases, retain Gemini Batch for historical jobs, and keep local schema/semantic validation authoritative. No AI component is added to order, risk, position, reconciliation, Approval, ARM, Live, or Withdraw paths.

**Tech Stack:** Python 3.12, pytest/unittest, raw HTTP transport, JSON Schema, SQLite audit ledgers, versioned JSON configuration.

## Global Constraints

- Do not request, load, persist, log, or transmit a real provider credential during this implementation.
- Credential names after migration are exactly `DEEPSEEK_API_KEY` and `GEMINI_API_KEY`.
- DeepSeek uses `https://api.deepseek.com/chat/completions`; it does not reuse OpenAI Responses or Batch protocol code.
- Active model aliases are `deepseek_reasoning_primary`, `deepseek_coding_primary`, and `deepseek_fast`.
- Historical batch jobs route only to `gemini_batch` until separately verified DeepSeek Batch support exists.
- Keep the fixed redacted smoke fixture and hash unchanged.
- Provider output remains untrusted until JSON parsing, JSON Schema validation, and business semantic validation all pass.
- Do not modify Demo, Live, order, position, risk, reconciliation, Approval, ARM, or Withdraw behavior.
- Do not create a compatibility alias that labels DeepSeek traffic as `openai`.

---

## Task 1: Add the DeepSeek synchronous adapter

**Files:**
- Create: `alphapilot_control_console/ai_orchestration/provider_adapters/deepseek_adapter.py`
- Modify: `alphapilot_control_console/ai_orchestration/provider_adapters/__init__.py`
- Modify: `tests/test_ai_provider_adapters.py`

- [ ] **Step 1: Replace the OpenAI adapter tests with DeepSeek contract tests**

Cover the endpoint, Bearer authentication, process-only credential lookup, provider identity check, JSON-only request, schema-bearing prompt, usage parsing, cost computation, and fail-closed malformed responses. The primary request assertion is:

```python
self.assertEqual(call["url"], "https://api.deepseek.com/chat/completions")
self.assertEqual(call["headers"]["Authorization"], "Bearer process-only")
self.assertEqual(call["json_body"]["model"], "deepseek-v4-pro")
self.assertEqual(call["json_body"]["response_format"], {"type": "json_object"})
self.assertIn("JSON", call["json_body"]["messages"][0]["content"])
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```powershell
& 'D:\Codex-Workspace\AlphaPilot-Control-Console\.venv\Scripts\python.exe' -m pytest -q tests\test_ai_provider_adapters.py
```

Expected: collection or assertion failure because `DeepSeekAdapter` does not yet exist.

- [ ] **Step 3: Implement the smallest native DeepSeek adapter**

The adapter must construct a stateless JSON-only Chat Completions request and parse only `choices[0].message.content`:

```python
class DeepSeekAdapter:
    provider = "deepseek"

    def invoke(self, identity: ModelIdentity, request: AIRequest) -> AIResponse:
        credential = str(self._api_key or os.environ.get("DEEPSEEK_API_KEY") or "").strip()
        if not credential:
            raise ProviderUnavailableError("DEEPSEEK_API_KEY is not configured in process memory")
        if identity.provider != self.provider:
            raise ProviderResponseError("DeepSeek adapter received another provider identity")
        payload = self._transport.post_json(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {credential}"},
            json_body=build_deepseek_chat_body(identity, request),
            timeout_seconds=request.timeout_seconds,
        )
        return parse_deepseek_response(identity, payload)
```

Do not persist `reasoning_content`, credentials, raw headers, or unvalidated response text.

- [ ] **Step 4: Export `DeepSeekAdapter` and run focused GREEN**

Run the same focused test. Expected: all adapter tests pass.

- [ ] **Step 5: Commit the adapter slice**

```powershell
git add alphapilot_control_console/ai_orchestration/provider_adapters tests/test_ai_provider_adapters.py
git commit -m "Add native DeepSeek orchestration adapter"
git push
```

---

## Task 2: Migrate registry, routing, budgets, and synchronous orchestration

**Files:**
- Modify: `config/ai_model_registry.json`
- Modify: `config/ai_budget_policy.json`
- Modify: `config/ai_prompt_registry.json`
- Modify: `alphapilot_control_console/ai_orchestration/model_registry.py`
- Modify: `alphapilot_control_console/ai_orchestration/task_router.py`
- Modify: `alphapilot_control_console/ai_orchestration/bootstrap.py`
- Modify: `alphapilot_control_console/ai_orchestration/provider_adapters/mock_adapter.py`
- Modify: `tests/test_ai_model_registry.py`
- Modify: `tests/test_ai_repository_config.py`
- Modify: `tests/test_ai_orchestration_service.py`
- Modify: `tests/test_ai_single_route_fallback.py`
- Modify: `tests/test_ai_mock_provider.py`
- Modify: `tests/test_ai_budget_and_circuit.py`
- Modify: `tests/test_ai_runtime_bootstrap.py`

- [ ] **Step 1: Change tests to require DeepSeek identities and routes**

Assert the exact active aliases and providers:

```python
self.assertEqual(
    set(registry.aliases()),
    {
        "deepseek_reasoning_primary",
        "deepseek_coding_primary",
        "deepseek_fast",
        "gemini_reasoning_primary",
        "gemini_multimodal_primary",
        "gemini_fast",
        "gemini_batch",
    },
)
```

Assert that strategy hypothesis and failure attribution use DeepSeek first and Gemini second, multimodal uses Gemini first with DeepSeek text fallback, and single-model summaries use DeepSeek with Gemini fallback.

- [ ] **Step 2: Run the synchronous orchestration tests and confirm RED**

Run:

```powershell
& 'D:\Codex-Workspace\AlphaPilot-Control-Console\.venv\Scripts\python.exe' -m pytest -q tests\test_ai_model_registry.py tests\test_ai_repository_config.py tests\test_ai_orchestration_service.py tests\test_ai_single_route_fallback.py tests\test_ai_mock_provider.py tests\test_ai_budget_and_circuit.py tests\test_ai_runtime_bootstrap.py
```

Expected: failures show the old OpenAI aliases, provider allowlist, routes, and composition root.

- [ ] **Step 3: Replace active registry and budget configuration**

Use versioned entries with positive pricing values:

```json
"deepseek_reasoning_primary": {
  "provider": "deepseek",
  "modelId": "deepseek-v4-pro",
  "capabilities": ["reasoning", "structured_output"],
  "pricingUsdPerMillionTokens": {"input": 0.435, "output": 0.87}
}
```

Add coding and fast aliases, remove all active OpenAI aliases, and rename the provider budget map key to `deepseek`.

- [ ] **Step 4: Migrate the registry allowlist, router, composition root, and mock provider**

The composition root must contain only:

```python
sync_adapters = {
    "deepseek": DeepSeekAdapter(),
    "gemini": GeminiAdapter(),
}
```

Keep task semantics and independent-review order unchanged apart from provider replacement.

- [ ] **Step 5: Run the focused tests and confirm GREEN**

Run the Step 2 command. Expected: all listed tests pass.

- [ ] **Step 6: Commit the registry and routing slice**

```powershell
git add config alphapilot_control_console/ai_orchestration tests
git commit -m "Route V62.4 research AI through DeepSeek and Gemini"
git push
```

---

## Task 3: Make batch, readiness, and smoke behavior truthful

**Files:**
- Modify: `alphapilot_control_console/ai_orchestration/provider_adapters/batch_adapters.py`
- Modify: `alphapilot_control_console/ai_orchestration/bootstrap.py`
- Modify: `alphapilot_control_console/ai_orchestration/provider_readiness.py`
- Modify: `alphapilot_control_console/ai_orchestration/provider_smoke.py`
- Modify: `alphapilot_control_console/ai_orchestration/compliance.py`
- Delete: `alphapilot_control_console/ai_orchestration/provider_adapters/openai_adapter.py`
- Modify: `tests/test_ai_batch_provider_adapters.py`
- Modify: `tests/test_ai_batch_service.py`
- Modify: `tests/test_ai_batch_ledger.py`
- Modify: `tests/test_ai_provider_readiness.py`
- Modify: `tests/test_ai_provider_smoke.py`
- Modify: `tests/test_ai_orchestration_boundaries.py`

- [ ] **Step 1: Write tests for Gemini-only batch and DeepSeek readiness/smoke**

Require:

```python
self.assertEqual(report["requiredEnvironmentVariables"], ["DEEPSEEK_API_KEY", "GEMINI_API_KEY"])
self.assertEqual(report["workerIdentity"]["allowedProviders"], ["deepseek", "gemini"])
self.assertEqual(report["providerConfigured"], {"deepseek": False, "gemini": False})
```

Provider smoke task order must be `provider_smoke_deepseek`, `provider_smoke_gemini`, then `provider_smoke_dual`. Batch submission must produce one Gemini job and preserve idempotency, ledger reconciliation, and invalid-output handling.

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```powershell
& 'D:\Codex-Workspace\AlphaPilot-Control-Console\.venv\Scripts\python.exe' -m pytest -q tests\test_ai_batch_provider_adapters.py tests\test_ai_batch_service.py tests\test_ai_batch_ledger.py tests\test_ai_provider_readiness.py tests\test_ai_provider_smoke.py tests\test_ai_orchestration_boundaries.py
```

Expected: failures show OpenAI Batch, old credential names, old smoke task names, and the old worker identity.

- [ ] **Step 3: Remove the active OpenAI sync and Batch implementations**

Delete the OpenAI adapter file, remove `OpenAIBatchAdapter` and its parser, remove their exports/imports, and leave only the Gemini Batch adapter. Preserve OpenAI and DeepSeek SDK names in the compliance denylist because direct provider SDK imports remain forbidden outside adapters.

- [ ] **Step 4: Update credential-free readiness and provider smoke**

Readiness must report only variable names and boolean presence. It must never include credential values. The fixed smoke hash remains:

```text
sha256:9868eccb0254a18d5a90bd2b6d5c6138b105395dbaf5133871273a5c2ebc96df
```

Provider smoke output max is 512 tokens and the orchestration cost ceiling remains USD 0.05.

- [ ] **Step 5: Run focused tests and confirm GREEN**

Run the Step 2 command. Expected: all listed tests pass.

- [ ] **Step 6: Commit the truthful runtime slice**

```powershell
git add alphapilot_control_console/ai_orchestration config tests
git commit -m "Make DeepSeek readiness and Gemini batch routing explicit"
git push
```

---

## Task 4: Validate boundaries, documentation, and credential checkpoint

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-07-23-v62-4-deepseek-provider-replacement-design.md` only if an implementation-result note is needed
- Modify: `D:/Codex-Workspace/踩坑日志.txt`

- [ ] **Step 1: Update operator-facing documentation**

Document DeepSeek + Gemini, exact environment variable names, Gemini-only historical Batch, no provider SDK calls from business modules, no provider credentials in the AI worker evidence, and the final `provider_credentials_required` checkpoint. Do not document live credential values or copy-paste examples containing secrets.

- [ ] **Step 2: Run all focused AI tests**

Run:

```powershell
$aiTests = Get-ChildItem -LiteralPath tests -Filter 'test_ai_*.py' | ForEach-Object FullName
& 'D:\Codex-Workspace\AlphaPilot-Control-Console\.venv\Scripts\python.exe' -m pytest -q @aiTests
```

Expected: all AI tests pass.

- [ ] **Step 3: Run the full repository validation**

Run:

```powershell
& 'D:\Codex-Workspace\AlphaPilot-Control-Console\.venv\Scripts\python.exe' -m pytest -q
& 'D:\Codex-Workspace\AlphaPilot-Control-Console\.venv\Scripts\python.exe' -m compileall -q alphapilot_control_console
git diff --check
```

Expected: full suite passes, compileall emits no errors, and diff check is clean.

- [ ] **Step 4: Run boundary and credential scans**

Verify that active code/config has no OpenAI provider, alias, credential, adapter, or Batch route. Permitted residual references are the design migration history, direct-SDK denylist, and negative boundary tests. Also scan for provider key values and confirm no secrets are present.

- [ ] **Step 5: Generate the no-credential readiness checkpoint**

Clear provider variables only in the validation shell and run:

```powershell
Remove-Item Env:DEEPSEEK_API_KEY,Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
& 'D:\Codex-Workspace\AlphaPilot-Control-Console\.venv\Scripts\python.exe' -m alphapilot_control_console.ai_orchestration.provider_readiness --repository-root .
& 'D:\Codex-Workspace\AlphaPilot-Control-Console\.venv\Scripts\python.exe' -m alphapilot_control_console.ai_orchestration.provider_smoke --repository-root .
```

Expected: readiness reports both providers unconfigured; smoke exits with the documented provider-credentials-required code without making an external request. Runtime authority fields remain false.

- [ ] **Step 6: Final self-review**

Compare the diff against the approved design. Confirm no Demo/Live/order/risk/position/reconciliation/Approval/ARM/Withdraw files changed, no compatibility shim remains, no fake DeepSeek Batch exists, and no validation result was overstated.

- [ ] **Step 7: Commit, push, and verify remote identity**

```powershell
git add README.md docs alphapilot_control_console config tests
git commit -m "Complete V62.4 DeepSeek provider replacement"
git push
git rev-parse HEAD
git ls-remote origin refs/heads/feature/v13.27.1.62.4-ai-orchestration-core
git status --short --branch
```

Expected: local and remote SHA match and the worktree is clean.

## Completion State

Stop at:

```text
provider_credentials_required
```

Report only the two required environment variable names, fixed redacted smoke hash, max output/cost budgets, AI worker identity, passed security tests, and the post-provisioning detection command with expected smoke order. Do not ask the user to paste credentials into Codex, UI, JSON, SQLite, logs, or evidence files.
