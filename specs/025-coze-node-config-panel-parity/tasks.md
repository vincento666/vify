# Tasks 025: Coze Node Config Panel and Canvas Interaction Parity

## 025.1 Variable reference foundation

- [x] RED: add failing unit tests for upstream reachability variable filtering.
- [x] RED: add failing frontend test where disconnected/downstream node outputs appear in the picker.
- [x] Implement graph variable source helper for Start, global/application, system, and upstream node outputs.
- [x] Add branch-aware filtering for condition/intent paths where graph data is available.
- [x] Add Coze-like variable reference input with chip display, clear action, source icon, type badge, and grouped popover.
- [x] Add value mode vs reference mode so raw values remain deliberate, not the default variable UX.
- [x] Wire variable reference control into existing input parameter rows without changing runtime output shape.
- [x] Unit green: variable source helper covers Start/global/system/upstream/downstream/disconnected cases.
- [x] E2E green: select Start variable in an LLM input and End response field.
- [x] Browser UAT: capture Coze variable picker and Hify variable picker/chip states.
- [x] Save evidence under `artifacts/slices/025-coze-node-config-panel-parity/025.1/`.
- [x] Gates pass.

## 025.2 Start panel parity

- [x] RED: add failing E2E/snapshot assertion that Start panel lacks Coze-like `输入` table columns.
- [x] Replace Start panel generic `输入参数` layout with dedicated `输入` section.
- [x] Show columns `变量名`, `变量类型`, and `必填`.
- [x] Show Chatflow defaults including `USER_INPUT` and supported conversation/system variables as appropriate.
- [x] Support add, rename, type select, required toggle, and delete for custom variables.
- [x] Preserve existing config serialization consumed by runtime/tests.
- [x] Ensure Start variables appear in downstream variable picker.
- [x] E2E green: add required Start variable, save graph, reload, and reference it downstream.
- [x] Browser UAT: capture Coze Start reference and Hify Start panel.
- [x] Save evidence under `artifacts/slices/025-coze-node-config-panel-parity/025.2/`.
- [x] Gates pass.

## 025.3 End panel parity

- [x] RED: add failing E2E/snapshot assertion for missing return mode, output format, and answer content layout.
- [x] Add End return mode segmented control: `返回文本` and `返回变量`.
- [x] Add output format selector with `文本`, `Markdown`, and `JSON`.
- [x] Add output variable rows with variable name, type selector, and value/reference editor for variable return mode.
- [x] Add answer content textarea with variable insert button for text return mode.
- [x] Add stream/typewriter toggle placement in the answer content section and persist it.
- [x] Keep current End runtime output compatible with existing tests.
- [x] E2E green: configure text response with variable chip.
- [x] E2E green: configure variable response mapping from LLM output.
- [x] Browser UAT: capture Coze End reference and Hify End panel in both modes.
- [x] Save evidence under `artifacts/slices/025-coze-node-config-panel-parity/025.3/`.
- [x] Gates pass.

## 025.4 LLM panel parity

- [x] RED: add failing E2E/snapshot assertion that LLM panel section order differs from Coze.
- [x] Add dedicated LLM panel order: header, `单次`, `模型`, `技能`, `输入`, `系统提示词`, `用户提示词`, `输出`.
- [x] Keep `批处理`, visual understanding, continuation writing, and exception handling hidden or disabled per this spec.
- [x] Replace model picker surface with Coze-like list styling using Hify internal provider/model data.
- [x] Keep model settings minimal and compatible with existing provider config.
- [x] Add skill/resource selector surface for available tools, knowledge, and subworkflows without raw IDs in basic mode.
- [x] Add input rows with `变量名`, `变量值`, type badge, variable chip picker, add, and delete.
- [x] Add Chatflow-only `会话历史` toggle in the input section.
- [x] Add system prompt textarea with variable insertion.
- [x] Add user prompt textarea with variable insertion.
- [x] Add output format selector with `文本`, `Markdown`, and `JSON`.
- [x] Add output variable rows with variable name, type selector, expand, add, and delete.
- [x] E2E green: configure model, Start input reference, system/user prompts, and JSON output variables.
- [x] Browser UAT: capture Coze LLM reference and Hify LLM panel top/middle/output sections.
- [x] Save evidence under `artifacts/slices/025-coze-node-config-panel-parity/025.4/`.
- [x] Gates pass.

