# Spec 011-012 Canvas Correction UAT Report

Date: 2026-06-01

## Scope

- Workflow and Chatflow canvas routes use an independent full-screen workbench instead of being embedded in the standard app layout.
- Chatflow reuses the workflow graph workbench and adds conversation lifecycle panels for opening text, guide questions, scoped variables, conversation run input, Open API, publish, and observation.
- END node supports response content templates, so Chatflow variables such as `{{sys.query}}` and `{{sys.channel}}` can be inserted, persisted, and rendered by runtime execution.

## Reference Alignment

- Local PRDs reviewed:
  - `/Users/vincento/work/develop/vifly-experiment/docs/reports/coze-workflow-target-prd-20260528.md`
  - `/Users/vincento/work/develop/vifly-experiment/docs/reports/coze-chatflow-target-prd-20260528.md`
- Official Coze/Coze Studio docs checked:
  - Coze Studio workflow nodes are modeled as DAG nodes with start/end lifecycle and persisted canvas configuration.
  - Coze API docs require published workflow/chatflow execution and expose visual debug links for run inspection.

## Gates

- Frontend unit: `npm run test:unit` passed, 18 files / 34 tests.
- Frontend build: `npm run build` passed.
- Backend workflow/chatflow red and integration tests: `uv run pytest tests/integration/workflow tests/unit -q` passed, 82 tests.
- Browser e2e/UAT on `http://127.0.0.1:15182` passed:
  - `workflow-tabs`
  - `workflow-canvas`
  - `workflow-config`
  - `workflow-variable`
  - `workflow-test-run`
  - `workflow-publish`
  - `chatflow-entry`
  - `chatflow-shared-graph`
  - `chatflow-variables`
  - `chatflow-conversation-run`
  - `chatflow-publish`

## Screenshots

PNG screenshots are generated locally under this folder and intentionally ignored by Git via
`artifacts/**/*.png`.

- `workflow-canvas.png`
- `workflow-config.png`
- `workflow-variable.png`
- `workflow-test-run.png`
- `workflow-publish.png`
- `chatflow-entry.png`
- `chatflow-shared-graph.png`
- `chatflow-variables.png`
- `chatflow-conversation-run.png`
- `chatflow-publish.png`
- `workflow-tabs.png`
