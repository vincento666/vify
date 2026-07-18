# Spec 226: AI Assistant Runtime Convergence And Activity Shell

Status: `accepted / CLOSED_LOOP`

## Problem

AI Assistant 已经具备单进程 Harness MVP、durable ToolRunner ledger、事件流、
审批和基础运行壳，但还没有形成最简的生产闭环：

- AI Assistant 使用模块内 `ThreadPoolExecutor` 消费队列，同时前端仍调用
  `/runs/{runId}/worker/process`；进程退出会丢失执行能力，且与已有
  `runtime_jobs` / standalone worker 重复。
- `runtime_jobs` 的表、claim、lease、heartbeat、retry、DLQ 和 crash takeover
  具备复用价值，但仓储、Worker builder、路由和 CLI 仍位于 `workflow` 模块。
- RequestContext 可直接从未验证请求头构造，审批 actor 又来自请求体；worker
  没有独立的可信身份恢复合同。
- AI Assistant SSE 在长连接中复用请求依赖的 repository/session；live model
  路径仍是同步接口。
- 当前产品壳把大段事件合并为一个会变化的“已处理”分组，不能稳定表达阶段、
  工具、Skill 和子智能体各自的运行/完成状态。
- 当前默认工具注册表混有 demo、blocked placeholder、stub 和生产工具；核心
  `harness.py`、router 与 `AiAssistantShell.vue` 也承担过多职责。
- AI Assistant 已有 ReAct、计划、ToolRunner、上下文、记忆和权限实现，但
  Customer Assistant 没有通过公共 Interface 复用，而是维护独立
  `ControlledReActCore`、`RestrictedReactWorker`、worker registry 与 tool
  policy；同时 AI Assistant tools 反向 import Customer Assistant adapter。

本 Spec 把 P0 安全/HA、P2 活动回显和有证据的精简化放在同一条迁移路线内。
它不是重做 Harness，也不以“文件更少”为由牺牲领域边界。

## Baseline Evidence

2026-07-17 仓库事实：

| 事实 | 当前实现 |
|---|---|
| 通用 job schema | `runtime_jobs` 已含 `owner_type`、`owner_id`、lease token、heartbeat、retry/DLQ 字段 |
| job 所属模块 | repository、domain worker、worker builder、Ops route、standalone CLI 由 `workflow` 承载 |
| AI Assistant 后台执行 | router 内 4-worker `ThreadPoolExecutor` + in-flight set |
| 前端提交 | `messages/async` 后仍显式调用 `/worker/process` |
| SSE | durable event + `afterSequence`，但迭代器复用请求 service/session |
| UI 折叠 | 只有运行级“已处理”分组；分组 ID 依赖首末 sequence |
| 子智能体 | Customer Assistant 有真实 lifecycle；AI Assistant 默认 registry 只有读取引用的 bridge |
| 主要聚合文件 | `harness.py` 5014 行、AI router 1037 行、`AiAssistantShell.vue` 2928 行 |

这些数字只是拆分信号，不是按行数验收的目标。

## Product Intent

### User

需要观察、干预和审计 AI 执行的工程用户与运营人员。

### Primary Job

在模型继续输出时立即看见当前阶段、工具/Skill、审批和子智能体状态；步骤结束后
回到紧凑对话，不让历史执行日志淹没最终答案。

### Visual Reference Contract

2026-07-17 已对当前 Codex 正在运行会话做窗口截图核对。只采纳以下结构语义：

- 模型文本与执行活动在同一时间线上即时出现；
- 当前活动是一条“正在运行”的可展开记录；
- 已完成活动压缩成一行，可点击恢复详情；
- 多个命令可形成简短汇总；
- 有计划时显示当前步骤 / 总步骤；
- 运行状态靠图标、动词、文案和层级共同表达。

明确不采纳：

- Codex 当前系统暗黑色、灰阶、品牌颜色和像素值；
- Codex 侧栏、环境面板和窗口 chrome；
- 截图里的会话文本、命令内容或任何隐藏推理。

Hify 使用现有亮色 design tokens、Ant Design Vue 组件语义和 `rem` 尺寸门禁。

## Architecture Decision

规范性决策见
`docs/adr/0005-ai-assistant-runtime-job-substrate.md`。

