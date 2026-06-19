# Spec 203: Runtime Response Layer Summary

## Goal

Expose a production-facing runtime result shape that summarizes status, result,
usage, retryability, and events without leaking node payload details.

This covers the first Phase 8 response-layer boundary in
`docs/chatflow-workflow-production-upgrade.md`.

## In Scope

- Add external summary fields to runtime result responses.
- Keep full runtime event and node detail APIs unchanged for canvas/debug views.
- Aggregate token usage from completed node outputs when available.
- Expose a compact event list that omits node inputs/outputs and raw payloads.

## Out of Scope

- Customer assistant UI redesign.
- SOP audit screens.
- New worker retry policies.
- New persistence tables beyond existing runtime state.

## Acceptance Criteria

- `/api/v1/runtime-runs/{runId}/result` includes `statusRef`, `latencyMs`,
  `usage`, `retryable`, `result`, and simplified `events`.
- Simplified events expose event identity/status context but do not include raw
  payloads or node outputs.
- `/api/v1/runtime-runs/{runId}/events` still returns full payload detail for
  canvas/debug inspection.
