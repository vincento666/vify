# Plan 196: Chatflow Session Message Gateway

## Slice 196.1 Message-First Gateway

1. 写 contract/integration 红测，锁定自动 session、短等待 answer、幂等重放、
   session/run events 查询。
2. 增加 `ChatflowMessageRequest` schema。
3. 增加 Chatflow message route，将 `message/sessionId/conversationId` 规范化为
   runtime v2 `sys.*` 输入。
4. 复用 runtime v2 start/complete/result refs，增加 `waitTimeoutMs` 短等待包装。
5. 在 Chatflow runtime v2 开始和完成时写入 `user_message` 与 `assistant_message` 事件。
6. 增加 session events 查询。
7. 跑 focused gates 与统一高规格验收，保存证据并提交。

## Risk Controls

- 不修改 legacy `/runs`。
- 不改前端产品代码；UAT 使用新增独立脚本。
- 幂等能力复用现有 runtime v2 started-event 查找。
- wait 仅做 REST 短等待包装，不把 daemon thread 扩成 durable worker。
