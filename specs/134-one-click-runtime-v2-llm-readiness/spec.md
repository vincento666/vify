# 134 One-Click Runtime V2 LLM Readiness

## Goal

Make the one-click MVP demo seed report explain whether the seeded topology is
ready for runtime-v2 provider-backed LLM demos, without exposing secrets or
pretending mock-safe local config is live-ready.

## Acceptance Criteria

- RED proves the seed manifest lacks `runtimeV2LlmReadiness`.
- The report includes runtime-v2 LLM readiness with direct Workflow/Chatflow
  API binding, Runtime Lab entrypoint binding, Customer Assistant entrypoint
  binding, preferred agent name, provider mode, live readiness, and model config
  ids.
- Mock-safe seeded provider/model reports `providerMode=mock_safe`,
  `liveReady=false`, and `liveProviderRequired=true`.
- The readiness payload is secret-free and does not include API keys.
- Focused one-click seed tests and Ruff pass.

## Non-goals

- Do not create real provider credentials.
- Do not call live LLM providers.
- Do not change frontend behavior.

## Evidence

Evidence lives under
`artifacts/slices/134-one-click-runtime-v2-llm-readiness/134.1/`.
