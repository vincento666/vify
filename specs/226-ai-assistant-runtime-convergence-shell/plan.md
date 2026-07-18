# Plan — Spec 226

Status: `accepted / Closed Loop starting at 226.1`

## Design Summary

执行顺序固定为：

```text
shared Agent Harness tracer
  -> AI Assistant + Customer Assistant Adapters
  -> neutral runtime core
  -> trusted execution identity
  -> AI Assistant durable worker
  -> stable activity events
  -> product shell
  -> evidence-based deletion
  -> exit gates
```

公共 Agent Harness 是 runtime、子智能体和产品壳共同使用的执行语义底座；P0
durable runtime 是 P2 的事实底座。UI 不能先用模拟运行态形成“看起来完成”的假象。

## Target Dependency Direction

```text
scripts / app composition root
  -> runtime job handler registry
       -> workflow adapter -> workflow domain
       -> chatflow adapter -> chatflow domain
       -> agent harness worker adapter

AI Assistant product adapter ─┐
                              ├─> agent harness
Customer Assistant adapter ───┘     -> bounded ReAct / plan / tool governance
                                    -> context / memory / permission / approval
                                    -> checkpoint / cancellation / standard events
                                         -> agent execution
                                         -> execution substrate

runtime job core
  -> core database / time / logging only

agent execution
  <- agent harness child providers
  -> execution refs / lifecycle / capabilities only

AI Assistant product shell
  -> AI Assistant API + durable raw events
  -> pure RunActivity projection
```

禁止：

```text
ai_assistant -> workflow.runtime_job_worker
runtime job core -> workflow | ai_assistant | customer_assistant
frontend -> /worker/process
UI fixture -> fake subagent running state
customer_assistant -> ai_assistant product module
agent_harness -> ai_assistant | customer_assistant | workflow | web | infra adapter
agent_execution -> ReAct | tools | memory | permissions | business tasks
```

## Public Module Map

### Execution Substrate

Deep Module with one Interface for enqueue/claim/lease/heartbeat/retry/DLQ/
fencing and handler registration. Workflow、Chatflow、AI Assistant are Adapters.

### Agent Execution

Deep Module with one Interface for parent-child identity、lifecycle、capability
refs and provider operations. Agent Harness uses it through product child-provider
Adapters. It does not duplicate the Harness loop or dispatch jobs itself.

### Agent Harness

Deep Module with one execution Interface. It owns the cross-product ordering,
state transitions and failure semantics for ReAct、plan、tool invocation、
context、memory、permission、approval、checkpoint、cancellation and standard
events. AI Assistant and Customer Assistant are two product Adapters.

Its external Seam is:

```text
AgentHarness.execute(HarnessRunRequest, HarnessProfile) -> HarnessRunResult
```

`HarnessProfile` is an Adapter composition, not a bag of optional callbacks.
It supplies typed model/planner、ToolRunner、Context Provider、Memory Provider、
Permission/Approval Policy、event/checkpoint store and result projector
Interfaces. The public Implementation owns their ordering and invariants.

The Interface guarantees:

- one bounded iteration budget and deterministic terminal status；
- permission/policy gate before tool execution；
- observation is recorded before the next planning iteration；
- cancellation/lease loss prevents later side-effect completion；
- checkpoint and standard events are monotonic/idempotent by stable run/step/
  operation identifiers；
- Adapter-specific payloads do not leak into the common event envelope。

First migration keeps compatibility facades. A facade may delegate to Agent
Harness but cannot keep a second active loop. It is deleted in 226.8 after caller
inventory and parity tests.

### Host Identity

Existing `app/core/host` becomes the trusted principal Seam shared by HTTP and
standalone worker Adapters. Raw header parsing is only a local-dev Adapter.

### Execution Activity

The lifecycle normalization can be a reusable pure Module because tool/Skill/
approval/subagent activities share one state machine. The Hify visual feed stays
inside AI Assistant until a second product actually consumes the same Interface.

Every public Module must have Interface-level contract tests and a dependency
test. No public Module may import an Adapter.

## Agent Harness Migration

### 226.1 Customer Assistant Tracer

Introduce `app/modules/agent_harness` and a single public ReAct execution
Interface. Move the bounded iteration、tool policy decision、observation
progression and terminal error semantics behind it. Customer Assistant maps
`TaskItem`/`WorkerResult` through an Adapter; its public behavior and event schema
remain compatible.

