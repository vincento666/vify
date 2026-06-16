# ADR 0003: Runtime V2 Transport And Chatflow Spike

## Status

Accepted for 058 spike.

## Context

Customer Assistant now uses durable one-way progress events over SSE. The next
Workflow/Chatflow runtime path needs live progress visibility without replacing
the whole legacy runtime or adding bidirectional infrastructure before product
need is proven.

## Decision

Use SSE for runtime v2 MVP progress events.

- SSE: selected for server-to-client progress, replay by sequence, simple
  browser consumption, and compatibility with current event-stream patterns.
- Streaming POST: kept only as legacy Chatflow completion-time replay through
  `POST /api/v1/chatflows/{chatflowId}/runs` with `Accept: text/event-stream`.
- WebSocket: deferred until one run connection must carry operator input,
  interrupts, or bidirectional low-latency control.
- Redis/pubsub: deferred until runtime workers are multi-process or
  multi-instance and DB polling is insufficient for fanout.

## Spike Scope

058 adds only a Chatflow-first runtime v2 spike:

- `POST /api/v1/chatflows/{chatflowId}/runs-v2`
- `GET /api/v1/runtime-runs/{runId}`
- `GET /api/v1/runtime-runs/{runId}/events`
- `GET /api/v1/runtime-runs/{runId}/events/stream`
- `GET /api/v1/runtime-runs/{runId}/result`
- `POST /api/v1/runtime-runs/{runId}/resume`

Supported graph shapes are intentionally narrow:

- `START -> MESSAGE -> END`
- `START -> QUESTION -> resume -> END`

This is not a generic Workflow/Chatflow runtime replacement.

## Persistence

The spike uses existing database-backed records:

- `workflow`, `workflow_node`, `workflow_edge` for Chatflow definitions.
- `workflow_run` and `workflow_node_run` for run status/result and node runs.
- `chatflow_session`, `chatflow_event`, and `chatflow_checkpoint` for live v2
  event/checkpoint state.

Chatflow definitions must be created, seeded, or migrated into the database.
Missing Chatflow rows return `404`; the v2 spike does not create ephemeral
in-memory definitions.

## Event Ordering

The spike reuses `chatflow_event.sequence`, currently assigned with
`max(sequence)+1` inside `ChatflowStateRepository`. This is acceptable only for
the single-process 058 prototype.

Production MySQL 8 runtime must replace this with a robust ordering strategy:
a unique `(run_id, sequence)` constraint plus retry, row-level locking, or a
database-generated per-run sequence.

## Compatibility

Legacy Chatflow sync and SSE replay endpoints remain unchanged. Runtime v2 live
streaming is explicit through `/runs-v2` and `/runtime-runs/.../events/stream`,
so old consumers are not silently moved to live v2 semantics.
