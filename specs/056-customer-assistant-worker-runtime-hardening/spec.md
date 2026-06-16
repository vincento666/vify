# Spec 056: Customer Assistant Worker Runtime Hardening

## Goal

Harden worker execution so timeouts, cancellation, async refs, and event streams
are real runtime semantics instead of best-effort synchronous scheduler behavior.

056 addresses the residual risk discovered after 047-052: worker timeout exists
at the result level, but not as a hard interrupt/cancel boundary.

## Dependency

056 depends on:

- 048 L1 SSE event stream;
- 049 restricted ReAct worker;
- 052 sub-agent refs and reserved worker async refs.

## Product Boundary

In scope:

- worker run identity;
- worker status/result/event refs;
- hard timeout semantics for local MVP workers;
- cooperative cancellation API;
- timeout/cancel events;
- scheduler behavior that returns after timeout without waiting indefinitely for
  the blocked worker;
- frontend/runtime payload that can display worker async refs when present.

Out of scope:

- distributed queue infrastructure;
- guaranteed process kill across all operating systems;
- WebSocket/Redis transport;
- generic agent harness replacement.

## API Shape

Target shape:

```text
workerRunId
workerStatusRef
workerEventStreamRef
workerResultRef
```

Optional endpoint:

```text
POST /api/v1/customer-assistant/worker-runs/{workerRunId}/cancel
```

## Runtime V2 Boundary

056 introduces customer-assistant worker runtime semantics only. Its worker refs
are the reference contract for later Workflow/Chatflow runtime v2 work, but
they are not the shared Workflow/Chatflow runtime storage layer.

If 056 adds tables, they must be customer-assistant scoped, such as:

```text
customer_assistant_worker_run
customer_assistant_worker_event
```

If 056 stores refs in existing task/event payloads for MVP speed, it must record
that limitation. Shared Workflow/Chatflow runtime event tables belong to 058+.

## Acceptance Criteria

- A blocked worker cannot block the entire turn beyond configured timeout.
- Timeout emits durable events and produces a failed worker result.
- Cancel emits durable events and marks the worker run cancelled where supported.
- 052 `workerAsyncRefs` becomes supported for at least one worker path.
- Worker async refs are explicitly documented as customer-assistant scoped
  contracts, not Workflow/Chatflow v2 storage.
- Existing synchronous MVP flow remains compatible.

## MVP Exit

056 is complete when one customer-assistant worker path has durable async refs,
timeout evidence, and cancellation semantics. It does not need to harden every
Chatflow/Workflow node; that belongs to 058+ after the shared runtime v2 design.