## 025.4a LLM selector and prompt interaction hardening

- [x] RED: add failing E2E assertion that clicking the LLM model name opens only model selection while the gear opens a model-parameters panel.
- [x] RED: add failing E2E assertion that LLM skills use resource-type tabs instead of one mixed knowledge/tool/subworkflow dropdown.
- [x] RED: add failing E2E assertion that LLM prompt headers do not show a separate `变量` button and typing `{{` opens the variable picker.
- [x] Move existing bottom `模型参数` schema controls into a gear-triggered panel/drawer.
- [x] Ensure the model display dropdown triggers provider/model selection, not the parameter panel.
- [x] Replace `技能调用` bottom section with an add-skill entry that opens tabbed resource selection.
- [x] Keep selected skills rendered as compact rows/chips with resource type, name, remove, and configuration affordance.
- [x] Add searchable/scrollable list behavior inside each resource tab and keep only a bounded default result count visible.
- [x] Remove top-right variable buttons from LLM system/user prompt headers.
- [x] Open the flow-aware variable picker when users type `{{` in LLM system/user prompt textareas and insert the selected reference inline.
- [x] Unit green: selector state helpers and inline prompt insertion behavior.
- [x] E2E green: model selector vs gear panel, tabbed skill add, inline `{{` prompt variable insertion.
- [x] Browser UAT: capture model selector, model parameter panel, skill tab picker, and inline variable picker.
- [x] Save evidence under `artifacts/slices/025-coze-node-config-panel-parity/025.4a/`.
- [x] Gates pass.

## 025.5 Running path and active branch animation

- [x] RED: add failing frontend test proving a running node does not mark its incoming edge.
- [x] Derive active incoming edge ids from current run node details.
- [x] Derive active condition/intent branch edge ids when branch condition metadata exists.
- [x] Add edge renderer classes: `edge-running`, `edge-succeeded`, `edge-active-branch`, `edge-inactive-branch`.
- [x] Add right-moving dashed animation for `edge-running`.
- [x] Respect `prefers-reduced-motion` by disabling movement while keeping visible running state.
- [x] Ensure non-active sibling branch edges do not animate.
- [x] E2E green: run a flow and observe current node incoming edge animation.
- [x] E2E green: run a conditional flow and observe only active branch animation.
- [x] Browser UAT: capture running edge and active branch screenshots or short video evidence.
- [x] Save evidence under `artifacts/slices/025-coze-node-config-panel-parity/025.5/`.
- [x] Gates pass.

## 025.6 Endpoint hover and selected-node affordances

- [x] RED: add failing visual/DOM test for handle size states and selected card highlight.
- [x] Add default, node-hover `1.2x`, endpoint-hover `1.5x`, and selected-node `1.2x` endpoint states.
- [x] Make endpoint growth use transform or stable sizing without node/card jitter.
- [x] Add selected node light inner border/highlight inside the endpoint area.
- [x] Ensure source and target endpoints remain correctly connected by Vue Flow after transform.
- [x] Ensure touch/mouse hit targets remain usable.
- [x] E2E green: hover node, hover endpoint, select node, and start a connection.
- [x] Browser UAT: capture default, node hover, endpoint hover, and selected node states.
- [x] Save evidence under `artifacts/slices/025-coze-node-config-panel-parity/025.6/`.
- [x] Gates pass.

## 025.7 Edge insert quick-connect hardening

