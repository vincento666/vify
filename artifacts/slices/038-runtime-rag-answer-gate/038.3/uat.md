# 038.3 Browser UAT

Date: 2026-06-09

Target: `http://127.0.0.1:18086/docs`

Setup:

- DB: `/tmp/hify_runtime_rag_uat.db`
- Knowledge base: `1`
- Server env:
  - `HIFY_RUNTIME_LAB_RAG_KNOWLEDGE_BASE_IDS=1`
  - `HIFY_RUNTIME_LAB_FAQ_KNOWLEDGE_BASE_IDS=`
  - `HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS=`

Flow:

1. Swagger `POST /api/v1/runtime-lab/sessions` created session `3`.
2. Swagger `POST /api/v1/runtime-lab/sessions/{session_id}/messages` with `航班延误超过4小时保险怎么赔？`.
3. Verified `ANSWER_RAG`, `sourceLayer=rag_policy`, `reasonCode=RAG_HIGH_CONFIDENCE`, citation `chunk:1`, `mutatesSopState=false`.
4. Swagger message `我要退票`.
5. Verified `START_SOP`, active SOP `refund_ticket`, step `collect_order_no`.
6. Swagger message `航班延误保险怎么赔？`.
7. Verified `ANSWER_RAG`, citation `chunk:1`, active task id/current step/checkpoint preserved, and `RAG_ANSWERED` event emitted.

Result: PASS

Evidence:

- `browser-uat-result.json`
- `screenshots/browser-uat-rag.png`
