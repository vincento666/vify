# Spec 089: Workflow LLM Fallback Observability

## Goal

Expose deterministic, redacted runtime evidence when a Workflow/Chatflow LLM node
falls back from its primary model to a configured fallback model.

## Acceptance Criteria

- Successful fallback calls set the effective debug model to the fallback model.
- LLM debug output includes a fallback attempt trail with primary failure and
  fallback success.
- Fallback failure reasons use the existing provider-error sanitizer and do not
  expose raw network stack traces or secrets.
- Existing usage projection and node events remain unchanged.

## Non-goals

- Do not call a live LLM provider in this slice.
- Do not change frontend observability panels.
- Do not add new provider configuration semantics beyond the existing
  `fallbackModel` / `fallback_model` support.

## Evidence

Evidence lives under
`artifacts/slices/089-workflow-llm-fallback-observability/089.1/`.
