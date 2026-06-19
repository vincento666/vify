# Spec 196: Chatflow Session Message Gateway

## Goal

将 Chatflow 对外入口推进为 `session/conversation + message` 模型，让调用方可以
像智能客服接口一样提交消息、自动创建会话、短等待同步拿答案，并继续使用 runtime
v2 的 run/status/events/result refs。

## Scope

In scope:

- 新增 Chatflow message-first REST 入口。
- 不传 `sessionId` 时自动创建可复用 session。
- 每条 message 创建或幂等重放一个 runtime v2 run。
- 支持 `waitTimeoutMs`：短运行在窗口内完成时直接返回 `answer`，超时则返回 run refs。
- 复用 `idempotencyKey` 防止重复创建同一轮 run。
- 提供 session 级事件查询，保留 run 级事件查询。
- Chatflow runtime v2 记录 user/assistant final message 事件，DB 继续作为事实来源。

Out of scope:

- `messages:stream` 流式入口。
- SOP Router 接入。
- 客服助手接入。
- Durable Worker/runtime_jobs。
- 前端产品 UI 改造。
- 为验收门禁或非功能修复新开 spec。

## Acceptance Criteria

- RED 证明当前没有 `POST /api/v1/chatflows/{id}/messages` message-first 入口。
- RED 证明当前无法通过 session 级 events 查询同一会话的多轮 turn 事件。
- GREEN 后，不传 `sessionId` 可提交第一条 message，并返回 `sessionId/conversationId/runId/status/answer`。
- GREEN 后，传回 `sessionId` 可继续第二轮，返回同一个 session 与新的 run。
- GREEN 后，`waitTimeoutMs` 内完成的短链路返回 `status=SUCCEEDED` 与 `answer`。
- GREEN 后，相同 `idempotencyKey` 重试返回同一个 `runId`，且不重复创建运行事件。
- GREEN 后，session events 包含该 session 的 user/assistant/runtime 事件，run events 仍可按 run 查询。

## Constraints

- 响应 envelope 仍为 `{code, message, data}`。
- runtime v2 refs URL 与现有 `/api/v1/runtime-runs/...` 合约保持兼容。
- 不改变 legacy `/api/v1/chatflows/{id}/runs` 的同步兼容行为。
- 不要求 Redis 必须配置；Redis Streams 仍只是实时缓冲。
- 所有证据保存到
  `artifacts/slices/196-chatflow-session-message-gateway/196.1/`。
