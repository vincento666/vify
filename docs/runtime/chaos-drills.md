# Runtime V2 Chaos Drills

## Scope

Spec 221 chaos drills validate the production-upgrade runtime under controlled failure modes. Automated tests use deterministic local simulations where killing real infrastructure would make the developer gate flaky; production-like environments should run the matching manual drill.

## Worker Crash And Takeover

Automated gate:

```bash
rtk uv run pytest tests/integration/runtime/chaos -q -k worker_crash
```

Local simulation:

1. Enqueue runtime jobs in a disposable MySQL database.
2. Let a worker claim a job and then stop sending heartbeat or completion.
3. Expire the lease to model a crashed worker.
4. Let another worker claim the same job with a new lease token.
5. Verify stale completion from the crashed worker is rejected.
6. Verify takeover worker completes the job and all jobs drain.

Production-like manual drill:

1. Start at least two standalone runtime workers with request-thread completion disabled.
2. Enqueue a batch of workflow runtime jobs.
3. Kill one worker process with `kill -9 <pid>` after it has claimed work.
4. Wait for lease expiry.
5. Confirm another worker claims the job, completes it once, and Runtime Ops shows no duplicate execution.

Acceptance: crashed-worker lease token cannot complete after takeover, takeover uses a new lease token, all jobs complete, and only crash-takeover jobs increment `attempt_count` to `2`.

## DB Reconnect

Automated gate:

```bash
rtk uv run pytest tests/integration/runtime/chaos -q -k db_reconnect
```

Local simulation:

1. Enqueue a runtime job in a disposable MySQL database.
2. Dispose the SQLAlchemy engine pool to simulate lost pooled DB connections.
3. Open a fresh session from the same factory.
4. Claim and complete the queued job.

Production-like manual drill:

1. Run API and standalone workers against a disposable DB instance.
2. Restart DB or cut existing worker DB connections.
3. Confirm pool pre-ping / reconnect opens fresh connections.
4. Confirm queued jobs can still be claimed and completed.

Acceptance: no job is lost, a fresh session can claim after pool disposal, and completed job ownership reflects the reconnecting worker.

## Redis Failure And DB Event Recovery

Automated gate:

```bash
rtk uv run pytest tests/integration/runtime/chaos -q -k redis_failure
```

Local simulation:

1. Append a runtime event with a stream bus that raises on publish.
2. Confirm the event remains queryable from DB event storage.
3. Confirm event outbox records the failed publish.
4. Replay the outbox into a healthy stream bus.

Production-like manual drill:

1. Run API with Redis stream acceleration enabled.
2. Stop or firewall Redis while DB stays available.
3. Confirm SSE clients can recover from DB event cursor.
4. Restore Redis and replay failed event outbox rows.

Acceptance: Redis publish failure does not drop the DB event, DB cursor recovery still works, and outbox replay republishes the missed event once Redis is healthy.

## Slow External Calls

Automated gate:

```bash
rtk uv run pytest tests/integration/runtime/chaos -q -k slow_external
```

Local simulation:

1. Use the Runtime V2 external-call governance wrapper with a fake clock.
2. Simulate a 60-second LLM call against a 100 ms deadline with one retry.
3. Confirm timeout classification, two attempts, and breaker-open event payload.
4. Call the same provider again and confirm circuit-open short-circuit without executing the operation.
5. Simulate a 120-second API call against a 100 ms deadline and confirm timeout + breaker-open.
6. Apply provider-level concurrency limit and confirm new work is degraded as backpressure.

Production-like manual drill:

1. Route LLM/API nodes to a controlled slow mock provider.
2. Configure low timeout / retry / breaker thresholds.
3. Start enough runs to exceed provider active limit.
4. Confirm Runtime Ops shows external-call failure events, breaker-open payloads, degraded backpressure, and no uncontrolled request-thread buildup.

Acceptance: slow calls are classified as `timeout`, breaker state opens after configured failures, open breaker avoids extra provider calls, and provider-level backpressure returns degraded state rather than unbounded execution.
