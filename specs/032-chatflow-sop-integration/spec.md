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

## 032.0 Spec Sign-off

Status: ready for 032.1 boundary discovery.

Spec 032.0 is a documentation-only gate. It establishes the scope for the first
real Chatflow-backed SOP integration behind the adapter port created in 031.
It does not introduce application code, tests, API behavior, database schema, or
runtime behavior.

Signed-off 032.0 boundaries:

- 032 depends on completed 031 adapter contract gates.
- 032 may implement one real Chatflow-backed SOP adapter path only.
- 032 must keep runtime-lab as the caller and control plane.
- 032 must not make Workflow/Chatflow import `runtime_lab`.
- 032 must not implement FAQ, RAG, Agent fallback, human handoff, frontend UI,
  or final `/chat` or `/query` API naming.

032.0 evidence is stored under
`artifacts/slices/032-chatflow-sop-integration/032.0/`.

## 032.1 Boundary Discovery Sign-off

Status: complete as documentation-only discovery.

Current Chatflow already has the minimum integration primitives needed to start
032 implementation:

- run a Chatflow through `WorkflowService.execute`;
- record Chatflow session state, events, and checkpoints;
- query session state and latest waiting checkpoint;
- resume an interrupted run through `WorkflowService.resume_run`;
- preserve scoped variables through checkpoint/resume flows.

Chosen adapter path:

```text
RuntimeLabService
  -> SopRuntimeAdapter
  -> ChatflowSopRuntimeAdapter
  -> WorkflowService.execute / get_session_state / resume_run
  -> ChatflowStateRepository checkpoint/event/session state
```

Known boundary constraints:

- existing Chatflow does not expose a general external "pause any arbitrary
  running node" API;
- 032 `suspend_sop` must map only an already waiting/interrupted Chatflow
  checkpoint, or return a controlled adapter failure;
- Chatflow remains the owner of internal flow node execution state;
- runtime-lab remains the owner of global task status, route events, idempotency,
  and resume policy.

032.1 evidence is stored under
`artifacts/slices/032-chatflow-sop-integration/032.1/`.

## 032 Slice Readiness Sign-off

The following implementation slices are signed off for future TDD work but are
not completed by this documentation gate:

- 032.2 must add RED tests for the real Chatflow adapter and, if needed, a
  test-only Chatflow SOP fixture.
- 032.3 must implement `ChatflowSopRuntimeAdapter` behind the 031 port.
- 032.4 must prove runtime-lab API E2E for the real Chatflow-backed path and
  preserve the mock SOP path.

No 032.2, 032.3, or 032.4 implementation task is complete until its RED,
implementation, gates, evidence, and slice commit are produced.
