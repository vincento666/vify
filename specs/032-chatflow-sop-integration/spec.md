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

## 032 Completion Sign-off

Status: complete.

032 has implemented the first real Chatflow-backed SOP integration behind the
031 adapter port.

Delivered scope:

- `ChatflowSopRuntimeAdapter` maps runtime SOP start/continue/suspend/resume
  operations to existing Chatflow `WorkflowService` run/resume/session-state
  APIs.
- Runtime checkpoints now persist adapter `scoped_variables`, including the
  Chatflow `runId`, `eventId`, `checkpointId`, `sessionId`, and resume mode
  required for persisted resume.
- One runtime-lab API E2E proves that a real Chatflow-backed `refund_ticket`
  SOP can start, be suspended by switching to a mock SOP, be offered for
  resume, resume from persisted checkpoint, continue, and complete.
- Mock SOP fallback remains available for non-real SOP paths during isolated
  runtime-lab validation.
- Chatflow/Workflow modules still do not import `runtime_lab`.

Evidence:

- 032.2 RED evidence:
  `artifacts/slices/032-chatflow-sop-integration/032.2/red.txt`
- 032.3 adapter integration:
  `artifacts/slices/032-chatflow-sop-integration/032.3/integration.txt`
- 032.4 API E2E:
  `artifacts/slices/032-chatflow-sop-integration/032.4/red.txt`
  and
  `artifacts/slices/032-chatflow-sop-integration/032.4/e2e.txt`
- 032.4 targeted regression:
  `artifacts/slices/032-chatflow-sop-integration/032.4/regression.txt`
- 032.4 static gates:
  `artifacts/slices/032-chatflow-sop-integration/032.4/ruff.txt`
  and `artifacts/slices/032-chatflow-sop-integration/032.4/mypy.txt`
- 032.4 full backend pytest:
  `artifacts/slices/032-chatflow-sop-integration/032.4/full-backend-pytest.txt`

Final gates:

- targeted runtime-lab and Chatflow regression: 59 passed;
- full backend pytest: 361 passed, 4 skipped;
- Ruff: passed;
- mypy: passed.

Remaining out of scope for later specs:

- multiple production Chatflow SOP bindings;
- FAQ/RAG/Agent/handoff policy;
- frontend surfaces;
- final `/chat` or `/query` API naming.

## 032.5 Airline Business Gate Sign-off

Status: complete.

032.5 extends the routing MVP acceptance from one real Chatflow-backed SOP to
five core airline service SOP intents:

- `refund_ticket`: refund / ticket cancellation;
- `change_flight`: flight change;
- `invoice_apply`: invoice / itinerary receipt;
- `baggage_service`: baggage service / extra baggage allowance;
- `seat_checkin`: check-in / seat selection.

Delivered scope:

- runtime-lab manifests and semantic recall fixtures cover all five SOPs;
- `tests/e2e/test_runtime_lab_airline_sop_business_gate.py` creates five real
  Chatflow fixtures and binds all five SOPs through `ChatflowSopRuntimeAdapter`;
- all business E2E traffic enters through
  `/api/v1/runtime-lab/sessions/{id}/messages`;
- three high-probability cross-SOP journeys are covered:
  refund -> invoice -> resume refund,
  change flight -> baggage -> resume change flight with non-interruptible
  switch rejection, and seat check-in -> refund -> resume seat check-in;
- expected-vs-actual route/output comparisons are written to
  `artifacts/slices/032-chatflow-sop-integration/032.5/airline-business-gate.md`;
- `tests/acceptance/test_runtime_lab_live_chatflow_llm_sop.py` adds an opt-in
  live gate proving routed Chatflow SOPs execute real provider-backed `LLM`
  nodes and return per-SOP live markers.

Live acceptance command:

```bash
HIFY_RUN_LIVE_RUNTIME_CHATFLOW=1 \
OPENROUTER_API_KEY=... \
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1 \
OPENROUTER_MODEL=xiaomi/mimo-v2-flash \
rtk env PYTHONPATH=. uv run pytest tests/acceptance/test_runtime_lab_live_chatflow_llm_sop.py -q
```

The live gate is skipped by default to avoid CI dependence on external model
availability and cost. Skipped-by-default behavior is itself verified by
`artifacts/slices/032-chatflow-sop-integration/032.5/live-acceptance-skip.txt`.

032.5 evidence:

- business gate:
  `artifacts/slices/032-chatflow-sop-integration/032.5/business-gate.txt`
- expected-vs-actual route/output artifact:
  `artifacts/slices/032-chatflow-sop-integration/032.5/airline-business-gate.md`
- live acceptance default skip:
  `artifacts/slices/032-chatflow-sop-integration/032.5/live-acceptance-skip.txt`
- static gates:
  `artifacts/slices/032-chatflow-sop-integration/032.5/ruff.txt`
  and `artifacts/slices/032-chatflow-sop-integration/032.5/mypy.txt`
- full backend pytest:
  `artifacts/slices/032-chatflow-sop-integration/032.5/full-backend-pytest.txt`

032.5 final gates:

- targeted runtime-lab business gate: 48 passed;
- live acceptance default behavior: 1 skipped unless live credentials are
  explicitly enabled;
- full backend pytest: 363 passed, 5 skipped;
- Ruff: passed;
- mypy: passed.
