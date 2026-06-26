# Spec 215: Runtime DAG Frontier Scheduler

> 来源：`docs/chatflow-workflow-production-upgrade.md` §7

## 背景

spec 214 已固化 DAG 语义，但 runtime v2 仍是单 current-node while-loop 推进。spec 215 把执行引擎升级为 frontier-based DAG scheduler，支持多个无依赖下游并发执行、隐式 join、skipped 状态传播、side-effect terminal leaf，以及失败策略矩阵（fail-fast / continue-on-error / error branch / partial success）。这是把 Hify 推到"生产 DAG runtime"的关键步骤。

## 目标（What）

逐条复用文档 §7 的目标和验收标准：

- Runtime 内部维护 node state graph，而不是只维护一个 current node。
- 支持 runnable frontier。
- 支持多个无依赖下游节点并发执行。
- 支持 selected / skipped / pending / running / completed / waiting / failed / cancelled 状态传播。
- 多输入节点等待所需 selected upstream 完成后执行。
- skipped upstream 不会永久阻塞下游。
- side-effect terminal leaf 完成后不报 `Next node not found`。
- run 完成判定基于 active path，而不是最后一个节点。
- 并发节点事件 sequence 单调递增。
- 支持失败策略：fail-fast / continue-on-error / error branch / partial success。
- 节点并发执行时变量作用域、输入输出、node run 记录互不串扰。

## 不在范围（Non-goals）

- 不动节点 executor 矩阵（属于 spec 217）。
- 不引入 worker job lease / heartbeat（属于 spec 218）。
- 不实现取消 / 限流 / 背压细节（属于 spec 219）。
- 不引入观测面板（属于 spec 220）。

## 与前序 spec 的依赖

- 前置：spec 214 ALL GREEN（DAG 语义模型已锁）。
- 文档 §15 顺序：本 spec 是 "DAG Scheduler"，紧跟语义模型。

## Slice 列表

| Slice | 内容 | 主要门禁 |
|-------|------|----------|
| 215.1 | Node state graph 数据结构与 frontier 计算（不带执行） | RED / Unit / Contract |
| 215.2 | Frontier scheduler 取代单 `_next_node_key` while-loop；普通顺序链路行为不变 | RED / Unit / Integration / E2E |
| 215.3 | 并发执行：多个无依赖下游同时调度；变量作用域 / node run 记录隔离 | RED / Unit / Integration / Contract |
| 215.4 | 状态传播：selected / skipped / waiting / cancelled；side-effect terminal leaf 不再报 Next node not found；run 完成判定基于 active path | RED / Integration / Contract / E2E |
| 215.5 | 失败策略矩阵：fail-fast / continue-on-error / error branch / partial success | RED / Unit / Contract / Integration |
| 215.6 | 事件 sequence 单调递增保证（并发下） | RED / Contract / Integration |
| 215.7 | 出口回归：spec 212 + 213 + 214 入口门禁全套 | All gates |

## 验收门禁映射（Acceptance Gate Map）

| 文档验收标准 | 对应 slice | 检测命令 |
|------------|-----------|---------|
| node state graph & frontier | 215.1 | `rtk uv run pytest tests/unit/runtime/scheduler -q` |
| 多无依赖下游并发执行 | 215.3 | `rtk uv run pytest tests/integration/runtime/test_concurrent_fanout.py -q` |
| 状态传播 selected/skipped/... | 215.4 | `rtk uv run pytest tests/contract/runtime_dag/test_state_propagation.py -q` |
| skipped 不永久阻塞 | 215.4 | `tests/contract/runtime_dag/test_skipped_does_not_block_join.py` 升级版 |
| side-effect terminal leaf 不报错 | 215.4 | `tests/integration/runtime/test_terminal_side_effect.py` |
| run 完成判定基于 active path | 215.4 | `tests/integration/runtime/test_run_completion.py` |
| 事件 sequence 单调递增 | 215.6 | `tests/contract/runtime/test_event_sequence_monotonic.py` |
| 失败策略矩阵 | 215.5 | `tests/contract/runtime_dag/test_failure_strategies.py` |
| 并发变量作用域隔离 | 215.3 | `tests/unit/runtime/test_scope_isolation.py`、UAT scoped variables |
| 普通顺序链路语义不变 | 215.2 | spec 212.5 UAT 全套 |

## 文档关联

- Source: `docs/chatflow-workflow-production-upgrade.md` §7
- Gates: `docs/testing/acceptance-gates.md`
- Semantics doc: `docs/runtime/dag-semantics.md`（spec 214 输出）
- Prior baseline evidence: `artifacts/slices/baseline-2026-06-26-runtime-prod-upgrade/baseline.md`
