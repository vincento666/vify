# Runtime V2 Capacity Report

## Scope

Spec 221 records production-upgrade acceptance for Runtime V2 after specs 213-220. This report keeps local-machine evidence separate from production-like drills so local hardware limits do not become product limits.

## Metrics

| Field | Meaning | Source |
|-------|---------|--------|
| `p50` / `p95` / `p99` | run or drill latency percentiles | load test samples |
| `queue_latency_ms` | time from runtime job enqueue to claim/start | runtime job rows |
| `node_latency_ms` | node started-to-completed duration | runtime node-run projection |
| `event_delay_ms` | event append-to-read delay | runtime event rows / stream replay |
| `error_rate` | failed samples / total samples | load test results |
| `resource_usage` | CPU / memory / FD observation where available | local process snapshot or manual note |

## Summary

| Scenario | Concurrency / Scale | p50 ms | p95 ms | p99 ms | Queue latency / state | Node latency | Event delay | Error rate | Resource usage |
|----------|---------------------|--------|--------|--------|-----------------------|--------------|-------------|------------|----------------|
| Local 20 | 20 concurrent runs | 1363.56 | 1399.01 | 1401.16 | request-thread completion | included in run latency | event sequence monotonic, 200 events read after terminal | 0% | not separately captured |
| Local 35 | 35 concurrent runs | 2176.87 | 2215.29 | 2216.09 | request-thread completion | included in run latency | event sequence monotonic, 350 events read after terminal | 0% | not separately captured |
| Local 50 | 50 concurrent runs | 2993.84 | 3060.66 | 3067.31 | request-thread completion | included in run latency | event sequence monotonic, 500 events read after terminal | 0% | not separately captured |
| Local 100 | 100 queued runs | 6902.64 | 7395.29 | 7428.01 | queued; 16 workers drained exact jobs | included in run latency | event sequence monotonic, 1000 events read after terminal | 0% | not separately captured |
| Local 150 | 150 queued runs | 10151.38 | 10832.26 | 10899.18 | queued; 16 workers drained exact jobs | included in run latency | event sequence monotonic, 1500 events read after terminal | 0% | not separately captured |
| Local 200 | 200 queued runs | 13521.22 | 14468.03 | 14592.46 | queued; 16 workers drained exact jobs | included in run latency | event sequence monotonic, 2000 events read after terminal | 0% | not separately captured |
| Multi-worker claim | 10 workers x 200 jobs | n/a | n/a | n/a | no duplicate claim/complete | n/a | n/a | 0% | disposable MySQL |
| DAG fan-out | 10/20 branches x 50 runs | n/a | n/a | n/a | queued worker drain | branch completion asserted | complete branch event set asserted | 0% | not separately captured |
| Resume no replay | 50 interrupt/resume runs | n/a | n/a | n/a | request-thread resume | side-effect node-run count stays 1 | event sequence monotonic | 0% | not separately captured |
| Worker crash | 10 crashes / 20 jobs | n/a | n/a | n/a | takeover after lease expiry | n/a | n/a | 0% | disposable MySQL |
| DB reconnect / Redis failure | pool dispose + stream failure | n/a | n/a | n/a | DB reconnect claim/complete | n/a | DB event recovery + outbox replay | 0% | disposable MySQL / in-memory stream |
| Slow external calls | 60s LLM / 120s API simulated | n/a | n/a | n/a | provider backpressure degraded | timeout/breaker event payload | n/a | expected failures classified | fake clock |

Raw metrics:

- `artifacts/slices/221-runtime-capacity-fault-acceptance/221.9/load-metrics.txt`
- `artifacts/slices/221-runtime-capacity-fault-acceptance/221.9/metrics.csv`
- `artifacts/slices/221-runtime-capacity-fault-acceptance/221.9/metrics.json`

## Local 20-50 Concurrent Runs

Status: GREEN on 2026-07-04.

Acceptance command:

```bash
rtk uv run pytest tests/integration/runtime/load -q -k concurrent_20_50
```

Result: `3 passed, 1 warning in 7.66s`.

Baseline config: test-local pool override `HIFY_DATABASE_POOL_SIZE=64`, `HIFY_DATABASE_MAX_OVERFLOW=64`, `HIFY_DATABASE_POOL_TIMEOUT_SECONDS=60`. The initial RED showed default pool `5 + 10` is too small for 50 concurrent request-thread completions on this machine, so 221.1 validates functional correctness under an explicit local acceptance pool instead of default low-footprint settings.

Observed behavior: 20, 35, and 50 concurrent workflow runs all reached `SUCCEEDED`, every run returned its unique final output, and each run's runtime event sequence was strictly monotonic from sequence `1`.

## Local 100-200 Concurrent Runs

Status: GREEN on 2026-07-04.

Acceptance command:

```bash
rtk uv run pytest tests/integration/runtime/load -q -k concurrent_100_200
```

Result: `3 passed, 3 deselected, 1 warning in 35.17s`.

Regression command after shared helper extraction:

```bash
rtk uv run pytest tests/integration/runtime/load -q -k "concurrent_20_50 or concurrent_100_200"
```

Result: `6 passed, 1 warning in 43.93s`.

Baseline config: request-thread completion disabled, queue-backed runtime jobs drained by 16 bounded workflow workers, test-local DB pool `HIFY_DATABASE_POOL_SIZE=64`, `HIFY_DATABASE_MAX_OVERFLOW=32`, `HIFY_DATABASE_POOL_TIMEOUT_SECONDS=90`.

