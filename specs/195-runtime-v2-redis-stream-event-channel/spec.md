# Spec 195: Runtime V2 Redis Stream Event Channel

## Goal

将 runtime v2 实时事件通道从纯 DB polling SSE 升级为 DB 事实来源 +
Redis Streams 实时缓冲的双轨模型。

## Scope

In scope:

- runtime v2 事件写入 DB 成功后，同步发布到 Redis Streams 抽象。
- SSE Gateway 优先读取 Redis Streams 中 `sequence > afterSequence` 的事件。
- Redis 不可用、stream 丢帧或未配置时，继续从 DB 事件表兜底回放。
- `afterSequence` 合约、`eventStreamRef` URL 和现有 `/events` 查询接口保持兼容。
- Redis Streams 仅作为实时缓冲，不替代 DB 中的 session/run/checkpoint/final result。

Out of scope:

- WebSocket 或双向控制。
- Durable Worker、runtime_jobs、lease 接管。
- Chatflow Session Gateway、SOP Router、客服助手 message-first 接入。
- 为门禁或修复本身新开 spec。

## Acceptance Criteria

- RED 证明当前 runtime v2 事件不会发布到 Redis stream 抽象。
- RED 证明 SSE 迭代器无法从 Redis stream 优先读取事件。
- GREEN 后，append event 会在 DB commit 后发布 `runId/sequence/type/payload` 到 stream bus。
- GREEN 后，SSE 对 `afterSequence` 的读取顺序为：Redis stream 命中优先，DB 兜底补漏，heartbeat 维持空闲连接。
- Redis 发布失败不得导致 DB 事件写入失败。
- 现有 runtime v2 focused gates 保持通过。

## Constraints

- 不改变现有 response envelope。
- 不改变 `/api/v1/runtime-runs/{runId}/events/stream?afterSequence=...` 合约。
- 不引入强制 Redis 依赖；未配置 Redis 时行为必须与阶段 1 一致。
- 所有新增测试遵循 RED -> GREEN，并保存证据到
  `artifacts/slices/195-runtime-v2-redis-stream-event-channel/195.1/`。
