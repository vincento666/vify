# Spec 070: Realtime Control And Scale-out Transport

## Goal

Introduce bidirectional realtime control or scale-out event fanout only when the
runtime has product evidence that SSE plus durable polling is insufficient.

This spec is intentionally late. It must not add WebSocket, Redis, or pub/sub
preemptively.

## Dependency

070 depends on:

- 061 async worker orchestration;
- 063 Chatflow runtime v2 facade;
- 065 Workflow runtime v2 facade if Workflow v2 is enabled;
- 066 async ChatflowSopWorker adapter if SOP worker v2 is enabled;
- 067 cross-runtime observability gates.

## Product Boundary

In scope when justified:

- worker waits for operator input during the same run;
- operator interrupts an in-flight worker;
- bidirectional low-latency control;
- multi-process or multi-instance event fanout;
- Redis/pubsub or equivalent broker decision;
- WebSocket decision and narrow spike.

Out of scope:

- replacing SSE for simple one-way progress;
- introducing distributed infrastructure without product/runtime evidence;
- changing task/worker semantics.

## Hard Constraints

- SSE remains default for one-way progress.
- WebSocket is justified only by bidirectional control needs.
- Redis/pubsub is justified only by multi-process/multi-instance fanout needs.
- Durable event store remains the source of truth.
- Connection loss must not delete the run.
- Realtime connections must be authorized for the run/session/tenant they read
  or control.
- Delivery semantics must be documented as at-least-once with idempotent client
  handling unless a stronger guarantee is explicitly implemented.
- Broker/pubsub, if introduced, is a fanout optimization only; missed broker
  messages must be recoverable from the durable event store.
- Heartbeat, reconnect, backpressure, and max-connection behavior must be
  specified before WebSocket or Redis is accepted.
- Realtime transport must not change task, worker, Chatflow, or Workflow
  semantics.
- 070 must not be marked complete if runtime/transport changes break the
  existing SOP multi-level router's ability to call Chatflow SOP workers,
  switch intents, suspend/resume tasks, or use v1 fallback.

## Acceptance Criteria

- ADR documents why SSE is insufficient for the selected scenario.
- A narrow realtime-control spike proves the needed control path.
- Durable run/event/result contracts remain intact.
- Browser UAT proves reconnect behavior.
- SOP multi-level router compatibility remains green for Chatflow SOP calls
  through v2-compatible refs and v1 fallback.
- Auth, heartbeat, reconnect, and backpressure behavior are tested or explicitly
  bounded for MVP.
- Broker miss recovery replays from the durable event store when pub/sub is used.

## MVP Exit

070 is complete when one justified realtime-control or scale-out scenario works
without weakening durable async run semantics.
