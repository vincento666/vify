# Plan 024: Runtime Streaming, API Resources, and Channel MVP

## Implementation Strategy

Keep this spec narrow and vertical. Do not start with broad 023 refactors.
Implement each product capability behind small adapters, then feed the existing
Workflow/Chatflow runtime and UI.

Recommended order:

1. streaming event model and UI rendering;
2. node usage/evidence projection;
3. API Resource and Tool Builder Lite;
4. channel adapter registry/profile compatibility.

## Architecture Notes

### Streaming

Add a small stream accumulator contract near the Workflow runtime:

- append deltas;
- produce final accumulated content;
- mark fallback/stream errors;
- expose events for node-test, full-run debug, and channel delivery.

The executor should never pass partial values into downstream node variables.
Only the final accumulated value updates `context.values`.

The frontend should render streaming from run events rather than inventing a
second client-only typewriter state. This keeps test, debug, and published
channel evidence consistent.

### Usage and Cost Evidence

Prefer a normalized projection over immediate schema churn where possible:

- exact provider usage when available;
- estimate text tokens when provider usage is absent;
- optional cost estimate from provider/model pricing config;
- preserve backward-compatible workflow node run shape.

If database columns are needed, use additive JSON/nullable fields and migration
tests. Do not rewrite all old run rows.

### API Resource and Tool Builder Lite

Introduce two product concepts:

- API Resource: technical HTTP integration.
- Tool: business wrapper used by Agent/Workflow/Chatflow/LLM skills.

Do not duplicate MCP server behavior. API-backed Tools should flow through the
same `TOOL_CALL` node evidence shape as MCP-backed Tools, with the adapter type
set to `API_RESOURCE`.

Direct `API_CALL` remains for compatibility. Publish validation can warn or
block advanced direct calls later, but 024 focuses on reusable resource
creation, testing, and invocation.

### Channel Profiles

Keep the existing Chatflow channel table and service shape. Add an adapter
descriptor registry around it:

- channel id;
- display name;
- runnable flag;
- required config schema;
- inbound normalization;
- delivery capabilities: sync, streaming, files, cards;
- unavailable reason.

API and Web stay runnable. Third-party channels remain visible descriptors with
explicit disabled reasons unless their credential/signature specs are accepted.

## Frontend Notes

- Reuse the existing Workflow/Chatflow run debug drawer.
- Add a compact usage row on node run detail: tokens, cost estimate, latency.
- Add resource pages or panels only as small CRUD/test surfaces; do not build a
  marketplace.
- In canvas config, prefer selectors over raw IDs once API-backed Tools exist.
- For LLM Skills, use resource-type tabs before resource selection; do not mix
  knowledge bases, MCP tools, API-backed tools, subworkflows, and agents in one
  unbounded dropdown.
- Keep direct text fields as advanced fallback where current tests rely on IDs.

## Evidence Log

- 024.1 complete: see `artifacts/slices/024-runtime-streaming-resource-channel-mvp/024.1/`.
- 024.2 complete: see `artifacts/slices/024-runtime-streaming-resource-channel-mvp/024.2/`.
- 024.3 complete: API Resource CRUD/test-call, Tool Builder Lite, API-backed
  `TOOL_CALL`, direct `API_CALL` Resource references, frontend resource surface,
  canvas selector, E2E, and Browser UAT evidence are saved under
  `artifacts/slices/024-runtime-streaming-resource-channel-mvp/024.3/`.
- 024.4 complete: channel adapter descriptors, API/Web compatibility,
  normalized inbound fields, delivery capabilities, disabled third-party shells,
  frontend channel profiles, E2E, and Browser UAT evidence are saved under
  `artifacts/slices/024-runtime-streaming-resource-channel-mvp/024.4/`.
- Final gate complete: frontend unit, frontend build, backend workflow
  unit/integration, relevant E2E, and Browser UAT summary are saved under
  `artifacts/slices/024-runtime-streaming-resource-channel-mvp/final-gate/`.

## Backend Notes

- Keep `/api/v1/...` response envelopes.
- Add integration tests before implementation for every slice.
- Add sanitized evidence snapshots for resource calls.
- Ensure channel profile test calls still use current `WorkflowService.test_channel`.
- Avoid changing the shared FlowGraph schema unless a test proves the need.

## Evidence

Each slice saves:

```text
artifacts/slices/024-runtime-streaming-resource-channel-mvp/{slice-id}/
├── red.txt
├── unit.txt
├── integration.txt
├── e2e.txt
├── uat.md
└── screenshots/
```
