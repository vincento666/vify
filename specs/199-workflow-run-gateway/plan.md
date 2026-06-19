# Plan

## Slice 199.1 Workflow Public Run Gateway

1. Add RED contract tests for `/workflows/{id}/runs` and
   `/workflows/{id}/runs:stream`.
2. Reuse the existing `WorkflowRuntimeV2Service` path behind `/runs`.
3. Add `/runs-legacy` for explicit synchronous compatibility.
4. Keep `/runs-v2` as an alias during migration.
5. Run focused workflow runtime v2, published snapshot, and frontend rem/unit
   gates.
6. Add browser UAT for run gateway refs and SSE.

## Risks

- Existing frontend/e2e scripts may still call `/workflows/{id}/runs` expecting
  a sync `output`; this slice changes the API default by design.
- Full durable queue semantics are not part of this slice.
