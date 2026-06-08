# 036 Browser UAT

- Server: http://127.0.0.1:18084
- UI: Swagger UI controlled through the Codex in-app browser
- Seeded FAQ KB: Runtime FAQ UAT, question `儿童票可以退吗？`

## Flow

1. Created runtime-lab session through Swagger UI.
2. Posted `儿童票可以退吗？` with no active SOP. Result: `ANSWER_FAQ`, `sourceLayer=faq_exact`, `reasonCode=EXACT_MATCH`, reply `儿童票如未使用可按客票规则申请退票。`.
3. Posted `我要退票`. Result: `START_SOP`, active task `refund_ticket`, step `collect_order_no`, checkpoint `1`.
4. Posted `儿童票可以退吗？` while refund SOP is active. Result: `ANSWER_FAQ`; active task id/currentStep/checkpointId/businessRefs were preserved; new events were `USER_MESSAGE, ROUTE_DECISION, FAQ_ANSWERED` and did not include `TASK_CONTINUED`.

## Evidence

- Raw result JSON: `browser-uat-result.json`
- Screenshot: `screenshots/browser-uat-faq.png`
