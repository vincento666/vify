# 072 Plan

## Slices

1. Live gate harness
   - Config/env loading.
   - Model pool ordering and explicit overrides.
   - Artifact rendering and redaction.
   - Default skip behavior.

2. Customer assistant live categories
   - Main runtime task-recognition accuracy through `CustomerAssistantService`.
   - Two-Stage primary recommendation through the real `two_stage_runtime` seam.
   - Restricted ReAct worker through a live OpenAI-compatible tool-call model.

3. Acceptance and UAT
   - `tests/acceptance/test_customer_assistant_live_react_acceptance.py`.
   - Browser UAT records the customer assistant panel route and confirms the
     live gate is opt-in from local evidence when no live key is present.

## Implementation Notes

- Reuse `ProviderBackedOpenAIChatClient`, `OpenAIChatRequestBuilder`, and
  `OpenAIAdapterParser`.
- Do not add live calls to default unit, integration, contract, e2e, or CI
  paths.
- The live runner may try the model pool sequentially and record per-model
  attempts before failing a category.
