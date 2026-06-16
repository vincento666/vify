# Plan 062: Hify Workflow/Chatflow Shared Runtime V2 Core

## Architecture

Target shape:

```text
Hify Runtime V2 Core
  -> ownerType: WORKFLOW | CHATFLOW
  -> workflow_run
  -> workflow_node_run
  -> runtime_event / workflow_run_event
  -> event sink
  -> status/result refs
```

Chatflow and Workflow stay different facades over the same core.

Canvas/debug state is a projection over this model. The frontend should not
invent separate node lifecycle states.

```text
node status:
  PENDING -> RUNNING -> COMPLETED
  PENDING -> RUNNING -> WAITING -> RUNNING -> COMPLETED
  PENDING -> RUNNING -> FAILED
  PENDING -> SKIPPED
```

When a node fails, the runner stops scheduling downstream nodes and marks the
run failed unless the graph explicitly supports an error/fallback edge in the
current node coverage.

## Event Store

Preferred production path:

```text
workflow_run_event
  run_id
  sequence
  type
  level
  source
  actor
  node_run_id
  node_key
  node_type
  span_id
  parent_span_id
  payload
```

Sequence strategy must be one of:

- unique `(run_id, sequence)` plus retry;
- row-level lock per run;
- database-generated sequence.

`max(sequence)+1` is allowed only as a documented single-process prototype.

Persisted runtime events are the source of truth. SSE streams, list endpoints,
debug timelines, and facade-specific summaries must project from the event
store instead of becoming independent authoritative logs.

Runtime v2 does not own the SOP multi-level router. It preserves caller context
so the existing router can call Chatflow/Workflow runs without losing intent
switching state:

```text
caller_context
  sop_key
  route_id
  route_turn_id
  intent_key
  task_id
  session_id
```

## Runner Semantics

Runtime create/resume calls should accept an idempotency key or derive a stable
request hash. Background execution must open its own DB session/unit of work and
must not keep a request-scoped session alive after HTTP return.

Terminal status transitions are monotonic. Cancellation and unsupported
cancellation both emit explicit runtime events.

## Compatibility Checker

Validation happens at graph level:

```text
canRunV2(graph) -> supported | unsupportedNodes | unsupportedPatterns
```

Do not mix v1 and v2 nodes inside the same run.
