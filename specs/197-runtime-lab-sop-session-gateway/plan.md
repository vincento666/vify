# Plan 197: Runtime Lab SOP Session Gateway

## Slice 197.1 SOP Message Gateway Projection

1. 写 contract/integration 红测，锁定顶层 message-first 入口与 SOP gateway 投影。
2. 扩展 Runtime Lab message schema，允许 `sessionId`。
3. 新增 `POST /api/v1/runtime-lab/messages`，无 `sessionId` 时自动创建 session。
4. 增强 Runtime Lab turn payload，输出 Phase 4 的 session/message 字段。
5. 让 Chatflow SOP v2 adapter 将 Runtime Lab session/task 语义写入 `sys.session_id`。
6. 跑 focused gates、相邻 runtime-lab/chatflow 回归、前端 rem/unit、浏览器 UAT。

## Risk Controls

- 不修改 customer assistant 文件。
- 不重写 Runtime Lab router/arbitration 状态机。
- 不改变 existing `/sessions/{id}/messages` 行为，只增加字段。
- 不改变 checkpoint/resume 语义。
