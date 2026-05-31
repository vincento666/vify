# 012.5 Browser UAT

## Scope

- Feature: Chatflow publish/Open API shell.
- Goal: publish is blocked until a successful Chatflow test run; shell shows channel and API fields without implementing real channel adapters.

## Browser Evidence

- Browser interaction screenshot: `../../../../output/playwright/0125-chatflow-publish.png`

## Acceptance

- Publish shell shows default channel, method `POST`, resource type `CHATFLOW`, and `/api/v1/chatflows/{id}/runs`.
- Publish is blocked before successful test run with `需要先完成一次成功试运行`.
- After conversation test run succeeds, shell shows `SUCCEEDED` and a Run ID.
- Publishing updates Chatflow status to `PUBLISHED`.
- Real channel adapters remain out of scope; only configuration/API fields are shown.

## Gate Evidence

- RED: `red.txt`
- Unit: `unit-publish.txt`, `frontend-unit.txt`
- Build: `frontend-build.txt`
- Backend integration: `backend-integration.txt`
- E2E: `e2e.txt`
