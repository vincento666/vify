# Spec 011: Workflow Visual Canvas

## Goal

Replace the incomplete JSON-only workflow form with a visual draggable canvas for the workflow node types already present in the replica runtime: START, LLM, CONDITION, KNOWLEDGE, API_CALL, END. The user can create, edit, validate, test run, and observe a workflow without touching raw graph JSON.

## Product Boundary

- This spec targets **Workflow** only, not Chatflow conversation behavior.
- It uses workflow resources with `flow_type=WORKFLOW`, the existing `/api/v1/workflows` graph CRUD shape, and `/api/v1/workflows/{id}/runs` sync run API.
- It does not add Dify-style multi-task switching, task stack, cross-flow interrupt/resume, or real tool calling.
- Coze visual reference is stored under `artifacts/research/coze-workflow/`. The current authenticated live audit is `artifacts/research/coze-workflow/spec-011-015-live-audit-20260601.md`, with screenshots under `artifacts/research/coze-workflow/screenshots/`.

## User Value

Workflow authors can assemble deterministic business logic visually: add nodes, connect them, configure fields, run a test, inspect node status, and later publish once validation passes.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 011.1 Workflow tab shell | Workflow module shows Workflow and Chatflow tabs; Workflow tab keeps current list and opens canvas builder | RED: route/list UI test fails; Unit: route helpers; Integration: existing workflow list unchanged; E2E: tab navigation; UAT: Workflow tab visible |
| 011.2 Canvas graph editor | User creates START/END default graph, drags nodes, adds current node types, connects/deletes edges, saves graph | RED: canvas save test fails; Unit: graph adapter; Integration: CRUD persists positions/config; E2E: create graph; UAT: drag/save/reopen |
| 011.3 Node config panel | Selecting a node opens Coze-style right panel with unified sections for input params, required config, output params, advanced config | RED: node config test fails; Unit: node schema metadata; Integration: saved config round-trips; E2E: edit LLM/Condition/API/Knowledge/End; UAT: config readable |
| 011.4 Output parameter editor | User edits node output rows with output format, variable name, variable type, expand, delete, and add actions | RED: output editor test fails; Unit: output parameter model; Integration: output config round-trips; E2E: rename output and reference it downstream; UAT: Coze-like output editor usable |
| 011.5 Variable reference picker | User can choose connected upstream START/node outputs and global variables in input fields without typing raw template paths | RED: variable picker test fails; Unit: variable catalog builder; Integration: saved template round-trips; E2E: select upstream output; UAT: picker inserts reference |
| 011.6 Input parameter editor | User edits node input rows with variable name, type, value mode, and value; reference mode uses the picker | RED: input editor test fails; Unit: input parameter model; Integration: config round-trips; E2E: edit current node inputs; UAT: row editor usable |
| 011.7 Coze panel polish | Node config panel matches Coze-style structure and applies shared basic input/output controls across current nodes | RED: panel visual/DOM test fails; Unit: schema section builder; E2E: all current nodes show shared sections; UAT: panel layout accepted |
| 011.8 Validate and test run | User runs validation and test input from Start schema; run result marks nodes succeeded/failed and shows output/error details | RED: run UI test fails; Unit: validator; Integration: `/runs` response; E2E: START->LLM->END returns output; UAT: run output visible |
| 011.9 Publish/open/observe shell | User sees publish, open API, and observe tabs/shells; publish blocked until validation and test run pass | RED: publish guard test fails; Unit: publish guard; Integration: status update remains compatible; E2E: publish blocked then enabled; UAT: shell fields visible |
| 011.10 LLM unified resource context | LLM Skills area uses Hify unified resources and clearly separates current Knowledge context from deferred MCP/subworkflow execution | RED: resource context test fails; Unit: resource config; Integration: LLM context or guard; E2E: resource state visible; UAT: support status clear |
| 011.11 Single-node test action | User can run only the selected node from the node panel header using editable upstream fixture inputs and inspect node-only output/error | RED: node test action fails; Unit: node fixture builder; Integration: selected node run/guard; E2E: run selected LLM node; UAT: node-only output visible |

## Node UX Requirements

