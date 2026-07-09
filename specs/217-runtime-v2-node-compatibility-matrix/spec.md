# Spec 217: Runtime V2 Node Compatibility Matrix

> 来源：`docs/chatflow-workflow-production-upgrade.md` §9

## 背景

DAG scheduler 与 Chatflow / SOP 兼容做完后，必须逐节点验证所有一等画布节点在 runtime v2 下的可执行性、状态、事件、上下文隔离与幂等保护。spec 217 把每个节点的 v2 兼容性形成可对照矩阵，把非法配置错误从"运行时模糊错误"挪到"compatibility check 阶段"，并明确 Chatflow / Workflow 同类节点的能力一致性。

## Post-Closure Note

spec 217 的矩阵记录 executor / capability 兼容性。2026-07-09 的复核发现，矩阵还
需要单独记录 Workflow 与 Chatflow 的产品 UAT 证据状态，避免把"有 executor"误读为
"所有 async / stream / published / resume / visual 场景均已验收"。证据状态闭环由
spec 223 承接。

## 目标（What）

逐条复用文档 §9 的目标和验收标准：

- 有完整节点兼容矩阵。
- 每个一等节点都有 v2 executor 或明确复用 executor。
- 每个节点支持 node run 状态记录。
- 每个节点支持 runtime event。
- 每个节点支持 DAG 并发上下文隔离。
- API、Tool、LLM、Knowledge、Agent、Execute Workflow 节点在 DAG 并发下通过测试。
- Side-effect 节点具备幂等键、执行记录或 proposed action 保护。
- 非法配置在 compatibility check 阶段给出可读错误。
- 不允许运行中才暴露模糊的 unsupported error。
- Chatflow 与 Workflow 的同类节点能力保持一致，除非有明确产品语义差异。

## 不在范围（Non-goals）

- 不引入 job lease / 重试 / DLQ（属于 spec 218）。
- 不引入取消 / 限流 / 背压（属于 spec 219）。
- 不引入观测面板（属于 spec 220）。

## 与前序 spec 的依赖

- 前置：spec 216 ALL GREEN。
- 文档 §15 顺序：本 spec 是 "全节点 Runtime V2 兼容"。

## Slice 列表

| Slice | 内容 | 主要门禁 |
|-------|------|----------|
| 217.1 | 节点兼容矩阵文档 + 自动化扫描（列出所有一等节点 + v2 executor 映射） | RED / Unit / Docs |
| 217.2 | LLM / Knowledge / Agent 节点 DAG 并发场景测试 | RED / Unit / Integration / E2E |
| 217.3 | API / Tool / Execute Workflow 节点 DAG 并发场景测试 + 幂等键 | RED / Integration / Contract |
| 217.4 | Side-effect 节点（消息发送、写库、转人工等）幂等键 / 执行记录 / proposed action 保护 | RED / Integration / Contract |
| 217.5 | Compatibility check：非法配置在编辑期 / 启动期暴露可读错误，运行时不再吐 unsupported error | RED / Unit / Contract / E2E |
| 217.6 | Chatflow / Workflow 同类节点能力一致性差异表 | Docs / Contract |
| 217.7 | 出口回归：spec 212-216 入口门禁全套 | All gates |

## 验收门禁映射（Acceptance Gate Map）

| 文档验收标准 | 对应 slice | 检测命令 |
|------------|-----------|---------|
| 完整节点兼容矩阵 | 217.1, 217.6 | 文档 `docs/runtime/node-compatibility-matrix.md` |
| 每个一等节点支持 node run / event / 并发隔离 | 217.2, 217.3 | `rtk uv run pytest tests/integration/runtime/nodes -q`、`rtk uv run pytest tests/unit/runtime/nodes -q` |
| API / Tool / LLM / Knowledge / Agent / Execute Workflow 并发场景通过 | 217.2, 217.3 | `tests/integration/runtime/nodes/test_<node>_concurrent.py`（每节点一个） |
| Side-effect 节点幂等 / proposed action | 217.4 | `tests/contract/runtime/nodes/test_side_effect_idempotency.py` |
| 非法配置 compatibility check 给可读错误 | 217.5 | `tests/unit/workflow/validation/test_compatibility_errors.py`、UAT |
| 运行时不再吐 unsupported error | 217.5 | grep `unsupported` 在 runtime 路径下零命中 |
| Chatflow / Workflow 同类节点一致 | 217.6 | `tests/contract/runtime/nodes/test_capability_parity.py` |

## 文档关联

- Source: `docs/chatflow-workflow-production-upgrade.md` §9
- Gates: `docs/testing/acceptance-gates.md`
- Output doc: `docs/runtime/node-compatibility-matrix.md`
- Semantics doc: `docs/runtime/dag-semantics.md`
