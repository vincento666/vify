# Spec 013 Slice: Start Node, Guide Questions, Run Inputs

Date: 2026-06-01

## Scope

- START node keeps a fixed card size and shows every variable that fits before a trailing `...`.
- Hidden START variables remain available through the full variable tooltip/title.
- START node right-side source endpoint remains visible.
- Chatflow `猜你想问` choices are vertically stacked and remain separate from the opening message.
- Workflow/chatflow trial inputs name the real runtime variables they populate.

## Browser UAT

- Workflow canvas: `http://127.0.0.1:15182/workflows/439/canvas`
  - visible START badges: `str.USER_INPUT`, `str.sys.query`
  - hidden marker: `...`
  - full title: `str.USER_INPUT · str.sys.query · str.sys.channel · str.sys.user_id · str.sys.conversation_id · str.external.ticket.context_payload`
  - source endpoint: visible
  - trial input label: `用户消息（userMessage / USER_INPUT）`
- Chatflow canvas: `http://127.0.0.1:15182/chatflows/441/canvas`
  - guide layout: `flex-direction: column`
  - opening message: `开场白_UX_1780311508665`
  - guide question: `引导问题_UX_1780311508665`
  - trial input labels: `用户消息（sys.query）`, `会话 ID（sys.conversation_id）`, `用户 ID（sys.user_id）`, `渠道（sys.channel）`
  - source endpoint: visible

Screenshots:

- `screenshots/in-app-workflow-start-ellipsis.png`
- `screenshots/in-app-workflow-run-labels.png`
- `screenshots/in-app-chatflow-guides-labels.png`
- `workflow-start-port-ellipsis.png`
- `chatflow-vertical-guides-input-labels.png`

## Gate Evidence

- RED/e2e regression: `workflow-canvas-ux-lifecycle.mjs` now fails if START collapses too early, loses the source endpoint, chatflow guide questions are not vertical, or trial inputs omit runtime variable names.
- Unit: `npm --prefix frontend run test:unit`
- Frontend build: `npm --prefix frontend run build`
- Backend unit/integration: `uv run pytest tests/unit/workflow tests/integration/workflow/test_chatflow_conversation_run.py tests/integration/workflow/test_workflow_condition_run.py -q`
- E2E/UAT:
  - `node frontend/e2e/workflow-canvas-ux-lifecycle.mjs`
  - `node frontend/e2e/chatflow-conversation-run.mjs`
  - `node frontend/e2e/chatflow-variables.mjs`
  - `node frontend/e2e/workflow-node-interactions.mjs`
  - `node frontend/e2e/workflow-chatflow-llm-run.mjs`
  - `node frontend/e2e/workflow-knowledge-condition-run.mjs`

## Variable Effectiveness

- Workflow `USER_INPUT` is validated by the multi-condition workflow run path: `refund`, `invoice`, and fallback inputs route to distinct outputs.
- Chatflow `sys.query`, `sys.conversation_id`, `sys.user_id`, and `sys.channel` are validated by `chatflowRunProfile` unit coverage, chatflow conversation e2e, and chatflow variable e2e.
- Global variable references are validated by `chatflow-variables.mjs`; real LLM and knowledge/condition paths are covered by the live e2e scripts listed above.
