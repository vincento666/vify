# 031.0 Spec Creation Evidence

## Status

Spec 031 is now fully implemented by slices 031.1 through 031.3 and is ready for
032 boundary discovery.

This file records the documentation-only 031.0 gate. No application code,
runtime behavior, API behavior, tests, or database schema changes are part of
031.0.

## Files

Spec files:

- `specs/031-chatflow-sop-adapter-contract/spec.md`
- `specs/031-chatflow-sop-adapter-contract/plan.md`
- `specs/031-chatflow-sop-adapter-contract/tasks.md`

Evidence file:

- `artifacts/slices/031-chatflow-sop-adapter-contract/031.0/spec-creation.md`

## Scope Signed Off

031 defines the adapter contract that sits between runtime-lab's control plane
and future Chatflow SOP execution.

Signed-off boundaries:

- Runtime-lab owns route control, task ledger, idempotency, and resume policy.
- The adapter owns only SOP execution semantics.
- 031 uses a fake adapter and does not call real Chatflow.
- Workflow/Chatflow must not import `runtime_lab`.
- Real Chatflow SOP integration begins in 032.

## Implementation Slices

031 implementation is split into:

- `031.1` adapter port and DTOs;
- `031.2` runtime service adapter boundary;
- `031.3` dependency-direction gate.

Each implementation slice has RED evidence, passing gates, and a dedicated
commit.
