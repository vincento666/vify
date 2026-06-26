# Spec 220: Runtime Observability & Ops Module

> 来源：`docs/chatflow-workflow-production-upgrade.md` §12

## 背景

run / job / node / event 数据模型在 spec 213-219 已稳定下来。spec 220 把这些数据组装成一个独立主菜单模块（建议命名 "运行观测" 或 "Runtime Ops"），让运维人员可观察、诊断、取消、恢复、重试 runtime run / job / node，而不是分散在调试页面。本 spec 不引入新的 runtime 能力，全部能力来自前序 spec 暴露的接口与事件。

## 目标（What）

逐条复用文档 §12 的目标和验收标准：

### 模块功能范围

Run 列表、Run 详情、DAG 节点状态图、Job 队列、Worker 心跳、Event timeline、DLQ、Provider / API / Tool 调用统计、失败与重试面板、租户 / owner type / 状态 / 时间范围过滤、安全运维动作。

### 验收标准

- 主菜单存在独立模块入口。
- 可按 owner type 过滤：Workflow、Chatflow、Customer Assistant、SOP。
- 可查看 run 状态：queued、running、waiting、succeeded、failed、cancelled。
- 可查看 DAG 执行图，包含 selected、skipped、running、completed、failed、waiting。
- 可查看每个 node run 的输入摘要、输出摘要、耗时、错误和事件。
- 可查看 job lease owner、heartbeat、attempt、next retry time。
- 可查看 DLQ 并执行 retry、ignore、mark resolved。
- 可执行安全运维动作：cancel run、retry failed job、resume interrupted run、reopen DLQ item。
- 高风险动作必须二次确认。
- 默认不显示隐藏思考过程。
- 默认显示事件、工具调用、节点输入输出摘要和错误证据。
- 实时更新使用事件流；断线后可恢复。
- 有前端单测、e2e 和浏览器 UAT 截图证据。

## 不在范围（Non-goals）

- 不引入新的 runtime / scheduler / job 能力（全部依赖 spec 213-219）。
- 不做容量与故障演练（属于 spec 221）。

## 与前序 spec 的依赖

- 前置：spec 219 ALL GREEN。
- 文档 §15 顺序：本 spec 是 "可观测与运维面板模块"。

## Slice 列表

| Slice | 内容 | 主要门禁 |
|-------|------|----------|
| 220.1 | 主菜单独立模块入口 + 路由 + 权限封顶 | RED / Frontend Unit / E2E |
| 220.2 | Run 列表 + 多维过滤（owner type / 状态 / 时间范围 / 租户） | RED / Frontend Unit / E2E / UAT |
| 220.3 | Run 详情：DAG 节点状态图（selected / skipped / running / completed / failed / waiting） | RED / Frontend Unit / E2E / UAT |
| 220.4 | Node run 输入摘要 / 输出摘要 / 耗时 / 错误 / 事件 timeline | RED / Frontend Unit / E2E / UAT |
| 220.5 | Job 队列 + Worker 心跳 + Job lease / heartbeat / attempt / next retry | RED / Frontend Unit / E2E / UAT |
| 220.6 | DLQ 列表 + 三动作（retry / ignore / mark resolved） | RED / Contract / E2E / UAT |
| 220.7 | 安全运维动作（cancel run / retry failed job / resume interrupted run / reopen DLQ item）+ 二次确认 | RED / Contract / E2E / UAT |
| 220.8 | Provider / API / Tool 调用统计 + 失败 / 重试面板 | RED / Frontend Unit / E2E |
| 220.9 | 实时更新（事件流） + 断线恢复 | RED / E2E / UAT |
| 220.10 | 出口回归：spec 212-219 入口门禁全套 | All gates |

## 验收门禁映射（Acceptance Gate Map）

| 文档验收标准 | 对应 slice | 检测命令 |
|------------|-----------|---------|
| 主菜单独立模块入口 | 220.1 | `rtk npm --prefix frontend run test:unit -- runtime-ops-router` + UAT |
| owner type 过滤 | 220.2 | `rtk node frontend/e2e/runtime-ops-list-filter.mjs`（新增） |
| run 状态 6 类 | 220.2 | E2E filter case |
| DAG 执行图 6 状态 | 220.3 | `rtk npm --prefix frontend run test:unit -- runtime-ops-dag-view` |
| node run 摘要 / 耗时 / 错误 / 事件 | 220.4 | `rtk npm --prefix frontend run test:unit -- runtime-ops-node-detail` + UAT |
| Job lease / heartbeat / attempt / next retry | 220.5 | `rtk node frontend/e2e/runtime-ops-jobs.mjs`（新增） |
| DLQ 三动作 | 220.6 | `tests/contract/runtime_jobs/test_dlq_actions.py` 复用 + UAT |
| 安全运维动作 + 二次确认 | 220.7 | E2E `rtk node frontend/e2e/runtime-ops-safe-actions.mjs`（新增）+ UAT |
| Provider / API / Tool 统计 + 失败 / 重试面板 | 220.8 | `rtk npm --prefix frontend run test:unit -- runtime-ops-stats` |
| 实时更新 + 断线恢复 | 220.9 | UAT 测断网恢复 |
| 默认不显示隐藏思考过程 | 220.4 | 单测 + UAT 截图确认 |
| 默认显示事件 / 工具调用 / 节点 IO 摘要 / 错误证据 | 220.4 | 同上 |

## 文档关联

- Source: `docs/chatflow-workflow-production-upgrade.md` §12
- Gates: `docs/testing/acceptance-gates.md`
- Output doc: `docs/runtime/observability-ops-module.md`
- Prior baseline evidence: `artifacts/slices/baseline-2026-06-26-runtime-prod-upgrade/baseline.md`
