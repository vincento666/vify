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

- [x] RED: output parameter editor test fails.
- [x] Implement Coze-like output format selector with `文本`, `Markdown`, and `JSON`.
- [x] Implement output variable rows: variable name, variable type, expand, delete.
- [x] Implement add output variable action.
- [x] Validate unique/legal output names.
- [x] Feed output names into downstream picker.
- [x] Gates pass.

## 011.5 Variable reference picker

- [x] RED: variable selector test fails.
- [x] Implement graph-aware variable catalog builder limited to connected upstream outputs plus START/global variables.
- [x] Implement Coze-like cascading variable selector with first-level user/application/system/upstream-node groups.
- [x] Implement second-level variable list with names and type badges.
- [x] Preserve `{{node.variable}}` template syntax in saved config from the picker across all variable-capable fields.
- [x] Gates pass.

## 011.6 Input parameter editor

- [x] RED: input parameter editor test fails.
- [x] Implement shared variable name/type/value-mode/value row editor.
- [x] Literal mode uses type-aware inputs.
- [x] Reference mode uses `VariableReferencePicker`.
- [x] Render Coze-like row controls: type prefix/dropdown, variable chip, picker/action icon, and delete action.
- [x] Apply to START, LLM, CONDITION, KNOWLEDGE, API_CALL, END current node fields.
- [x] Gates pass.

## 011.7 Coze panel polish

- [x] RED: panel section/visual DOM test fails.
- [x] Refactor panel to shared Header/Input/Settings/Output/Advanced sections.
- [x] Implement LLM header with description, run icon, more menu, close icon.
- [x] Keep LLM mode as current `单次` behavior; do not implement `批处理`.
- [x] Add LLM model section with dropdown and settings gear shell.
- [x] Add model selection popover with title, search icon, internal provider/model groups, model rows, descriptions, health/enabled status, and capability tags when known.
- [x] Add LLM unified resource/skills section with add button and empty state shell.
- [x] Add unified resource picker groups for Knowledge Bases, MCP tools/servers, and subworkflows.
- [x] Mark runtime support by resource type: Knowledge callable now; MCP tools and subworkflows disabled or later-stage until runtime exists.
- [x] Do not implement visual-understanding input in current MVP.
- [x] Add LLM system prompt and user prompt editors with helper icon row and manual `{{variable}}` placeholder guidance.
- [x] Add LLM output extras: output format selector and helper/import shell.
- [x] Do not implement `支持续写` or `异常处理` in current MVP.
- [x] Apply shared basic controls to every current node.
- [x] Match live Coze bottom toolbar order with Hify override: panel/view control, zoom dropdown, utility icon buttons, visible operation-mode icon button, `+ 添加节点`, `角色`, wrench/debug, green `试运行`.
- [x] Wire visible operation-mode icon button so clicking switches icon state, tooltip/aria label (`触控板模式` / `鼠标模式`), and canvas pan/zoom control behavior; persist only as local UI preference.
- [x] Implement bottom-toolbar add-node popover with search and Coze-aligned grouped entries; enable only runtime-backed nodes.
- [x] Add bottom toolbar wrench/debug icon button.
- [x] Implement wrench-toggleable bottom debug/tools panel with `错误列表` empty/error states, `调试` run tree/detail states, log/diagnostic placeholders, close action, and non-overlap with right config panel.
- [x] Keep advanced fields read-only/placeholder unless backed by runtime.
- [x] Gates pass.

## 011.8 Validate and test run

- [x] RED: test run UI fails.
- [x] Implement graph validator.
- [x] Add test input panel and run result mapping.
- [x] Align full-flow run evidence with live Coze bottom `调试` dock: left run tree, right detail/flamegraph or output detail, close action, and sticky primary run/debug action where applicable.
- [x] Re-run 011.8 gates after live Coze bottom-debug alignment passes.

## 011.9 Publish/open/observe shell

- [x] RED: publish guard fails.
- [x] Implement publish guard and publish modal shell.
- [x] Implement open API and observe tab placeholders with business fields.
- [x] Gates pass.

## 011.10 LLM unified resource context

- [x] RED: LLM resource context runtime/guard test fails.
- [x] Implement or explicitly guard Knowledge Resource context in LLM runs.
- [x] If implemented, retrieve selected Knowledge Bases and append snippets to model context before LLM call.
- [x] Verify MCP Tool resources are not runnable from LLM node until tool-call runtime is wired.
- [x] Verify Subworkflow resources are not runnable from LLM node until nested-run runtime is wired.
- [x] Gates pass.

