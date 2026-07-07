# Runtime Event, Cancel, Rate Limit Operations

Source specs: `specs/219-runtime-event-cancel-ratelimit-backpressure/`

## SSE Reconnect / Outbox Compensation

Runtime events use the database as the source of truth and Redis Streams, or an
equivalent `RuntimeEventStreamBus`, as the realtime acceleration layer.

Reconnect rules:

- Clients resume with `afterSequence`.
- The SSE endpoint first performs a non-blocking stream-bus probe.
- If the stream has no immediate rows, the endpoint returns any database events
  with `sequence > afterSequence` without waiting for the heartbeat interval.
- If both realtime and database sources are empty, the endpoint waits on the
  stream bus for the heartbeat interval, then polls the database again to close
  the race between commit and publish.

This keeps reconnect latency bounded by a quick database read while preserving
Redis Streams as the low-latency path for already-buffered events.

Publish compensation:

- `chatflow_event` remains the durable fact source.
- When a realtime bus is configured, each committed event creates a
  `runtime_event_outbox` row before publish.
- Successful publish marks the outbox row `PUBLISHED`.
- Failed publish marks the row `FAILED`, increments `attempt_count`, and stores
  a bounded `last_error`.
- `ChatflowStateRepository.replay_event_outbox()` republishes `PENDING` and
  `FAILED` rows to a supplied stream bus and marks successful rows `PUBLISHED`.

Operational query examples:

```sql
SELECT id, run_id, event_id, sequence, status, attempt_count, last_error
FROM runtime_event_outbox
WHERE status IN ('PENDING', 'FAILED')
ORDER BY updated_at ASC, id ASC
LIMIT 100;
```

Outbox replay must use the same committed event payload shape used by normal
publishes. Normal replay excludes `PUBLISHED` rows, so repeated operator runs
only target rows that still need compensation. Consumers should keep using
`runId` + `sequence` cursors when reading streams, because Redis Streams itself
does not deduplicate manually republished entries.

## DAG Concurrent Node Event State

Frontend runtime v2 debug state treats each node as an independent state row
keyed by `nodeKey`. Concurrent fan-out events are merged into the node-state
store instead of replacing the whole run projection.

Event mapping rules:

- `workflow_node_started` maps to `RUNNING`.
- `workflow_node_completed` maps to `COMPLETED`.
- `workflow_node_failed` maps to `FAILED`.
- `workflow_node_waiting` maps to `WAITING`.
- `workflow_node_skipped` maps to `SKIPPED`.

Node event payloads may include `selectionState`. The frontend preserves that
metadata so active and inactive branch edges can be rendered before a later
node-list poll arrives. Completed events may report `payload.outputs` or
`payload.output`; both are accepted as node outputs. If a later event omits
outputs or selection metadata, the frontend keeps the previous values for that
node instead of erasing them.

This matters for explicit fan-out waves: two or more child nodes can be
`RUNNING` at the same time, one branch can be `SKIPPED`, and a downstream join
can be `WAITING` or `COMPLETED` while still retaining selected/skipped upstream
metadata for canvas edge classes.

## Cancel Semantics And Deadline

Runtime V2 cancel is applied at the run, runtime-job, checkpoint, and active
node-run layers so queued, waiting, and running executions converge on the same
terminal shape.

API contract:

- `POST /api/v1/runtime-runs/{runId}/cancel` accepts optional `reason` and
  `deadlineMs`.
- The response remains the normal runtime result envelope and adds
  `cancellation.phase`, `deadlineMs`, `deadlineAt`, `cancelledNodeKeys`, and
  `runtimeJobStatus`.
- Terminal or already-cancelled runs are idempotent: callers still receive a
  result with `cancellation.applied=false`.

Phase rules:

- `queued`: a runtime job exists and no node has started. Cancel marks the job
  `CANCELLED`; unstarted nodes remain absent from node-run projection.
- `waiting`: a waiting checkpoint exists or the run is interrupted. Cancel
  completes the checkpoint and marks active waiting node-runs `CANCELLED`.
- `running`: at least one active node-run is `RUNNING` or `WAITING`. Cancel
  marks those node-runs `CANCELLED`, emits `workflow_node_cancelled` and
  `node_status_changed`, and prevents downstream scheduling.
- `scheduled`: the run was cancellable but no job/checkpoint/active node-run
  was present when cancel was applied.

Cooperative checks happen before each frontier wave, before each pre-started
node, before node execution, and again before node success is persisted. If a
request thread or standalone worker finishes an external call after the run was
cancelled, the node-run is not converted back to `SUCCEEDED` and
`workflow_run_completed` is not emitted.

Standalone workers treat a job that was cancelled while the worker was running
as a terminal idempotent outcome. If job completion fails because the lease is
no longer owned, the worker re-reads the job and returns `CANCELLED` or
`IGNORED` instead of turning a successful cancellation into a worker error.

