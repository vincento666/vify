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
- [ ] Implement variable reference insertion through the shared Coze-like selector for Chatflow node fields.
- [ ] Gates pass.

## 012.4 Chatflow input/output controls

- [ ] RED: Chatflow parameter editor test fails.
- [ ] Reuse Workflow input/output parameter editors.
- [ ] Add system/scoped variables to reference mode.
- [ ] Verify `sys.query`, `sys.conversation_id`, `sys.user_id`, `sys.channel` can be selected.
- [ ] Add Chatflow-only LLM `会话历史` toggle in the input section.
- [ ] Verify Start variables such as `USER_INPUT` and `CONVERSATION_NAME` render as selectable input chips.
- [ ] Gates pass.

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

- [ ] RED: Chatflow debug/run visual/state test fails.
- [ ] Implement conversation-shaped `试运行` input surface with `查看日志` and close action.
- [ ] Add `对话流入参配置` or equivalent message-profile body layout with test dataset selector shell.
- [ ] Add linked agent/app required selector shell.
- [ ] Add test input rows with type badges, `JSON模式` toggle, and `AI 补全` action shell.
- [ ] Add save-current-input checkbox and sticky `保存并开始对话调试` action.
- [ ] Align result evidence with live Coze bottom `调试` dock: run tree, detail/flamegraph or output detail, close action, and validation/error states.
- [ ] Ensure shared wrench/debug bottom panel and `错误列表` states remain visible/closable while any input drawer is open.
- [ ] Gates pass.

## 012.8 Chatflow resource context

- [ ] RED: Chatflow LLM resource context runtime/guard test fails.
- [ ] Reuse Workflow LLM Knowledge Resource context with Chatflow system variables.
- [ ] If `会话历史` is enabled, include bounded conversation history with retrieved Knowledge context.
- [ ] Verify MCP Tool resources are not runnable from Chatflow LLM node until tool-call runtime is wired.
- [ ] Verify Subworkflow resources are not runnable from Chatflow LLM node until nested-run and interrupt/resume rules exist.
- [ ] Gates pass.

## 012.9 Chatflow single-node test profile

- [ ] RED: Chatflow selected-node test fails.
- [ ] Reuse Workflow node-test UI and selected-node execution path.
- [ ] Build node fixtures through the Chatflow runtime profile.
- [ ] Include system/scoped variables such as `sys.query`, `sys.conversation_id`, `sys.user_id`, and `sys.channel`.
- [ ] If LLM `会话历史` is enabled, expose bounded editable/mock history in the node-test fixture.
- [ ] Preserve Coze-like drawer states from 011.11: idle input, running/stop, success result, failure/error.
- [ ] Verify node-only output/error rendering does not continue downstream.
- [ ] Gates pass.
