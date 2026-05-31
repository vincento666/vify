# 011.4 Variable Reference Selector Gate

## RED

- `red.txt`
- Verified the variable catalog test failed because graph-aware catalog helpers did not exist.

## Unit

- `unit-variable.txt`
- `frontend-unit.txt`
- Verified available variables are limited to START variables and connected upstream node outputs.
- Verified inserted references use `{{node.variable}}` syntax.

## Integration

- `backend-integration.txt`
- Verified Workflow graph CRUD preserves config fields containing template references.

## E2E

- `e2e.txt`
- Browser automation added an LLM node, connected it, opened the variable selector, inserted `{{start.USER_INPUT}}`, saved, reloaded, and verified the reference persisted.
- Screenshot: `output/playwright/0114-workflow-variable.png`

## Browser UAT

- Local in-app Browser UAT: `in-app-browser-uat-variable-open.png`
- User-visible result: the node config panel exposes a `变量` trigger beside text fields, keeps selected node state, and shows inserted references in the field and node output.
