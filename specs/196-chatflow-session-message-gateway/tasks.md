# Tasks 196: Chatflow Session Message Gateway

## 196.1 Message-First Gateway

- [x] RED: prove message-first Chatflow endpoint is missing.
- [x] RED: prove session-level events query is missing.
- [x] Add message request schema.
- [x] Add `POST /api/v1/chatflows/{chatflowId}/messages`.
- [x] Normalize message/session/conversation input into runtime v2 `sys.*`.
- [x] Support `waitTimeoutMs` with direct answer on short completed runs.
- [x] Reuse runtime v2 idempotency for same message turn.
- [x] Persist Chatflow `user_message` and `assistant_message` events.
- [x] Add session-level events query.
- [x] Run focused unit/integration/contract gates.
- [x] Run frontend remScaleClosure and full frontend unit gates.
- [x] Run browser UAT and save evidence.
- [x] Commit the slice.
