# Spec 197: Runtime Lab SOP Session Gateway

## Goal

将 Runtime Lab 的 SOP Router 对外收敛为 session/message-first 入口，使客服场景的
SOP 调用语义与 Chatflow Session Gateway 对齐。

## Scope

In scope:

- 新增 `POST /api/v1/runtime-lab/messages`，支持省略 `sessionId` 自动创建会话。
- 保留现有 `/api/v1/runtime-lab/sessions/{sessionId}/messages`。
- Runtime Lab turn 响应增加 SOP gateway 投影：
  `sessionId/conversationId/currentSopId/runId/intent/status/answer/latencyMs`。
- Chatflow-bound SOP v2 run 使用稳定的 Chatflow session id，而不是 run-scoped fallback id。
- 继续复用现有 Runtime Lab events 与 chatflow trace 查询接口。

Out of scope:

- 客服助手接入。
- `messages:stream`。
- 改造 checkpoint resume 为每条消息一个新 run。
- Durable Worker/runtime_jobs。
- 前端产品 UI 改造。
- 为验收门禁或非功能修复新开 spec。

## Acceptance Criteria

- RED 证明当前没有 `/api/v1/runtime-lab/messages` 顶层 message-first 入口。
- RED 证明当前 Runtime Lab turn 响应缺少 SOP gateway 投影字段。
- GREEN 后，首轮 `POST /api/v1/runtime-lab/messages` 可自动创建 session，并返回
  `sessionId/conversationId/currentSopId/runId/intent/status/answer/latencyMs`。
- GREEN 后，后续请求带回 `sessionId` 可以复用同一 Runtime Lab session。
- GREEN 后，Chatflow trace 中的 `chatflow.runId` 与 turn 响应的 `runId` 对齐。
- GREEN 后，Chatflow trace 中的 `chatflow.sessionId` 使用 Runtime Lab SOP 语义稳定值。

## Constraints

- 响应 envelope 仍为 `{code, message, data}`。
- 现有 Runtime Lab session-scoped message endpoint 保持兼容。
- trace/events 查询接口保持现有 URL。
- 不触碰客服助手脏改或现有前端 e2e 脏文件。
- 所有证据保存到
  `artifacts/slices/197-runtime-lab-sop-session-gateway/197.1/`。
