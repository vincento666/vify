# 012.2 Browser UAT

## Scope

- Feature: shared graph persistence for Chatflow with `flow_type=CHATFLOW` separation.
- Goal: Chatflow can be created, reopened, and listed independently from Workflow while storing nodes/edges in the shared workflow graph tables.

## Browser Evidence

- Browser interaction screenshot: `../../../../output/playwright/0122-chatflow-shared-graph.png`

## Acceptance

- `/api/v1/chatflows` creates resources with `flowType: CHATFLOW`.
- `/api/v1/workflows` creates and lists only `WORKFLOW` resources by default.
- Chatflow detail is available through `/api/v1/chatflows/{id}` and hidden from `/api/v1/workflows/{id}`.
- Chatflow START defaults include conversational variables such as `sys.query`, `sys.conversation_id`, `sys.user_id`, `sys.channel`, and `sys.round`.
- Browser create/reopen path displays the saved Chatflow name and persisted system variables.

## Gate Evidence

- RED: `red.txt`
- Unit: `unit-flow-type.txt`, `frontend-unit.txt`
- Build: `frontend-build.txt`
- Backend integration: `backend-integration.txt`
- E2E: `e2e.txt`
