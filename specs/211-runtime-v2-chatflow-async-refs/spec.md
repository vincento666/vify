# Spec 211: Runtime V2 Chatflow Async Refs Closure

## Goal

Close the public and internal runtime-v2 invocation gap for Chatflow, Workflow,
SOP, and customer-assistant paths so all callers expose and consume the same
durable runtime refs, events, result, and node state.

## In Scope

- `POST /api/v1/chatflows/{chatflowId}/runs:stream` starts a runtime-v2
  Chatflow run and streams durable runtime events.
- Workflow and Chatflow start/resume callers use a shared internal invocation
  gateway for start-only, start-and-wait, stream-ref, and resume-and-wait
  semantics.
- Runtime-lab SOP and customer-assistant `chatflow_sop` workers move from
  synchronous projection-only calls toward async refs-driven behavior while
  preserving explicit compatibility behavior.
- Standalone runtime workers can claim Workflow, Chatflow, or both owner types
  without wrong-owner job execution.
- Docs list the supported Workflow/Chatflow/message/runtime-run endpoints and
  distinguish async, sync compatibility, and SSE behavior.

## Out of Scope

- Real RAG, real tool calling, or MCP upgrades beyond existing runtime-v2
  node support.
- Replacing the durable DB event store.
- Adding specs for incidental test environment or gate fixes.
- Removing legacy Chatflow/Workflow compatibility endpoints.

## Acceptance Criteria

- Chatflow `/runs:stream` returns `text/event-stream`.
- The first frame and replay frames belong to the same `runId`.
- `afterSequence`, heartbeat comments, `_testLimit`, failure, and waiting-input
  behavior are covered by contract and e2e tests.
- `/runtime-runs/{runId}/events/stream?afterSequence=N` reconnects from durable
  runtime events.
- Shared gateway callers return consistent refs/status/result/events.
- SOP trace, customer-assistant task panels, and runtime SSE read the same
  durable runtime event sequence.
- Standalone worker owner filtering prevents Workflow workers from draining
  Chatflow jobs and vice versa.
