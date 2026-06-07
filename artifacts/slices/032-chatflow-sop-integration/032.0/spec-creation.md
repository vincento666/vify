# 032.0 Spec Creation Evidence

## Status

Spec 032 is ready for implementation planning and 032.2 RED-test work after
032.1 discovery.

This evidence file records a documentation-only gate. No application code,
runtime behavior, API behavior, tests, or database schema changes are part of
032.0.

## Files

Spec files:

- `specs/032-chatflow-sop-integration/spec.md`
- `specs/032-chatflow-sop-integration/plan.md`
- `specs/032-chatflow-sop-integration/tasks.md`

Evidence file:

- `artifacts/slices/032-chatflow-sop-integration/032.0/spec-creation.md`

## Scope Signed Off

032 connects one real Chatflow-backed SOP path behind the adapter contract from
031.

Signed-off boundaries:

- Runtime-lab remains the caller and control plane.
- Workflow/Chatflow must not import `runtime_lab`.
- The runtime task ledger remains source of truth for task status, route
  events, idempotency, and resume policy.
- Chatflow remains source of truth for internal flow node execution state.
- 032 does not implement FAQ, RAG, Agent fallback, human handoff, frontend UI,
  or final product API naming.

## Dependency Check

031 is complete and signed off by:

```text
312c9bb docs: sign off runtime adapter spec 031
```

Implementation must start with 032.2 RED tests after the 032.1 discovery
decision is accepted.
