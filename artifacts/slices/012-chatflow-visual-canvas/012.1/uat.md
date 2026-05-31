# 012.1 Browser UAT

## Scope

- Feature: Chatflow first-class module entry.
- Goal: Chatflow tab, list entry, create route, and detail canvas route are visible and navigable.

## Browser Evidence

- Browser interaction screenshot: `../../../../output/playwright/0121-chatflow-entry.png`

## Acceptance

- Workflow module exposes sibling `Workflow` and `Chatflow` tabs.
- Chatflow list shows `新建 Chatflow` and an empty/default state.
- Create route `/chatflows/create` opens the Chatflow canvas shell.
- Detail route `/chatflows/:id/canvas` opens the same shell with the target Chatflow identity.

## Gate Evidence

- RED: `red.txt`
- Unit: `unit-route.txt`, `frontend-unit.txt`
- Build: `frontend-build.txt`
- Backend compatibility smoke: `backend-integration.txt`
- E2E: `e2e.txt`
