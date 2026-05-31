# 011.3 Node Config Panel Gate

## RED

- `red.txt`
- Verified the node config schema test failed because the config schema/patch helper did not exist.

## Unit

- `unit-config.txt`
- `frontend-unit.txt`
- Verified START, LLM, CONDITION, KNOWLEDGE, API_CALL, and END expose runtime-backed editable fields.
- Verified config updates preserve `config.ui.position`.

## Integration

- `backend-integration.txt`
- Verified Workflow graph CRUD remains compatible with persisted node configs.

## E2E

- `e2e.txt`
- Browser automation added an LLM node, opened the right config panel, edited node name, prompt, and output variable, saved, reloaded, and verified persisted values.
- Screenshot: `output/playwright/0113-workflow-config.png`

## Browser UAT

- Coze in-app Browser reference: `artifacts/research/coze-workflow/in-app-coze-node-config-0113.png`
- Local in-app Browser UAT: `in-app-browser-uat-config-panel.png`
- User-visible result: selecting a node shows a purple selected border and a right-side config panel with collapsible sections and persisted fields.