- [x] RED: add failing unit test for splitting an edge and preserving original branch condition.
- [x] RED: add failing E2E test for midpoint `+` -> choose node -> new node auto-connected.
- [x] Keep or fix `insertWorkflowNodeOnEdge` so the original edge is removed.
- [x] Keep or fix upstream-to-new-node edge with the original condition/branch metadata.
- [x] Keep or fix new-node-to-downstream edge without duplicating the original edge.
- [x] Select the inserted node and open its config panel after insertion.
- [x] Close edge palette and clear edge hover/selection state after insertion.
- [x] Unit green: edge split, condition preservation, and no duplicate edges.
- [x] E2E green: use midpoint `+` to insert LLM between Start and End.
- [x] E2E green: use midpoint `+` on a condition branch and preserve the branch edge.
- [x] Browser UAT: capture palette open and inserted connected node.
- [x] Save evidence under `artifacts/slices/025-coze-node-config-panel-parity/025.7/`.
- [x] Gates pass.

## 025.8 Secondary Chatflow node panels

- [x] RED: add failing panel assertions for `MESSAGE`, `QUESTION`, `INFORMATION_COLLECTION`, and `INTENT_RECOGNITION`.
- [x] Align `MESSAGE` panel with send-message/no-wait semantics and output/stream controls where supported.
- [x] Align `QUESTION` panel with wait-for-answer semantics, answer variable, options/default branch, and resume behavior.
- [x] For `QUESTION`, replace raw `options` JSON with option rows when `answerType=option`.
- [x] Align `INFORMATION_COLLECTION` panel with multi-turn slot collection MVP fields and global context toggle.
- [x] For `INFORMATION_COLLECTION`, replace raw `fields` JSON with collection field rows/cards: name, type, required, description, target scope, target variable.
- [x] Align `INTENT_RECOGNITION` panel with LLM-driven intent branches and fallback branch.
- [x] For `INTENT_RECOGNITION`, replace raw `intents` JSON with intent rows/cards: key, name, description, examples, and branch binding.
- [x] Reuse variable reference control in all covered panels.
- [x] E2E green: configure a basic customer-service dialog path using covered nodes.
- [x] Browser UAT: capture each panel.
- [x] Save evidence under `artifacts/slices/025-coze-node-config-panel-parity/025.8/`.
- [x] Gates pass.

## 025.9 Resource node panel alignment

- [x] RED: add failing panel assertions for `TOOL_CALL`, `API_CALL`, `KNOWLEDGE_RETRIEVAL`, `EXECUTE_WORKFLOW`, and `AGENT_CALL` where present.
- [x] RED: add failing `TOOL_CALL` panel test while basic mode still exposes MCP server id, MCP tool name, or raw input mapping JSON.
- [x] Align resource selectors with Specs 017, 022, and 024 resource models.
- [x] For `KNOWLEDGE`, show a Knowledge Base selector instead of requiring raw `knowledgeBaseId` in basic mode.
- [x] For `API_CALL` resource mode, parse the selected API Resource input JSON Schema into row-based input mappings.
- [x] For `TOOL_CALL` basic mode, show a business Tool selector instead of raw MCP server/tool fields.
- [x] For `TOOL_CALL` basic mode, show an adapter badge (`MCP`, `API`, `Internal`, `Subworkflow`) as read-only evidence.
- [x] For `TOOL_CALL` basic mode, parse the selected Tool input JSON Schema into row-based `参数名` / `参数类型` / `参数值` mapping.
- [x] Keep schema-derived `参数名` and `参数类型` read-only in basic mode, while `参数值` supports variable reference or literal input.
- [x] Surface schema required/default/description hints in the row UI without exposing raw JSON by default.
- [x] Avoid raw IDs in basic mode for selectable tools, API resources, knowledge bases, subworkflows, and agents.
- [x] Keep `mcpServerId`, `toolName`, and `inputMappingJson` out of the ordinary authoring path; expose them only as read-only debug/migration data when needed.
- [x] Add compatibility rendering for existing nodes that already store MCP server and input mapping JSON.
- [x] For `EXECUTE_WORKFLOW`, select a published Workflow and generate input/output mapping rows from target Start/output schema.
- [x] For `EXECUTE_WORKFLOW`, avoid editable raw `targetWorkflowId`, `inputMappings`, and `outputMappings` in the ordinary panel; show only read-only debug data if needed.
- [x] For `AGENT_CALL`, select an Agent and generate message/variable mapping rows from the Agent invocation contract.
- [x] For `AGENT_CALL`, avoid editable raw `targetAgentId`, `resourceId`, `inputMappings`, and `outputMappings` in the ordinary panel; show only read-only debug data if needed.
- [x] Add a migration path or explicit copy action from legacy MCP fields to a managed Tool resource when possible.
- [x] Reuse variable reference control for resource input mappings.
- [x] E2E green: choose a business Tool, map input variables through rows/chips, run a flow, and inspect output.
- [x] E2E green: open a legacy MCP-backed `TOOL_CALL` node and verify technical fields are hidden from basic mode and only visible as read-only debug/migration data when needed.
- [x] Browser UAT: capture each covered resource panel after the read-only debug/migration rule is verified.
- [x] Save updated evidence under `artifacts/slices/025-coze-node-config-panel-parity/025.9/`.
- [x] Gates pass.

