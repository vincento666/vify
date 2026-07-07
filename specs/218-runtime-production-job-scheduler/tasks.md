# Tasks — Spec 218

证据根目录：`artifacts/slices/218-runtime-production-job-scheduler/<slice>/`

## Slice 218.1 — DB engine/session factory reuse & pool config schema

- [x] RED：写 `tests/unit/core/test_database_factory.py`、`test_pool_config.py`，断言全局共用 engine + pool 参数可配；当前应红；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.1/red.txt`
- [x] GREEN：新增 `DatabasePoolConfig`、全局 engine/session factory cache、`reset_engine_cache()`；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.1/green-targeted.txt`
- [x] Unit：`rtk uv run pytest tests/unit/core -q` 全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.1/unit.txt`
- [x] Integration：`rtk uv run pytest tests/integration -q` 不回归；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.1/integration.txt`
- [x] Docs：新增 `docs/runtime/job-scheduler-operations.md` 并写 pool config 章节；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.1/docs-check.txt`
- [x] Git commit：`feat(core): centralize DB engine and expose pool config`

## Slice 218.2 — Atomic runtime job claim

- [x] RED：写 `tests/contract/runtime_jobs/test_claim_atomic.py`，N=20 并发 claim 同一 batch 断言无重复；当前应红；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.2/red.txt`
- [x] GREEN：`claim_next` 使用单条 MySQL 原子 `UPDATE ... ORDER BY ... LIMIT 1` + lease token 反查，并对 deadlock 做有限重试；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.2/green-targeted.txt`
- [x] Contract：`rtk uv run pytest tests/contract/runtime_jobs -q` 全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.2/contract.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime_jobs -q` 全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.2/integration.txt`
- [x] Git commit：`feat(runtime-jobs): atomic claim with single-row update`

## Slice 218.3 — Heartbeat + lease renew + crash takeover

- [x] RED：写 `tests/integration/runtime_jobs/test_heartbeat.py`、`test_lease_renew.py`、`test_worker_crash_takeover.py`；当前应红；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.3/red.txt`
- [x] GREEN：heartbeat / complete / fail 校验当前 worker + lease token，过期 lease 可 takeover 且旧 token 失效；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.3/green-targeted.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime_jobs -q` 全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.3/integration.txt`
- [x] E2E：`rtk node frontend/e2e/runtime-v2-cancel-lifecycle.mjs` 不回归；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.3/e2e.txt`
- [x] Docs：在 job-scheduler-operations.md 增补 "heartbeat / lease / takeover"；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.3/docs-check.txt`
- [x] Git commit：`feat(runtime-jobs): heartbeat, lease renew and crash takeover`

## Slice 218.4 — Retry policy: backoff / max / reason recording

- [x] RED：写 `tests/contract/runtime_jobs/test_retry_policy.py`，覆盖 backoff 序列、max attempts、error reason 持久化；当前应红；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.4/red.txt`
- [x] GREEN：失败未达 `max_attempts` 时按 backoff 重排为 `QUEUED`，达上限才 `FAILED`；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.4/green-targeted.txt`
- [x] Contract：`rtk uv run pytest tests/contract/runtime_jobs -q` 全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.4/contract.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime_jobs -q` 全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.4/integration.txt`
- [x] Git commit：`feat(runtime-jobs): retry with backoff/max-attempts/error-reason`

## Slice 218.5 — DLQ actions: query / retry / ignore

- [x] RED：写 `tests/contract/runtime_jobs/test_dlq_actions.py`，断言 query / retry / mark-ignored 三动作；当前应红；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.5/red.txt`
- [x] GREEN：新增 `list_dlq()` / `retry_dlq()` / `ignore_dlq()`，失败作业可查询、重排或标记忽略；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.5/green-targeted.txt`
- [x] Contract：`rtk uv run pytest tests/contract/runtime_jobs -q` 全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.5/contract.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime_jobs -q` 全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.5/integration.txt`
- [x] Docs：在 job-scheduler-operations.md 增补 "DLQ Semantics"；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.5/docs-check.txt`
- [x] Git commit：`feat(runtime-jobs): DLQ with query/retry/ignore actions`

## Slice 218.6 — Idempotency keys & proposed action protection across run/job/node

- [x] RED：写 `tests/contract/runtime/test_idempotency_layers.py`，覆盖 run / job / node 三层幂等键 + side-effect proposed action；当前应红；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.6/red.txt`
- [x] GREEN：runtime job payload 携带 run 幂等元数据，side-effect / proposed action key 改为稳定 run+node key；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.6/green-targeted.txt`
- [x] Contract：`rtk uv run pytest tests/contract/runtime -q` 全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.6/contract.txt`
- [x] Integration：`rtk uv run pytest tests/integration -q` 不回归；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.6/integration.txt`
- [x] Docs：在 job-scheduler-operations.md 增补 "Idempotency Layers And Proposed Actions"；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.6/docs-check.txt`
- [x] Git commit：`feat(runtime): enforce idempotency at run/job/node layers`

## Slice 218.7 — Standalone worker entry & offload request thread

- [x] RED：写 `tests/integration/runtime_jobs/test_standalone_worker_entry.py`、`tests/integration/runtime/test_request_thread_offloading.py`；当前应红；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.7/red.txt`
- [x] GREEN：新增独立 worker `--job-id` 入口与请求线程 offload 开关；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.7/green-targeted.txt`
- [x] Unit：`rtk uv run pytest tests/unit/core/test_config.py tests/unit/workflow/test_runtime_job_worker_script.py -q` 全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.7/unit.txt`
- [x] Integration：`rtk uv run pytest tests/integration -q` 全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.7/integration.txt`
- [x] E2E：`rtk node frontend/e2e/runtime-v2-production-node-uat.mjs` 在独立 worker 模式下全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.7/e2e.txt`
- [x] Browser UAT：独立 worker owner `e2e-scoped-standalone-worker` 完成 runtime jobs；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.7/uat.md`
- [x] Docs：在 job-scheduler-operations.md 写 "standalone worker entry" + 启动命令；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.7/docs-check.txt`
- [x] Git commit：`feat(runtime): standalone worker entry and request-thread offload` (`24ac674c`)

## Slice 218.8 — Regression on spec 212-217 entry gates

- [x] Unit / Integration / Contract / Frontend / rem：六 spec 入口套件重跑全绿；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.8/{unit,integration,contract,frontend-unit,rem}.txt`
- [x] Browser UAT：spec 212.5 + 214.5 + 215.7 + 216.6 + 217.7 全套；证据 `artifacts/slices/218-runtime-production-job-scheduler/218.8/uat.md`
- [x] Docs：在 baseline.md 追记 "spec 218 exit @ SHA 24ac674c"
- [x] Git commit：`test(runtime): seal spec 218 exit regression`
