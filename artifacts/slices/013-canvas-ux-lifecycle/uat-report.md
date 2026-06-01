# Spec 013 Canvas UX Lifecycle Gate

Date: 2026-06-01

## Scope

- Workflow/Chatflow canvas topbar removes the duplicated `Open API` action; the lifecycle `开放` tab remains the Open API entry.
- The previous `快速连线` topbar action is replaced by a bottom-toolbar `自动布局` icon action.
- Workflow `画布概览` and Chatflow `对话设置` side panels can collapse and expand from the panel edge.
- Chatflow opening text appears as the first trial-run assistant message, and guide questions fill the runtime input before execution.
- Existing node drag, keyboard delete, publish/Open API/observe, variable insertion, LLM, knowledge, and condition paths remain green.

## Red Tests

- `rtk npm --prefix frontend run test:unit -- flowGraph.test.ts`
  - Initial failure: `autoLayoutWorkflowGraph is not a function`
  - Covered missing deterministic auto-layout behavior before implementation.

## Verification

- `rtk npm --prefix frontend run test:unit`
  - 18 files, 35 tests passed.
- `rtk npm --prefix frontend run build`
  - `vue-tsc` and Vite production build passed.
- `rtk uv run pytest tests/unit/workflow -q`
  - 15 tests passed.
- `HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-canvas-ux-lifecycle.mjs`
  - Passed Workflow/Chatflow canvas UX lifecycle UAT.
- `HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-canvas.mjs`
  - Passed canvas save/reopen.
- `HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-test-run.mjs`
  - Passed validation red path and connected run path.
- `HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-publish.mjs`
  - Passed publish gate, Open API, and observe paths.
- `HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-variable.mjs`
  - Passed variable insertion persistence.
- `HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-node-interactions.mjs`
  - Passed mouse drag and Enter-key deletion behavior.
- `HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-chatflow-llm-run.mjs`
  - Passed live Workflow and Chatflow LLM runs; outputs did not contain `LLM mock:`.
- `HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-knowledge-condition-run.mjs`
  - Passed Workflow and Chatflow knowledge + condition paths; outputs did not contain `Knowledge mock:`.

## Screenshot Evidence

Screenshots were generated locally under `artifacts/slices/013-canvas-ux-lifecycle/` and are intentionally ignored by Git:

- `workflow-ux.png`
- `chatflow-opening.png`
- `workflow-live-llm.png`
- `chatflow-live-llm.png`
- `workflow-kc-hit.png`
- `chatflow-kc-hit.png`
- `workflow-node-interactions.png`