## 025.10 Data and structured node panel alignment

- [x] RED: add failing panel assertions while raw JSON textareas are the only basic path for `JSON_PARSE`, `VARIABLE_AGGREGATION`, `VARIABLE_ASSIGN`, and `HUMAN_INPUT`.
- [x] For `JSON_PARSE`, replace raw `fieldMap` JSON with mapping rows: output variable, JSONPath/source path, type, and delete/add controls.
- [x] For `JSON_PARSE`, suggest mapping rows from upstream LLM JSON output schema when available.
- [x] For `VARIABLE_AGGREGATION`, replace raw `sources` JSON with source rows using variable/value controls, source labels, and strategy selector.
- [x] For `VARIABLE_ASSIGN`, use target scope/variable selectors where variables are known and a variable/value control for source value.
- [x] For `HUMAN_INPUT`, replace raw `inputSchema` JSON with schema field rows/cards: field name, type, required, description, and approval behavior.
- [x] Keep raw JSON editors for these nodes only under `高级/兼容配置`.
- [x] Keep existing runtime config serialization compatible.
- [x] E2E green: configure JSON parse field mapping without raw JSON and use parsed output downstream.
- [x] E2E green: configure variable aggregation and assignment through rows/chips.
- [x] E2E green: configure human input schema through rows/cards and resume with payload.
- [x] Browser UAT: capture each covered structured editor.
- [x] Save evidence under `artifacts/slices/025-coze-node-config-panel-parity/025.10/`.
- [x] Gates pass.

## Final gate

- [x] Full relevant frontend unit suite green.
- [x] Relevant backend compatibility tests green if config shape changed.
- [x] Relevant E2E suite green.
- [x] Browser UAT evidence saved for Coze reference and Hify result.
- [x] `spec.md`, `plan.md`, and `tasks.md` updated with final evidence.
- [x] `specs/README.md` remains ordered and accurate.

## 025.11 Canvas/node panel regression hardening

- [x] RED: config-panel open/close zoom stability test fails before removing side-panel resize/refit.
- [x] RED: edge insert palette occlusion test fails before palette offset/z-index fix.
- [x] RED: inline variable insertion test verifies non-END node text fields insert local-only refs.
- [x] Keep node config panel behavior aligned while preserving existing structured panel coverage for resource and transform nodes.
- [x] Evidence: `artifacts/slices/083-workflow-chatflow-canvas-node-parity/`.
- [x] Gates pass.
