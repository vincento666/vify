# 133 Demo Entrypoint Runtime V2 LLM Binding

## Goal

Ensure Runtime Lab and Customer Assistant Chatflow SOP runtime-v2 entrypoints
reuse the provider-backed Workflow LLM completer, not only the direct
Workflow/Chatflow `/runs-v2` APIs.

## Acceptance Criteria

- RED proves Runtime Lab Chatflow SOP runtime-v2 still returns deterministic
  `LLM mock:` output when a non-mock provider-backed preferred agent exists.
- RED proves Customer Assistant Chatflow SOP runtime-v2 still returns
  deterministic `LLM mock:` output through the production SOP adapter helper.
- Runtime Lab binds a runtime-v2 LLM completer resolver using its existing
  `RUNTIME_LAB_AIRLINE_LLM_AGENT_NAME`.
- Customer Assistant binds a runtime-v2 LLM completer resolver using its
  existing `CUSTOMER_ASSISTANT_LLM_AGENT_NAME`.
- Existing mock/fallback behavior remains unchanged when no preferred live
  provider agent exists.
- Focused integration/e2e, related regressions, and Ruff pass.

## Non-goals

- Do not call a real network LLM.
- Do not change runtime-v2 core behavior.
- Do not change frontend layout or browser behavior.

## Evidence

Evidence lives under
`artifacts/slices/133-demo-entrypoint-v2-llm-binding/133.1/`.