- Page shell follows the current Coze canvas chrome: back navigation, flow icon/name, info/edit icons, autosave status, right-side action icons, primary `发布` button, and more menu. The 2026-06-01 reference has no top product banner, so Hify must not reserve banner height in the canvas viewport.
- Canvas surface uses a light dotted grid and keeps node cards floating directly on the canvas, not inside page cards.
- START and END exist by default and cannot be deleted.
- Node card visually follows Coze workflow canvas conventions: compact rounded card, icon/title header, subtle type/status treatment, input/output summaries, hover affordances, selection outline, run status badge, and field-level error indicator.
- START variable chips keep a fixed card width. Chips render left to right until the next chip would overflow, then collapse the overflow into one trailing `...` chip. The full variable list must remain discoverable through a single Coze-like hover/click popover or equivalent detail surface, without duplicate native and custom tooltips.
- Ports visually follow Coze endpoint behavior: left-side input port, right-side output port, branch-specific output ports for CONDITION, clear hover/drag/connect states, and no exposed raw port IDs.
- Edge labels show branch names for CONDITION; internal IDs are hidden.
- Node card dynamic behavior includes hover actions, selected state, invalid state, running state, success state, failure state, skipped state, and disabled delete affordance for START/END.
- Node config panel uses one information architecture across node types:
  - Header: icon, editable name, run icon, menu, close.
  - Input parameters.
  - Required config.
  - Output parameters.
  - Advanced config, collapsed by default.
- Node config panel visually follows Coze layout: fixed right-side panel, compact section headers, row-based parameter editor, variable selector instead of raw path typing, inline validation, node test action in header, and technical JSON/schema only in advanced view.
- Variable references use selector UI when possible and preserve current `{{node.variable}}` template compatibility.
- Bottom canvas toolbar follows the live Coze interaction shape plus Hify's product override: compact panel/view control, zoom dropdown, utility icon buttons, visible operation-mode icon button, prominent `+ 添加节点`, `角色`, wrench/debug action, and green full-flow `试运行`.
- Operation-mode toggle is a required visible icon button in Hify even though the 2026-06-01 Coze reference did not expose one. The toolbar must not render the mode name as visible text. The icon button uses tooltip/aria label to expose `触控板模式` or `鼠标模式`; clicking it switches modes, and the selected mode remains a local UI preference outside persisted FlowGraph data.
- Wrench/debug and full-flow trial actions open or focus a bottom docked debug/detail panel without replacing the right-side node config panel.
- Validation and run diagnostics can appear in a bottom docked panel with title, close action, empty state, row list, run tree, and detail area once errors or run evidence exist.

## Canvas Toolbar And Bottom Debug Panel UX

The shared canvas chrome includes a Coze-like centered bottom toolbar.

- Required actions: panel/view control, zoom selector, fit/view utility icons where supported, visible operation-mode icon button, add-node action, role/action shell where supported, wrench/debug action, and full-flow `试运行`.
- Operation mode:
  - `鼠标模式`: left mouse drag pans the canvas and wheel zooms.
  - `触控板模式`: two-finger pan moves the canvas and pinch/trackpad gesture zooms where the browser/device reports those gestures.
  - Clicking the visible icon button switches to the other mode and updates the icon state and tooltip/aria label immediately.
  - The selected mode is local UI preference, not part of the FlowGraph persisted business data.
- Wrench/debug action:
  - Toggles or focuses a bottom docked debug/tools panel.
  - The panel can show tabs or sections such as `错误列表`, `运行日志`, `调试`, run tree, flamegraph/detail, and future diagnostics.
  - MVP must at least support the existing error-list empty/error states; run-enabled slices must show run tree/detail evidence similar to the Coze `调试` panel.
  - The panel has a title, close action, empty state or detail state, and scrollable content area.
  - Opening the panel must not close the selected node config panel or the Chatflow run drawer.

## Add-Node Palette UX

The live Coze add-node menu opens from the centered bottom toolbar as a floating popover with a search field and grouped two-column entries.

- Current live reference entries: `大模型`, `插件`, `工作流`, `代码`, `选择器`, `意图识别`, `循环`, `批处理`, `变量聚合`, `异步任务`, `输入`, `输出`, `SQL自定义`, `新增数据`, `更新数据`, `查询数据`, `删除数据`, `知识库写入`, `知识库检索`.
- Hify 011 only enables runtime-backed current nodes: START/输入, LLM/大模型, CONDITION/选择器, KNOWLEDGE/知识库检索, API_CALL/API or HTTP call, END/输出.
- Unsupported or later-stage entries must be hidden, disabled, or tagged as not available. They must not look runnable before their runtime contract and tests exist.
- The add-node menu belongs in the bottom toolbar flow; the Workflow left panel must not duplicate the same primary node-add action.

## Variable Reference UX

- Input fields that accept upstream data must provide a variable selector.
- Selector visuals and interaction should follow Coze conventions: popover/dropdown anchored to the field, first-level source groups, second-level variable list, compact rows, source-node icon/name, variable name, type badge when known, and inserted reference preview.
- Selector groups variables by variable scope/source node, then variable/output name.
- Only connected upstream node outputs are selectable for the currently selected node.
- START variables count as global entry variables and appear first.
- Global variables appear with START/global variables before node outputs.
- Disconnected nodes, downstream nodes, sibling branches that cannot reach the current node, and the current node's own outputs are not selectable.
- Upstream node outputs appear in graph/topological order after global/START variables.
- Each option shows source node name, variable name, type when known, and inserted template value.
- Selecting a variable inserts current compatible template syntax, for example `{{start.userMessage}}`.
- Manual template typing remains possible but is not the primary UX.
- Invalid or missing references show inline field errors and node-card error state.
- CONDITION branch labels must be business labels, not raw edge IDs.

