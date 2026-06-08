# 033.4 Browser UAT

Date: 2026-06-09 Asia/Shanghai

Tool: Codex in-app Browser controlling Swagger UI.

Server:

```text
HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS= uv run uvicorn app.main:app --host 127.0.0.1 --port 18083
```

Flow:

1. Opened `http://127.0.0.1:18083/docs`.
2. Expanded `POST /api/v1/runtime-lab/sessions`.
3. Clicked `Try it out` and `Execute`; created session `6797`.
4. Expanded `POST /api/v1/runtime-lab/sessions/{session_id}/messages`.
5. Sent `我要退票`; verified `START_SOP` and active task `refund_ticket`.
6. Sent `我要人工客服`; verified hard-stop `HANDOFF_TO_HUMAN`.

Checks:

- `routeDecision.action == HANDOFF_TO_HUMAN`
- `finalDecision.sourceLayer == explicit_signal`
- `finalDecision.reasonCode == USER_REQUEST`
- `routeDecision.handoff.matchedTerms` includes `人工客服`
- runtime events include `HANDOFF_DECIDED`
- runtime events include `HANDOFF_REQUESTED`
- active task remains `refund_ticket` in `RUNNING`
- no `SOP_ADAPTER` or `CHATFLOW_START_FAILED` evidence appears

Evidence:

- `browser-uat-result.json`: structured check result with `passed=true`.
- `screenshots/browser-uat-handoff.png`: full-page Swagger response screenshot.
