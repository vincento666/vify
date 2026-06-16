# Spec 058: Realtime Runtime Transport And Workflow/Chatflow V2 Spike

## Goal

Decide and spike the next realtime transport/runtime path after the customer
assistant runtime is stable: keep SSE for one-way progress, introduce WebSocket
only for bidirectional interruption, and align one narrow Chatflow-first v2 run
path with the eventful runtime contract.

## Dependency

058 depends on:

- 053 Workflow/Chatflow runtime v2 event alignment;
- 056 worker runtime hardening;
- 057 operator turn mode if bidirectional operator interruption is required;
- MySQL 8 migration readiness for Workflow/Chatflow persistence, or a documented
  temporary SQLite/fallback strategy for the spike.

## Product Boundary

In scope:

- transport decision record: SSE, streaming POST, WebSocket, Redis/pubsub;
- one narrow runtime v2 spike for Chatflow first;
- database-backed run/event/checkpoint records compatible with the MySQL 8
  migration direction;
- durable run id/status/events/result shape;
- compatibility wrapper for existing synchronous run endpoint;
- frontend debug/event consumer spike if needed.

Out of scope:

- replacing all Workflow/Chatflow endpoints;
- generic distributed queue platform;
- real-time collaboration between multiple operators;
- making WebSocket mandatory before the product needs bidirectional control.
- completing the entire MySQL 8 migration.
- generalizing the spike to all Workflow/Chatflow node types.

## Spike Shape

The first runtime v2 spike is fixed to Chatflow and must cover these minimal
paths:

```text
START -> MESSAGE -> END
START -> QUESTION -> resume -> END
```

Generic Workflow v2 and broad node coverage are follow-on work. The spike may
reuse Workflow engine internals, but the product-facing proof must be Chatflow
because customer-assistant SOP workers already depend on Chatflow behavior.

## Database Boundary

Workflow/Chatflow definitions and runtime records are database-backed. 058 must
not assume ephemeral in-memory Chatflow definitions or developer-local IDs.

The spike must document:

- which MySQL 8 tables or SQLAlchemy models are used or proposed;
- how Chatflow/SOP definitions are seeded or migrated;
- how run/event/checkpoint records survive process restart;
- how compatibility wrappers behave when required Chatflow rows are missing.
- how runtime event sequence ordering is guaranteed or, for a single-process
  prototype, why it is explicitly temporary.

For production-aligned MySQL 8 design, event ordering must use a robust strategy
such as a unique `(run_id, sequence)` constraint with retry, row-level locking,
or database-generated sequence values. A `max(sequence)+1` strategy is
acceptable only for a documented single-process spike.

## Live Vs Replay Boundary

Existing Chatflow streaming behavior is a compatibility replay: the legacy
`POST /api/v1/chatflows/{chatflow_id}/runs` endpoint may return an SSE body
after synchronous execution has completed.

Runtime v2 live streaming must use a new endpoint or explicit v2 mode. Its event
stream must show durable run/node events while the run is still active. A v2
test must prove at least one `workflow_run_started` or `workflow_node_started`
event is observable before the terminal result is available.

## Transport Rule

Use SSE when the product needs:

- server-to-client progress events;
- event replay by sequence id;
- simple run lifecycle visibility.

Use WebSocket later when the product needs:

- worker waits for input on the same run connection;
- operator interrupts an in-flight worker;
- bidirectional low-latency control;
- multi-client coordination.

Use Redis/pubsub only when:

- app workers are multi-process or multi-instance;
- in-memory polling is insufficient;
- event fanout must survive process boundaries.

## Acceptance Criteria

- ADR compares SSE, streaming POST, WebSocket, and Redis/pubsub for this project.
- One Chatflow-first runtime v2 spike emits durable L1 node events.
- V2 live event streaming proves pre-terminal event visibility and does not
  rely on completion-time replay.
- Spike uses database-backed Chatflow/runtime records or documents why a
  temporary fallback is still in use.
- Runtime event sequence strategy is documented and tested or explicitly marked
  single-process-only.
- Compatibility wrapper proves old consumers still work.
- Legacy Chatflow SSE replay remains compatible and is not confused with v2 live
  streaming.
- Browser UAT shows event progress in the relevant debug/operator surface.

## MVP Exit

058 is complete when one narrow Chatflow-first v2 path proves the durable
run/status/event/result contract without replacing the whole canvas runtime or
changing legacy endpoint behavior.

It may choose to stay on SSE if bidirectional control is still not required.