### 1. Promote A Domain-neutral Runtime Job Substrate

复用已有 `runtime_jobs` 能力，但把下列内容提升到领域中立的 runtime 模块：

- RuntimeJob repository contract 与 SQLAlchemy adapter；
- claim / lease / heartbeat / retry / DLQ 状态机；
- bounded worker loop；
- handler registry；
- standalone worker composition。

通用 runtime 模块不得 import `workflow`、`ai_assistant` 或
`customer_assistant`。各领域注册 handler，并在自己的 adapter 内恢复 run、
调用领域 service、写领域事件。

### 2. Extract A Public Deep Agent Harness Module

AI Assistant 与 Customer Assistant 是两个真实调用方。两者共同需要的执行不变量
提升为公共 `agent_harness` Module，而不是让 Customer Assistant import
`app.modules.ai_assistant` 产品模块。

该 Module 的外部 Interface 保持为一个执行入口：

```text
AgentHarness.execute(HarnessRunRequest, HarnessProfile) -> HarnessRunResult
```

`HarnessProfile` 是产品 Adapter，提供模型/规划、ToolRunner、Context Provider、
Memory Provider、Permission/Approval Policy、事件/Checkpoint Store 与最终结果投影。
公共 Implementation 负责：

- bounded ReAct progression、最大迭代和停止条件；
- 计划状态与标准 phase/step transitions；
- tool 调用排序/并发边界、policy gate 与 observation 回灌；
- context/memory 装配顺序和预算；
- permission/approval/cancel/checkpoint transitions；
- 标准 execution event、错误与 terminal semantics。

AI Assistant Adapter 提供 workspace/Skill/Markdown memory/现有 ToolRunner 与对话结果；
Customer Assistant Adapter 提供 Task Ledger、客服工具、proposed action、worker profile
与客服结果投影。Customer Assistant business task、AI Assistant repository/schema、
Web route 和产品壳都不进入公共 Module。

公共 Module 不 import `ai_assistant`、`customer_assistant`、`workflow` 或 Web/infra
Adapter。删除该 Module 时，ReAct、policy、event/checkpoint 等复杂度会重新散回两个
调用方，因此通过 deletion test。

### 3. Keep A Bounded Public Agent Execution Module

AI Assistant 与 Customer Assistant 已经形成两个真实 Adapter，因此父子执行中
可复用的不变量提升为公共 `agent_execution` Module：

```text
SubagentExecutionRef
  provider
  childRunId
  displayName
  status
  statusRef
  eventStreamRef
  resultRef
  cancellable
```

该 Module 的 Interface 只包含：

- parent/child identity 与稳定 correlation；
- lifecycle status state machine；
- status/event/result refs 与 capability flags；
- spawn/attach/observe/cancel provider Interfaces；
- 跨 Adapter contract tests。

Agent Harness 使用该 Module spawn/attach/observe/cancel child。AI Assistant 与
Customer Assistant 分别提供 provider Adapter；父子事实仍写入 durable event，
不另建重复执行账本。Agent Execution 不重复实现 ReAct、Plan、Tool、Context、
Memory 或 Permission。

### 4. Public Module Extraction Rule

所有可复用能力按同一规则处理：

1. 两个以上真实 Adapter/调用方使用同一不变量时，提取为公共 Module；
2. 公共 Module 必须拥有状态机、错误语义或资源治理等深 Implementation，不能是
   pass-through DTO/helper；
3. 公共 Module 只暴露一个小而稳定的 Interface，业务差异留在 Adapter；
4. 公共 Module 不用 owner/type `if/else` import 业务实现；
5. 使用 deletion test：删除后复杂度若会散回多个调用方，Module 才有保留价值；
6. 一次性逻辑和仅有一个 Adapter 的可变点留在领域内部，不创建假 Seam；
7. 禁止 `common/`、`shared/`、`utils/` 作为无归属杂物包。

本 Spec 已确认的公共 Module：

| Public Module | Shared invariant | Adapters |
|---|---|---|
| Execution Substrate | job/lease/heartbeat/retry/DLQ/fencing | Workflow、Chatflow、AI Assistant |
| Agent Harness | ReAct/plan/tool/context/memory/permission/checkpoint/event execution invariants | AI Assistant、Customer Assistant |
| Agent Execution | parent-child refs/lifecycle/capabilities | Agent Harness child providers |
| Host Identity | trusted principal/scope/audit metadata | HTTP host、standalone worker、tests |