Browser UAT for this slice uses a local delayed OpenAI-compatible provider to
exercise a real LLM node HTTP call without depending on external model latency
or persisting any real provider secret.

## External Call Governance

Runtime V2 external nodes share one governance layer for LLM, API, Tool, and
Knowledge calls. The layer normalizes timeout, retry, circuit-breaker, and error
event metadata while preserving existing node-specific executors.

Policy fields are read from node config:

- `timeoutMs`: max expected elapsed time in milliseconds. If only `timeout` is
  present, it is treated as seconds for compatibility with existing API node
  config.
- `retryCount`: number of retries after the first failed attempt.
- `breakerFailureThreshold`: failed attempts required to open the provider
  breaker.
- `breakerResetMs`: time before an opened breaker is allowed to reset.

Runtime behavior:

- LLM nodes use provider key `llm:{modelConfigId|model|default}`.
- API nodes use provider key `api:{resourceId|url|endpoint|direct}`.
- Tool nodes use provider key `tool:{resourceId|toolName|default}`.
- Knowledge nodes use provider key `knowledge:{knowledgeBaseId|default}`.
- A successful call clears the provider breaker's failure count.
- Exhausted failures increment the failure count by attempts; when the threshold
  is reached, later calls fail fast with `errorKind=circuit_open` until reset.

When governance rejects or exhausts a call, Runtime V2 emits
`workflow_node_external_call_failed` before the existing
`workflow_node_failed` / handled-error event. The payload includes:

- `callType`
- `providerKey`
- `nodeKey`
- `nodeRunId`
- `nodeType`
- `errorKind`
- `message`
- `attempts`
- `timeoutMs`
- `retryCount`
- `breakerOpen`

This event is intentionally additive so existing consumers that only listen for
`workflow_node_failed` keep working, while operations tooling can distinguish
provider timeout, provider error, and open-breaker failures.

## Multi-Level Concurrency Limits And Queue States

Runtime V2 queue admission uses five explicit limit levels. All limits default
to `0`, which means disabled, so existing local and CI flows keep their current
behavior unless an operator opts in.

Configuration:

- `HIFY_RUNTIME_V2_TENANT_ACTIVE_LIMIT`
- `HIFY_RUNTIME_V2_WORKFLOW_ACTIVE_LIMIT`
- `HIFY_RUNTIME_V2_CHATFLOW_ACTIVE_LIMIT`
- `HIFY_RUNTIME_V2_WORKER_RUNNING_LIMIT`
- `HIFY_RUNTIME_V2_PROVIDER_ACTIVE_LIMIT`
- `HIFY_RUNTIME_V2_QUEUE_CAPACITY_LIMIT`

Queue gate inputs:

- Tenant: request host context `tenantId`, defaulting to `local`.
- Workflow / Chatflow: runtime owner type and owner id.
- Worker: running job `lease_owner`.
- Provider: provider keys derived from Runtime V2 node definitions:
  `llm:*`, `api:*`, `tool:*`, and `knowledge:*`.
- Queue capacity: current `QUEUED` runtime jobs.

Decision priority and states:

- Tenant limit reached: `rate_limited`, not admitted.
- Queue capacity reached: `rejected`, not admitted.
- Workflow or Chatflow active limit reached: `queued`, admitted, but inline
  request-thread completion is not started.
- Worker running limit reached: `queued`, admitted, but inline request-thread
  completion is not started.
- Provider active limit reached: `degraded`, not admitted.
- No limit reached: `queued`, admitted, normal inline completion may start.

For `/workflows/{id}/runs` and `/chatflows/{id}/runs`, the response includes a
`queueState` payload with `status`, `admitted`, `level`, `current`, `limit`, and
`reason`. Admitted jobs store `tenantId` and `providerKeys` in the runtime job
payload for later queue-gate decisions. Non-admitted runs are cancelled
immediately with a queue-specific cancel reason; this avoids leaving unclaimable
runtime runs in `RUNNING`.

## High-Frequency Event Compaction

Runtime V2 compacts high-frequency event types before writing to
`chatflow_event` and the outbox. The current high-frequency set is:

- `llm_delta`
- `agent_delta`
- `node_progress`
- `tool_delta`
- `token_delta`

Compaction policy:

- Keep the first 5 events for each `(runId, nodeKey, eventType)` unchanged.
- After that, write `runtime_event_summary` events instead of every raw event.
- Summary payloads include `compactedEventType`, cumulative `sampledCount`,
  `latestPayload`, and the policy values `keepFirst` / `sampleInterval`.
- Non-sampled events update the latest summary row rather than creating a new
  event row, so the DB fact source retains the latest payload while event row
  growth stays bounded.

Critical runtime events are never compacted because they are not in the
high-frequency set. This preserves run lifecycle, node lifecycle, failure,
waiting/resume, cancel, user/assistant message, and final output semantics for
clients and operators.

## Future Sections

The remaining spec 219 slices extend this document with:

- Spec 219 exit regression and baseline update.
