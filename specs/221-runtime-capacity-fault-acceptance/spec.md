# Spec 221: Runtime Capacity, Fault and Production-like Acceptance

> 来源：`docs/chatflow-workflow-production-upgrade.md` §13

## 背景

spec 213-220 把 runtime 升级到生产级架构。spec 221 是出厂验收：用合理分层的测试证明系统能力，避免把本机资源限制误判为系统极限。本机阶段聚焦 20-50 / 100-200 并发的功能正确性与中等压力烟测；类生产环境聚焦多 worker claim、DAG fan-out 压测、interrupt/resume 不重跑 side-effect、worker crash 演练、DB / Redis 故障演练、LLM / API 慢调用演练，最终产出容量报告（p50 / p95 / p99 / queue latency / node latency / event delay / 错误率 / 资源占用）。

## 目标（What）

逐条复用文档 §13 的目标和验收标准：

### 本机单体单节点验收

- 20 到 50 并发 run：作为功能正确性和异步行为基础门禁。
- 100 到 200 并发 run：作为本机中等压力烟测，观察连接池、队列、worker、事件流是否有明显瓶颈。

### 类生产环境验收

- 多 worker 并发 claim 无重复执行。
- DAG fan-out 压测下，多分支执行结果和事件一致。
- interrupt/resume 压测下，不重跑已完成 side-effect 节点。
- worker crash 演练后，job 可被接管。
- DB 重连演练后，连接池恢复正常。
- Redis 故障演练后，实时流可降级，DB 事件仍可恢复。
- LLM / API 慢调用演练下，deadline、熔断和背压生效。
- 输出容量报告，包含 p50、p95、p99、queue latency、node latency、event delay、错误率、资源占用。

## 不在范围（Non-goals）

- 不引入新的 runtime / scheduler / ops 能力（全部依赖 spec 213-220）。
- 不要求本机硬扛 1000+ 并发；1000+ 由类生产环境验证。

## 与前序 spec 的依赖

- 前置：spec 220 ALL GREEN。
- 文档 §15 顺序：本 spec 是 "容量、故障与类生产验收"，是整个 12 章产品升级的最后一步。

## Slice 列表

| Slice | 内容 | 主要门禁 |
|-------|------|----------|
| 221.1 | 本机 20-50 并发功能正确性门禁脚本 | RED / Integration / E2E |
| 221.2 | 本机 100-200 并发烟测：连接池 / 队列 / worker / 事件流瓶颈观察 | RED / Integration / Docs |
| 221.3 | 多 worker claim 无重复执行（类生产） | RED / Contract / Integration |
| 221.4 | DAG fan-out 压测：多分支执行结果 / 事件一致 | RED / Integration / Docs |
| 221.5 | interrupt / resume 压测：不重跑 side-effect 节点 | RED / Integration / Docs |
| 221.6 | Worker crash 演练 + job 接管 | RED / Integration / Docs |
| 221.7 | DB / Redis 故障演练：DB 重连 + Redis 降级 + DB event 恢复 | RED / Integration / Docs |
| 221.8 | LLM / API 慢调用演练：deadline / 熔断 / 背压生效 | RED / Integration / Docs |
| 221.9 | 容量报告输出（p50 / p95 / p99 / queue latency / node latency / event delay / 错误率 / 资源占用） | Docs / 证据归档 |
| 221.10 | 出口回归：spec 212-220 入口门禁全套 | All gates |

## 验收门禁映射（Acceptance Gate Map）

| 文档验收标准 | 对应 slice | 检测命令 |
|------------|-----------|---------|
| 20-50 并发功能正确性 | 221.1 | `tests/integration/runtime/load/test_concurrent_20_50.py` |
| 100-200 并发烟测 | 221.2 | `tests/integration/runtime/load/test_concurrent_100_200.py` |
| 多 worker 无重复执行 | 221.3 | `tests/contract/runtime_jobs/test_multi_worker_no_duplicate.py` |
| DAG fan-out 压测 | 221.4 | `tests/integration/runtime/load/test_dag_fanout_stress.py` |
| interrupt / resume 不重跑 side-effect | 221.5 | `tests/integration/runtime/load/test_resume_no_side_effect_replay.py` |
| Worker crash 演练 | 221.6 | `tests/integration/runtime/chaos/test_worker_crash.py` |
| DB / Redis 故障演练 | 221.7 | `tests/integration/runtime/chaos/test_db_reconnect.py`、`test_redis_failure.py` |
| LLM / API 慢调用演练 | 221.8 | `tests/integration/runtime/chaos/test_slow_external_calls.py` |
| 容量报告 | 221.9 | `docs/runtime/capacity-report.md` + `artifacts/slices/221-*/221.9/` |
| 出口回归 | 221.10 | spec 212-220 全套 |

## 文档关联

- Source: `docs/chatflow-workflow-production-upgrade.md` §13
- Gates: `docs/testing/acceptance-gates.md`
- Output docs: `docs/runtime/capacity-report.md`, `docs/runtime/chaos-drills.md`
- Prior baseline evidence: `artifacts/slices/baseline-2026-06-26-runtime-prod-upgrade/baseline.md`