RED must prove the current Customer Assistant production worker does not cross
the public Agent Harness Seam. GREEN must prove read-only completion、denied
tool、approval wait and max-iteration behavior through that Seam.

### 226.2 AI Assistant Adapter

Adapt the AI Assistant live ReAct path to the same Interface while retaining its
durable repository、ToolRunner ledger、plan、memory and streaming behavior as
Adapters. Remove the AI Assistant -> Customer Assistant harness helper import by
moving shared child-reference invariants to Agent Execution.

RED must prove both product paths use the same Harness Module and dependency
direction. GREEN must preserve existing AI Assistant and Customer Assistant
contract/integration behavior.

### 226.8 Harness Cleanup

Only after both Adapters are green:

- delete or reduce `ControlledReActCore` and `RestrictedReactWorker` to product
  Adapters without a second loop；
- move worker/profile/task/result semantics that remain specific to Customer
  Assistant back behind its Adapter；
- delete compatibility helpers that fail the caller/deletion tests；
- keep AI Assistant storage、UI and workspace-specific tools private。

## Runtime Substrate

### Proposed Modules

Names may follow existing repo conventions, but responsibilities are frozen：

- `app/modules/runtime/domain/job.py`
  - repository protocol、claim result、lease fencing、job status。
- `app/modules/runtime/domain/worker.py`
  - bounded `run_once` 和 heartbeat lifecycle，不知道任何业务 owner。
- `app/modules/runtime/application/handler_registry.py`
  - `job_type/owner_type -> handler factory`，缺 handler fail closed。
- `app/modules/runtime/infra/runtime_job_repository.py`
  - 现有 SQLAlchemy 行为的唯一实现。
- `app/modules/runtime/composition.py`
  - 由应用入口注册 Workflow、Chatflow、AI Assistant adapters。
- `scripts/runtime_job_worker.py`
  - 使用 registry；`--owner` 增加 `ai-assistant|all`，不 import 业务 builder。

不为了目录整齐复制类；迁移时先保留 import compatibility facade，再在 226.6
清理没有 caller 的 facade。

### Schema Migration

当前 unique key 是 `(run_id, job_type)`，不同领域的数值 run id 可能相撞。
226.1 RED 必须先证明该冲突，再迁移到至少：

```text
(owner_type, run_id, job_type)
```

同时验证：

- owner type 大小写规范化；
- 现有 Workflow/Chatflow 数据无损；
- scope/tenant 可由 job payload 或明确列过滤；
- migration upgrade/downgrade 与单一 Alembic head；
- runtime ops refs 不把不同 owner 的 run id 混为同一资源。

不在没有 RED 的情况下重命名 `owner_id` 或扩充通用 job 表。

## Security Design

### Trusted Principal

在 host boundary 引入可替换 resolver：

- production resolver：由 host authentication/session 或签名 context 构造；
- local-dev resolver：显式配置时才允许 header adapter；
- tests：dependency override 提供可信 fixture。

AI Assistant endpoint 只接收 action/reason，不接收 actor 真相。若兼容 schema
暂时保留 `actorId`，服务端忽略并记录 deprecated field，随后按 API 迁移清理。

### Durable Execution Scope

enqueue 时把不可伪造的 scope snapshot/version 写入 run；job 仅引用 run。
worker 根据 run 恢复：

- tenant/user/workspace；
- principal source 与 request/trace id；
- permission policy ref/version；
- provider credential ref，而不是 credential value。

每次 control、approval、ToolRunner side effect 和 child attach 都重新做 scope/
policy gate，不能把入队时 allow 当成永久授权。

### Fail-closed Rules

- production 缺 host principal -> 401/403，不降级为 `local-user`；
- unknown owner/job handler -> FAILED/DLQ，不执行 fallback business handler；
- unknown policy effect -> require approval 或 deny；
- body actor 与 trusted actor 不一致 -> trusted actor 生效并产生 security audit；
- lease token 不匹配 -> 禁止 complete/fail/side-effect commit。

## AI Assistant Worker Design

### Enqueue

`messages/async` 的同一请求必须：

1. 创建/重放 run；
2. 写 initial durable events；
3. 幂等 enqueue `AI_ASSISTANT` job；
4. commit；
5. 返回 run/job/status/events/result refs。

如果现有 transaction boundary 不能原子覆盖 run+job，使用明确 outbox/recovery，
不得依赖进程内 submit 补偿。

### Handler

AI Assistant job handler：

