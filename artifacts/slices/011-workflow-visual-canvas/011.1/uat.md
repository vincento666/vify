# 011.1 Workflow Tab Shell Gate

## RED

- `red.txt`
- Verified the route/list UI test failed because `/chatflows` and tab metadata were missing.

## Unit

- `unit-route.txt`
- `frontend-unit.txt`
- Verified router exposes `/workflows`, `/workflows/create`, `/chatflows`, and `/chatflows/create` with shared Workflow/Chatflow tab metadata.

## Integration

- `backend-integration.txt`
- Verified existing Workflow CRUD/list behavior remains compatible.

## E2E

- `e2e.txt`
- Browser script visited Workflow, switched to Chatflow, switched back, and opened Workflow create shell.

## Browser UAT

- Screenshot: `output/playwright/0111-workflow-tabs.png`
- User-visible result: Workflow module displays `Workflow` and `Chatflow` tabs, keeps the Workflow list/create path, and exposes the Chatflow entry shell.

## Coze Reference

- Research notes: `artifacts/research/coze-workflow/notes.md`
- Primary visual reference for next slice: `artifacts/research/coze-workflow/coze-workflow-node_hu_503fa31c1fa4b206.png`
