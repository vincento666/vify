# 012.4 Browser UAT

## Scope

- Feature: Chatflow conversation-shaped test run.
- Goal: test panel accepts a user message and conversation profile, injects `sys.*` variables, runs the shared executor, and displays assistant-style output.

## Browser Evidence

- Browser interaction screenshot: `../../../../output/playwright/0124-chatflow-conversation-run.png`

## Acceptance

- Test profile maps message, conversation ID, user ID, channel, round, and metadata to `sys.*` variables.
- Shared runtime renders `{{sys.query}}` and `{{sys.channel}}` in Chatflow templates.
- Browser test run saves the Chatflow, calls `/api/v1/chatflows/{id}/runs`, and displays a user/assistant message pair.
- Assistant result contains the real backend-rendered output `机器人收到 查订单 via web`.

## Gate Evidence

- RED: `red.txt`
- Unit: `unit-run-profile.txt`, `frontend-unit.txt`
- Build: `frontend-build.txt`
- Backend integration: `backend-integration.txt`
- E2E: `e2e.txt`
