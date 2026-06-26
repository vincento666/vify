# Spec 219: Runtime Event Stream, Cancel, Rate Limit, Backpressure

> 来源：`docs/chatflow-workflow-production-upgrade.md` §11

## 背景

生产 runtime 必须在实时观察和过载保护之间取得平衡：SSE 断线重连、事件游标续传、DB / Redis 两层事件协同、取消语义、各级并发上限、过载明确状态、高频事件压缩。spec 219 把这些能力一次性补到 runtime / gateway / SSE / Redis stream 层，让 runtime 在高并发和故障下保持可控。

## 目标（What）

逐条复用文档 §11 的目标和验收标准：

- SSE 支持断线重连和事件游标续传。
- DB event 是事实源。
- Redis Streams 或等价机制是实时加速层。
- Redis publish 失败后可由 DB / outbox 补偿。
- DAG 并发节点事件能正确映射到前端节点状态。
- Cancel 对未开始节点立即生效。
- Cancel 对运行中节点至少支持协作式取消和 deadline。
- LLM / API / Tool / Knowledge 调用具备 timeout、重试、熔断和错误事件。
- 支持租户级、workflow / chatflow 级、worker 级、provider 级并发上限。
- 队列满时返回明确状态：queued、rejected、rate_limited 或 degraded。
- 过载时不会无限创建线程、连接、job 或事件。
- 高频事件有压缩、采样或摘要策略。

## 不在范围（Non-goals）

- 不实现观测面板（属于 spec 220）。
- 不做容量 / 故障 / 类生产验收（属于 spec 221）。

## 与前序 spec 的依赖

- 前置：spec 218 ALL GREEN。
- 文档 §15 顺序：本 spec 是 "事件流、取消、限流与背压"。

## Slice 列表

| Slice | 内容 | 主要门禁 |
|-------|------|----------|
| 219.1 | SSE 断线重连 + `afterSequence` 游标续传；DB event 事实源 + Redis stream 实时层 + outbox 补偿 | RED / Contract / Integration / E2E |
| 219.2 | DAG 并发节点事件 → 前端节点状态映射 | RED / Frontend Unit / E2E / UAT |
| 219.3 | Cancel：未开始节点立即生效；运行中节点协作式取消 + deadline | RED / Contract / Integration / E2E |
| 219.4 | LLM / API / Tool / Knowledge 调用 timeout / 重试 / 熔断 / 错误事件统一 | RED / Unit / Integration |
| 219.5 | 多级并发上限：tenant / workflow / chatflow / worker / provider；队列满返回 queued / rejected / rate_limited / degraded | RED / Contract / Integration |
| 219.6 | 高频事件压缩 / 采样 / 摘要 | RED / Contract / Integration |
| 219.7 | 出口回归：spec 212-218 入口门禁全套 | All gates |

## 验收门禁映射（Acceptance Gate Map）

| 文档验收标准 | 对应 slice | 检测命令 |
|------------|-----------|---------|
| SSE 断线重连 + cursor 续传 | 219.1 | `tests/contract/runtime/test_sse_reconnect.py` + `rtk node frontend/e2e/chatflow-resume-reliability.mjs` |
| DB event 事实源 + Redis stream 加速 + outbox 补偿 | 219.1 | `tests/integration/runtime/test_event_outbox_compensation.py` |
| DAG 并发节点事件 ↔ 前端状态映射 | 219.2 | `rtk npm --prefix frontend run test:unit -- runtime-node-state-store` + UAT |
| Cancel 未开始节点立即生效 | 219.3 | `tests/contract/runtime/test_cancel_unstarted_node.py` |
| Cancel 运行中节点协作式 + deadline | 219.3 | `tests/integration/runtime/test_cooperative_cancel.py` |
| LLM / API / Tool / Knowledge 调用治理 | 219.4 | `tests/unit/runtime/test_external_call_governance.py`、`tests/integration` 子套件 |
| 多级并发上限 | 219.5 | `tests/contract/runtime/test_concurrency_limits.py` |
| 队列满返回明确状态 | 219.5 | `tests/contract/runtime/test_queue_states.py` |
| 高频事件压缩 / 采样 | 219.6 | `tests/contract/runtime/test_event_compaction.py` |
| 过载不创建无限资源 | 219.5, 219.6 | 集成测试断言 connection / thread 上限 |

## 文档关联

- Source: `docs/chatflow-workflow-production-upgrade.md` §11
- Gates: `docs/testing/acceptance-gates.md`
- Output doc: `docs/runtime/event-cancel-ratelimit.md`
- Prior baseline evidence: `artifacts/slices/baseline-2026-06-26-runtime-prod-upgrade/baseline.md`
