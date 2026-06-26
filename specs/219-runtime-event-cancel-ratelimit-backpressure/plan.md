# Plan — Spec 219

## 实施策略

按 RED → GREEN → REFACTOR 串行推进 slice 列表。每个 slice 必须先写红测证据再写最小实现。

- 219.1 把 SSE 事件流可靠化（DB 事实源 + Redis 加速 + outbox 补偿）。
- 219.2 把"DAG 并发节点事件"投影到前端 store / 节点状态。
- 219.3 取消语义：未开始 vs 运行中两种 case。
- 219.4 外部调用治理（timeout / 重试 / 熔断 / 错误事件）补齐。
- 219.5 多级并发上限 + 队列状态。
- 219.6 高频事件压缩。
- 219.7 出口回归。

## 关键风险

- 风险 1：DB / Redis 双写引入数据不一致。
  - 缓解：219.1 钉死 "DB 为事实源 / Redis 仅加速 / outbox 写后补"；contract 用 chaos test 模拟 Redis 故障。
- 风险 2：取消运行中节点时，外部 client（LLM/API/Tool）可能不响应 cancel。
  - 缓解：219.3 协作式 cancel + deadline + 强制 timeout；外部 client 必须在 N 秒内放弃。
- 风险 3：并发上限收紧后老 UAT 可能因排队超时失败。
  - 缓解：219.5 默认上限设置在合理水位；UAT 跑前 reset；CI 不开启严格限流。
- 风险 4：事件压缩策略可能丢"业务关键 event"。
  - 缓解：219.6 列出"不压缩 event"白名单（error / waiting input / final reply）。

## 与其他 spec 的相互影响

- 与 spec 218：cancel / retry / DLQ 共用 job 状态机。
- 与 spec 220：本 spec 暴露的 event store + Redis stream 是观测面板实时通道源头。
- 与 spec 221：本 spec 完成后才允许在 221 做容量演练。

## 工程任务序列

1. 219.1 → 219.2 → 219.3 → 219.4 → 219.5 → 219.6 → 219.7。

## 出口条件（Definition of Done for the whole spec）

- SSE 断线重连 + 事件游标续传可用，DB / Redis / outbox 一致。
- DAG 并发事件正确映射到前端状态。
- Cancel 两类语义在 contract + integration + UAT 上有证据。
- LLM / API / Tool / Knowledge 调用 timeout / 重试 / 熔断 / 错误事件统一。
- 多级并发上限 + 队列状态在 contract 上明确。
- 高频事件压缩有策略且不丢业务关键 event。
- spec 212-218 入口门禁回归全绿。
