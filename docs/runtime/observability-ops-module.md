# Runtime Observability Ops Module

## 220.1 Main Menu Entry And Route

- Route: `/runtime-ops`
- Route name: `HifyRuntimeOps`
- Main menu label: `运行观测`
- Baseline read permission: `runtime_ops:read`

The frontend permission gate is host-scoped: if the host runtime config provides a
`permissions` array, `runtime_ops:read` is required; if no permissions array is
provided, local development remains open.

## 220.2 Run List Filters

The runtime ops run list reads the existing Runtime V2 fact tables:

- `workflow_run` supplies run id, status, timestamps, elapsed time, and refs.
- `workflow` supplies owner display name and fallback owner type.
- `runtime_jobs` supplies owner type/id, queue state, tenant id, lease owner, heartbeat, and retry timestamps.

Endpoint:

- `GET /api/v1/runtime-runs`

Supported query params:

- `ownerType`: `WORKFLOW`, `CHATFLOW`, `CUSTOMER_ASSISTANT`, or `SOP`
- `state`: `queued`, `running`, `waiting`, `succeeded`, `failed`, or `cancelled`
- `tenantId`
- `createdFrom`
- `createdTo`
- `page`
- `pageSize`

## 220.3 Run Detail DAG Status View

The run detail DAG view reuses existing Runtime V2 node projection:

- `GET /api/v1/runtime-runs/{runId}`
- `GET /api/v1/runtime-runs/{runId}/nodes`

Node cards render `selectionState.state` first, falling back to runtime node status.
The visible state set is `completed`, `skipped`, `running`, `waiting`, `failed`,
`cancelled`, and `pending`. Selected and skipped upstream links are displayed from
`selectedUpstreamNodeKeys` and `skippedUpstreamNodeKeys`.

## 220.4 Node Detail And Event Timeline

Clicking a DAG node opens a node detail panel composed from:

- node run projection from `GET /api/v1/runtime-runs/{runId}/nodes`
- run event timeline from `GET /api/v1/runtime-runs/{runId}/events`

The panel shows input summary, output summary, elapsed duration, error evidence,
and node-scoped runtime events. Reasoning and chain-of-thought fields are hidden
by default, including nested `reasoning`, `thought`, `chainOfThought`, and
provider debug reasoning under `__debug`.

## 220.5 Job Queue And Worker Heartbeat

The Runtime Ops Jobs tab is a read-only view over `runtime_jobs`.

Endpoint:

- `GET /api/v1/runtime-jobs`

Supported query params:

- `ownerType`: `WORKFLOW`, `CHATFLOW`, `CUSTOMER_ASSISTANT`, or `SOP`
- `status`: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, or `IGNORED`
- `tenantId`
- `page`
- `pageSize`

The API exposes `jobId`, `runId`, `ownerType`, `ownerId`, `status`, `leaseOwner`,
`lastHeartbeatAt`, `leaseExpiresAt`, `attemptCount`, `maxAttempts`, `availableAt`,
`nextRetryAt`, `lastError`, `createdAt`, and `updatedAt`. `nextRetryAt` mirrors
`availableAt` so queued retry jobs can be inspected without knowing the internal
scheduler column name.

The frontend Jobs tab renders job rows with worker lease owner, last heartbeat,
lease expiry, attempt count, next retry time, tenant id, and latest error
evidence. It does not claim, retry, ignore, or otherwise mutate jobs; operator
actions remain deferred to later Runtime Ops slices.

## 220.6 DLQ List And Actions

The DLQ view is the failed-job subset of `runtime_jobs`.

Endpoints:

- `GET /api/v1/runtime-jobs/dlq`
- `POST /api/v1/runtime-jobs/{jobId}/retry`
- `POST /api/v1/runtime-jobs/{jobId}/ignore`
- `POST /api/v1/runtime-jobs/{jobId}/mark-resolved`

