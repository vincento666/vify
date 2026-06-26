# Chatflow/Workflow Production Runtime Target

本文档固化 Hify Chatflow/Workflow 生产级运行底座的目标、边界与验收标准。

本文不列 spec 编号，不作为单个开发任务清单；它用于约束后续所有实现阶段的方向和验收口径。

## 1. 总目标

把 Hify 的 Chatflow、Workflow、SOP 路由、客服助手 worker 统一到一套生产级异步运行底座上：

- Chatflow 面向对话场景，以 session/message 为一等模型。
- Workflow 面向任务场景，以 run/result 为一等模型。
- SOP 路由是客服场景下的 Chatflow 多级路由和意图切换机制。
- 客服助手通过 worker/sub-agent 调用 Chatflow/SOP/Workflow 能力。
- Runtime 统一负责异步 run、节点执行、事件流、checkpoint、resume/cancel、结果持久化。
- Runtime v2 需要支持类似 Coze/Eino 的 DAG 多路径执行语义，而不是当前单路径 `_next_node_key` 推进模型。
- 可观测与运维能力需要作为独立产品模块，而不只是开发调试页面。

最终系统应满足：

- 默认 async-first、durable-first。
- 支持实时事件回显与断线恢复。
- 支持中断、恢复、取消、重试、幂等与失败治理。
- 支持一个节点端口连接多个下游，并按 DAG 多路径语义执行。
- 不强制显式 Join 节点；多输入节点天然形成隐式汇聚。
- 支持没有下游的 terminal side-effect path，例如只调用 API 发送通知。
- Chatflow/SOP 原有多轮对话、信息收集、意图切换、转人工能力不因底层 runtime 升级受损。
- Workflow 可被外部任务系统调用，也可被 Chatflow/SOP/客服助手内部调用。
- 运维人员能观察、诊断、取消、恢复、重试 runtime run/job/node。

SOP Router 的状态边界：

- SOP Router 只维护轻量路由账本，不维护独立的 SOP 执行状态事实源。
- `current_step`、`pending_prompt`、`collected`、`scoped_variables`、`checkpoint`、`node events`、`run status` 必须来自对应 child Chatflow session/run/checkpoint/event。
- 一次客服 conversation 可以挂载多个 child Chatflow session/run。
- SOP Router 只记录 active/suspended child Chatflow 映射、route history、resume offer、intent/task 摘要。
- 不允许 SOP Router 与 Chatflow runtime 双写同一份执行状态。

## 2. 非目标

本轮目标不包含：

- 把普通画布用户暴露在 worker lease、Redis stream、checkpoint 内部结构等工程概念里。
- 强制新增显式 Join 节点或特殊 join edge。

## 3. 目标架构

```text
External Chatflow API / Customer Assistant / SOP Router
  -> Chatflow Session Gateway
    -> Runtime Invocation Gateway
      -> Async Durable Runtime
        -> DAG Scheduler
          -> Node Executors
          -> Worker Jobs
          -> Runtime Events
          -> Checkpoints / Results

External Workflow API / Internal Workflow Node
  -> Workflow Run Gateway
    -> Runtime Invocation Gateway
      -> Async Durable Runtime
```

事实来源：

- DB 是 run、node run、checkpoint、result、event 的事实来源。
- Redis Streams 或等价实时通道用于高频事件推送。
- SSE 是默认实时观察和调试通道。
- REST 查询接口是审计、恢复、短等待、断线兜底通道。

## 4. 目标一：基线锁定与回归门禁

目标：先冻结当前功能表现，避免后续 DAG 和生产化重构破坏已有能力。

验收标准：

- 后端 runtime gateway、Chatflow/Workflow stream、SOP adapter、客服助手 worker 测试全绿。
- 前端完整单测与 rem 门禁全绿。
- Chatflow 核心 UAT 通过：消息、问题、信息收集、条件分支、意图分支、转人工、resume。
- SOP 完整 UAT 通过，覆盖启动、继续、暂停、切换、恢复、拒绝切换、澄清、FAQ/RAG/Agent fallback、转人工。
- Workflow 核心 UAT 通过：LLM、API、Tool、Code、Knowledge、Execute Workflow、Agent Call。
- 明确当前 legacy 单路径行为，作为兼容基线和迁移对照。
- 后续每个阶段都必须运行基础回归门禁。

