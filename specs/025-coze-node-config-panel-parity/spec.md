# Spec 025: Coze Node Config Panel and Canvas Interaction Parity

## Goal

Make the Workflow/Chatflow canvas genuinely usable for business authors by
bringing the most-used node configuration panels and canvas interactions close
to Coze's product behavior.

This spec deliberately moves the first implementation block to:

1. Start node;
2. End node;
3. LLM node;
4. variable reference control.

Only after those are usable should the implementation continue into secondary
nodes and advanced fields. The goal is not full Coze parity in one pass. The
goal is that a basic Chatflow/Workflow can be configured without raw JSON,
manual variable typing, or layout confusion.

## Product Boundary

In scope:

- Coze-like right-side configuration panel shell for node-specific forms;
- Start, End, and LLM node panel fields, order, labels, and visual layout;
- variable reference picker and chip input that only exposes allowed variables;
- canvas running-path visual state for current node and active branch;
- node endpoint hover/selected affordances for easier connection aiming;
- edge midpoint insert button and palette quick-connect hardening;
- browser UAT screenshots comparing Coze and Hify for the covered panels.

Out of scope:

- full Coze advanced fields such as batch processing, visual understanding,
  continuation writing, and exception handling;
- full model parameter depth beyond the minimal controls already accepted in
  earlier specs;
- plugin marketplace and third-party authentication fields;
- backend runtime redesign;
- new node catalog expansion beyond compatibility tasks needed by this spec.

## Current Baseline

| Area | Current State | Gap |
|------|---------------|-----|
| Start panel | Uses generic `输入参数` and output tags | Coze Start uses `输入` with `变量名/变量类型/必填`; Start variables become selectable outputs |
| End panel | Has simplified output rows and response content | Coze End separates return mode, output variable mapping, answer content, and stream/typewriter control |
| LLM panel | Generic schema order: model, skills, input, prompt, parameters, output | Coze order is mode, model, skills, input, system prompt, user prompt, output; model/skill controls must not reuse the same dropdown behavior |
| Variable references | Existing picker exists, but still mixed with raw value editing | Needs Coze-like chip input, source menu, upstream-only filtering, type labels, and no invalid downstream choices |
| Running state | Nodes show run status | Incoming edge/current branch do not show moving dashed right-flow animation |
| Endpoints | Static handles exist | Node hover, endpoint hover, and selected node states need size/outline behavior |
| Edge insert | Midpoint `+` and `insertWorkflowNodeOnEdge` already exist | Needs acceptance tests and UAT that selecting a palette item splits the edge and auto-connects correctly |

## Product Decisions

### Panel priority

The first four slices are the P0 authoring loop. No secondary node panels,
resource-node panels, or advanced fields should jump ahead of this block.

Implementation order inside this P0 block is:

1. variable reference foundation used by the panel fields;
2. Start panel;
3. End panel;
4. LLM panel;
5. canvas running path and endpoint interactions;
6. secondary node panels.

The variable foundation is first only because Start, End, and LLM all consume
the same picker/chip behavior. It should stay narrow and immediately serve those
three panels.

### Start node

Start should look and behave like the source of flow input variables.

Required MVP fields:

- section title: `输入`;
- table columns: `变量名`, `变量类型`, `必填`;
- default Chatflow variables include `USER_INPUT` and conversation/system
  variables already supported by the current runtime;
- Workflow Start can keep workflow input variables but uses the same table
  layout;
- custom rows support add, rename, type select, required toggle, and delete;
- Start variables are exposed to downstream variable reference controls.

Avoid a separate `输出变量` section for Start in this slice. Start input
variables are its referenceable outputs.

### End node

End is the user/API response boundary.

Required MVP fields:

- section title: `输入参数` when returning mapped variables is needed;
- section title: `输出`;
- return mode segmented control: `返回文本` and `返回变量`;
- output format selector with `文本`, `Markdown`, `JSON`;
- output variable rows with variable name, variable type, and variable value
  reference/value editor when return mode is variable-based;
- answer content textarea labeled `响应内容` or `回答内容`;
- variable insert button beside the textarea;
- stream/typewriter toggle placed with answer content, wired to Spec 024 when
  the runtime supports it.

Advanced exception handling remains collapsed/out of scope.

### LLM node

LLM should follow Coze's information architecture rather than the current
generic schema order.

Required MVP section order:

1. node header with title, description, run-test button, more button, close;
2. mode switch: `单次` visible and active, `批处理` disabled/hidden until a
   future batch spec;
3. `模型`;
4. `技能`;
5. `输入`;
6. `系统提示词`;
7. `用户提示词`;
8. `输出`.

