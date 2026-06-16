# Spec 092: Workflow LLM Fallback Debug Panel

## Goal

Surface the structured LLM fallback evidence from runtime v2 workflow node
outputs in the canvas debug dock, so demo operators can explain primary model
failure and fallback success without opening raw JSON.

## Acceptance Criteria

- Workflow node debug helpers format `outputs.__debug.llm.fallback` into a
  concise human-readable evidence string.
- Evidence includes request model, fallback model, per-attempt status, and the
  fallback reason when present.
- Evidence redacts obvious secret values before display.
- The workflow debug dock renders the fallback evidence next to existing
  token/cost/latency evidence.

## Non-goals

- Do not change backend runtime v2 fallback behavior.
- Do not add provider configuration UI in this slice.
- Do not run live LLM acceptance in this slice.

## Evidence

Evidence lives under
`artifacts/slices/092-workflow-llm-fallback-debug-panel/092.1/`.