- 用短 session 加载 run/scope；
- claim AI Assistant run checkpoint；
- 执行 bounded ReAct loop；
- 每次外部等待前后检查 cancellation/lease；
- 用独立短 session heartbeat；
- terminal 后更新 run/job 与事件；
- ambiguity 交给 Spec 224 UNKNOWN，而不是盲目 replay。

### SSE

route 只做权限校验和生成器构造。生成器通过 session factory 每轮短读 durable
events/run status；空闲 sleep 使用 async primitive。Redis/event bus 只作加速，
DB event 仍是恢复真相。

## Activity Event And Projection Design

### Correlation

为以下 lifecycle 保证稳定 ID：

- phase: `run:{runId}:phase:{phaseKey}`
- plan step: persisted `planStepId`
- tool: Spec 224 `operationId`
- skill: persisted invocation id
- subagent: `{provider}:{childRunId}`
- approval: approval id

started/progress/completed/failed event 必须复用同一 ID。无 correlation 的历史事件
只进入“历史详情”，不能污染新活动状态机。

### Projection

新增纯函数 `buildRunActivities(events)`：

- 输入乱序/重复 event 时仍幂等；
- reconnect 后同一 activity ID 不变；
- terminal status 单调，除非有显式 retry/reopen event；
- raw event 仍可从 activity detail 访问；
- model text 独立聚合，不当作工具活动；
- 不通过 event title/中文文案推断领域状态。

### Expansion State

前端保存：

```text
activityOverrides[runId][activityId] = expanded | collapsed
```

默认状态是纯函数：

```text
running -> expanded
waiting_approval | failed -> expanded
completed | cancelled -> collapsed
```

只有无 override 的 activity 在完成时自动折叠。session reload 可不持久化到服务端，
但同一页面 SSE reconnect 和 activity upsert 不能丢 override。

## Subagent Design

226 只做一层真实 child，并通过公共 Agent Execution Module：

1. AI Assistant Adapter 通过 `AgentExecutionProvider` spawn 或 attach 一个已授权的
   Customer Assistant child；
2. Customer Assistant Adapter 返回 `SubagentExecutionRef` durable refs；
3. parent ledger 记录 `subagent.started/progress/completed/failed/cancelled`；
4. worker 或 adapter 以真实 child status 更新 parent event；
5. UI 只投影上述 lifecycle。

bridge 返回 `linked`、reserved refs 或 `supported: false` 时只显示“已关联/能力不可用”，
不得显示“正在运行”。

## Product Shell Design

### Direction

- Subject：执行活动流，不是 dashboard 卡片集合。
- Audience：需要快速判断“现在在做什么、是否需要我介入”的工程/运营用户。
- Tone：克制、紧凑、可审计、Hify 亮色原生。
- Hierarchy：模型文本 > 当前活动 > 已完成活动 > 原始详情。

### Components

- `RunActivityFeed.vue`
- `RunActivityRow.vue`
- `SubagentActivityGroup.vue`
- `RunStepProgress.vue`
- `useAiAssistantRunStream.ts`
- `runActivityProjection.ts`

`AiAssistantShell.vue` 保留会话选择、布局和 composition；Inspector 复用 raw event/
audit refs，不复制 activity 状态机。

### Interaction

- 新活动插入在当前模型输出附近，不跳到独立 dashboard；
- running row 展开，完成后平滑收成一行；
- 支持 keyboard toggle 与 `aria-expanded`；
- reduced-motion 下无高度动画；
- summary 最多两行，详情才显示长输出；
- shell/tool output 保持 monospace 与复制动作；
- approval actions 保持就地可操作；
- child group 可显示 active count，不用头像墙或装饰性 agent 卡片。

## Evidence-based Refactor

每个 slice 只提取当前行为需要的 Seam：

- 226.1 提取 Agent Harness ReAct tracer，并接 Customer Assistant Adapter；
- 226.2 接 AI Assistant Adapter，证明两个真实调用方；
- 226.3 提取 runtime job core；
- 226.4 提取 principal/policy Seam；
- 226.5 从 router 删除 execution ownership；
- 226.6 提取 Agent Execution 与 activity event/projection；
- 226.7 提取 shell Modules；
- 226.8 做 caller inventory 后删除重复 Harness/compatibility/demo/stub。

禁止先做整文件重写再补行为测试。

## Slice Verification Strategy

### 226.1 Agent Harness Customer Adapter

RED：