## First Node Config Boundary

Use minimal runtime-backed fields inside a Coze-like layout shell. Do not implement full Coze configuration depth in this spec.

- START: input variables.
- LLM: single-run mode, model selector, unified resource/skill section, input rows, system prompt, user prompt, and output variables.
- CONDITION: expression, branches/default.
- KNOWLEDGE: query, optional knowledge base, output variable.
- API_CALL: method, URL/endpoint, output variable.
- END: output variable or output template.

Out of scope for first canvas: batch mode, visual-understanding input, streaming/continue support, exception handling, editable model parameter panels behind the gear, plugin authentication, real skill/tool configuration, multimodal runtime, full HTTP headers/query/body editor, structured output schema editor beyond flat output rows, retry/error policy editor, and real plugin/tool execution.

## LLM Node Panel UX

The Coze reference LLM panel is the target for the current LLM node shell.

- Header: node icon, editable title, run icon, more menu, close icon, and description text.
- Mode: MVP only implements `单次`; `批处理` is not shown as editable behavior in the first implementation.
- Model section: collapsible title, info icon, model dropdown, and settings gear. The dropdown value also appears on the node card summary.
- Model selection popover: title `模型选择`, info icon, search icon, internal provider/model groups from spec 003, and rows with provider logo/name, model name, short description, health/enabled status, and capability tags when known.
- Model settings gear: may open a read-only/placeholder advanced settings shell. Editable protocol type, generation diversity, length, default instruction, and deep-thinking controls are out of scope for current MVP.
- Skills/resource section: collapsible title, add button, empty state, and unified resource picker styling. It can list Knowledge Bases, MCP tools/servers, and subworkflows using Hify resources, but runtime support is staged by resource type.
- Input section: collapsible title, add button, variable-name column, variable-value column, type selector, reference chip, variable-picker/action icon, and delete action.
- System prompt section: large text editor with compact helper icons, expand action, and AI-assist shell.
- User prompt section: large text editor with placeholder explaining manual syntax such as `{{variable}}`, `{{variable.child}}`, and `{{variable[0]}}`.
- Output section: output format selector, helper/import action shell, add action, output variable rows, type dropdowns, expand/detail action, and delete action.

## LLM Unified Resource Boundary

The LLM `技能` section should be modeled as a Hify Unified Resource selector, not as a Coze-only plugin concept.

Official Coze alignment:

- Coze uses broad `resource` language for workflows, plugins, databases, knowledge bases, and variables.
- Coze workflow docs still treat large model nodes and plugin nodes as different node types.
- Coze UI/web strings expose `workflow_prompt_editor_skill`, plugin-node descriptions, workflow-node descriptions, and knowledge-node empty states. Therefore the Hify LLM `技能` area may share a resource selector, but each resource type must keep its own runtime contract.

Resource types:

- Knowledge Base: callable in the current basic runtime phase as LLM Resource Context.
- MCP Tool or MCP Server tools: selectable only after tool-call runtime is wired into Workflow/Chatflow LLM nodes.
- Subworkflow: selectable only after explicit nested workflow execution is wired and recursion/run evidence rules exist.
- Imageflow: present in Coze skill vocabulary, but out of current Hify MVP.

Current 011/012 callable boundary:

- Knowledge Base can be invoked before the LLM call by rendering a query from the LLM input/user prompt, running `KnowledgeFacade.search_chunks`, and appending retrieved snippets to the model context.
- MCP Tool execution is not current-stage behavior inside an LLM node. Although chat already has MCP tool calling, LLM-node tool use needs node-level resource binding, OpenAI-compatible tool payloads, tool-call parsing, execution, second LLM round, and node-run evidence.
- Subworkflow execution is not current-stage behavior inside an LLM node. It needs explicit input mapping, nested run tracking, cycle prevention, timeout/error policy, and output mapping.
- The UI may show unsupported resource types disabled or tagged as later-stage, but must not imply they run if runtime is not implemented.

## Basic Parameter Controls

Before expanding node-specific advanced fields, implement shared basic controls and apply them to all current nodes.

### Input Parameter Rows

Each input row has:

- Variable name.
- Variable type: string, number, boolean, object/json, array, file where supported.
- Value mode: reference or literal.
- Value:
  - reference mode uses the Variable Reference Picker.
  - literal mode uses a type-aware input.
- Coze-like row controls: type dropdown prefix, selected variable chip, variable picker/action icon, and delete action.
- Required marker and inline error.