## 5. 目标二：Async Runtime 默认化

目标：把当前“支持 async”升级为“默认 async”。

验收标准：

- Chatflow/Workflow debug run 默认创建 durable runtime run。
- SOP 路由调用 Chatflow 默认返回 runtime refs。
- 客服助手 worker 调用 Chatflow/SOP 默认返回 async refs。
- 内部调用统一经过 Runtime Invocation Gateway。
- `sync` 仅作为显式 fallback，不再是默认路径。
- run 启动后立即返回 `runId`、`statusRef`、`eventsRef`、`eventStreamRef`、`nodesRef`、`resultRef`。
- 断线后可通过 `runId` 恢复查询状态、事件、节点状态和结果。
- 原有 Chatflow 多轮推进、等待输入、转人工、SOP 路由行为不退化。
- SOP Router 的 active task 摘要必须引用 child Chatflow `sessionId/runId/checkpointId`，不得复制维护 Chatflow 的 `current_step/pending_prompt/collected/scoped_variables/run status` 作为事实源。

## 6. 目标三：DAG 多路径执行语义

目标：对齐 Coze/Eino 类似的 DAG workflow 语义，允许多下游分支执行，而不是单路径选择。

核心语义：

- 一个 source port 可以连接多个 target node。
- 条件、意图、错误分支选择的是 port 或 branch group。
- 被选中的 port 下所有 target node 都进入 runnable frontier。
- 未选中的 port 及其仅依赖该 port 的下游标记为 skipped。
- 普通节点的 default port 多下游可以作为 fan-out 语义，但必须通过画布校验明确允许。
- 不要求显式 Join 节点。
- 一个节点如果依赖多个 selected upstream，则它天然是隐式 join 点。
- 没有下游的 side-effect 节点可以作为 terminal leaf。
- 整个 run 在所有 selected active paths 都完成、失败、取消或等待后进入最终状态。

验收标准：

- 有明确的 edge/port/branch/skipped/terminal/final-output 语义文档。
- 画布校验能区分合法 fan-out、多分支、side-effect terminal、隐式 join、非法孤岛节点。
- 普通顺序链路仍按原语义执行。
- 条件/意图节点命中一个 branch port 时，该 port 的多个下游都可执行。
- 未命中 branch 不阻塞后续隐式 join 判定。
- terminal side-effect path 不要求连接 End 节点。
- Chatflow 必须至少有一条 selected path 能产生可见回复、等待输入、转人工或明确的无回复执行结果。
- Workflow 可以允许无最终业务输出，但必须返回 run 状态、节点事件和 side-effect evidence。

## 7. 目标四：DAG Scheduler

目标：把 runtime v2 从单 `current node` while-loop 升级为 frontier-based DAG scheduler。

验收标准：

- Runtime 内部维护 node state graph，而不是只维护一个 current node。
- 支持 runnable frontier。
- 支持多个无依赖下游节点并发执行。
- 支持 selected、skipped、pending、running、completed、waiting、failed、cancelled 状态传播。
- 多输入节点等待所需 selected upstream 完成后执行。
- skipped upstream 不会永久阻塞下游。
- side-effect terminal leaf 完成后不报 `Next node not found`。
- run 完成判定基于 active path，而不是最后一个节点。
- 并发节点事件 sequence 单调递增。
- 支持失败策略：
  - fail-fast
  - continue-on-error
  - error branch
  - partial success
- 节点并发执行时变量作用域、输入输出、node run 记录互不串扰。

## 8. 目标五：Chatflow/SOP 兼容

目标：DAG 能力不能破坏 Chatflow/SOP 面向对话的逐轮推进心智。

验收标准：

- 默认 Chatflow 仍表现为清晰的步骤推进。
- 多路径只在明确 fan-out 或 branch 多 target 时发生。
- 信息收集、问题、人工输入、转人工节点仍可中断并 resume。
- 多路径中任一路径 waiting 时，run 能表达等待节点集合。
- resume 只恢复对应等待节点，不重跑已完成 side-effect 节点。
- SOP 多级路由调用 Chatflow 能继续支持意图切换、澄清、信息收集、转人工。
- 客服助手 worker 能正确消费 running、waiting、completed、failed、cancelled 状态。
- SOP Router 的路由账本只保存：
  - conversation id；
  - active child Chatflow session/run；
  - suspended child Chatflow sessions/runs；
  - route decision history；
  - resume offer；
  - intent/task 摘要；
  - 必要的展示缓存。