`Execution Activity` 目前是 AI Assistant product read model；其 event normalization
与状态机可公开，但视觉 Module 只有出现第二个真实调用方后才提升，避免伪复用。

### 5. Preserve Raw Events, Project Activities

durable raw event ledger 继续是回放和审计事实源。UI 不新增第二套活动表。
相关事件必须携带稳定 correlation ID；前端纯投影生成 `RunActivity`：

```text
activityId
parentActivityId?
kind = phase | tool | skill | subagent | approval
status = queued | running | waiting_approval | completed | failed | cancelled
title
summary
startedAt
completedAt?
durationMs?
detailEventIds[]
subagentRef?
```

`activityId` 必须来自 plan step id、operation id、skill invocation id 或 child
run id，不得再使用“当前最后一个 sequence”形成不稳定身份。

## P0 Security Contract

1. 生产 principal 必须来自 host 认证/签名上下文或已验证 session；任意
   `X-Hify-*` header 只能在显式 local-dev adapter 中使用。
2. pause/resume/cancel/approve/deny 的 actor 由服务端 RequestContext 决定，
   不接受请求体 `actorId` 作为审计真相。
3. session、run、job、event、approval、operation、memory 与 child execution
   都必须按 tenant/user/workspace scope 授权。
4. worker 从 durable run 中恢复已验证 scope snapshot；job payload 只保存
   identifier、policy/version ref 和非敏感执行参数，不保存 API key、cookie、
   bearer token 或原始 secret。
5. production policy fail closed。deny 高于 require approval，高于 allow；
   `always_approve` 不能绕过 managed deny、sandbox、unknown side-effect 或
   production restriction。
6. enqueue、claim、lease loss、retry、DLQ、control、approval、policy decision、
   ToolRunner UNKNOWN/reconciliation 与 child lifecycle 都有 actor/source/trace
   可审计字段。
7. 跨 scope 访问、伪造 actor、重放审批和被取消 worker 的后续写入必须有 RED
   与 contract/integration 测试。

## P0 HA Contract

1. `messages/async` 在返回前持久化 AI Assistant run 与 runtime job；请求线程
   不执行 ReAct 长任务。
2. standalone worker 能 claim `AI_ASSISTANT` owner，并通过 handler registry
   执行；API 进程退出后 job 仍可由另一 worker 接管。
3. delivery 是 at-least-once；run idempotency 与 Spec 224 operation ledger
   防止重复 user turn 和重复副作用。side-effect `UNKNOWN` 不自动重放。
4. heartbeat/lease renewal 使用独立短 session；lease 丢失后的旧 worker
   不得完成 job 或继续提交领域副作用。
5. pause/resume/cancel 与 runtime job 状态一致；运行中外部调用至少支持
   cooperative cancellation/deadline。
6. SSE 每次 poll 使用短 session/read model，不在连接生命周期持有
   SQLAlchemy session；断线后仍由 durable event + `afterSequence` 恢复。
7. 外部 LLM/HTTP/tool I/O 使用 async client 或明确隔离且有界的 compatibility
   executor；并发、timeout、retry、breaker 和 backpressure 有显式上限。
8. AI Assistant owner 进入已有 Runtime Ops 的 job/DLQ/heartbeat 观测，不再
   维护只存在于进程内的 in-flight 真相。

## Public API Migration

`POST /api/v1/ai-assistant/runs/{runId}/worker/process` 是已有公开路径，不能静默
删除：

1. 先删除 Hify 前端调用；
2. 兼容期内把 endpoint 限制为幂等 enqueue/inspect shim，不在请求线程执行
   长任务，并返回 deprecation metadata；
3. 扫描仓库、文档和已知消费者；若只有已迁移的 Hify 内部调用，按本 Spec 与
   ADR 的批准在最后清理 slice 删除；
4. 若发现外部消费者，保留 shim 并把物理删除升级为独立兼容合同。

所有 `/api/v1/...` 响应继续使用 `{code, message, data}`；已有 SSE
`delta|done|error` 兼容语义不被破坏。

