# Plan 048: Customer Assistant Live L1 Events SSE

## Architecture

Backend additions:

```text
app/modules/customer_assistant/
├── domain/
│   ├── event_stream.py
│   └── service.py
└── web/
    └── router.py
```

Frontend additions:

```text
frontend/src/api/customerAssistant.ts
frontend/src/views/customerAssistant/
├── customerAssistantEventStream.ts
├── customerAssistantRuntime.ts
├── customerAssistantViewModel.ts
└── CustomerAssistantPanel.vue
```

## Backend Stream Plan

Implement a small SSE generator:

```text
validate session
last_sequence = afterSequence or Last-Event-ID or 0
loop:
  query events where sequence > last_sequence order by sequence asc
  yield each event as SSE frame
  update last_sequence
  if no events: yield heartbeat on interval
  stop on disconnect
```

Use repository reads so reconnect behavior is based on durable state.

## Runtime Instrumentation Plan

Add or normalize events around existing phases:

```text
run_started
task_recognized
task_started
worker_started
worker_result_received
recommendation_started
recommendation_completed
run_completed
run_failed
```

Where a phase has start and completion boundaries, include timing payloads.

For worker execution, add timing at the scheduler or service boundary without
requiring internal Chatflow node streaming in 048.

## Frontend Stream Plan

The panel currently creates a session lazily when sending the first turn. 048
should adjust the flow:

```text
ensure session exists
open SSE stream for session
send turn with normal HTTP POST
merge SSE events into runtime state while POST is pending
after POST resolves, refresh tasks/events as reconciliation
```

The stream client should support:

- `afterSequence`;
- reconnect using last seen sequence;
- stop/cleanup on component unmount;
- visible error state without losing existing panel data.

## UI Plan

Keep the product surface task-centric:

- stage checklist near the operator result area;
- task list updates as events arrive;
- recommendation/draft loading state until complete;
- collapsed timeline below operator-side panels.

Avoid making the raw event feed the dominant visual element.

## Testing Strategy

Backend tests:

- SSE frame format contract;
- `afterSequence` resume behavior;
- heartbeat behavior;
- slow-worker execution-time streaming proof;
- list-events compatibility after streaming.

Frontend tests:

- SSE client parses events;
- runtime state merges live events without waiting for turn result;
- panel shows checked stages from events;
- timeline collapsed by default;
- cleanup closes stream on unmount.

UAT:

- run FastAPI and Vite;
- open `/customer-assistant`;
- start a customer turn that triggers refund + baggage tasks;
- verify task/stage progress appears while request is active;
- save screenshots and notes.

## Evidence

Save evidence under:

```text
artifacts/slices/048-customer-assistant-live-l1-events-sse/
```
