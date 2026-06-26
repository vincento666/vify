# Spec 212: Runtime Baseline Lock and Regression Gate

> 来源：`docs/chatflow-workflow-production-upgrade.md` §4

## 背景

生产级运行底座升级（spec 213-221）共改动 runtime 调度、DAG 语义、节点矩阵、任务调度、事件流、观测面板和容量验收。在动手前必须先冻结当前 Chatflow/Workflow/SOP/客服助手 worker 的行为表现作为兼容基线，并定义一组始终可重放的回归门禁。spec 212 既是整个推进序列的入口，也是 spec 213+ 的回退安全网。基线绿则放行；基线红则在 212 内修复，绝不带病进入 213。

## 目标（What）

逐条复用文档 §4 的目标和验收标准：

- 后端 runtime gateway、Chatflow/Workflow stream、SOP adapter、客服助手 worker 测试全绿。
- 前端完整单测与 rem 门禁全绿。
- Chatflow 核心 UAT 通过：消息、问题、信息收集、条件分支、意图分支、转人工、resume。
- SOP 完整 UAT 通过，覆盖启动、继续、暂停、切换、恢复、拒绝切换、澄清、FAQ/RAG/Agent fallback、转人工。
- Workflow 核心 UAT 通过：LLM、API、Tool、Code、Knowledge、Execute Workflow、Agent Call。
- 明确当前 legacy 单路径行为，作为兼容基线和迁移对照。
- 后续每个阶段都必须运行基础回归门禁。

## 不在范围（Non-goals）

- 不引入 DAG 多路径语义（属于 spec 214）。
- 不实现 Async Runtime 默认化（属于 spec 213）。
- 不重构 frontier scheduler（属于 spec 215）。
- 不实现观测/运维面板（属于 spec 220）。
- 不动 `docs/chatflow-workflow-production-upgrade.md` 内容。

## 与前序 spec 的依赖

- 前置：无。spec 212 是 §15 推进顺序中的第一步。
- 文档 §15 顺序硬约束：spec 213 不得在 spec 212 全部 slice 闭环前启动。

## Slice 列表

| Slice | 内容 | 主要门禁 |
|-------|------|----------|
| 212.0 | `pyproject.toml` 增加 `[tool.pytest.ini_options].pythonpath = ["."]`，去掉 contract 套件的 `PYTHONPATH=.` 前缀依赖 | RED（不带前缀 contract 收集失败）/ Unit / Contract / Docs |
| 212.1 | 修 `customer-assistant-chatflow-runtime-gateway-uat` operator-task-ledger `refund_ticket` 行不可见的时序问题 | RED 截图 / E2E / Browser UAT / Docs |
| 212.2 | 修 `chatflow-conversation-run` 入口 Chatflow 名称占位符消失（L16 断言失败） | RED 截图 / Frontend Unit / Browser UAT / Docs |
| 212.3 | 在 `docs/testing/acceptance-gates.md` 增补 Chrome-MCP harness 调用约定与基线判定口径 | Docs review / 引用一致性检查 |
| 212.4 | 起 pgvector 后跑 pgvector-dependent UAT 子集并归档证据 | Browser UAT / Docs |
| 212.5 | 重跑全套基线门禁（unit/integration/contract/frontend/UAT/rem）→ ALL GREEN，作为后续 spec 213+ 入口门禁 | All gates / 证据归档 |
| 212.6 | 修 `customer-assistant-chatflow-runtime-gateway-uat:148` 第二轮响应 `chatflowSession: null`（baseline 时被 L124 timeout 屏蔽，slice 212.1 修复后才暴露） | RED / Unit/Integration/Contract / E2E / Browser UAT / Docs |
| 212.7 | 修 `chatflow-conversation-run.mjs` 在 Ant Design composer 迁移（commit `29aca2d4`）后丢失的 3 处 selector 契约：L27 testid `chatflow-run-fields-toggle`、L28 placeholder `发送消息`、L45 button name `重置会话`（slice 212.2 修复 L16 后暴露） | RED / Frontend Unit / rem / E2E / Browser UAT / Docs |
| 212.8 | 修 `chatflow-conversation-run.mjs:36` chatflow trial run 发消息后 `chatflow-assistant-message` innerText 为空（sys variable `{{sys.query}}` / `{{global.brand}}` 等未注入回复气泡；属 runtime/SSE 渲染层，非 selector，由 212.7 修复后暴露） | RED / Unit/Integration / Frontend Unit / E2E / Browser UAT / Docs |
| 212.9 | 修 `chatflow-conversation-run.mjs:58` `.chatflow-profile-grid .run-input-field` 控件 height 全为 0（Ant 迁移后控件 wrapper layout collapse 或 selector 失配，由 212.8 修复后暴露） | RED / Frontend Unit / rem / E2E / Browser UAT / Docs |