## P2 Activity Shell Contract

### Streaming And Collapse

- 模型 `text.delta` 保持即时文本输出，不等待工具或阶段完成。
- `running` 活动默认展开并显示 spinner、动词、标题、已用时和当前摘要。
- 未被用户手动切换的活动从 `running` 转为 `completed` 后自动折叠为一行；
  行内保留完成图标、标题、简短结果、耗时和展开箭头。
- 用户手动展开/折叠属于当前 run 的 override，状态更新和 SSE 重连后保持；
  手动选择优先于自动折叠。
- `waiting_approval`、`failed` 不自动折叠；`cancelled` 显示明确原因。
- 详情中显示 tool/skill 输入输出的脱敏摘要、事件范围、审计引用；不显示隐藏
  chain-of-thought。
- 有 durable plan 时显示 `第 x / n 步`；无 plan 时不伪造步骤。

### Subagent Presence

- 只有真实 durable child lifecycle 才显示子智能体。
- 至少显示运行中的数量；展开后显示 display name/type、当前状态、当前摘要、
  已用时和 status/result ref。
- child 开始时显示 `正在运行 N 个子智能体`；全部完成后自动折叠为
  `已完成 N 个子智能体`；失败/等待审批保持展开。
- MVP 只要求一层 parent-child；递归团队、agent 间聊天、任务抢占和动态图编排
  不在范围。
- 现有 link-only `customer_assistant_subagent_bridge` 不能作为“正在运行”证据。
  它必须接到真实 adapter/lifecycle，或移出默认 registry。

### Light Visual Language

- 使用 Hify 现有 `--color-*`、radius、spacing、typography tokens；
- 新视觉尺寸全部使用 `rem`，1px 边框除外；
- 不复制 Codex 暗色背景、灰阶或品牌色；
- 状态不能只靠颜色表达，并遵守 reduced-motion；
- desktop 为主，中心 feed 可独立滚动；不引入新的全局三栏 IA。

## Evidence-based Cleanup Contract

删除不是按文件年龄，而是按以下证据：

```text
no accepted contract
AND no production caller
AND no migration obligation
AND replacement path is green
```

候选清单：

| 候选 | 处理 |
|---|---|
| AI router autonomous executor/lock/in-flight set | durable worker green 后删除 |
| 前端 `processAiAssistantRunWorker` | durable enqueue E2E green 后删除 |
| `/worker/process` | 按 Public API Migration 处理 |
| sequence-range “已处理”分组 | stable RunActivity 投影 green 后删除 |
| request-body actor / hard-coded `operator-ui` | server principal green 后删除 |
| `echo_context`、blocked customer update、MockAviation 默认注册 | 无生产 caller 时移到 demo/eval profile |
| link-only subagent bridge | 接真实 lifecycle 或移出默认 registry |
| stub knowledge / skill script / shell placeholder | 有真实 adapter 才进入默认 registry，否则隔离为 capability-unavailable |
| 无 handler 的 Add Context、无行为差异的 planning label | 实现真实行为或删除 UI/option |

模块边界验收：

- runtime job core 不 import 任何业务模块；
- Agent Harness 不 import AI Assistant、Customer Assistant、Workflow、Web 或 infra
  Adapter；两个产品路径都通过同一 Harness Interface；
- Customer Assistant 不 import AI Assistant 产品模块，AI Assistant 不反向 import
  Customer Assistant harness helper；
- AI Assistant router 不拥有 executor、ReAct、tool dispatch 或 projection 逻辑；
- `AiAssistantShell.vue` 不再内嵌 event grouping、SSE lifecycle 和 inspector
  projection 三套逻辑；
- 不保留新旧双路径作为“保险”；兼容 shim 必须有明确删除条件。

## Non-goals

- 不重写模型 provider、Spec 224 ToolRunner ledger 或 MEMORY.md 语义；
- 不引入 Kafka/Celery/Temporal/WebSocket 或新的 broker；
- 不做 Kubernetes 多机部署、自动扩缩容或真实容量认证；
- 不实现 OS/container 级 sandbox；
- 不扩展递归 multi-agent team、agent marketplace 或 agent-to-agent chat；
- 不模仿 Codex 暗色视觉；
- 不在本 Spec 执行生产 migration、deploy、push、merge 或真实外部模型消费。

