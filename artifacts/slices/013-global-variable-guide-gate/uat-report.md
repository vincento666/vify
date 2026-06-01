# Spec 013 Global Variable And Guide Persistence Gate

Date: 2026-06-01

## Scope

- Chatflow `引导问题` renders as initial `猜你想问` choices and remains visible after the user clicks a choice.
- START node dimensions stay fixed regardless of output variable count.
- START node displays only a bounded set of variables plus one trailing `...`; hover tooltip shows the full variable list.
- Chatflow global variables are injected into runtime input and can be referenced by nodes with `{{global.brand}}` and `{{global.locale}}`.

## Verification

- `rtk npm --prefix frontend run test:unit -- chatflowRunProfile.test.ts`
  - Passed global variable injection unit coverage.
- `rtk uv run pytest tests/integration/workflow/test_chatflow_conversation_run.py -q`
  - Passed backend template rendering with `global.brand` and `global.locale`.
- `rtk zsh -lc 'HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-canvas-ux-lifecycle.mjs'`
  - Passed START fixed-size variable ellipsis, hover tooltip, multi-condition UAT, and guide-choice persistence after click.
- `rtk zsh -lc 'HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/chatflow-variables.mjs'`
  - Passed `{{global.brand}}` insertion from the left variable panel and persistence after save/reload.
- `rtk zsh -lc 'HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/chatflow-conversation-run.mjs'`
  - Passed runtime rendering of `{{global.brand}}` and `{{global.locale}}`.
- `rtk npm --prefix frontend run test:unit`
  - 18 files, 35 tests passed.
- `rtk npm --prefix frontend run build`
  - `vue-tsc` and Vite production build passed.
- `rtk uv run pytest tests/unit/workflow tests/integration/workflow/test_chatflow_conversation_run.py tests/integration/workflow/test_workflow_condition_run.py -q`
  - 17 tests passed.
- `rtk zsh -lc 'HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-chatflow-llm-run.mjs'`
  - Passed live Workflow and Chatflow LLM paths; no `LLM mock:` output.
- `rtk zsh -lc 'HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-knowledge-condition-run.mjs'`
  - Passed Workflow and Chatflow knowledge + condition paths; no `Knowledge mock:` output.

## Screenshot Evidence

Screenshots were generated locally under `artifacts/slices/013-global-variable-guide-gate/` and are ignored by Git:

- `workflow-start-ellipsis.png`
- `chatflow-guide-persist.png`
- `chatflow-global-variable.png`
- `chatflow-global-run.png`
- `workflow-live-llm.png`
- `chatflow-live-llm.png`
- `workflow-kc-hit.png`
- `chatflow-kc-hit.png`
