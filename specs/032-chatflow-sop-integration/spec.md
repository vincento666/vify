# Spec 032: Chatflow SOP Integration

## Goal

Connect one real Chatflow-backed SOP path to the isolated runtime router through
the adapter contract from 031.

032 is the first controlled integration from runtime-lab into existing Chatflow.
It must preserve one-way dependency and prove that runtime routing can start,
interrupt, resume, and complete a real Chatflow SOP without destabilizing the
current Chatflow engine.

## Dependency

032 starts only after 031 gates pass.

Required 031 capabilities:

- explicit SOP adapter port;
- fake adapter contract tests;
- checkpoint serialization contract;
- dependency-direction gate.

## Scope

In scope:

- one real Chatflow SOP fixture or seed definition;
- adapter implementation that maps runtime SOP operations to existing Chatflow
  run/resume behavior;
- runtime checkpoint mapping to Chatflow session state;
- integration tests for start, continue, suspend, resume, and complete;
- API E2E through runtime-lab endpoints;
- evidence proving existing Chatflow tests still pass.

Out of scope:

- multiple real SOPs;
- frontend UI;
- full product API naming;
- FAQ/RAG/Agent/handoff policy;
- broad refactor of Chatflow engine;
- making Chatflow depend on runtime-lab.

## Integration Rules

- Runtime-lab remains the caller.
- Existing Chatflow modules must not import runtime-lab.
- Adapter maps normalized runtime requests into existing Chatflow service
  inputs.
- Adapter maps Chatflow state back into runtime-safe checkpoint payloads.
- Runtime ledger remains source of truth for active/suspended/completed task
  state.
- Chatflow remains source of truth for internal flow node execution state.

## Minimum Real SOP

Use one narrow aviation SOP, preferably the simplest existing Chatflow fixture
that resembles:

```text
collect_order_no -> confirm -> completed
```

If no suitable fixture exists, 032 may add a test-only Chatflow fixture. The
fixture must be documented and isolated from production seed data.

## Acceptance Criteria

- Runtime can start the real Chatflow SOP through the adapter.
- Runtime can continue the real Chatflow SOP.
- Runtime can suspend the real Chatflow SOP at an interruptible point.
- Runtime can resume from a persisted checkpoint.
- Runtime can complete the real Chatflow SOP.
- Existing mock SOP path remains available for tests.
- Existing Chatflow tests still pass.
- One-way dependency remains true.

## Completion Gate

032 is complete only when:

- targeted runtime-lab and Chatflow integration tests pass;
- API E2E passes for the real Chatflow-backed path;
- dependency-direction gate passes;
- full backend pytest passes or unrelated failures are documented;
- evidence is saved under
  `artifacts/slices/032-chatflow-sop-integration/`;
- one git commit contains only 032 changes.