### Variable Reference Picker

The picker follows the Coze cascading popover:

- Opens from the variable-value cell/action icon and is anchored to the row.
- First level groups variable sources, including user variables, application variables, system variables, and connected upstream nodes.
- Connected upstream node groups include START and only nodes that can reach the current node.
- Hovering or selecting a source opens a second panel listing variables.
- Variable rows show variable name and type badge.
- Selecting a variable writes a compact chip into the field and persists the compatible template reference.

### Output Parameter Rows

Each output row has:

- Output name.
- Type.
- Expand/detail action for nested schema or future field detail.
- Delete action when node type allows custom output removal.
- Validation for unique and legal output names.

The output section also has:

- Output format selector with `文本`, `Markdown`, and `JSON`.
- Add output variable action.
- Read-only hint that declared outputs enter the downstream variable pool. This is not an editable "can reference" switch.

Coze visual reference: LLM output panel shows output format selector, rows of variable name + variable type, expand icon, delete icon, and add output action.

### Advanced Fields

Advanced fields remain minimal until basic input/output controls pass across all current nodes. The first advanced area may show read-only technical details or placeholders, but must not expose unsupported configuration as editable product behavior.

## Validation Rules

- START and END must exist.
- Every non-END path must be able to reach END.
- Unknown node type fails validation.
- Required config is complete:
  - LLM: prompt or user prompt, output variable.
  - CONDITION: expression and branch/default edges.
  - KNOWLEDGE: query and output variable; knowledge base is optional in mock mode.
  - API_CALL: method, URL/endpoint, output variable.
- END: output variable or output template.
- Variables referenced in templates must come from START/global variables or a connected upstream node when statically knowable.

## Single-Node Test UX

The node panel header run icon is a real selected-node test action, not decoration.

- It runs only the selected node and does not continue into downstream nodes.
- It builds a node input fixture from the selected node's configured input rows, connected upstream output definitions, START/global variables, and literal defaults.
- Missing required upstream values are editable in a Coze-like node-test surface before running.
- Selected-node testing starts from the right panel header run icon. Full-flow trial/debug evidence uses the bottom `调试` panel; selected-node fixture input may appear as a drawer over the right panel only if it keeps the parent node header context visible and does not conflict with the bottom debug panel.
- Drawer idle state:
  - Header title `试运行`, optional `查看日志`, and close icon.
  - `试运行输入` section with one row per required node input.
  - Each input row shows variable name, type badge, and value editor.
  - `JSON模式` toggle switches between row editor and JSON fixture editor.
  - `AI 补全` split button is a UI shell in MVP unless backed by runtime; it can later fill fixture values.
  - Sticky footer shows a full-width green `运行` button with play icon.
- Drawer running state:
  - Body shows centered spinner and `试运行进行中...`.
  - Footer button changes to grey `停止`.
  - Header/node run affordance changes to a stop state.
- Drawer success state:
  - Header shows green success pill with elapsed time, token usage when available, and `查看日志`.
  - Body preserves `试运行输入` and shows `运行结果`.
  - Result sections include `输入`, `推理内容`, `技能调用`, and `输出`.
  - `推理内容` means model-visible response/debug text returned by the node execution, not hidden chain-of-thought.
  - `技能调用` is empty when no resource/tool was invoked and lists resource/tool calls when supported.
  - `输出` shows parsed node output variables.
  - Footer returns to green `运行` for rerun.
- Drawer failure state mirrors success with red status, error details, and log access.
- START node test validates/normalizes the start input schema.
- END node test previews the mapped output from supplied fixture values.
- Single-node test evidence is separate from full-flow run evidence and must not unlock publish by itself.

## Evidence

- Coze screenshot package: `artifacts/research/coze-workflow/`.
- Primary live audit: `artifacts/research/coze-workflow/spec-011-015-live-audit-20260601.md`.
- Primary shared canvas screenshot: `artifacts/research/coze-workflow/screenshots/coze-live-canvas-20260601.png`.
- Add-node menu screenshots: `artifacts/research/coze-workflow/screenshots/coze-live-add-node-menu-header-20260601.png`, `artifacts/research/coze-workflow/screenshots/coze-live-add-node-menu-top-20260601.png`, and `artifacts/research/coze-workflow/screenshots/coze-live-add-node-menu-full-20260601.png`.
- Bottom debug screenshot: `artifacts/research/coze-workflow/screenshots/coze-live-bottom-debug-after-trial-click-20260601.png`.
- LLM right-panel screenshot: `artifacts/research/coze-workflow/screenshots/coze-live-llm-selected-full-20260601.png`.
- Research notes: `artifacts/research/coze-workflow/notes.md`.
- Slice evidence: `artifacts/slices/011-workflow-visual-canvas/{slice-id}/`.
