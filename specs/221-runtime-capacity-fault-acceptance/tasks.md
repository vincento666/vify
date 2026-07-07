# Tasks — Spec 221

证据根目录：`artifacts/slices/221-runtime-capacity-fault-acceptance/<slice>/`

## Slice 221.1 — Local 20-50 concurrent runs functional correctness

- [x] RED：写 `tests/integration/runtime/load/test_concurrent_20_50.py`，跑 20 / 35 / 50 并发 run 断言全部成功 + 事件 sequence 合法；当前应红；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.1/red.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime/load -q -k concurrent_20_50` 全绿；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.1/integration.txt` (`3 passed, 1 warning in 7.66s`)
- [x] Docs：在 `docs/runtime/capacity-report.md`（如缺则新增）的 "Local 20-50" 节填初始结果
- [x] Git commit：`test(runtime): local 20-50 concurrent run baseline`

## Slice 221.2 — Local 100-200 mid-pressure smoke

- [x] RED：写 `tests/integration/runtime/load/test_concurrent_100_200.py`，跑 100 / 150 / 200 并发，断言连接池 / worker / 事件流无明显瓶颈（阈值表）；当前应红；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.2/red.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime/load -q -k concurrent_100_200` 全绿；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.2/integration.txt` (`3 passed, 3 deselected, 1 warning in 35.17s`)
- [x] Docs：capacity-report.md 写 "Local 100-200" 结果与 CPU / 内存 / FD 观察
- [x] Git commit：`test(runtime): local 100-200 mid-pressure smoke`

## Slice 221.3 — Multi-worker claim under stress (no duplicate execution)

- [x] RED：写 `tests/contract/runtime_jobs/test_multi_worker_no_duplicate.py`（升级 spec 218.2 测试），跑 N=10 worker × 200 job；当前应红；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.3/red.txt`、`red-deadlock-complete.txt`
- [x] Contract：`rtk uv run pytest tests/contract/runtime_jobs -q` 全绿；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.3/contract.txt` (`8 passed, 1 warning in 10.96s`)
- [x] Integration：`rtk uv run pytest tests/integration/runtime_jobs -q` 全绿；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.3/integration.txt` (`8 passed, 1 warning in 12.45s`)
- [x] Docs：capacity-report.md 写 "multi-worker claim" 结果
- [x] Git commit：`test(runtime-jobs): multi-worker claim no duplicate under stress`

## Slice 221.4 — DAG fan-out stress (consistent results & events)

- [x] RED：写 `tests/integration/runtime/load/test_dag_fanout_stress.py`，跑 fan-out 10-20 并发分支 × 50 run；当前应红；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.4/red.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime/load -q -k dag_fanout` 全绿；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.4/integration.txt` (`2 passed, 6 deselected, 1 warning in 16.90s`)
- [x] Docs：capacity-report.md 写 "DAG fan-out" 结果
- [x] Git commit：`test(runtime): DAG fan-out stress consistency`

## Slice 221.5 — Interrupt/resume stress (no side-effect replay)

- [x] RED：写 `tests/integration/runtime/load/test_resume_no_side_effect_replay.py`；当前应红；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.5/red.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime/load -q -k resume_no_side_effect` 全绿；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.5/integration.txt` (`1 passed, 8 deselected, 1 warning in 5.67s`)
- [x] Docs：capacity-report.md 写 "resume" 结果
- [x] Git commit：`test(runtime): interrupt/resume stress no side-effect replay`

## Slice 221.6 — Worker crash drill & takeover

- [x] RED：写 `tests/integration/runtime/chaos/test_worker_crash.py`，kill -9 worker N 次断言 job 全部接管；当前应红；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.6/red.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime/chaos -q -k worker_crash` 全绿；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.6/integration.txt` (`1 passed in 1.47s`)
- [x] Docs：新增 `docs/runtime/chaos-drills.md` 写 "worker crash" 演练手册
- [x] Git commit：`test(runtime): worker crash chaos drill with takeover`

## Slice 221.7 — DB reconnect / Redis failure drill

- [x] RED：写 `tests/integration/runtime/chaos/test_db_reconnect.py`、`test_redis_failure.py`，断 DB 后连接池恢复 / 断 Redis 后 stream 降级 + DB event 仍可恢复；当前应红；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.7/red.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime/chaos -q -k "db_reconnect or redis_failure"` 全绿；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.7/integration.txt` (`2 passed, 1 deselected in 2.56s`)
- [x] Docs：chaos-drills.md 增补 "DB / Redis" 章节
- [x] Git commit：`test(runtime): DB reconnect and Redis failure chaos drills`

## Slice 221.8 — Slow LLM/API call drill (deadline / breaker / backpressure)

- [x] RED：写 `tests/integration/runtime/chaos/test_slow_external_calls.py`，mock provider 注入 60s / 120s 延迟，断言 deadline / 熔断 / 背压都触发；当前应红；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.8/red.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime/chaos -q -k slow_external` 全绿；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.8/integration.txt` (`1 passed, 3 deselected in 0.23s`)
- [x] Docs：chaos-drills.md 增补 "slow external call" 章节
- [x] Git commit：`test(runtime): slow external call chaos drill`

## Slice 221.9 — Capacity report output

- [x] Docs：完成 `docs/runtime/capacity-report.md`，覆盖 p50 / p95 / p99 / queue latency / node latency / event delay / 错误率 / 资源占用 全字段
- [x] Evidence：`artifacts/slices/221-runtime-capacity-fault-acceptance/221.9/` 归档原始 metrics csv / json
- [x] Git commit：`docs(runtime): publish capacity report after acceptance drills`

## Slice 221.10 — Regression on spec 212-220 entry gates

- [x] Unit / Integration / Contract / Frontend / rem：九 spec 入口套件重跑全绿；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.10/{unit,integration,contract,frontend-unit,rem}.txt`
- [x] Browser UAT：spec 212.5 + 214.5 + 215.7 + 216.6 + 217.7 + 218.8 + 219.7 + 220.10 全套；证据 `artifacts/slices/221-runtime-capacity-fault-acceptance/221.10/uat.md`
- [x] Docs：在 baseline.md 追记 "spec 221 exit @ SHA 0b571ad7 — production upgrade complete"
- [x] Git commit：`test(runtime): seal spec 221 exit regression and production upgrade closure`
