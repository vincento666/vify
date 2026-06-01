# Tasks 011: Workflow Visual Canvas

## 011.1 Workflow tab shell

- [x] RED: route/list UI test fails.
- [x] Implement Workflow/Chatflow tabs in workflow module shell.
- [x] Preserve existing workflow list behavior.
- [x] Gates pass.

## 011.2 Canvas graph editor

- [x] RED: canvas save/reopen test fails.
- [x] Add `@vue-flow/core`.
- [x] Implement Coze-like custom node cards, ports, hover/selected/run states, and edge labels.
- [x] Implement default START/END graph.
- [x] Implement add, drag, connect, delete, save, reopen.
- [x] Gates pass.

## 011.3 Node config panel

- [x] RED: node config persistence test fails.
- [x] Implement node metadata registry.
- [x] Implement unified config panel for START, LLM, CONDITION, KNOWLEDGE, API_CALL, END.
- [x] Gates pass.

## 011.4 Output parameter editor

- [ ] RED: output parameter editor test fails.
- [ ] Implement Coze-like output format selector with `文本`, `Markdown`, and `JSON`.
- [ ] Implement output variable rows: variable name, variable type, expand, delete.
- [ ] Implement add output variable action.
- [ ] Validate unique/legal output names.
- [ ] Feed output names into downstream picker.
- [ ] Gates pass.

## 011.5 Variable reference picker

- [x] RED: variable selector test fails.
- [x] Implement graph-aware variable catalog builder limited to connected upstream outputs plus START/global variables.
- [ ] Implement Coze-like cascading variable selector with first-level user/application/system/upstream-node groups.
- [ ] Implement second-level variable list with names and type badges.
- [ ] Preserve `{{node.variable}}` template syntax in saved config from the picker across all variable-capable fields.
- [ ] Gates pass.

## 011.6 Input parameter editor

- [ ] RED: input parameter editor test fails.
- [ ] Implement shared variable name/type/value-mode/value row editor.
- [ ] Literal mode uses type-aware inputs.
- [ ] Reference mode uses `VariableReferencePicker`.
- [ ] Render Coze-like row controls: type prefix/dropdown, variable chip, picker/action icon, and delete action.
- [ ] Apply to START, LLM, CONDITION, KNOWLEDGE, API_CALL, END current node fields.
- [ ] Gates pass.

## 011.7 Coze panel polish

- [ ] RED: panel section/visual DOM test fails.
- [ ] Refactor panel to shared Header/Input/Settings/Output/Advanced sections.
- [ ] Implement LLM header with description, run icon, more menu, close icon.
- [ ] Keep LLM mode as current `单次` behavior; do not implement `批处理`.
- [ ] Add LLM model section with dropdown and settings gear shell.
- [ ] Add model selection popover with title, search icon, internal provider/model groups, model rows, descriptions, health/enabled status, and capability tags when known.
- [ ] Add LLM unified resource/skills section with add button and empty state shell.
- [ ] Add unified resource picker groups for Knowledge Bases, MCP tools/servers, and subworkflows.
- [ ] Mark runtime support by resource type: Knowledge callable now; MCP tools and subworkflows disabled or later-stage until runtime exists.
- [ ] Do not implement visual-understanding input in current MVP.
- [ ] Add LLM system prompt and user prompt editors with helper icon row and manual `{{variable}}` placeholder guidance.
- [ ] Add LLM output extras: output format selector and helper/import shell.
- [ ] Do not implement `支持续写` or `异常处理` in current MVP.
- [ ] Apply shared basic controls to every current node.
- [ ] Match live Coze bottom toolbar order with Hify override: panel/view control, zoom dropdown, utility icon buttons, visible operation-mode icon button, `+ 添加节点`, `角色`, wrench/debug, green `试运行`.
- [ ] Wire visible operation-mode icon button so clicking switches icon state, tooltip/aria label (`触控板模式` / `鼠标模式`), and canvas pan/zoom control behavior; persist only as local UI preference.
- [ ] Implement bottom-toolbar add-node popover with search and Coze-aligned grouped entries; enable only runtime-backed nodes.
- [ ] Add bottom toolbar wrench/debug icon button.
- [ ] Implement wrench-toggleable bottom debug/tools panel with `错误列表` empty/error states, `调试` run tree/detail states, log/diagnostic placeholders, close action, and non-overlap with right config panel.
- [ ] Keep advanced fields read-only/placeholder unless backed by runtime.
- [ ] Gates pass.

## 011.8 Validate and test run

- [x] RED: test run UI fails.
- [x] Implement graph validator.
- [x] Add test input panel and run result mapping.
- [ ] Align full-flow run evidence with live Coze bottom `调试` dock: left run tree, right detail/flamegraph or output detail, close action, and sticky primary run/debug action where applicable.
- [ ] Re-run 011.8 gates after live Coze bottom-debug alignment passes.

## 011.9 Publish/open/observe shell

- [x] RED: publish guard fails.
- [x] Implement publish guard and publish modal shell.
- [x] Implement open API and observe tab placeholders with business fields.
- [x] Gates pass.

## 011.10 LLM unified resource context

- [ ] RED: LLM resource context runtime/guard test fails.
- [ ] Implement or explicitly guard Knowledge Resource context in LLM runs.
- [ ] If implemented, retrieve selected Knowledge Bases and append snippets to model context before LLM call.
- [ ] Verify MCP Tool resources are not runnable from LLM node until tool-call runtime is wired.
- [ ] Verify Subworkflow resources are not runnable from LLM node until nested-run runtime is wired.
- [ ] Gates pass.

## 011.11 Single-node test action

- [ ] RED: selected-node test action fails.
- [ ] Implement node input fixture builder from input rows, connected upstream output definitions, START/global variables, and literal defaults.
- [ ] Add Coze-like node-test drawer launched from the panel header run icon.
- [ ] Implement drawer idle state: `试运行`, `查看日志`, close icon, `试运行输入`, `JSON模式`, `AI 补全`, typed input rows, and sticky green `运行`.
- [ ] Implement drawer running state: stop icon/header state, centered spinner, `试运行进行中...`, and sticky grey `停止`.
- [ ] Implement drawer success state: green elapsed/tokens pill, `查看日志`, `运行结果`, `输入`, `推理内容`, `技能调用`, `输出`, copy affordances, and rerun button.
- [ ] Implement drawer failure state with red status, error details, and log access.
- [ ] Allow editing missing required fixture values before running.
- [ ] Run only the selected node and do not continue downstream.
- [ ] Render node-only status, rendered input, model-visible response/debug text, skill/resource calls, output variables, raw output, and error details.
- [ ] Keep single-node test evidence separate from full-flow run/publish gates.
- [ ] Gates pass.
