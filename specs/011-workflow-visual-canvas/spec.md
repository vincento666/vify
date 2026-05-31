# Spec 011: Workflow Visual Canvas

## Goal

Replace the incomplete JSON-only workflow form with a visual draggable canvas for the workflow node types already present in the replica runtime: START, LLM, CONDITION, KNOWLEDGE, API_CALL, END. The user can create, edit, validate, test run, and observe a workflow without touching raw graph JSON.

## Product Boundary

- This spec targets **Workflow** only, not Chatflow conversation behavior.
- It uses workflow resources with `flow_type=WORKFLOW`, the existing `/api/v1/workflows` graph CRUD shape, and `/api/v1/workflows/{id}/runs` sync run API.
- It does not add Dify-style multi-task switching, task stack, cross-flow interrupt/resume, or real tool calling.
- Coze visual reference requires logged-in browser evidence. Current unauthenticated Edge attempt is stored at `artifacts/research/coze-workflow/coze-edge-initial.png` and shows the login gate.

## User Value

Workflow authors can assemble deterministic business logic visually: add nodes, connect them, configure fields, run a test, inspect node status, and later publish once validation passes.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 011.1 Workflow tab shell | Workflow module shows Workflow and Chatflow tabs; Workflow tab keeps current list and opens canvas builder | RED: route/list UI test fails; Unit: route helpers; Integration: existing workflow list unchanged; E2E: tab navigation; UAT: Workflow tab visible |
| 011.2 Canvas graph editor | User creates START/END default graph, drags nodes, adds current node types, connects/deletes edges, saves graph | RED: canvas save test fails; Unit: graph adapter; Integration: CRUD persists positions/config; E2E: create graph; UAT: drag/save/reopen |
| 011.3 Node config panel | Selecting a node opens Coze-style right panel with unified sections for input params, required config, output params, advanced config | RED: node config test fails; Unit: node schema metadata; Integration: saved config round-trips; E2E: edit LLM/Condition/API/Knowledge/End; UAT: config readable |
| 011.4 Variable reference selector | User can choose upstream START/node outputs in input fields without typing raw template paths | RED: variable selector test fails; Unit: variable catalog builder; Integration: saved template round-trips; E2E: select upstream output; UAT: selector inserts reference |
| 011.5 Validate and test run | User runs validation and test input from Start schema; run result marks nodes succeeded/failed and shows output/error details | RED: run UI test fails; Unit: validator; Integration: `/runs` response; E2E: START->LLM->END returns output; UAT: run output visible |
| 011.6 Publish/open/observe shell | User sees publish, open API, and observe tabs/shells; publish blocked until validation and test run pass | RED: publish guard test fails; Unit: publish guard; Integration: status update remains compatible; E2E: publish blocked then enabled; UAT: shell fields visible |

## Node UX Requirements

- START and END exist by default and cannot be deleted.
- Node card visually follows Coze workflow canvas conventions: compact rounded card, icon/title header, subtle type/status treatment, input/output summaries, hover affordances, selection outline, run status badge, and field-level error indicator.
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

## Variable Reference UX

- Input fields that accept upstream data must provide a variable selector.
- Selector visuals and interaction should follow Coze conventions: popover/dropdown anchored to the field, searchable grouped list, compact rows, source-node icon/name, variable name, type badge when known, and inserted reference preview.
- Selector groups variables by source node, then output name.
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
- LLM: prompt, output variable.
- CONDITION: expression, branches/default.
- KNOWLEDGE: query, optional knowledge base, output variable.
- API_CALL: method, URL/endpoint, output variable.
- END: output variable or output template.

Out of scope for first canvas: model parameter panels, plugin authentication, full HTTP headers/query/body editor, structured output schema editor, retry/error policy editor, and real plugin/tool configuration. Advanced sections may show placeholders or read-only technical details only when useful.

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

## Evidence

- Coze screenshot package: `artifacts/research/coze-workflow/`.
- Pixel/interaction reference must include logged-in Coze canvas screenshots or a documented login-block fallback before 011.2 implementation signoff.
- Slice evidence: `artifacts/slices/011-workflow-visual-canvas/{slice-id}/`.
