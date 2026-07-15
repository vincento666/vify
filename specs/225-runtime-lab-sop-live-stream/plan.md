# Plan 225: RuntimeLab SOP live stream over Runtime V2

## Architecture

```text
RuntimeLab Vue POST :stream
  -> RuntimeLab SSE adapter
  -> SOP router / Chatflow adapter
  -> RuntimeInvocationGateway start_or_resume_and_stream_ref
  -> durable Runtime V2 job + standalone Chatflow worker
  -> Runtime V2 lifecycle event log
  -> RuntimeLab SSE projection and reconnect cursor
```

For an LLM node, the worker consumes an asynchronous provider chunk iterator.
It emits ordered, bounded `llm_delta` event batches to the existing Runtime V2
event append path before it writes final node output and node/run completion.
The RuntimeLab adapter maps these and existing lifecycle rows into its public
`delta|done|error` envelopes. It does not manufacture token events from final
output.

## Implementation Constraints

- Reuse the Runtime V2 durable event log, stream cursor, job ownership, and
  standalone Chatflow worker. Do not introduce another queue or polling loop.
- Keep SQLAlchemy sessions out of SSE generators and provider awaits.
- Bound request-side resources: cancel stream subscriptions on disconnect,
  preserve worker execution, and use existing heartbeat/backpressure rules.
- Preserve child-run references in RuntimeLab payload/ledger records. The UI
  projects the child ledger; it does not recreate execution-state mirrors.
- Batch only adjacent provider text from one node/run, preserving sequence and
  terminal ordering. Flush on 100 ms, 256 characters, node completion,
  cancellation, or error.
- If the current provider facade has no async stream primitive, add the smallest
  capability-oriented protocol and adapters required for existing configured
  providers. Do not silently wrap a blocking full completion as token stream.

## Delivery Sequence

1. 225.1: write a public API test for the absent stream route. Make the
   smallest gateway-backed SSE tracer green with a fake durable event source.
2. 225.2: write a fake-provider RED proving a pre-completion chunk boundary;
   implement the provider/runtime event path and non-stream fallback.
3. 225.3: write resume and request-path RED tests; replace wait/inline paths
   with a reference-returning gateway operation and worker execution.
4. 225.4: write UI RED tests for incremental merge/reconnect; implement
   stream client lifecycle, cleanup, and JSON fallback.
5. 225.5: run required regression and independent review. Correct only the
   stale execution-state-mirror E2E assertion confirmed against Spec 216.
6. 225.6: introduce an async-capable shared Provider Transport behind the
   existing synchronous facade. First prove the contract with a deterministic
   transport: streams obey a configured process-local provider concurrency
   bound without blocking their event loop, cancellation closes the request,
   partial visible output is never retried wholesale, and non-stream callers preserve their
   response/error shape. Then prove Customer Assistant
   SSE, worker, and shadow compatibility without changing its public behavior.
7. 225.7: extend only the existing in-process Runtime V2 frontier executor.
   Start with a public LLM fan-out overlap RED proof, then add KNOWLEDGE and
   safe-TOOL waves one vertical behavior at a time. A safe Tool receives a
   stable run/node idempotency key before dispatch and returns a receipt;
   nonconforming Tools remain serial/rejected. Add a deadline/cancellation
   controller that makes node timeout terminal immediately, fences late
   commits, and emits sanitized failure data. Preserve RuntimeLab `error` and
   add `failure`; direct workflow callers receive standard failure
   `errorCode`/generic-message data while retaining its existing envelope.
   Failed Chatflow runs are turn-scoped so the next
   interaction is not poisoned. Do not add a ledger, migration, queue,
   capacity change, or automatic node retry.
8. 225.8: preserve the existing Redis realtime fast path but make its read
   projection resilient to cross-process/outbox publication order. Sort and
   deduplicate currently visible Redis records by their durable `sequence`.
   When an ordered live batch has any cursor discontinuity, use a fresh
   short-lived database session to read the durable backlog and emit it
   first. This is an SSE read-side recovery only: no Redis publisher protocol,
   distributed lock, schema migration, or queue is added.

## Stop / Escalate

Stop and obtain a new contract if implementation requires a migration,
node-attempt ledger, Customer Assistant public behavior/API/worker change,
worker capacity/deployment change, new scheduler/queue, new dependency,
auth/permission change, automatic node retry, or real-provider spending.
Record any failed gate and next diagnosis in the slice evidence instead of
treating an unrun gate as pass.
