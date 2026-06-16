# Plan 045: Customer Assistant Runtime MVP

## Architecture

Create a new backend module:

```text
app/modules/customer_assistant/
├── domain/
│   ├── runtime.py
│   ├── react_core.py
│   ├── controller.py
│   ├── ledger.py
│   ├── worker.py
│   ├── scheduler.py
│   ├── policy.py
│   ├── events.py
│   └── result.py
├── infra/
│   ├── schema.py
│   └── repository.py
└── web/
    ├── router.py
    └── schemas.py
```

Keep the module independent from `runtime_lab`. Reuse adapter contracts and
facades where possible, but do not call `RuntimeLabService.handle_message()`.

## Control Model

Implement a controlled ReAct-shaped loop:

```text
reason -> validate -> act -> observe -> final
```

MVP settings:

```text
max_iterations = 1
controller = DeterministicTaskRecognitionController
action_policy = strict customer-assistant policy
worker_scheduler = local parallel fan-out/join
aggregator = deterministic stub
```

The loop must be written so later specs can replace the deterministic
controller and aggregator with LLM structured-output implementations without
changing persistence or worker contracts.

## Persistence

Add database-backed repositories for:

- assistant session;
- assistant run;
- assistant task;
- assistant event;
- proposed action.

JSON columns can store worker checkpoint/result payloads in MVP. Keep columns
small and explicit for statuses, task identity, run identity, and event order.

## Worker Integration

### ChatflowSopWorker

Use existing real Chatflow/SOP integration:

```text
CustomerAssistantRuntime
  -> ChatflowSopWorker
  -> ChatflowSopRuntimeAdapter
  -> WorkflowService.execute / resume_run
```

The worker maps:

```text
TaskItem + turn input
  -> SopExecutionRequest
SopExecutionResult
  -> WorkerResult
```

The assistant ledger remains source of truth for task status. Chatflow remains
source of truth for internal node state and checkpoints.

### StubQaWorker

Return deterministic `COMPLETED` results for a small vocabulary such as baggage
allowance. This proves multi-task aggregation before real RAG is introduced.

## Eventing

Use an `EventSink` abstraction inside the runtime. The sink writes session-level
sequence numbers through the repository. Worker events are normalized before
persistence.

MVP APIs expose stored events through list endpoints. SSE/WebSocket streaming is
reserved for later specs.

## Proposed Actions

Introduce `ProposedAction` persistence and confirmation APIs. The confirm/reject
endpoints update local proposed-action state only in 045 unless the action is
explicitly safe and locally executable.

Do not call external write APIs from proposed-action confirmation in the first
MVP slice.

## API Wiring

Add `app/modules/customer_assistant/web/router.py` and register it in
`app/main.py` using the existing router/envelope conventions.

Response schemas should use camelCase aliases at the API boundary while keeping
domain objects snake_case internally.

## Testing Strategy

Follow Spec Kit/TDD:

- RED tests first for every slice;
- unit tests for controller, ledger, policy, scheduler, and aggregation;
- integration tests for repository persistence and API;
- targeted regression for existing Chatflow/runtime-lab compatibility;
- no frontend rem/browser UAT until a frontend slice is introduced.

## Slice Order

045.0 -> 045.1 -> 045.2 -> 045.3 -> 045.4 -> 045.5 -> 045.6

## Slice Status

- 045.0: complete; evidence under
  `artifacts/slices/045-customer-assistant-runtime-mvp/045.0/`.
- 045.1: complete; RED/unit/integration/E2E-N/A/UAT-N/A evidence under
  `artifacts/slices/045-customer-assistant-runtime-mvp/045.1/`.
- 045.2: complete; RED/unit/integration-regression/E2E-N/A/UAT-N/A
  evidence under `artifacts/slices/045-customer-assistant-runtime-mvp/045.2/`.
- 045.3: complete; RED/unit/integration/E2E-N/A/UAT-N/A evidence under
  `artifacts/slices/045-customer-assistant-runtime-mvp/045.3/`.
- 045.4: complete; RED/integration/E2E-N/A/UAT-N/A evidence under
  `artifacts/slices/045-customer-assistant-runtime-mvp/045.4/`.
- 045.5: complete; RED/contract/focused API E2E/UAT-N/A evidence under
  `artifacts/slices/045-customer-assistant-runtime-mvp/045.5/`.
- 045.6: complete; RED/E2E/focused gates/runtime-lab regression/lint/mypy/full
  non-acceptance backend evidence under
  `artifacts/slices/045-customer-assistant-runtime-mvp/045.6/`.

## Dependencies

Helpful existing capabilities:

- 018 Chatflow session state/checkpoint/resume;
- 031 SOP adapter contract;
- 032 real Chatflow SOP integration;
- 039 controlled Agent-output policy pattern;
- 041 runtime observability/profile concepts as later production hardening.

045 must not depend on unimplemented generic agent harness work.