## 验收门禁映射（Acceptance Gate Map）

| 文档验收标准 | 对应 slice | 检测命令 |
|------------|-----------|---------|
| 后端 runtime gateway / stream / SOP adapter / 客服 worker 测试全绿 | 212.0, 212.5 | `rtk uv run pytest tests/unit -q`、`rtk uv run pytest tests/integration -q`、`rtk uv run pytest tests/contract -q` |
| 前端完整单测与 rem 门禁全绿 | 212.2, 212.5 | `rtk npm --prefix frontend run test:unit`、`rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts` |
| Chatflow 核心 UAT 通过 | 212.2, 212.5 | `rtk node frontend/e2e/chatflow-channels.mjs`、`...chatflow-information-collection.mjs` 等 |
| SOP 完整 UAT 通过 | 212.5 | `rtk node frontend/e2e/unified-routing-sop-chatflow-runtime-uat.mjs` 等 SOP 套件 |
| Workflow 核心 UAT 通过 | 212.5 | `rtk node frontend/e2e/workflow-six-node-matrix.mjs` 等 |
| 明确 legacy 单路径行为基线 | 212.5 | 归档 `baseline.md` 并冻结 |
| 后续每个阶段必须运行基础回归门禁 | 212.3, 212.5 | `docs/testing/acceptance-gates.md`（含新增 § Chrome-MCP UAT Harness 章节，定义 Chrome-MCP 脚本调用约定、screenshot/日志归档路径、PASS / LOGIC-RED / ENV-BLOCKED-CHROME-MCP / ENV-BLOCKED-PGVECTOR 判定关键字） |

## Baseline 已知项

锁定 SHA：`136b31ef`
证据目录：`artifacts/slices/baseline-2026-06-26-runtime-prod-upgrade/`

### Backend gates（基线绿）

- unit: 368 passed
- integration: 444 passed / 10 skipped
- contract: 98 passed（需 `PYTHONPATH=.` 前缀；建议 slice 212.0 修 `pyproject.toml`）

### Frontend gates（基线绿）

- unit: 416 tests / 98 files passed
- remScaleClosure: 1 passed

### Browser UAT 子集（基线 PARTIAL）

- PASS: `runtime-v2-production-node-uat`, `runtime-v2-cancel-lifecycle`, `unified-routing-sop-chatflow-runtime-uat`, `chatflow-channels`
- LOGIC-RED: `customer-assistant-chatflow-runtime-gateway-uat`（operator-task-ledger refund_ticket 时序），`chatflow-conversation-run`（Chatflow 名称占位符）
- ENV-BLOCKED-CHROME-MCP: `chatflow-inapp-deep-tree-uat`, `chatflow-inapp-visible-output-uat`
- ENV-BLOCKED-PGVECTOR: 任何依赖 pgvector 的脚本（postgres 5432 DOWN）

### Baseline-residual slices（212.0~212.5）

- 212.0: `pyproject.toml` 添加 `[tool.pytest.ini_options].pythonpath = ["."]`
- 212.1: 修 customer-assistant-chatflow-runtime-gateway-uat operator-task-ledger refund_ticket
- 212.2: 修 chatflow-conversation-run 入口（Chatflow 名称占位符）
- 212.3: 定义 Chrome-MCP harness 调用约定（acceptance-gates.md 增补）
- 212.4: 启动 pgvector 后跑 pgvector-dependent UAT 子集
- 212.5: 重跑全套基线 → ALL GREEN，作为后续 spec 213+ 的入口门禁
- 212.6: 修 customer-assistant gateway 第二轮 `chatflowSession: null`（212.1 后暴露的预先存在问题）
- 212.7: 修 chatflow-conversation-run.mjs Ant 迁移 selector 漂移（L27/L28/L45，212.2 后暴露的预先存在问题）
- 212.8: 修 chatflow-conversation-run.mjs:36 assistant bubble 空内容（testid race condition：loading 占位符提前匹配，212.7 后暴露）
- 212.9: 修 chatflow-conversation-run.mjs:58 run-input-field height 0（layout/CSS 或 selector 失配，212.8 后暴露）

## 文档关联

- Source: `docs/chatflow-workflow-production-upgrade.md` §4
- Gates: `docs/testing/acceptance-gates.md`
- Prior baseline evidence: `artifacts/slices/baseline-2026-06-26-runtime-prod-upgrade/baseline.md`