RED finding: running 100 / 150 / 200 with request-thread completion and pool `256 + 256` overloaded local MySQL (`1040 Too many connections`). The GREEN path uses the intended spec 218 production shape: concurrent enqueue, queued jobs, bounded workers, terminal result polling, and monotonic event replay.

Observed behavior: 100, 150, and 200 concurrent workflow invocations were admitted as queued jobs, all jobs were drained by workers, all runs reached `SUCCEEDED`, outputs remained unique, event sequences stayed monotonic, and p99 start-to-terminal latency stayed below the local smoke threshold of `120000` ms.

## Multi-Worker Claim

Status: GREEN on 2026-07-04.

Acceptance commands:

```bash
rtk uv run pytest tests/contract/runtime_jobs/test_multi_worker_no_duplicate.py -q
rtk uv run pytest tests/contract/runtime_jobs -q
rtk uv run pytest tests/integration/runtime_jobs -q
```

Results:

- Targeted: `1 passed in 2.03s`.
- Contract suite: `8 passed, 1 warning in 10.96s`.
- Integration suite: `8 passed, 1 warning in 12.45s`.

Scenario: 10 workers concurrently claim and complete 200 workflow runtime jobs in a disposable MySQL database. Acceptance requires 200 completed claims, 200 unique job ids, 200 unique run ids, all jobs `COMPLETED`, and `attempt_count=1`.

RED finding: `RuntimeJobRepository.complete()` could surface MySQL 1213 deadlocks under concurrent completion. The fix adds bounded retry for 1213 / SQLSTATE 40001 / deadlock messages, matching the existing claim-side contention behavior.

## DAG Fan-Out Stress

Status: GREEN on 2026-07-04.

Acceptance command:

```bash
rtk uv run pytest tests/integration/runtime/load -q -k dag_fanout
```

Result: `2 passed, 6 deselected, 1 warning in 16.90s`.

Load regression:

```bash
rtk uv run pytest tests/integration/runtime/load -q
```

Result: `8 passed, 1 warning in 58.26s`.

Scenario: two fan-out workflows with 10 and 20 parallel `MESSAGE` branches. Each workflow receives 50 concurrent runtime invocations through queued jobs and 16 bounded workers. Acceptance checks each run's final output contains every branch result, each branch emits one completed event, `END` completes once, and runtime event sequence stays monotonic.

Observed behavior: all 100 fan-out runs completed successfully; branch result aggregation and event sets stayed consistent for 10-way and 20-way fan-out.

## Interrupt / Resume No Side-Effect Replay

Status: GREEN on 2026-07-04.

Acceptance command:

```bash
rtk uv run pytest tests/integration/runtime/load -q -k resume_no_side_effect
```

Result: `1 passed, 8 deselected, 1 warning in 5.67s`.

Load regression:

```bash
rtk uv run pytest tests/integration/runtime/load -q
```

Result: `9 passed, 1 warning in 63.82s`.

Scenario: 50 concurrent Chatflow Runtime V2 runs fan out from START to a `CODE` side-effect node and a `QUESTION` waiting node. After all runs interrupt, 50 resume requests are sent concurrently. Acceptance requires `notify_1` to have exactly one node-run before and after resume for every run, resumed outputs to include the preserved side-effect value, waiting node projections to clear, and event sequences to stay monotonic.

Observed behavior: all 50 interrupted runs resumed to `SUCCEEDED`; no completed side-effect node replayed.

## Worker Crash And Takeover

Status: GREEN on 2026-07-04.

Acceptance command:

```bash
rtk uv run pytest tests/integration/runtime/chaos -q -k worker_crash
```

Result: `1 passed in 1.47s`.

Scenario: 20 jobs in disposable MySQL; 10 simulated worker crashes claim a job, lose the lease, and are replaced by takeover workers. Stale worker completion is rejected after takeover. Remaining jobs drain normally.

Observed behavior: all jobs completed, exactly the crash-takeover jobs had `attempt_count=2`, stale lease tokens could not write back, and takeover workers completed with new lease tokens.

## DB Reconnect And Redis Failure

Status: GREEN on 2026-07-04.

Acceptance command:

```bash
rtk uv run pytest tests/integration/runtime/chaos -q -k "db_reconnect or redis_failure"
```

Result: `2 passed, 1 deselected in 2.56s`.

Chaos regression:

```bash
rtk uv run pytest tests/integration/runtime/chaos -q
```

Result: `3 passed in 3.91s`.

DB reconnect scenario: dispose the SQLAlchemy engine pool after enqueuing a runtime job, then open a fresh session and claim/complete the job. Redis failure scenario: force stream publish failure, recover event from DB, confirm failed outbox row, replay to a healthy in-memory stream bus.

Observed behavior: DB pool disposal did not prevent runtime job claim/complete, Redis publish failure did not drop the durable DB event, and outbox replay republished the missed event.

## Slow External Calls

Status: GREEN on 2026-07-04.

Acceptance command:

```bash
rtk uv run pytest tests/integration/runtime/chaos -q -k slow_external
```

Result: `1 passed, 3 deselected in 0.23s`.

Chaos regression:

```bash
rtk uv run pytest tests/integration/runtime/chaos -q
```

Result: `4 passed in 3.88s`.

Scenario: fake-clock 60-second LLM call against 100 ms deadline with one retry, fake-clock 120-second API call against 100 ms deadline, second LLM call after breaker opens, and provider-level concurrency backpressure.

Observed behavior: slow calls were classified as `timeout`, breaker state opened, the open breaker short-circuited without executing the provider operation, and provider-level active limit returned `degraded` / `admitted=false`.
