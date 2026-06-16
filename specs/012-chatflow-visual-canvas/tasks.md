# Tasks 012: Chatflow Visual Canvas

## 012.1 Chatflow resource entry

- [x] RED: Chatflow tab/list route test fails.
- [x] Implement Chatflow tab, list, create button, route shell.
- [x] Gates pass.

## 012.2 Shared graph model

- [x] RED: Chatflow create/detail separation test fails.
- [x] Add flow type persistence and API separation.
- [x] Default Chatflow START/END graph uses chat system variables.
- [x] Gates pass.

## 012.3 Variable panel and picker

- [x] RED: variable catalog UI test fails.
- [x] Implement System/Global/Conversation/User/Channel/External Input variable panels.
- [x] Implement variable reference insertion through the shared Coze-like selector for Chatflow node fields.
- [x] Gates pass.

## 012.4 Chatflow input/output controls

- [x] RED: Chatflow parameter editor test fails.
- [x] Reuse Workflow input/output parameter editors.
- [x] Add system/scoped variables to reference mode.
- [x] Verify `sys.query`, `sys.conversation_id`, `sys.user_id`, `sys.channel` can be selected.
- [x] Add Chatflow-only LLM `会话历史` toggle in the input section.
- [x] Verify Start variables such as `USER_INPUT` and `CONVERSATION_NAME` render as selectable input chips.
- [x] Gates pass.

## 012.5 Conversation test run

- [x] RED: Chatflow test run fails.
- [x] Implement system variable mapping and message-shaped test panel.
- [x] Map run output to conversation-style result.
- [x] Gates pass.

## 012.6 Chatflow publish/open shell

- [x] RED: publish/open guard fails.
- [x] Implement channel/API publish shell fields.
- [x] Keep real channel adapters out of scope.
- [x] Gates pass.

## 012.7 Coze debug/run polish

- [x] RED: Chatflow debug/run visual/state test fails.
- [x] Implement conversation-shaped `试运行` input surface with `查看日志` and close action.
- [x] Add `对话流入参配置` or equivalent message-profile body layout with test dataset selector shell.
- [x] Add linked agent/app required selector shell.
- [x] Add test input rows with type badges, `JSON模式` toggle, and `AI 补全` action shell.
- [x] Add save-current-input checkbox and sticky `保存并开始对话调试` action.
- [x] Align result evidence with live Coze bottom `调试` dock: run tree, detail/flamegraph or output detail, close action, and validation/error states.
- [x] Ensure shared wrench/debug bottom panel and `错误列表` states remain visible/closable while any input drawer is open.
- [x] Gates pass.

## 012.8 Chatflow resource context

- [x] RED: Chatflow LLM resource context runtime/guard test fails.
- [x] Reuse Workflow LLM Knowledge Resource context with Chatflow system variables.
- [x] If `会话历史` is enabled, include bounded conversation history with retrieved Knowledge context.
- [x] Verify MCP Tool resources are not runnable from Chatflow LLM node until tool-call runtime is wired.
- [x] Verify Subworkflow resources are not runnable from Chatflow LLM node until nested-run and interrupt/resume rules exist.
- [x] Gates pass.

## 012.9 Chatflow single-node test profile

- [x] RED: Chatflow selected-node test fails.
- [x] Reuse Workflow node-test UI and selected-node execution path.
- [x] Build node fixtures through the Chatflow runtime profile.
- [x] Include system/scoped variables such as `sys.query`, `sys.conversation_id`, `sys.user_id`, and `sys.channel`.
- [x] If LLM `会话历史` is enabled, expose bounded editable/mock history in the node-test fixture.
- [x] Preserve Coze-like drawer states from 011.11: idle input, running/stop, success result, failure/error.
- [x] Verify node-only output/error rendering does not continue downstream.
- [x] Gates pass.

## 012.10 Runtime parity hardening

- [x] Reuse 011.13 runtime executor hardening for Chatflow canvases.
- [x] Verify Chatflow full-chain run uses real Knowledge retrieval, real LLM provider output, and real API_CALL HTTP execution.
- [x] Verify Chatflow run input labels expose `sys.query` clearly instead of anonymous fields.
- [x] Verify Chatflow LLM resource context remains active with bounded conversation profile variables.
- [x] Run shared six-node browser e2e for workflow and chatflow.
- [x] Run Codex in-app browser UAT against live chatflow canvas and confirm real assistant output is not mock content.
- [x] Evidence: `artifacts/slices/011-workflow-visual-canvas/011.13-runtime-parity/`.
- [x] Gates pass.

## 012.11 Canvas config-panel zoom and edge insert regression

- [x] RED: shared config-panel zoom E2E fails for side-panel induced canvas resize.
- [x] RED: `chatflow-edge-interactions.mjs` fails while edge insert palette overlaps the plus button and sits below its z-index.
- [x] Keep Chatflow viewport stable on config open/close.
- [x] Open edge insert palette away from the plus button and above it.
- [x] Evidence: `artifacts/slices/083-workflow-chatflow-canvas-node-parity/`.
- [x] Gates pass.
