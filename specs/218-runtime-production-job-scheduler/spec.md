# Spec 218: Runtime Production Job Scheduler

> 来源：`docs/chatflow-workflow-production-upgrade.md` §10

## 背景

DAG scheduler + 节点矩阵就绪后，runtime 的执行层必须达到生产可靠性：run / job 不丢失、不重复、不假死、可恢复。spec 218 把 DB engine 与 session 全局复用、连接池参数可配、job claim 原子化、heartbeat / lease renew、worker crash 接管、retry 与 DLQ、幂等键、proposed action 保护、独立 worker 进程等"生产任务调度"能力一次性补齐。本 spec 不引入实时事件 / 取消 / 限流（spec 219）也不上观测面板（spec 220）。

## 目标（What）

逐条复用文档 §10 的目标和验收标准：

- DB engine / session factory 全局复用。
- DB 连接池参数可配置，包括 pool size、overflow、timeout、recycle、pre-ping。
- Runtime job claim 原子化，支持多 worker 竞争。
- Job 执行中有 heartbeat 和 lease renew。
- Worker 崩溃后 job 可被其他 worker 接管。
- Retry 支持 backoff、最大次数、错误原因记录。
- DLQ 可查询、可重试、可标记忽略。
- Run / job / node 执行具备幂等 key 或等价去重机制。
- Side-effect 节点恢复或重试时不会重复执行高风险写操作；高风险写操作默认走 proposed action 或审批。
- 生产路径中，请求线程不负责长任务执行。
- 支持独立 worker 进程执行 runtime jobs。

## 不在范围（Non-goals）

- 不引入 SSE 断线重连 / Redis stream 事件加速（属于 spec 219）。
- 不引入取消 / 限流 / 背压（属于 spec 219）。
- 不引入观测面板（属于 spec 220）。
- 不做真实压测（属于 spec 221）。

## 与前序 spec 的依赖

- 前置：spec 217 ALL GREEN。
- 文档 §15 顺序：本 spec 是 "生产级任务调度"。

## Slice 列表

| Slice | 内容 | 主要门禁 |
|-------|------|----------|
| 218.1 | DB engine / session factory 全局复用 + 连接池参数 schema-driven 配置 | RED / Unit / Integration |
| 218.2 | Runtime job claim 原子化（多 worker 竞争安全） | RED / Contract / Integration |
| 218.3 | Heartbeat + lease renew + worker crash 接管 | RED / Integration / E2E |
| 218.4 | Retry：backoff + max attempts + 错误原因记录 | RED / Contract / Integration |
| 218.5 | DLQ：可查询、可重试、可标记忽略（API + 后端语义） | RED / Contract / Integration |
| 218.6 | 幂等键 / proposed action 全链路：run / job / node 三层 | RED / Contract / Integration |
| 218.7 | 独立 worker 进程入口 + 请求线程不执行长任务 | RED / Integration / E2E |
| 218.8 | 出口回归：spec 212-217 入口门禁全套 | All gates |

## 验收门禁映射（Acceptance Gate Map）

| 文档验收标准 | 对应 slice | 检测命令 |
|------------|-----------|---------|
| DB engine / session 全局复用 | 218.1 | `tests/unit/core/test_database_factory.py` |
| 连接池参数可配 | 218.1 | `tests/unit/core/test_pool_config.py` |
| Job claim 原子化 | 218.2 | `tests/contract/runtime_jobs/test_claim_atomic.py` |
| Heartbeat + lease renew | 218.3 | `tests/integration/runtime_jobs/test_heartbeat.py`、`test_lease_renew.py` |
| Worker crash 接管 | 218.3 | `tests/integration/runtime_jobs/test_worker_crash_takeover.py` |
| Retry backoff / max / 错误原因 | 218.4 | `tests/contract/runtime_jobs/test_retry_policy.py` |
| DLQ 三动作 | 218.5 | `tests/contract/runtime_jobs/test_dlq_actions.py` |
| 幂等键 / proposed action 三层 | 218.6 | `tests/contract/runtime/test_idempotency_layers.py` |
| 请求线程不执行长任务 | 218.7 | `tests/integration/runtime/test_request_thread_offloading.py` |
| 独立 worker 进程 | 218.7 | `tests/integration/runtime_jobs/test_standalone_worker_entry.py` |

## 文档关联

- Source: `docs/chatflow-workflow-production-upgrade.md` §10
- Gates: `docs/testing/acceptance-gates.md`
- Prior baseline evidence: `artifacts/slices/baseline-2026-06-26-runtime-prod-upgrade/baseline.md`
- Output doc: `docs/runtime/job-scheduler-operations.md`
