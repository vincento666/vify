# Spec 013 Chatflow Left Panel And Multi-Condition Gate

Date: 2026-06-01

## Answers Locked By This Slice

- Previous condition UAT covered one explicit condition plus a default branch. This slice adds multi-condition coverage: two explicit branches (`refund`, `invoice`) plus the default branch.
- START nodes keep a fixed height when output variables grow. Long variable chips are clipped with ellipsis, and hover shows the full variable list.
- Chatflow opening text and guide questions are separate runtime concepts:
  - Opening text renders as the first assistant message.
  - Guide questions render as initial user choices under `猜你想问`.
  - Clicking a guide question fills the user input and the actual trial run uses that value.
- Chatflow left panel effective functions verified in this slice:
  - Opening text persists into the runtime conversation.
  - Guide questions render as `猜你想问`, are clickable, and affect run input/output.
  - Variable panel inserts `{{sys.query}}`, persists it into the END node output template, and trial run renders `sys` variables.
- The future switch for “每轮使用 LLM 总结上下文生成 3 个推荐引导问题” is not added in this slice because it requires a separate backend runtime contract and real LLM call gate. No inactive UI control was added.

## Verification

- `rtk zsh -lc 'HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-canvas-ux-lifecycle.mjs'`
  - Passed multi-condition Workflow UAT, START variable clipping/hover tooltip, and Chatflow opening + `猜你想问` runtime behavior.
- `rtk uv run pytest tests/integration/workflow/test_workflow_condition_run.py -q`
  - Passed backend multi-condition routing with two explicit branches plus default branch.
- `rtk zsh -lc 'HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/chatflow-variables.mjs'`
  - Passed Chatflow variable panel insert and persistence.
- `rtk zsh -lc 'HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/chatflow-conversation-run.mjs'`
  - Passed Chatflow trial run using left-panel variable output behavior.
- `rtk npm --prefix frontend run test:unit`
  - 18 files, 35 tests passed.
- `rtk npm --prefix frontend run build`
  - `vue-tsc` and Vite production build passed.
- `rtk uv run pytest tests/unit/workflow tests/integration/workflow/test_workflow_condition_run.py -q`
  - 16 tests passed.
- `rtk zsh -lc 'HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-chatflow-llm-run.mjs'`
  - Passed live Workflow and Chatflow LLM paths; no `LLM mock:` output.
- `rtk zsh -lc 'HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-knowledge-condition-run.mjs'`
  - Passed Workflow and Chatflow knowledge + condition paths; no `Knowledge mock:` output.

## Screenshot Evidence

Screenshots were generated locally under `artifacts/slices/013-chatflow-left-panel-gate/` and are ignored by Git:

- `workflow-start-multicondition.png`
- `chatflow-suggested-questions.png`
- `chatflow-variables.png`
- `chatflow-conversation-run.png`
- `workflow-live-llm.png`
- `chatflow-live-llm.png`
- `workflow-kc-hit.png`
- `chatflow-kc-hit.png`