- SOP Router 不单独持有以下事实源：
  - `current_step`；
  - `pending_prompt`；
  - `collected`；
  - `scoped_variables`；
  - `checkpoint`；
  - `node events`；
  - `run status`。
- 上述信息必须从 child Chatflow session/run/checkpoint/event 聚合得出。
- 一个客服 conversation 下允许多个 child Chatflow session/run；每个 child Chatflow 独立维护自己的 checkpoint、变量、节点事件和运行状态。
- Chatflow 最终回复规则明确：
  - End 节点优先；
  - 回复节点或 answer mapping 次之；
  - 多回复候选按 priority/output mapping 决定；
  - side-effect-only branch 不参与用户回复；
  - 全路径只产生 side effect 时返回结构化执行摘要。

SOP 完整 UAT 场景矩阵：

- 新会话首轮命中强意图，启动目标 SOP，并创建对应 child Chatflow session/run。
- 用户补充信息后继续 active SOP，推进到下一等待点或完成。
- 用户在可中断步骤表达新意图，当前 child Chatflow 进入 suspended 映射，新 SOP 创建新的 child Chatflow session/run。
- 新 SOP 完成后，系统给出可恢复旧 SOP 的 resume offer。
- 用户选择恢复旧 SOP，继续原 child Chatflow session/run/checkpoint，而不是新建重复执行状态。
- 用户在不可中断步骤表达新意图，系统拒绝切换并继续当前 SOP。
- 用户表达“继续处理上一个/退回刚才流程”等显式恢复信号，能恢复正确 suspended child Chatflow。
- 用户输入不明确时进入澄清，不误创建新的 child Chatflow run。
- FAQ/RAG 命中时直接回答，不污染 active/suspended child Chatflow 状态。
- Agent fallback 命中时作为问答或建议，不替代 active SOP 的执行状态事实源。
- 转人工时保留 conversation、active/suspended child Chatflow 映射和 runtime refs。
- 多个 child Chatflow 共存时，SOP Router 只展示聚合任务摘要，`current_step/pending_prompt/collected/scoped_variables/checkpoint/node events/run status` 均从对应 child Chatflow 聚合。
- UAT 需要同时验证 API 响应、事件流、任务面板展示和刷新/断线后的恢复结果。

## 9. 目标六：全节点 Runtime V2 兼容

目标：所有合法配置的一等画布节点都能在 runtime v2 中执行。

验收标准：

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

## 10. 目标七：生产级任务调度

目标：run/job 在生产中不会丢失、重复、假死或不可恢复。

验收标准：

- DB engine/session factory 全局复用。
- DB 连接池参数可配置，包括 pool size、overflow、timeout、recycle、pre-ping。
- Runtime job claim 原子化，支持多 worker 竞争。
- Job 执行中有 heartbeat 和 lease renew。
- Worker 崩溃后 job 可被其他 worker 接管。
- Retry 支持 backoff、最大次数、错误原因记录。
- DLQ 可查询、可重试、可标记忽略。
- Run/job/node 执行具备幂等 key 或等价去重机制。
- Side-effect 节点恢复或重试时不会重复执行高风险写操作；高风险写操作默认走 proposed action 或审批。
- 生产路径中，请求线程不负责长任务执行。
- 支持独立 worker 进程执行 runtime jobs。

## 11. 目标八：事件流、取消、限流与背压

目标：实时可见，同时高并发和故障下系统可控。

验收标准：

- SSE 支持断线重连和事件游标续传。
- DB event 是事实源。
- Redis Streams 或等价机制是实时加速层。
- Redis publish 失败后可由 DB/outbox 补偿。
- DAG 并发节点事件能正确映射到前端节点状态。
- Cancel 对未开始节点立即生效。
- Cancel 对运行中节点至少支持协作式取消和 deadline。
- LLM/API/Tool/Knowledge 调用具备 timeout、重试、熔断和错误事件。
- 支持租户级、workflow/chatflow 级、worker 级、provider 级并发上限。
- 队列满时返回明确状态：queued、rejected、rate_limited 或 degraded。
- 过载时不会无限创建线程、连接、job 或事件。
- 高频事件有压缩、采样或摘要策略。

## 12. 目标九：可观测与运维面板模块

