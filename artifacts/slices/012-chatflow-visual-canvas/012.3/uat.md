# 012.3 Browser UAT

## Scope

- Feature: Chatflow variable scopes and variable insertion.
- Goal: authors can see scoped Chatflow variables and insert references into a node-backed field that persists through save/reopen.

## Browser Evidence

- Browser interaction screenshot: `../../../../output/playwright/0123-chatflow-variables.png`

## Acceptance

- Variable panel shows `System`, `Global`, `Conversation`, `User`, `Channel`, and `External Input`.
- System variables include `{{sys.query}}`, `{{sys.conversation_id}}`, `{{sys.user_id}}`, and `{{sys.channel}}`.
- Inspector variable selector inserts `{{sys.query}}` into the reply template.
- Saving Chatflow stores the template in node config and reopening preserves it.

## Gate Evidence

- RED: `red.txt`
- Unit: `unit-variables.txt`, `frontend-unit.txt`
- Build: `frontend-build.txt`
- Backend integration: `backend-integration.txt`
- E2E: `e2e.txt`
