# Slice 198.1 Customer Assistant Message Gateway

## 修改范围

- `app/modules/customer_assistant/web/schemas.py`
  - Added `CustomerAssistantMessageRequest`.
- `app/modules/customer_assistant/web/router.py`
  - Added `POST /api/v1/customer-assistant/messages`.
  - Added `POST /api/v1/customer-assistant/sessions/{sessionId}/messages`.
- `app/modules/customer_assistant/domain/service.py`
  - Added session-create/reuse message gateway wrapper.
  - Added external message response projection.
  - Added `chatflowSession` and `recovery` projection for SOP-backed Chatflow
    runs.
  - Persisted `message.delta`, `message.completed`, `requires_input`,
    `handoff_requested`, `run.completed`, and `run.failed` events for
    non-replayed turns.
- `app/modules/customer_assistant/domain/workers.py`
  - Injected stable customer-assistant Chatflow `sessionId`/`conversationId`.
  - Added worker evidence projection for Chatflow runtime refs.
- `frontend/src/api/customerAssistant.ts`
  - Existing `sendCustomerAssistantTurn` compatibility helper now calls the
    message gateway endpoint.
- `frontend/e2e/customer-assistant-message-gateway-uat.mjs`
  - Added browser UAT for first message, session reuse, replay, and
    `afterSequence` recovery.

## 红测证据

- `red.txt`
  - `POST /api/v1/customer-assistant/messages` returned 404 before the gateway.
- `frontend-red.txt`
  - Frontend API helper still called `/turns` before the message gateway switch.

## 实现摘要

- The customer-assistant UI can keep using its existing helper name while the
  API path is now message-first.
- The old `/sessions/{sessionId}/turns` endpoint is untouched for compatibility.
- The new top-level message endpoint auto-creates a customer-assistant session.
- Session-scoped message endpoint reuses the existing session.
- Idempotent replay returns the original run and does not append duplicate
  projected message events.
- SOP worker turns expose stable Chatflow session/runtime refs through
  `chatflowSession` and `recovery`.
- SSE recovery still uses the existing
  `/sessions/{sessionId}/events/stream?afterSequence=` channel.

## 已跑门禁

- Focused contract: `focused-green.txt` — 2 passed.
- Backend gate: `backend-gate.txt` — 29 passed.
- Chatflow SOP worker integration rerun: `chatflow-sop-worker-integration.txt`
  — 7 passed.
- Ruff: `ruff.txt` — passed.
- Py compile: `py-compile.txt` — passed.
- Frontend focused: `frontend-focused.txt` — 17 passed.
- Frontend runtime stream/runtime: `frontend-runtime.txt` — 17 passed.
- Frontend rem: `frontend-rem.txt` — 1 passed.
- Full frontend unit: `frontend-unit.txt` — 417 passed.
- Browser UAT: `browser-uat.txt` — passed.
- UAT report: `customer-assistant-message-gateway-uat.json`.
- UAT screenshot: `screenshots/customer-assistant-message-gateway.png`.

## 剩余风险

- `tests/e2e/customer_assistant/test_customer_assistant_runtime_e2e.py` fails in
  the current worktree because the pre-existing async worker runtime dirty
  changes leave `baggage_qa` in `RUNNING` instead of the historical
  `COMPLETED`. Evidence: `customer-assistant-runtime-e2e.txt`.
- One earlier combined run of `test_chatflow_sop_worker_v2_adapter.py` hit the
  same async worker/DB timing surface; an immediate full-file rerun passed.
- `message.delta` is currently a whole-answer projection, not token-level
  streaming. True token streaming remains a later runtime/worker capability.
- Local UAT must clear `HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS` unless the configured
  Chatflow ids exist in the test database.
