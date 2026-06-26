# Tasks — Spec 218

证据根目录：`artifacts/slices/218-runtime-production-job-scheduler/<slice>/`

## Slice 218.1 — DB engine/session factory reuse & pool config schema

- [ ] RED：写 `tests/unit/core/test_database_factory.py`、`test_pool_config.py`，断言全局共用 engine + pool 参数可配；当前应红；证据 `artifacts/218.1/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/core -q` 全绿；证据 `artifacts/218.1/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration -q` 不回归；证据 `artifacts/218.1/integration.txt`
- [ ] Docs：新增 `docs/runtime/job-scheduler-operations.md` 并写 pool config 章节
- [ ] Git commit：`feat(core): centralize DB engine and expose pool config`

## Slice 218.2 — Atomic runtime job claim

- [ ] RED：写 `tests/contract/runtime_jobs/test_claim_atomic.py`，N=20 并发 claim 同一 batch 断言无重复；当前应红；证据 `artifacts/218.2/red.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_jobs -q` 全绿；证据 `artifacts/218.2/contract.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime_jobs -q` 全绿；证据 `artifacts/218.2/integration.txt`
- [ ] Git commit：`feat(runtime-jobs): atomic claim with SELECT FOR UPDATE SKIP LOCKED`

## Slice 218.3 — Heartbeat + lease renew + crash takeover

- [ ] RED：写 `tests/integration/runtime_jobs/test_heartbeat.py`、`test_lease_renew.py`、`test_worker_crash_takeover.py`；当前应红；证据 `artifacts/218.3/red.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime_jobs -q` 全绿；证据 `artifacts/218.3/integration.txt`
- [ ] E2E：`rtk node frontend/e2e/runtime-v2-cancel-lifecycle.mjs` 不回归；证据 `artifacts/218.3/e2e.txt`
- [ ] Docs：在 job-scheduler-operations.md 增补 "heartbeat / lease / takeover"
- [ ] Git commit：`feat(runtime-jobs): heartbeat, lease renew and crash takeover`

## Slice 218.4 — Retry policy: backoff / max / reason recording

- [ ] RED：写 `tests/contract/runtime_jobs/test_retry_policy.py`，覆盖 backoff 序列、max attempts、error reason 持久化；当前应红；证据 `artifacts/218.4/red.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_jobs -q` 全绿；证据 `artifacts/218.4/contract.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime_jobs -q` 全绿；证据 `artifacts/218.4/integration.txt`
- [ ] Git commit：`feat(runtime-jobs): retry with backoff/max-attempts/error-reason`

## Slice 218.5 — DLQ actions: query / retry / ignore

- [ ] RED：写 `tests/contract/runtime_jobs/test_dlq_actions.py`，断言 query / retry / mark-ignored 三动作；当前应红；证据 `artifacts/218.5/red.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_jobs -q` 全绿；证据 `artifacts/218.5/contract.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime_jobs -q` 全绿；证据 `artifacts/218.5/integration.txt`
- [ ] Docs：在 job-scheduler-operations.md 增补 "DLQ semantics"
- [ ] Git commit：`feat(runtime-jobs): DLQ with query/retry/ignore actions`

## Slice 218.6 — Idempotency keys & proposed action protection across run/job/node

- [ ] RED：写 `tests/contract/runtime/test_idempotency_layers.py`，覆盖 run / job / node 三层幂等键 + side-effect proposed action；当前应红；证据 `artifacts/218.6/red.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime -q` 全绿；证据 `artifacts/218.6/contract.txt`
- [ ] Integration：`rtk uv run pytest tests/integration -q` 不回归；证据 `artifacts/218.6/integration.txt`
- [ ] Git commit：`feat(runtime): enforce idempotency at run/job/node layers`

## Slice 218.7 — Standalone worker entry & offload request thread

- [ ] RED：写 `tests/integration/runtime_jobs/test_standalone_worker_entry.py`、`tests/integration/runtime/test_request_thread_offloading.py`；当前应红；证据 `artifacts/218.7/red.txt`
- [ ] Integration：`rtk uv run pytest tests/integration -q` 全绿；证据 `artifacts/218.7/integration.txt`
- [ ] E2E：`rtk node frontend/e2e/runtime-v2-production-node-uat.mjs` 在独立 worker 模式下全绿；证据 `artifacts/218.7/e2e.txt`
- [ ] Docs：在 job-scheduler-operations.md 写 "standalone worker entry" + 启动命令
- [ ] Git commit：`feat(runtime): standalone worker entry and request-thread offload`

## Slice 218.8 — Regression on spec 212-217 entry gates

- [ ] Unit / Integration / Contract / Frontend / rem：六 spec 入口套件重跑全绿；证据 `artifacts/218.8/{unit,integration,contract,frontend-unit,rem}.txt`
- [ ] Browser UAT：spec 212.5 + 214.5 + 215.7 + 216.6 + 217.7 全套；证据 `artifacts/218.8/uat.md`
- [ ] Docs：在 baseline.md 追记 "spec 218 exit @ SHA <sha>"
- [ ] Git commit：`test(runtime): seal spec 218 exit regression`
