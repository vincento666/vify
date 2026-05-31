# Spec 011: Workflow Visual Canvas

## Goal

Replace the incomplete JSON-only workflow form with a visual draggable canvas for the workflow node types already present in the replica runtime: START, LLM, CONDITION, KNOWLEDGE, API_CALL, END. The user can create, edit, validate, test run, and observe a workflow without touching raw graph JSON.

## Product Boundary

- This spec targets **Workflow** only, not Chatflow conversation behavior.
- It uses the existing `/api/v1/workflows` graph CRUD and `/api/v1/workflows/{id}/runs` sync run API.
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
| 011.4 Validate and test run | User runs validation and test input from Start schema; run result marks nodes succeeded/failed and shows output/error details | RED: run UI test fails; Unit: validator; Integration: `/runs` response; E2E: START->LLM->END returns output; UAT: run output visible |
| 011.5 Publish/open/observe shell | User sees publish, open API, and observe tabs/shells; publish blocked until validation and test run pass | RED: publish guard test fails; Unit: publish guard; Integration: status update remains compatible; E2E: publish blocked then enabled; UAT: shell fields visible |

## Node UX Requirements

- START and END exist by default and cannot be deleted.
- Node card shows icon, display name, node type, key input/output summary, and latest run status.
- Edge labels show branch names for CONDITION; internal IDs are hidden.
- Node config panel uses one information architecture across node types:
  - Header: icon, editable name, run icon, menu, close.
  - Input parameters.
  - Required config.
  - Output parameters.
  - Advanced config, collapsed by default.
- Variable references use selector UI when possible and preserve current `{{node.variable}}` template compatibility.

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
- Variables referenced in templates must come from START or an upstream node when statically knowable.

## Evidence

- Coze screenshot package: `artifacts/research/coze-workflow/`.
- Slice evidence: `artifacts/slices/011-workflow-visual-canvas/{slice-id}/`.
