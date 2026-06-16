# ADR 0004: Realtime Control And Scale-out Transport

## Status

Accepted for Spec 070.

## Decision

Decision: NO-GO for WebSocket and Redis/pubsub in the 070 MVP.

SSE + durable polling remains the default because current runtime evidence shows
one-way progress, reconnect, heartbeat, and durable replay are already covered
by existing contracts:

- Customer-assistant SSE can resume with `afterSequence` and `Last-Event-ID`.
- Runtime v2 exposes durable `eventsRef`, `eventStreamRef`, and result refs.
- Durable event storage remains the source of truth after connection loss.
- Browser UAT can verify reconnect by comparing streamed data with durable
  polling from the event list endpoint.

## Option Comparison

- SSE + durable polling: accepted default for one-way progress and reconnect.
- Streaming POST: useful for chat-style request streaming, but not needed for
  durable runtime progress refs.
- WebSocket: not justified until there is product evidence for bidirectional
  low-latency control such as interrupting an in-flight worker in the same run.
- Redis/pubsub: not justified until there is product evidence for multi-process
  or multi-instance fanout. If later introduced, it must be a fanout
  optimization only.
- DB polling: accepted as durable fallback and recovery path.

## Delivery Semantics

Delivery is at-least-once. Clients must handle duplicate event ids/sequences
idempotently. Missed realtime frames are recovered from durable event endpoints
using `afterSequence`.

## Bounds

- Heartbeat: SSE comment heartbeat, bounded by existing API limits.
- Reconnect: use `afterSequence` query parameter or `Last-Event-ID` header.
- Backpressure: single-process MVP only; max-connection expansion is out of
  scope until scale-out evidence exists.
- Auth/scope: realtime reads and future controls must remain scoped by
  run/session/tenant authorization dependencies.
- Broker miss recovery: any future pub/sub message miss must replay from the
  durable event store.

## Consequences

No WebSocket, Redis, or new pub/sub dependency is added in 070. Runtime task,
worker, Chatflow, Workflow, and SOP router semantics remain unchanged. A future
transport spike must first attach measured evidence that SSE + durable polling
is insufficient for a concrete product scenario.
