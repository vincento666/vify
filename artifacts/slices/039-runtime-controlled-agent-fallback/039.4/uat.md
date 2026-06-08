# 039.4 Browser UAT

Date: 2026-06-09

Target: `http://127.0.0.1:18087/docs`

Flow:

1. Swagger `POST /api/v1/runtime-lab/sessions` created session A.
2. Message `机场大巴末班车几点`.
3. Verified `AGENT_FALLBACK`, `sourceLayer=agent_policy`, `reasonCode=AGENT_ANSWER`, `mutatesSopState=false`.
4. Swagger created session B.
5. Messages `不知道`, `还是那个`, `不知道`.
6. Verified first two turns returned `CLARIFY` with `AGENT_CLARIFICATION`.
7. Verified third clarification failure returned `HANDOFF_TO_HUMAN`, `sourceLayer=agent_policy`, `reasonCode=CLARIFICATION_FAILED`, with `HANDOFF_REQUESTED` event.

Result: PASS

Evidence:

- `browser-uat-result.json`
- `screenshots/browser-uat-agent.png`