## 011.11 Single-node test action

- [x] RED: selected-node test action fails.
- [x] Implement node input fixture builder from input rows, connected upstream output definitions, START/global variables, and literal defaults.
- [x] Add Coze-like node-test drawer launched from the panel header run icon.
- [x] Implement drawer idle state: `试运行`, `查看日志`, close icon, `试运行输入`, `JSON模式`, `AI 补全`, typed input rows, and sticky green `运行`.
- [x] Implement drawer running state: stop icon/header state, centered spinner, `试运行进行中...`, and sticky grey `停止`.
- [x] Implement drawer success state: green elapsed/tokens pill, `查看日志`, `运行结果`, `输入`, `推理内容`, `技能调用`, `输出`, copy affordances, and rerun button.
- [x] Implement drawer failure state with red status, error details, and log access.
- [x] Allow editing missing required fixture values before running.
- [x] Run only the selected node and do not continue downstream.
- [x] Render node-only status, rendered input, model-visible response/debug text, skill/resource calls, output variables, raw output, and error details.
- [x] Keep single-node test evidence separate from full-flow run/publish gates.
- [x] Gates pass.

## 011.12 Six-node runtime matrix and parity audit

- [x] RED: Knowledge node `topK` runtime test fails because executor fixed `top_k=1`.
- [x] RED: START selected-node fixture test fails because declared output variables are missing from node-test inputs.
- [x] RED: real provider client retry/proxy tests fail before retry and `trust_env=False`.
- [x] Implement Knowledge node `topK/top_k` runtime support.
- [x] Implement START selected-node fixture rows from declared `outputVariables`.
- [x] Expose selected-node run action for every current runtime-backed node type, not only LLM.
- [x] Add backend six-node engine matrix and workflow API integration matrix.
- [x] Add workflow/chatflow browser e2e six-node full chain and workflow selected-node matrix.
- [x] Add transient LLM transport retry and disable inherited system proxy for real provider calls.
- [x] Capture browser UAT screenshots for local workflow/chatflow six-node canvases.
- [x] Document matrix, current Coze parity, and remaining gaps.
- [x] Gates pass.

## 011.13 Runtime parity hardening

- [x] RED: API_CALL executor test fails because node still returns mock output.
- [x] RED: CONDITION branch test fails because Coze-style multi-condition branches are ignored.
- [x] RED: LLM parameter integration test fails because node-level model params do not reach the provider payload.
- [x] RED: selected-node fixture test fails because `conditionBranches`, API `headers`, and API `body` variables are not extracted.
- [x] Implement real HTTP execution for API_CALL with templated endpoint, headers, body, timeout, JSON/text response handling, and transport/HTTP error propagation.
- [x] Implement Coze-style CONDITION multi-condition branches with AND/OR logic, default branch, and comparison operators.
- [x] Wire LLM node model parameters into the live provider payload: system prompt, model, temperature, max tokens, top_p, frequency/presence penalties, response format, stop words, and seed.
- [x] Restrict variable catalog to graph-aware upstream outputs plus in-canvas global user/session/system variables.
- [x] Verify Knowledge node uses real vector retrieval and LLM Knowledge resources inject retrieved context into the model prompt.
- [x] Run workflow six-node browser e2e with real Knowledge, real LLM, real API_CALL, selected-node matrix, and screenshots.
- [x] Run Codex in-app browser UAT against live workflow canvas with visible bottom toolbar operation-mode button, LLM/API/CONDITION config panels, and real run output.
- [x] Evidence: `artifacts/slices/011-workflow-visual-canvas/011.13-runtime-parity/`.
- [x] Gates pass.

## 011.14 Canvas config-panel zoom stability regression

- [x] RED: `workflow-config-panel-zoom-stability.mjs` fails while opening LLM config shrinks `.coze-flow` from 1149.984375 to 631.578125.
- [x] Keep Workflow canvas viewport, node bbox, transform, scale, and zoom label stable while config panel opens/closes.
- [x] Focused E2E covers Workflow and Chatflow canvases.
- [x] Evidence: `artifacts/slices/083-workflow-chatflow-canvas-node-parity/`.
- [x] Gates pass.