目标：把 runtime 观测与运维做成独立主菜单模块，而不是散落在调试页面中。

模块建议命名：运行观测，或 Runtime Ops。

功能范围：

- Run 列表。
- Run 详情。
- DAG 节点状态图。
- Job 队列。
- Worker 心跳。
- Event timeline。
- DLQ。
- Provider、API、Tool 调用统计。
- 失败与重试面板。
- 租户、owner type、状态、时间范围过滤。
- 安全运维动作。

验收标准：

- 主菜单存在独立模块入口。
- 可按 owner type 过滤：Workflow、Chatflow、Customer Assistant、SOP。
- 可查看 run 状态：queued、running、waiting、succeeded、failed、cancelled。
- 可查看 DAG 执行图，包含 selected、skipped、running、completed、failed、waiting。
- 可查看每个 node run 的输入摘要、输出摘要、耗时、错误和事件。
- 可查看 job lease owner、heartbeat、attempt、next retry time。
- 可查看 DLQ 并执行 retry、ignore、mark resolved。
- 可执行安全运维动作：
  - cancel run
  - retry failed job
  - resume interrupted run
  - reopen DLQ item
- 高风险动作必须二次确认。
- 默认不显示隐藏思考过程。
- 默认显示事件、工具调用、节点输入输出摘要和错误证据。
- 实时更新使用事件流；断线后可恢复。
- 有前端单测、e2e 和浏览器 UAT 截图证据。

## 13. 目标十：容量、故障与本机测试门槛

目标：用合理分层的测试证明系统能力，避免把本机资源限制误判为系统极限。

本机单体单节点验收：

- 20 到 50 并发 run：作为功能正确性和异步行为基础门禁。
- 100 到 200 并发 run：作为本机中等压力烟测，观察连接池、队列、worker、事件流是否有明显瓶颈。

类生产环境验收：

- 多 worker 并发 claim 无重复执行。
- DAG fan-out 压测下，多分支执行结果和事件一致。
- interrupt/resume 压测下，不重跑已完成 side-effect 节点。
- worker crash 演练后，job 可被接管。
- DB 重连演练后，连接池恢复正常。
- Redis 故障演练后，实时流可降级，DB 事件仍可恢复。
- LLM/API 慢调用演练下，deadline、熔断和背压生效。
- 输出容量报告，包含 p50、p95、p99、queue latency、node latency、event delay、错误率、资源占用。

## 14. UI 与产品表现原则

业务用户界面应该隐藏 runtime 工程细节。

画布调试可以展示：

- 节点状态。
- 分支走向。
- 输入输出摘要。
- 变量快照。
- API/Tool/LLM evidence。
- 错误详情。
- 完整 event timeline。

客服助手和 SOP 侧应展示：

- 会话记录。
- 当前任务和状态。
- 推荐回复。
- 等待输入或转人工原因。
- 简化的工具/API/知识库证据。

不应在普通业务界面常驻展示：

- worker lease。
- checkpoint 内部结构。
- Redis stream。
- durable queue 细节。
- 幂等锁。
- DB event 表结构。

## 15. 推进顺序约束

推荐顺序：

1. 基线锁定与回归门禁。
2. Async Runtime 默认化。
3. DAG 多路径语义模型。
4. DAG Scheduler。
5. Chatflow/SOP 兼容。
6. 全节点 Runtime V2 兼容。
7. 生产级任务调度。
8. 事件流、取消、限流与背压。
9. 可观测与运维面板模块。
10. 容量、故障与类生产验收。

关键约束：

- 不要先做运维面板；面板依赖稳定的 run/job/node/event 数据模型。
- 不要先做大规模压测；没有 job lease、heartbeat、幂等、背压之前，压测只会证明系统会坏。
- 不要把 DAG fan-out 塞进当前单路径 while-loop；必须先改成 frontier scheduler。
- 不要强制 Join 节点；正确目标是隐式 join 和 terminal side-effect path。
- Chatflow 要保守，Workflow 可以更 DAG 化；Chatflow 必须保持对话流程可解释。
- 本机测试不要求 1000 并发硬门禁；1000+ 放到类生产环境。

核心原则：

> 先保证 async runtime 默认且语义无损，再引入 DAG 多路径执行，再补任务调度可靠性和事件可靠性，最后建设可观测运维模块与容量证明。
