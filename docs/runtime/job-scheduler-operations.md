# Runtime Job Scheduler Operations

Source specs: `specs/218-runtime-production-job-scheduler/`

## Database Engine And Pool Config

Runtime production scheduling uses the process-wide database engine from
`app.core.database.get_engine()`. `get_session_factory()` reuses the same engine
and sessionmaker until the cache is explicitly reset.

Pool settings are schema-driven through `HIFY_` environment variables:

| Setting | Default | SQLAlchemy argument |
|---|---:|---|
| `HIFY_DATABASE_POOL_SIZE` | `5` | `pool_size` |
| `HIFY_DATABASE_MAX_OVERFLOW` | `10` | `max_overflow` |
| `HIFY_DATABASE_POOL_TIMEOUT_SECONDS` | `30.0` | `pool_timeout` |
| `HIFY_DATABASE_POOL_RECYCLE_SECONDS` | `1800` | `pool_recycle` |
| `HIFY_DATABASE_POOL_PRE_PING` | `true` | `pool_pre_ping` |

Operational notes:

- Call `reset_engine_cache()` only in tests or controlled process reload paths.
- The engine still requires a MySQL8 URL; SQLite remains rejected by the runtime
  database boundary.
- Later spec 218 slices add atomic job claim, heartbeat, retry, DLQ, and
  standalone worker entry on top of this shared engine/session foundation.

## Heartbeat, Lease Renew, And Takeover

Runtime jobs are claimed with a worker id, lease token, lease expiry, and
heartbeat timestamp. A worker may renew only the lease it currently owns:

- `heartbeat(jobId, workerId, leaseToken)` extends `lease_expires_at` and writes
  `last_heartbeat_at`.
- `complete()` and `fail()` also require the current worker/token pair.
- If a worker crashes and the lease expires, another worker can claim the job;
  the previous worker's stale token can no longer complete, fail, or renew it.

MySQL deadlocks during concurrent claim are treated as retryable contention.
Claiming uses one atomic single-row update ordered by priority and id, then
loads the claimed row by lease token.

## DLQ Semantics

Runtime jobs enter the DLQ when they reach terminal `FAILED` after exhausting
their retry policy.

- `list_dlq()` returns failed jobs ordered by oldest update time, optionally
  filtered by owner type.
- `retry_dlq(jobId)` reopens a failed or ignored job by setting it back to
  `QUEUED`, clearing lease state, clearing `finished_at`, and making it
  immediately available.
- `ignore_dlq(jobId, reason)` marks a failed job as `IGNORED` and records the
  operator reason in `last_error`.

Ignored jobs are not returned by `list_dlq()`; they can still be explicitly
retried by id.

## Idempotency Layers And Proposed Actions

Runtime V2 protects duplicate execution at three layers:

- Run layer: start requests store the caller `idempotencyKey` in the
  `workflow_run_started` event; duplicate starts replay the existing run.
- Job layer: runtime job payloads carry `runId`, `ownerType`, `ownerId`,
  `idempotencyKey`, and `idempotencyLayer=run` so standalone workers can audit
  and recover the original start contract.
- Node layer: side-effect-capable nodes use a stable key
  `runtime-v2:{runId}:{nodeKey}:{nodeType}` while the execution record keeps the
  concrete `nodeRunId` for traceability.

High-risk write-like actions, including Chatflow handoff, expose a pending
`proposedAction` whose `idempotencyKey` matches the node side-effect protection
key. Retrying or recovering the same run/node must reuse that stable key instead
of deriving a new key from a transient node-run row.

## Standalone Worker Entry And Request Thread Offload

Production runtime jobs should be completed by a standalone worker process, not
by the API request thread. Set the API process to enqueue jobs only:

```bash
HIFY_RUNTIME_V2_REQUEST_THREAD_COMPLETION_ENABLED=false uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then run a worker process that claims both Workflow and Chatflow runtime jobs:

```bash
uv run python scripts/runtime_job_worker.py --owner both --worker-id runtime-v2-worker-1
```

The standalone entry resolves handlers through the runtime composition registry.
Owner filters are:

- `workflow`: Workflow jobs only.
- `chatflow`: Chatflow jobs only.
- `ai-assistant`: AI Assistant jobs only.
- `both`: compatibility filter for Workflow and Chatflow.
- `all`: all registered Workflow, Chatflow, and AI Assistant handlers.

The AI Assistant handler and owner filter are available at the Spec 226.3
foundation boundary. Durable enqueue from `messages/async`, takeover/cancel
fencing, and removal of the API in-process worker remain the separate 226.5 HA
gate; do not treat handler registration alone as that gate passing.

Operational controls:

- `--once` claims and runs at most one job, then exits.
- `--job-id <id>` claims a specific queued job, useful for safe manual replay or
  focused recovery.
- `--lease-seconds <seconds>` controls the claim lease duration.
- `--poll-interval <seconds>` controls idle polling delay.

Local developer mode keeps `HIFY_RUNTIME_V2_REQUEST_THREAD_COMPLETION_ENABLED`
enabled by default so existing synchronous smoke paths still complete without a
separate worker. Production-like UAT should disable it and verify runtime jobs
show a standalone `lease_owner`.