- Customer Assistant production worker 未通过 `agent_harness` public Interface；
- 公共 Module 缺失时，ReAct iteration/tool policy/observation 仍在产品 Module。

GREEN：

- Agent Harness Interface-level tests；
- Customer Assistant read/deny/approval/max-iteration behavior 经 Adapter 保持；
- `agent_harness` 无业务 import。

### 226.2 AI Assistant Adapter

RED：

- AI Assistant live ReAct 未通过同一 Agent Harness Interface；
- AI Assistant tools 反向 import Customer Assistant helper。

GREEN：

- 两个真实 product Adapters 使用同一 Harness Implementation；
- AI Assistant ToolRunner/stream/plan/memory/permission 行为回归不变；
- dependency contract 全绿。

### 226.3 Runtime Core

RED：

- owner run id collision；
- core import business module；
- registry 缺 AI handler。

GREEN：

- migration + repository/worker relocation；
- Workflow/Chatflow current suites unchanged；
- standalone worker uses registry。

### 226.4 Security

RED：

- spoofed headers choose another scope；
- body actor controls approval audit；
- production always-approve bypass；
- worker restores secret/plain credential from payload。

GREEN：

- trusted resolver + server actor + scoped repository queries + audit。

### 226.5 Durable AI Worker

RED：

- API process exits after enqueue；
- two workers claim；
- lease expires during model/tool call；
- SSE connection count exhausts DB pool；
- cancel followed by late write。

GREEN：

- standalone AI handler、takeover、short-session SSE、bounded async I/O。

### 226.6 Activity Foundation

RED：

- appended event changes group ID；
- duplicate/reordered event creates duplicate activity；
- link-only bridge is labeled running。

GREEN：

- public Agent Execution Module + child-provider Adapters + stable correlation + pure
  projection + real child lifecycle。

### 226.7 Product Shell

RED：

- running not expanded；
- completion not collapsed；
- manual override lost on SSE reconnect；
- failed/approval collapsed；
- dark hard-coded colors or px visual rules；
- child presence absent。

GREEN：

- component/unit/E2E/Browser UAT against real Hify light theme。

### 226.8 Cleanup

RED/characterization：

- production caller inventory and route compatibility matrix。

GREEN：

- remove duplicate Customer Assistant harness loop、in-process worker/front-end
  call/unstable grouping；
- isolate demo/stub registry entries；
- delete compatibility facade only when the Spec condition is satisfied。

### 226.9 Exit

- security and crash/takeover regression；
- AI Assistant full unit/contract/integration/e2e/eval；
- Runtime V2 regression；
- frontend unit/build/rem；
- Browser UAT screenshot and steps；
- migration single head；
- dependency audit；
- `git diff --check`；
- Checker ALL GREEN，Reviewer PASS。

## Rollback

- Schema migration supports downgrade and preserves existing job rows。
- handler registration can disable AI Assistant owner without deleting runs/jobs。
- frontend activity components can fall back to raw timeline without changing event storage；
  fallback is release rollback only，不作为永久双路径。
- trusted principal migration must retain explicit local-dev adapter for local work，不得以
  production insecure default 作为 rollback。

## Risks

1. **表键迁移污染现有 Runtime V2**

   用 owner collision RED、upgrade/downgrade、现有 218/219 suite 限定。
2. **worker 接管导致 ToolRunner 重复副作用**

   依赖 lease fencing + Spec 224 operation ledger/UNKNOWN 联合测试。
3. **安全边界改动影响本地开发**

   保留显式 local-dev resolver，production 默认 fail closed。
4. **活动投影变成第二事实源**

   只做纯投影，不建 activity persistence table。
5. **公共 Agent Harness 退化为 God Module**

   外部 Interface 只保留 execute + typed Profile；公共 Implementation 拥有通用
   执行不变量，产品存储、业务任务、UI 和工具实现留在 Adapter。内部 Module 可以
   组合，但不扩大外部 Seam。
6. **纯重构范围失控**

   每个提取都绑定垂直 RED；无 caller/contract 证据不删除。

## Authorization Boundary

合同获批后允许：

- 本地代码、测试、Alembic migration、文档和本地 Browser UAT；
- 本地 standalone worker/fault fixture；
- mock/deterministic provider。

不允许：

- 应用 migration 到生产或共享数据库；
- 真实 provider 调用或成本；
- 部署、push、PR、merge；
- 处理真实用户敏感数据；
- 引入新基础设施依赖。
