# 132 Runtime V2 Provider-Backed LLM Binding

## Goal

Wire Workflow/Chatflow runtime v2 LLM nodes into the existing provider-backed
Workflow LLM completer so `/runs-v2` can use configured live agents, model
parameters, fallback models, and persisted debug/usage records.

## Acceptance Criteria

- RED proves `/api/v1/workflows/{id}/runs-v2` still returns `LLM mock:` despite
  a configured non-mock provider-backed agent.
- Workflow `/runs-v2` calls the provider-backed client when a live agent exists
  and persists `__debug` / `__usage` into node outputs and completed-node events.
- Node-level LLM options such as `model`, `temperature`, `maxTokens`, `topP`,
  `responseFormat`, `stopSequences`, and `seed` are forwarded to the provider
  request.
- Chatflow `/runs-v2` records fallback attempts from provider failure into
  runtime node outputs without leaking credentials.
- Existing no-provider runtime-v2 tests keep deterministic mock fallback.
- Focused integration, legacy LLM regression, runtime-v2 regression, and Ruff
  pass.

## Non-goals

- Do not call a real network LLM in this slice.
- Do not implement runtime-v2 LLM tool calling.
- Do not alter frontend behavior or visual layout.

## Evidence

Evidence lives under
`artifacts/slices/132-runtime-v2-provider-backed-llm-binding/132.1/`.