The list endpoint supports `ownerType`, `tenantId`, `page`, and `pageSize`.
Actions return the same Runtime Ops job projection used by the queue list.

Action semantics:

- `retry`: moves a failed or ignored DLQ job back to `QUEUED`, clears lease
  fields, clears `availableAt`, and keeps the latest error as failure evidence.
- `ignore`: moves a failed job to `IGNORED`, clears lease fields, sets
  `finishedAt`, and stores the operator reason in `lastError`.
- `mark-resolved`: moves a failed job to `RESOLVED`, clears lease fields, sets
  `finishedAt`, and stores the operator reason in `lastError`.

`IGNORED` and `RESOLVED` jobs are no longer returned by the DLQ list. Reopening
or broader audited operator actions are intentionally left to the safe-actions
slice.

## 220.7 Safe Operator Actions

Runtime Ops exposes four confirmed operator actions:

- cancel runtime run: `POST /api/v1/runtime-runs/{runId}/cancel`
- resume interrupted runtime run: `POST /api/v1/runtime-runs/{runId}/resume`
- retry failed runtime job: `POST /api/v1/runtime-jobs/{jobId}/retry`
- reopen closed DLQ item: `POST /api/v1/runtime-jobs/{jobId}/reopen`

The frontend requires a browser confirmation before each action. Run-list actions
render Cancel and Resume controls; job-list actions render Retry for failed jobs
and Reopen for ignored or resolved DLQ jobs.

Every safe action writes an `audit_record` row with the host request context:

- `RUNTIME_OPS_CANCEL_RUN`
- `RUNTIME_OPS_RESUME_RUN`
- `RUNTIME_OPS_RETRY_JOB`
- `RUNTIME_OPS_REOPEN_DLQ`

`reopen` changes an `IGNORED` or `RESOLVED` runtime job back to `FAILED`, clears
lease fields, keeps the row durable, and stores the operator reason in
`lastError`. Broader permission modeling remains guarded by the host-scoped
`runtime_ops:read` surface until a write permission is introduced.

## 220.8 Provider / API / Tool Stats

Runtime Ops computes call statistics on the frontend from existing Runtime V2
observability projections:

- node run rows from `GET /api/v1/runtime-runs/{runId}/nodes`
- run events from `GET /api/v1/runtime-runs/{runId}/events`
- job queue rows from `GET /api/v1/runtime-jobs`
- DLQ rows from `GET /api/v1/runtime-jobs/dlq`

No new backend fields are introduced. The Stats tab groups external call
activity into:

- Provider: LLM calls and `llm:*` provider keys
- API: API call nodes and `api:*` provider keys
- Tool: tool call nodes and `tool:*` provider keys

For each group the UI displays total calls, failed calls, and retry count. Failed
external-call events are listed with `providerKey`, `errorKind`, attempts,
retry count, and breaker-open evidence when present.

The failure/retry panel also includes runtime job retry rows and DLQ rows so an
operator can see provider/API/tool failure evidence next to scheduler retry
state without leaving the Runtime Ops module.

## 220.9 Realtime Updates

Runtime Ops subscribes to the existing Runtime V2 event stream after a run is
selected:

```text
GET /api/v1/runtime-runs/{runId}/events/stream?afterSequence=<last-sequence>
```

The frontend uses `fetch` instead of browser `EventSource` so host context
headers can be sent with the stream request. Incoming `data:` frames are parsed
as runtime events, merged into the selected run timeline, and applied to the DAG
node projection when the event references a node.

Reconnect rules mirror spec 219:

- the initial stream starts from the max sequence already loaded by
  `GET /api/v1/runtime-runs/{runId}/events`
- if the stream closes, Runtime Ops reconnects with the latest observed
  `afterSequence`
- the UI exposes live state, latest sequence, reconnect count, and latest event
  type so operators can tell whether the panel is current

This slice does not change the SSE backend; it only consumes the existing
runtime event stream in the Runtime Ops module.