Required MVP fields:

- model selector using Hify's internal providers/models but Coze-like list
  styling;
- clicking the model name opens only the model selector; the gear button opens a
  dedicated model-parameters panel using the existing accepted minimal model
  controls;
- skill selector entry uses an add button plus resource-type tabs, so knowledge
  bases, MCP/API tools, subworkflows, and agents are not piled into one long
  mixed dropdown;
- skill/resource lists show a compact default page and support search/scroll
  before selection, following Coze's browse-then-configure behavior;
- input rows: `变量名`, `变量值`, type badge, variable chip picker, add/delete;
- Chatflow-only `会话历史` toggle in the input section;
- system prompt textarea supports inline variable insertion by typing `{{`;
- user prompt textarea supports inline variable insertion by typing `{{`;
- output format selector with `文本`, `Markdown`, `JSON`;
- output rows: variable name and type selector, add/delete, expand icon;
- JSON output allows multiple named output variables.

Do not implement visual understanding, continuation writing, exception handling,
or batch fields in this spec unless a later slice explicitly accepts them.

### Variable reference control

The picker must behave like a constrained flow-aware selector, not a free-form
text box.

Selectable sources:

- Start variables;
- global/application variables;
- Chatflow system variables such as `sys.query`, `sys.conversation_id`,
  `sys.user_id`, `sys.channel`, `sys.channel_id`, `sys.message_id`,
  `sys.round`, and `sys.files` when supported;
- only connected upstream node output variables.

Rules:

- downstream nodes are never selectable;
- disconnected nodes are never selectable;
- branch-local variables are selectable only when the current node is reachable
  from that branch;
- source labels, variable names, and variable type badges are visible;
- selected values render as chips with source icon, truncated label, clear
  button, and type information;
- prompt textareas do not show a separate top-right `变量` button; typing `{{`
  opens the same flow-aware variable picker at the caret where practical, and
  inserts `{{source.variable}}` into the textarea;
- raw value input remains available only as a deliberate value mode, not as the
  default variable reference UX.

### Running path and active branch

When a node is running, its incoming edge should show a right-moving dashed
animation. This gives authors a clear sense of "the flow has reached here".

Rules:

- the currently running node keeps the existing node-level running state;
- the edge immediately before that node receives a moving dashed path class;
- if the running node was reached through a condition/intent branch, only the
  active branch edge animates;
- non-active sibling branch edges can remain normal or lightly dimmed, but must
  not animate;
- completed edges may retain a subtle success state after a run detail is open;
- the animation must not move nodes or labels.

### Endpoint hover and selected-node affordances

Endpoint handles should be easier to aim at without making the canvas visually
heavy.

Required states:

- default endpoint: compact;
- node hover: both source/target endpoints scale to `1.2x`;
- endpoint hover: the hovered endpoint scales to `1.5x`;
- selected node: endpoints use the same `1.2x` size as node-hover;
- selected node card gets a light inner border/highlight inside the endpoint
  area, not an oversized outer glow;
- all size changes use transform or stable layout constraints to avoid card or
  edge jitter.

### Edge midpoint insert quick-connect

The existing midpoint `+` button behavior becomes an explicit acceptance
requirement.

When a user clicks the midpoint `+` on an existing edge and chooses a node from
the palette:

- one new node of that type is created near the clicked edge;
- the original edge is removed;
- the original upstream node is connected from its right/source endpoint to the
  new node's left/target endpoint;
- the new node is connected from its right/source endpoint to the original
  downstream node's left/target endpoint;
- if the original edge represented a condition/intent branch, that branch
  condition stays on the upstream-to-new-node edge;
- the new node is selected and its config panel opens;
- the palette closes and no duplicate edge remains.

### Resource node basic vs advanced panels

Resource invocation nodes must separate business configuration from technical
adapter configuration.

For `TOOL_CALL`, the basic panel should not ask authors to fill MCP server ids,
MCP tool names, or raw input mapping JSON. The basic panel is:

- section title: `工具`;
- tool selector grouped by business Tool category/name, not by raw adapter id;
- read-only adapter badge such as `MCP`, `API`, `Internal`, or `Subworkflow`;
- input mapping table generated from the selected Tool input JSON Schema with
  `参数名`, `参数类型`, and `参数值`;
- parameter values use the shared variable reference/value control;
- `参数名` and `参数类型` come from schema properties and are normally read-only;
- `参数值` supports either a connected variable reference or a literal typed
  value;
- required/default/description information from the schema should be visible
  where useful without turning the basic panel into a raw schema editor;
