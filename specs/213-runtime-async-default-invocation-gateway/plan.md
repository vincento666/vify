# Plan — Spec 213

## 实施策略

按 RED → GREEN → REFACTOR 串行推进 slice 列表。每个 slice 必须先写红测证据再写最小实现。

- 213.1 先定义 Gateway Protocol / DTO 与六元组 refs 契约。
- 213.2~213.4 把三类调用方（Chatflow / Workflow debug、SOP Router、客服 worker）逐个迁到默认 async。
- 213.5 把 recovery 收敛为统一查询语义。
- 213.6 把 spec 212 入口门禁重跑一遍作为出口签收。

## 关键风险

- 风险 1：默认 async 后，前端调试页若仍按 sync 期望解析响应，会立刻红测。
  - 缓解：213.2 同步更新前端 store / runner，并在 e2e 加 RED 证据；不允许在 backend 双写 sync+async。
- 风险 2：SOP Router 现有写入路径可能多处 mutate `current_step / collected / scoped_variables`。
  - 缓解：213.3 用合约级单测断言 ledger schema 只含 conversation/active/suspended/route history/resume offer/intent summary 字段；移除其余字段时统一通过仓库层去找写入位点。
- 风险 3：客服 worker 同步 fallback 在某些 prompt 模式下仍是必要回退路径。
  - 缓解：保留 `sync=true` 显式开关并加 metric 标识；默认路径必须返回 async refs。
- 风险 4：runId 恢复路径在 LLM 流式中途断线时，event stream cursor 与 result ref 不一致。
  - 缓解：213.5 用 `afterSequence` 与 durable result 一致性测试覆盖；不引入新存储。

## 与其他 spec 的相互影响

- 与 spec 212：213.6 必须重跑 212.5 的入口门禁全套脚本，做出口签收。
- 与 spec 214 / 215：默认 async 是 DAG scheduler 的前置；frontier scheduler 在 213 完成后才能上线。
- 与 spec 218：213 引入的 runId / refs 是 218 job 调度的写入入口；任何 ref 字段变更须告知 218 设计。
- 与 spec 220：213 暴露的 refs 是观测面板列表 / 详情页的字段源头，不允许 220 阶段再扩展同名字段。

## 工程任务序列

1. 完成 213.1 Protocol / DTO 与契约测试。
2. 完成 213.2 Chatflow / Workflow debug run 默认 async；同步迁移前端。
3. 完成 213.3 SOP Router ledger 收紧；从代码层确认无 `current_step / collected / scoped_variables / run status` 写回。
4. 完成 213.4 客服 worker 默认 async refs。
5. 完成 213.5 runId 恢复一致性测试。
6. 完成 213.6 出口回归。

## 出口条件（Definition of Done for the whole spec）

- 所有 Chatflow / Workflow / SOP / 客服 worker 入口调用默认返回 `RuntimeInvocationGateway` 六元组 refs。
- `sync` 仅作为显式 fallback；代码搜索 sync=true 调用集中在 fallback / test 列表内。
- SOP Router 的 ledger schema 通过单测 / 合约测试断言，不再持有 Chatflow 执行状态字段。
- 断线 → runId → status/events/nodes/result 恢复链路有 contract 与 UAT 证据。
- spec 212 入口门禁（unit / integration / contract / frontend / UAT / rem）全套通过。
