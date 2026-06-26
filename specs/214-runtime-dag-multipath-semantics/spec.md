# Spec 214: Runtime DAG Multipath Semantics

> 来源：`docs/chatflow-workflow-production-upgrade.md` §6

## 背景

当前 runtime v2 仍按单路径 `_next_node_key` 推进，无法对齐 Coze / Eino 类 DAG workflow 语义。spec 214 把 edge / port / branch / skipped / terminal / final-output 这些概念固化为画布契约和 runtime 数据模型，作为 frontier scheduler（spec 215）的语义基底。本 spec 不实现新调度器，只定义并锁定语义模型。

## 目标（What）

逐条复用文档 §6 的目标和验收标准：

- 一个 source port 可以连接多个 target node。
- 条件、意图、错误分支选择的是 port 或 branch group。
- 被选中的 port 下所有 target node 都进入 runnable frontier。
- 未选中的 port 及其仅依赖该 port 的下游标记为 skipped。
- 普通节点的 default port 多下游可以作为 fan-out 语义，但必须通过画布校验明确允许。
- 不要求显式 Join 节点；一个节点如果依赖多个 selected upstream，则它天然是隐式 join 点。
- 没有下游的 side-effect 节点可以作为 terminal leaf。
- 整个 run 在所有 selected active paths 都完成、失败、取消或等待后进入最终状态。
- 有明确的 edge / port / branch / skipped / terminal / final-output 语义文档。
- 画布校验能区分合法 fan-out、多分支、side-effect terminal、隐式 join、非法孤岛节点。
- 普通顺序链路仍按原语义执行。
- 条件 / 意图节点命中一个 branch port 时，该 port 的多个下游都可执行。
- 未命中 branch 不阻塞后续隐式 join 判定。
- terminal side-effect path 不要求连接 End 节点。
- Chatflow 必须至少有一条 selected path 能产生可见回复、等待输入、转人工或明确的无回复执行结果。
- Workflow 可以允许无最终业务输出，但必须返回 run 状态、节点事件和 side-effect evidence。

## 不在范围（Non-goals）

- 不实现 frontier scheduler 与并发执行（属于 spec 215）。
- 不修改各节点 executor 行为（属于 spec 217）。
- 不实现 fail-fast / continue-on-error 策略（属于 spec 215）。
- 不动观测面板（属于 spec 220）。

## 与前序 spec 的依赖

- 前置：spec 213 ALL GREEN，gateway / refs 已就位。
- 文档 §15 顺序：本 spec 是 "DAG 多路径语义模型"，先于 spec 215 调度器。

## Slice 列表

| Slice | 内容 | 主要门禁 |
|-------|------|----------|
| 214.1 | 定义 edge / port / branch group / skipped / terminal / final-output 语义文档与 Pydantic schema | RED / Unit / Contract / Docs |
| 214.2 | 画布校验：合法 fan-out / 多分支 / side-effect terminal / 隐式 join / 非法孤岛节点；前端校验提示 | RED / Unit / Frontend Unit / E2E |
| 214.3 | runtime 数据模型升级：node 状态包含 selected / skipped / pending / waiting；保留 legacy 单路径行为路径 | RED / Unit / Contract / Integration |
| 214.4 | Chatflow 最终回复规则与 Workflow side-effect-only 输出约束写入合约 | RED / Unit / Contract / E2E |
| 214.5 | 出口回归：spec 212 + 213 入口门禁全套；新增 DAG semantic contract 套件 | All gates |

## 验收门禁映射（Acceptance Gate Map）

| 文档验收标准 | 对应 slice | 检测命令 |
|------------|-----------|---------|
| edge / port / branch / skipped / terminal / final-output 语义文档 | 214.1 | grep `docs/runtime/dag-semantics.md` 章节 |
| 画布校验识别合法 fan-out / 非法孤岛 | 214.2 | `rtk npm --prefix frontend run test:unit -- canvas-validation`、`rtk uv run pytest tests/unit/workflow/validation -q` |
| 普通顺序链路语义不变 | 214.3 | spec 212 入口门禁回归 |
| branch 命中后多下游可执行（语义层面） | 214.3 | `tests/contract/runtime_dag/test_branch_multi_target.py` |
| 未命中 branch 不阻塞隐式 join 判定 | 214.3 | `tests/contract/runtime_dag/test_skipped_does_not_block_join.py` |
| terminal side-effect path 不连接 End | 214.4 | `tests/contract/runtime_dag/test_terminal_side_effect.py` |
| Chatflow 至少一条 selected path 产生可见回复 / 等待 / 转人工 / 明确无回复结果 | 214.4 | `tests/integration/chatflow/test_final_output_rules.py` + UAT |
| Workflow 可以无最终业务输出但需 run 状态 + 事件 + side-effect evidence | 214.4 | `tests/contract/workflow/test_workflow_no_final_output.py` |

## 文档关联

- Source: `docs/chatflow-workflow-production-upgrade.md` §6
- Gates: `docs/testing/acceptance-gates.md`
- Prior baseline evidence: `artifacts/slices/baseline-2026-06-26-runtime-prod-upgrade/baseline.md`
- Output doc (新增): `docs/runtime/dag-semantics.md`