- output preview or output variable section showing the Tool output schema;
- test-run entry that uses the same node test drawer semantics as other nodes.

Technical fields belong outside the ordinary node panel:

- MCP server connection, MCP tool name, authentication, and low-level schema live
  in Tool/Resource management;
- legacy node configs with `mcpServerId`, `toolName`, or `inputMappingJson`
  remain readable;
- legacy technical fields must not be editable in the ordinary business panel;
- if legacy inspection is needed, expose it as a read-only developer/debug view
  or migration prompt, not as a normal authoring path;
- advanced JSON editing must not be the default path for a business author.

`API_CALL` is different from `TOOL_CALL`: it can still expose technical request
configuration because its purpose is direct HTTP integration. Once an API is
wrapped as a Tool, the `TOOL_CALL` node should consume the business Tool
contract instead of re-exposing endpoint/body/header details.

### Schema-derived row editors across node types

The same principle applies to every node that currently stores a list, mapping,
or schema in JSON form: the basic panel should render a structured editor. Raw
JSON remains an advanced compatibility/debugging path.

| Node | Basic Panel Rule | Advanced/Compatibility |
|------|------------------|------------------------|
| `API_CALL` | If an API Resource is selected, generate input rows from the API Resource input JSON Schema and use variable/value controls for values | Direct one-off HTTP mode may expose endpoint, method, headers, body, and raw templates |
| `EXECUTE_WORKFLOW` | Select a published Workflow; generate input mapping rows from target Start variables/input schema and output mapping rows from target output schema | Internal IDs/raw mappings may be inspected read-only for debugging; not edited as ordinary config |
| `AGENT_CALL` | Select an Agent; generate message/variable mapping rows from the Agent invocation contract and output mapping rows from Agent output schema | Internal IDs/raw mappings may be inspected read-only for debugging; not edited as ordinary config |
| `KNOWLEDGE` | Select a Knowledge Base resource, set query with variable/value control, and configure topK/retrieval options | Raw `knowledgeBaseId` is legacy/read-only display only |
| `INTENT_RECOGNITION` | Edit intents as rows/cards: key, name, description, examples, branch binding, default intent | Raw `intents` JSON only in advanced/legacy mode |
| `INFORMATION_COLLECTION` | Edit collection fields as rows/cards: field name, type, required, description, target scope/variable | Raw `fields` JSON only in advanced/legacy mode |
| `QUESTION` | Edit options as option rows when `answerType=option`; answer variable/type remains explicit | Raw `options` JSON only in advanced/legacy mode |
| `HUMAN_INPUT` | Edit human input schema as rows/cards, similar to information collection fields | Raw `inputSchema` JSON only in advanced/legacy mode |
| `JSON_PARSE` | Edit field mappings as rows: output variable, JSONPath/source path, type; suggest rows from upstream JSON output schema when available | Raw `fieldMap` JSON only in advanced/legacy mode |
| `VARIABLE_AGGREGATION` | Edit sources as rows with variable/value controls and labels; strategy remains a selector | Raw `sources` JSON only in advanced/legacy mode |
| `VARIABLE_ASSIGN` | Select target scope/variable and set source value through variable/value control | Raw target/source text is legacy fallback only |

`CODE` is the exception: it is intentionally a technical node, so the code
editor itself is not hidden. Its inputs and outputs should still use structured
row editors where possible.

## Slices

