# Spec 048: Customer Assistant Live L1 Events SSE

## Goal

Add true execution-time L1 runtime event streaming for the customer-assistant
operator panel using a one-way SSE stream backed by the persisted event ledger.

048 must let the frontend display progress while a run is still executing. It
must not wait for `POST /turns` to complete and then replay all events.

## Dependency

048 depends on:

- 045 Customer Assistant Runtime MVP;
- 046 Customer Assistant Operator Panel MVP;
- 047 Actor persistence for event payload consistency.

048 does not require a full async run lifecycle. The existing synchronous
`POST /turns` API may remain synchronous while the frontend opens a separate
SSE connection for runtime events.

## Product Boundary

In scope:

- SSE endpoint for customer-assistant session events;
- DB event ledger as stream source of truth;
- execution-time event emission inside the runtime;
- frontend SSE subscription for the operator panel;
- live task/run progress checklist;
- task status and recommendation loading states that update before the turn
  response returns;
- event timeline as collapsed auxiliary evidence below the operator side;
- runtime timing fields for later evaluation.

Out of scope:

- WebSocket;
- Redis/pubsub;
- bidirectional worker interruption;
- human input that resumes a worker inside the same open connection;
- full async run lifecycle with `POST /runs -> runId`;
- internal Chatflow/Workflow node-level events as first-class UI events;
- L2 recursive React worker traces.

## MVP Scope Guard

048 is a live-progress MVP for the customer-assistant runtime only. It proves
execution-time event delivery through persisted L1 events and an independent
SSE stream. It must not refactor Workflow/Chatflow into async run lifecycle,
introduce WebSocket/Redis infrastructure, or make internal worker traces part
of the primary product UI.

## Transport Decision

048 uses SSE because the MVP needs server-to-client progress only:

```text
frontend opens GET events/stream
frontend sends POST turns over normal HTTP
backend persists events while the turn executes
SSE reads persisted events and pushes them to the panel
```

Use WebSocket later only when the product needs same-connection bidirectional
control, such as:

- worker waits mid-run for human input before it can continue;
- operator live interjection changes a running worker;
- multiple operators collaborate in the same live run;
- voice/transcript streams require bidirectional transport.

## API Contract

Add:

```text
GET /api/v1/customer-assistant/sessions/{sessionId}/events/stream?afterSequence=0
```

SSE message:

```text
id: <sequence>
event: customer_assistant_event
data: {"id":1,"sessionId":1,"sequence":1,"type":"run_started",...}
```

Rules:

- `afterSequence` defaults to 0;
- stream first sends any persisted events after `afterSequence`;
- stream then polls for new persisted events;
- event ordering follows session `sequence`;
- stream sends heartbeat comments or heartbeat events during idle periods;
- stream ends only on client disconnect, server shutdown, or explicit test
  timeout;
- auth/session checks must match existing list-events endpoint behavior.

## Event Source Of Truth

The SSE endpoint must read from `customer_assistant_event`, not from an
in-memory queue. This keeps reconnect behavior simple:

```text
Last-Event-ID / afterSequence -> query persisted events -> continue polling
```

In-memory broadcast may be introduced later for efficiency, but it must not be
the only source of truth.

## Execution-Time Requirement

048 must prove that events are visible before the turn response completes.

At minimum, tests should use a slow or blocking test worker:

```text
open SSE
start POST /turns in another task/thread
observe run_started/task_started/worker_started on SSE
only then let the worker complete
assert POST /turns was still pending when progress arrived
```

This distinguishes real live streaming from complete-then-replay behavior.

## L1 Event Scope

048 streams customer-assistant L1 runtime events only.

First-class events:

```text
run_started
task_recognized
task_added
task_retained
task_cancelled
task_started
task_waiting
task_completed
task_failed
worker_started
worker_checkpointed
worker_interrupted
worker_proposed_action
worker_result_received
recommendation_started
recommendation_completed
proposed_action_created
proposed_action_confirmed
proposed_action_rejected
run_completed
run_failed
```

Internal Chatflow/SOP node details stay in worker payload summaries in 048.
Spec 053+ will evaluate Workflow/Chatflow runtime v2 and align node-level
events with React worker L2 events.

## Timing Payload

Add timing fields where available:

```text
startedAt
completedAt
elapsedMs
```

048 only displays task/run elapsed time. It does not calculate concurrency
benefit. Spec 051 will use these fields for eval metrics.

## Frontend Behavior

The operator panel should show:

- active run checklist;
- task list status updates;
- recommendation/draft pending and completed states;
- proposed action status updates;
- collapsed Event Timeline as supporting evidence.

The event log must not become the main product UI.

Recommended checklist stages:

```text
Recognizing tasks
Running workers
Generating recommendation
Ready for operator
```

## Acceptance Criteria

- SSE endpoint streams persisted events in sequence.
- Reconnect with `afterSequence` resumes from the next event.
- A slow-worker test proves at least one progress event arrives before
  `POST /turns` completes.
- The frontend opens SSE after session creation and merges incoming events into
  panel state.
- During a multi-task run, the operator panel shows task progress before the
  final turn response.
- Event Timeline is collapsed by default under the operator side.
- No WebSocket or Redis/pubsub dependency is introduced.
- Existing list-events endpoint remains compatible.

## Completion Capability

After 048, the customer-assistant runtime feels alive in the operator panel:
completed tasks and major stages appear as they happen, while the simpler
synchronous turn API remains intact for this phase.