## Slices

| Slice | Priority | Vertical outcome |
|---|---|---|
| 226.0 | Contract | 接受 Agent Harness Module、ADR、Goal Gate、verifier 与当前指针 |
| 226.1 | Foundation | 公共 Agent Harness ReAct tracer + Customer Assistant Adapter |
| 226.2 | Foundation | AI Assistant Adapter 使用同一 Harness Interface；移除反向依赖 |
| 226.3 | P0 | 领域中立 runtime job core + handler registry，Workflow/Chatflow 行为不变 |
| 226.4 | P0 | trusted principal、scope、server-derived actor、production policy/audit |
| 226.5 | P0 | AI Assistant durable enqueue + standalone worker + takeover/cancel/SSE short-session |
| 226.6 | P2 foundation | Agent Execution + stable activity correlation/projection +真实 child lifecycle event |
| 226.7 | P2 product | 亮色活动流、完成自动折叠、步骤进度、运行中子智能体存在态 |
| 226.8 | Cleanup | 重复 CA Harness、默认 registry、legacy worker path 与聚合 Module 清理 |
| 226.9 | Exit | fault/security/e2e/browser UAT、架构依赖审计与全量回归 |

226.1/226.2 未 ALL GREEN 不进入 runtime/HA 迁移；P0 未 ALL GREEN 不进入 226.6；
P2 不得用 UI fixture 掩盖缺失的 durable
runtime 或真实 child lifecycle。

## Success Predicate

以下条件必须同时成立：

1. AI Assistant 和 Customer Assistant 均通过公共 Agent Harness Interface
   执行；公共 Module 不依赖产品 Adapter，且 Customer Assistant 不依赖 AI
   Assistant 产品模块。
2. 仅调用 `messages/async` 即得到 durable run/job refs；API 进程退出后 standalone
   worker 完成 run，第二 worker 可接管过期 lease。
3. 前端不调用 worker endpoint，AI router 无 autonomous executor；重复 claim
   不产生重复 tool effect。
4. 伪造 actor/tenant/workspace、body actor 和 production `always_approve`
   绕过均被拒绝并可审计。
5. SSE reconnect 不持有长 session，按 cursor 恢复；cancel/lease loss 后无晚写。
6. Browser UAT 证明文本即时输出、运行活动展开、完成后自动折叠、失败/审批保持
   展开、手动 override 稳定。
7. Browser UAT 证明至少一个真实运行中 child 显示存在态，并在完成后折叠。
8. dependency test 证明 runtime core 与 Agent Harness 不依赖业务 Adapter；候选清理有 caller/contract
   证据，不留无期限双路径。

## Goal Gate

| Control | Contract |
|---|---|
| `success_predicate` | 上述 8 条全部有独立证据 |
| `verifier` | `loop/VERIFIERS.md` + 每 slice artifact + Checker + Reviewer |
| `max_attempts` | 每 slice 最多 3 轮定向修复；全量出口回归最多 2 轮 |
| `ttl_or_deadline` | Closed Loop 获批启动后 14 个日历日 |
| `budget_policy` | 无可核验 token budget；外部 provider 调用上限为 0，除非另行授权 |
| `on_exhaustion` | `WAITING_HUMAN`，报告失败假设、diff、证据和最小决策点 |
| `review_context` | `standard`；Checker 与 Reviewer 仍必须角色独立、只读审查 |

## Human Gates

2026-07-18 已确认：

- 已接受 Module-first 原则：边界清晰，复用不变量抽为公共 Module；
- 接受 Agent Harness 为 Customer Assistant 底层公共深层 Module，AI Assistant 与
  Customer Assistant 都作为 Adapter；
- 接受 ADR 0005 修订后的公共 Module 地图与依赖方向；
- 接受 runtime job unique key / scope 所需 Alembic migration；
- 接受 `/worker/process` 的兼容迁移与条件删除；
- 接受生产 principal 不再信任任意请求头和请求体 actor；
- 接受默认 registry 的 demo/stub 隔离清单。

命中生产数据迁移、外部消费者、真实 provider 成本、部署、push/merge 或范围扩张时
再次进入 `WAITING_HUMAN`。