| Slice | User Value | Acceptance Gate |
|-------|------------|-----------------|
| 025.1 Variable reference foundation | Authors can pick valid upstream/global variables without manual typing | RED: invalid downstream/disconnected references are selectable; Unit: graph reachability and variable grouping; E2E/UAT: Coze-like picker and chips |
| 025.2 Start panel parity | Start variables are configured in the expected Coze-like table | RED: Start panel lacks `输入` table shape; E2E/UAT: add required variable and reference it downstream |
| 025.3 End panel parity | End responses can be configured as text or mapped variables with stream option | RED: End panel lacks return mode/output format/answer content layout; E2E/UAT: text and variable response modes |
| 025.4 LLM panel parity | LLM configuration follows Coze section order and supports inputs/prompts/outputs | RED: LLM panel order/labels mismatch; E2E/UAT: configure model, input ref, prompts, JSON outputs |
| 025.4a LLM selector and prompt interaction hardening | Model, skill, and prompt controls behave like distinct Coze controls | RED: model name and gear share one dropdown; RED: skills pile all resource types into one selector; RED: prompt variable button exists instead of `{{` trigger; E2E/UAT: model parameter panel, tabbed skill picker, inline prompt variable insertion |
| 025.5 Running path and active branch animation | Running flows show which node/branch is active | RED: run detail cannot mark active incoming edge; E2E/UAT: condition branch animates only active edge |
| 025.6 Endpoint hover and selection affordances | Users can aim connections reliably | RED: hover/selected states do not resize handles or highlight node; Browser UAT: handle size states captured |
| 025.7 Edge insert quick-connect hardening | Mid-edge `+` creates and connects a node in one step | RED: edge insertion creates node without correct split connections; Unit/E2E/UAT: split edge, preserve branch condition, open new panel |
| 025.8 Secondary Chatflow node panels | Message, Question, Info Collect, Intent use the same panel language | RED: covered secondary panels still use generic labels; E2E/UAT: configure common customer-service dialog path |
| 025.9 Resource node panel alignment | Tool/API/Knowledge/Subworkflow/Agent selectors align with resource specs | RED: Tool Call basic panel still requires MCP server or raw JSON mapping; E2E/UAT: choose resource, map inputs with rows/chips, and run a flow |
| 025.10 Data and structured node panel alignment | Transform/schema/list nodes stop requiring raw JSON in basic mode | RED: JSON Parse, Variable Aggregation, Variable Assign, Human Input, and API Resource mode still expose raw JSON as primary inputs; E2E/UAT: configure each through rows/chips |

## Success Criteria

- A new author can create a Start -> LLM -> End flow using only panel controls
  and variable chips.
- Chatflow Start variables and system variables are selectable by LLM and End
  only when they are valid upstream/global sources.
- LLM JSON output variables can be defined in the panel and referenced by End.
- Running a flow visually identifies the current incoming edge and active branch.
- Hovering nodes/handles and selecting nodes makes connection endpoints easier
  to hit without layout jitter.
- Mid-edge insertion creates the selected node and reconnects the split edge in
  one action.
- Browser UAT evidence includes Coze reference screenshots and Hify screenshots
  for Start, End, LLM, variable picker, running path, endpoint hover, and
  midpoint insert.

## Completion Evidence

### 025.8 Secondary Chatflow node panels

Completed on 2026-06-05.

- Added structured basic panel editors for `QUESTION.options`,
  `INFORMATION_COLLECTION.fields`, and `INTENT_RECOGNITION.intents`.
- Updated `MESSAGE`, `QUESTION`, `INFORMATION_COLLECTION`, and
  `INTENT_RECOGNITION` section language to match the secondary Chatflow panel
  model.
- Kept existing runtime config shapes compatible by serializing row editors back
  to the same config keys.
- Evidence directory:
  `artifacts/slices/025-coze-node-config-panel-parity/025.8/`.

### 025.9 Resource node panel alignment

Completed on 2026-06-05.

- Moved raw resource ids and JSON mappings out of the basic panel path for
  Tool, Knowledge, Subworkflow, and Agent resource nodes.
- Added schema-derived parameter mapping rows for selected resources, with
  read-only parameter name/type and editable reference/literal values.
- Reused the flow-aware variable chip selector for schema mapping values, so
  references like `{{start.USER_INPUT}}` are rendered as chips rather than raw
  text.
- Added Tool adapter evidence badges and compatibility rendering for legacy MCP
  tool configuration; legacy MCP/tool/mapping fields are read-only debug data
  outside the ordinary authoring path.
- Kept direct `API_CALL` request configuration visible while adding API
  Resource selection and schema mapping before the direct request fields.
- Evidence directory:
  `artifacts/slices/025-coze-node-config-panel-parity/025.9/`.

### 025.10 Data and structured node panel alignment

Completed on 2026-06-05.

- Replaced basic raw JSON textareas for `JSON_PARSE`, `VARIABLE_AGGREGATION`,
  `VARIABLE_ASSIGN`, and `HUMAN_INPUT` with structured row editors.
- Kept runtime config serialization compatible by writing back to existing
  `fieldMap`, `sources`, `targetScope`/`targetVariable`/`source`/`writeMode`,
  and `inputSchema` keys.
- Kept legacy/raw editors only under `高级/兼容配置`.
- Added default JSON field mapping suggestions from upstream output parameters
  when a `JSON_PARSE` node has an empty `fieldMap`.
- Evidence directory:
  `artifacts/slices/025-coze-node-config-panel-parity/025.10/`.

### Final gate

Completed on 2026-06-05.

- Frontend unit suite, frontend production build, backend workflow
  unit/integration suite, and relevant 025 E2E batch are green.
- Browser UAT summary and screenshots are saved under
  `artifacts/slices/025-coze-node-config-panel-parity/final-gate/`.
