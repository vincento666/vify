# Spec 213: Runtime Async-Default Invocation Gateway

> 来源：`docs/chatflow-workflow-production-upgrade.md` §5

## 背景

当前 Chatflow / Workflow / SOP / 客服助手 worker 的运行调用是"支持 async、但默认 sync"。要把 Hify 升级为 durable-first 生产底座，必须把入口收敛到一个 Runtime Invocation Gateway，让所有调用路径默认走 async / durable，sync 仅作为显式 fallback。同时把 SOP Router 的状态写回收紧成"账本 + child refs"，避免成为 Chatflow 执行状态的第二个事实源。

## 目标（What）

逐条复用文档 §5 的目标和验收标准：

- Chatflow / Workflow debug run 默认创建 durable runtime run。
- SOP 路由调用 Chatflow 默认返回 runtime refs。
- 客服助手 worker 调用 Chatflow / SOP 默认返回 async refs。
- 内部调用统一经过 Runtime Invocation Gateway。
- `sync` 仅作为显式 fallback，不再是默认路径。
- run 启动后立即返回 `runId`、`statusRef`、`eventsRef`、`eventStreamRef`、`nodesRef`、`resultRef`。
- 断线后可通过 `runId` 恢复查询状态、事件、节点状态和结果。
- 原有 Chatflow 多轮推进、等待输入、转人工、SOP 路由行为不退化。
- SOP Router 的 active task 摘要必须引用 child Chatflow `sessionId/runId/checkpointId`，不得复制维护 Chatflow 的 `current_step/pending_prompt/collected/scoped_variables/run status` 作为事实源。

## 不在范围（Non-goals）

- 不引入 DAG 多路径执行语义（属于 spec 214）。
- 不重写 frontier scheduler（属于 spec 215）。
- 不修改节点 executor 矩阵（属于 spec 217）。
- 不实现 job lease/heartbeat（属于 spec 218）。
- 不引入观测面板（属于 spec 220）。

## 与前序 spec 的依赖

- 前置：spec 212 必须 ALL GREEN（基线锁定）。
- 文档 §15 顺序：spec 213 紧跟 spec 212，是"Async Runtime 默认化"步骤。

## Slice 列表

| Slice | 内容 | 主要门禁 |
|-------|------|----------|
| 213.1 | 定义 `RuntimeInvocationGateway` Protocol / DTO：runId、statusRef、eventsRef、eventStreamRef、nodesRef、resultRef 六元组 | RED / Unit / Contract / Docs |
| 213.2 | Chatflow debug run 与 Workflow debug run 默认走 async path（旧 sync 路径降级为显式 `?sync=true`） | RED / Unit / Integration / E2E / UAT |
| 213.3 | SOP Router 调用 Chatflow 默认返回 runtime refs；SOP Router state 仅保存 conversation/active-child/suspended/route history/resume offer/intent summary | RED / Unit / Integration / E2E / UAT |
| 213.4 | 客服助手 worker 调用 Chatflow / SOP 默认返回 async refs；旧同步路径仅在测试 `--sync` 标记开启 | RED / Unit / Integration / E2E |
| 213.5 | 断线 recovery：所有 refs 在 runId 已知的情况下可重建 (status / events from N / nodes / result) | RED / Integration / Contract / Docs |
| 213.6 | 回归：Chatflow 多轮、信息收集、转人工；SOP 路由、客服 worker；行为不退化 | UAT 全套 + spec 212 入口门禁重跑 |
| 213.7 | 修 chatflow_sop bridge 与 chatflow runtime v2 异步进度之间的 race（spec 212.5 诊断转交）。Mode A：第二轮 chatflowSession degenerate `runtimeVersion=1 / runId=null / status=FAILED`。Mode B：confirm 轮 `replyType=DRAFT` 且 worker `WAITING at collect`。212.6 修了 carryover empty 但未盖 bridge synchronisation 盲区，必须 bound chatflow_sop bridge to poll runtime v2 nodes/result until terminal-or-collect-advance or short deadline；FAILED/missing v2 run 时返回 explicit retry envelope 而非 degenerate carryover | RED 多次复跑 / Unit / Integration / E2E `customer-assistant-chatflow-runtime-gateway-uat` 全 PASS（10 次重跑 0 fail） / UAT / Docs |

## 验收门禁映射（Acceptance Gate Map）

| 文档验收标准 | 对应 slice | 检测命令 |
|------------|-----------|---------|
| Chatflow / Workflow debug run 默认 durable | 213.2 | `rtk uv run pytest tests/integration/runtime -q`、`rtk node frontend/e2e/chatflow-run-debug-deeplink.mjs` |
| SOP 路由默认返回 runtime refs | 213.3 | `rtk uv run pytest tests/integration/runtime_lab -q`、`rtk node frontend/e2e/unified-routing-sop-chatflow-runtime-uat.mjs` |
| 客服助手 worker 默认 async refs | 213.4 | `rtk uv run pytest tests/integration/customer_assistant -q`、`rtk node frontend/e2e/customer-assistant-chatflow-runtime-gateway-uat.mjs` |
| 内部调用统一经过 gateway | 213.1, 213.2-213.4 | `rtk uv run pytest tests/contract/runtime_gateway -q`（新增） |
| `sync` 仅作为显式 fallback | 213.2-213.4 | grep `sync=true` 引用集中在 fallback / test |
| 启动立刻返回六元组 refs | 213.1, 213.2 | contract 套件断言 refs schema |
| 断线后通过 runId 恢复 | 213.5 | `tests/contract/runtime_recovery` 套件 + UAT |
| 原有行为不退化 | 213.6 | spec 212 入口门禁全部脚本重跑 |
| SOP Router 不复制 Chatflow 执行状态 | 213.3 | `tests/unit/runtime_lab/sop_router` 断言 ledger 字段集；`tests/integration` 断言 `current_step/pending_prompt/collected/scoped_variables/run status` 来自 child Chatflow |

## 文档关联

- Source: `docs/chatflow-workflow-production-upgrade.md` §5
- Gates: `docs/testing/acceptance-gates.md`
- Prior baseline evidence: `artifacts/slices/baseline-2026-06-26-runtime-prod-upgrade/baseline.md`
- Related runtime refs matrix: `specs/211-runtime-v2-chatflow-async-refs/stream-refs-matrix.md`
