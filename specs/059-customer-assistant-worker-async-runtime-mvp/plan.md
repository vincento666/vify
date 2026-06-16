# Plan 059: Customer Assistant Worker Async Runtime MVP

## Implementation Shape

Add a customer-assistant scoped worker runtime:

```text
customer_assistant_worker_run
customer_assistant_worker_event
```

or an explicitly documented durable equivalent.

Recommended first worker:

```text
StubQaWorker
```

It is low risk and avoids coupling this slice to Chatflow runtime v2.

## Runtime Contract

```text
POST /api/v1/customer-assistant/worker-runs
GET  /api/v1/customer-assistant/worker-runs/{workerRunId}
GET  /api/v1/customer-assistant/worker-runs/{workerRunId}/events
GET  /api/v1/customer-assistant/worker-runs/{workerRunId}/events/stream
GET  /api/v1/customer-assistant/worker-runs/{workerRunId}/result
POST /api/v1/customer-assistant/worker-runs/{workerRunId}/cancel
```

The route shape can be adjusted to match existing API conventions, but the refs
must be real and fetchable.

## Compatibility

The existing `LocalWorkerScheduler.run()` can keep returning `WorkerResult`.
When async mode is enabled for the selected worker, the scheduler may create a
worker run, wait for a short configured deadline, and either return the completed
result or return a pending result with refs.

## Risk Controls

- Keep storage customer-assistant scoped.
- Do not reuse Hify Workflow/Chatflow runtime event tables.
- Do not claim full cancellation if only cooperative cancellation exists.
- Do not convert all workers in this spec.
- Deduplicate worker creation by a stable idempotency key/request hash.
- Run background workers with their own DB session/unit of work.
- Treat persisted worker events as the observable source for status, replay, and
  UI evidence.
- Redact worker event payloads before persistence or display.
