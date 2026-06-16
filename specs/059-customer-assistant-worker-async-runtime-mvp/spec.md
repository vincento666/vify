# Spec 059: Customer Assistant Worker Async Runtime MVP

## Goal

Turn one customer-assistant worker path into a real asynchronous worker runtime
instead of returning only payload-level worker refs from the parent assistant
run.

The MVP must prove that a worker has its own durable run identity, status,
events, result, and cancellation semantics. It must not attempt to generalize
all Hify Workflow/Chatflow execution.

## Dependency

059 depends on:

- 048 customer-assistant L1 SSE event stream;
- 052 harness-compatible customer-assistant sub-agent refs;
- 056 worker runtime hardening and timeout/cancel evidence;
- 060 MySQL 8 migration readiness if the active implementation target is MySQL.

## Product Boundary

In scope:

- `customer_assistant_worker_run` and worker event persistence, or an explicit
  durable equivalent;
- `workerRunId`, `workerStatusRef`, `workerEventStreamRef`, `workerResultRef`;
- one low-risk worker path, preferably `StubQaWorker` or `RestrictedReactWorker`;
- worker status lifecycle: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`,
  `TIMED_OUT`, `CANCELLED`, `CANCEL_UNSUPPORTED`;
- event replay by sequence;
- cooperative cancellation or explicit `cancel_unsupported`;
- compatibility with the existing synchronous customer-assistant turn.

Out of scope:

- async `ChatflowSopWorker`;
- Hify Workflow/Chatflow runtime v2 storage;
- distributed queue infrastructure;
- hard process kill guarantees;
- standardizing all ReAct worker behavior.

## Hard Constraints

- Worker refs must point to a real worker run, not only the parent assistant run.
- Timeout must not be described as hard cancellation unless the worker is truly
  stopped.
- Cancellation must emit durable events even when unsupported.
- Existing customer-assistant run and task ledger behavior must remain
  compatible.
- Worker creation must be idempotent for a stable assistant run/task/worker
  request; retries must not spawn duplicate worker runs.
- Worker event payloads must not persist secrets, credentials, or raw provider
  payloads unless explicitly redacted.

## Runner Boundary

The async worker runner must be a real execution boundary:

- background execution opens its own database session or unit of work;
- request-scoped sessions must not be reused after the HTTP request returns;
- terminal status transitions are monotonic and guarded against late writes;
- event sequence is unique per worker run and replayable after reconnect;
- process restart either recovers the persisted terminal state or marks an
  interrupted run with an explicit recovery/failure event.

An implementation that only returns `workerRunId` inside the parent payload
after synchronous execution completes does not satisfy this spec.

## Acceptance Criteria

- One worker can be started and observed through worker status/result/event refs.
- Repeated create/retry with the same idempotency key does not create duplicate
  worker runs.
- Worker events can be streamed or listed after reconnect.
- A timeout produces durable timeout events and a terminal worker result.
- A cancellation request records either `worker_cancelled` or
  `worker_cancel_unsupported`.
- Background worker execution does not depend on request-scoped database
  sessions.
- Existing assistant turn tests remain green.

## MVP Exit

059 is complete when one worker path has a durable async lifecycle. Other worker
types may still run through the legacy scheduler.
