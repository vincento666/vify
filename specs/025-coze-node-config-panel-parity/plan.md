# Plan 025: Coze Node Config Panel and Canvas Interaction Parity

## Implementation Strategy

Treat this as a product-authoring UX spec, not a runtime expansion. Keep the
shared FlowGraph schema and existing node runtime semantics where possible, and
replace generic panel rendering only where the node needs a Coze-like dedicated
form.

Recommended implementation order:

1. build the variable-source model and reference chip control;
2. implement Start, End, and LLM node-specific panels;
3. wire the same control into prompts, input rows, and response content;
4. add running-edge/branch classes based on existing run detail state;
5. polish endpoint hover/selected styles;
6. harden the already-existing edge midpoint insert flow with tests.

The first four slices must remain one P0 block. Do not start secondary nodes,
resource nodes, or advanced Coze-only fields before Start, End, LLM, and the
shared variable reference control are accepted.

## Architecture Notes

### Dedicated panels over one generic schema renderer

The current generic field renderer is useful for long-tail nodes, but it makes
core nodes feel unlike Coze and mixes field order across node types. For Start,
End, and LLM, add dedicated panel components or dedicated render branches with
small shared controls:

- `FlowPanelSection`;
- `VariableReferenceInput`;
- `VariableRowEditor`;
- `OutputVariableEditor`;
- `ModelSelector`;
- `PromptTextarea`.

Do not create a broad design-system refactor before the first slices are green.
Extract only once two or more panels need the same code.

### Variable source model

Create a frontend helper that derives selectable variables from the graph:

- graph nodes and edges;
- selected node key;
- flow type;
- Start variables;
- global/application/system variables;
- upstream reachability.

The helper should return grouped sources with stable identifiers:

- user variables;
- application/global variables;
- system variables;
- Start;
- upstream node outputs.

This helper is the acceptance boundary for "only connected upstream variables".
It should be unit-tested independently from Vue rendering.

### Start panel data mapping

Start configuration can continue using the current serialized config shape if
the runtime already consumes it. The panel should present it as:

- input variable rows;
- type selector;
- required toggle.

If a legacy `output` projection exists for Start, preserve it in compatibility
helpers but do not show a separate output section in the MVP panel.

### End panel data mapping

End should support two modes:

- `text`: response content text/Markdown/JSON template;
- `variables`: named output rows that map variable names to values/references.

Keep downstream runtime compatibility by producing the same final output fields
currently consumed by tests. Add adapter helpers rather than scattering
conditionals in the template.

Streaming/typewriter should call into Spec 024's event model when available. In
025 it is enough that the panel exposes and persists the toggle.

### LLM panel data mapping

LLM panel fields should normalize to the current LLM node config:

- model provider/model ids;
- skill/resource ids;
- input parameters;
- conversation history flag for Chatflow;
- system prompt;
- user prompt;
- output format;
- output parameters.

The panel may store extra UI metadata only when it is additive and ignored by
runtime code that does not understand it.

Model and skill control behavior must stay separated:

- clicking the model display opens the provider/model selector only;
- clicking the gear opens a model-parameters panel/drawer using the existing
  `temperature`, `maxTokens`, `topP`, timeout, and related accepted controls;
- the model parameter controls are not also rendered as a bottom schema section;
- clicking skill add opens a resource-type tab picker, then the selected type
  exposes its own searchable/scrollable selector and configuration fields;
- resource types must not be mixed into one long dropdown because that hides
  the product concept and makes large resource sets unusable.

Prompt variable insertion should be inline-first. System/user prompt textareas
listen for `{{` and open the flow-aware variable picker at the editing context.
The old top-right `变量` button is removed from prompt headers for LLM.

### Running path animation

Use the active run node details already shown in debug panels where possible.
Derive:

- running node keys;
- succeeded node keys;
- active incoming edge id;
- active branch condition when present.

Apply classes through the custom Vue Flow edge renderer:

- `edge-running`;
- `edge-succeeded`;
- `edge-active-branch`;
- `edge-inactive-branch`.

The CSS animation should use stroke dash offset moving rightward along the
Bezier path. It must respect reduced-motion preferences by disabling movement
while keeping a visible running state.

### Endpoint affordances

Prefer CSS transforms on `.node-port` so node boxes and Vue Flow layout do not
shift. Suggested state model:

- `.coze-node:hover .node-port`;
- `.coze-node.node-selected .node-port`;
- `.node-port:hover`;
- `.coze-node.node-selected`.

Scale rules are fixed: node hover and selected-node endpoints use `1.2x`;
direct endpoint hover uses `1.5x`.

The selected card highlight should be inside the card boundary through
`box-shadow: inset ...` or a light border that does not change dimensions.

### Edge midpoint insert

The current code already has:

- `edge-insert-button`;
- `edge-insert-palette`;
- `insertWorkflowNodeOnEdge`;
- condition preservation on the upstream-to-inserted edge.

This slice should add or tighten tests and UAT around the existing behavior
instead of replacing it. If bugs are found, fix narrowly.

### Tool Call panel mapping

`TOOL_CALL` should render from the managed Tool contract, not from raw adapter
fields in basic mode.

Implementation shape:

- fetch/select business Tools from the resource registry;
- render adapter type as a read-only badge;
- render Tool input JSON Schema properties as row-based mappings using the
  shared variable reference/value control;
- keep schema-derived parameter name/type rows stable and generally read-only;
- let only the mapped value column switch between variable reference and literal
  input, with type hints/validation from the schema;
- render Tool output schema as output preview or output variables;
- keep legacy `mcpServerId`, `toolName`, and `inputMappingJson` out of the
  ordinary authoring path; expose them only in read-only debug/migration views
  when needed;
- preserve old node configs by adapting them into the basic display when a
  matching managed Tool exists, and otherwise showing a clear legacy state.

Do not remove direct `API_CALL` technical configuration. `API_CALL` remains the
one-off HTTP integration node; `TOOL_CALL` is the business capability node.

### Structured editors instead of raw JSON

Several existing nodes store arrays or mapping objects in config fields that are
currently rendered as textarea JSON. For basic mode, implement reusable
structured editors rather than one-off textareas:

- schema property mapping editor: parameter name/type/value;
- output mapping editor: source/path/target/type;
- option list editor;
- intent list editor;
- collection field schema editor;
- variable source list editor.

These editors should serialize back to the existing config fields to preserve
runtime compatibility. Raw JSON views may remain in advanced/legacy sections,
but tests should fail if raw JSON is the only basic path for business authors.
For resource identity fields such as Tool server ids, Agent ids, Workflow ids,
and Knowledge ids, prefer read-only inspection or automatic migration over
editable raw fields.

## Frontend Notes

- Use browser screenshots for Coze reference and Hify comparison at the same
  viewport where practical.
- Keep colors and spacing close to the observed Coze panels but use Hify's
  existing typography scale and icon library.
- Do not add large help text blocks inside panels. The form itself should carry
  the workflow.
- Avoid nested cards inside the right panel. Sections should be separated by
  dividers/bands like Coze.
- Maintain keyboard and pointer usability for dropdowns and popovers.

## Backend Notes

- No backend runtime rewrite is expected for 025.
- Add backend tests only if a config shape must be normalized server-side.
- Existing Workflow/Chatflow execution, publish, and debug APIs must remain
  compatible.
- If new config fields are persisted, they must be additive and ignored safely by
  older runtime paths.

## Evidence

Each slice saves:

```text
artifacts/slices/025-coze-node-config-panel-parity/{slice-id}/
├── red.txt
├── unit.txt
├── integration.txt
├── e2e.txt
├── uat.md
└── screenshots/
```

For Browser UAT, include:

- Coze reference screenshot;
- Hify before screenshot when useful;
- Hify after screenshot;
- short notes about matched/mismatched fields.

## Evidence Log

### 025.8 Secondary Chatflow node panels

- RED: `artifacts/slices/025-coze-node-config-panel-parity/025.8/red-secondary-panels.txt`
- Unit: `artifacts/slices/025-coze-node-config-panel-parity/025.8/unit-node-config.txt`
- Integration: `artifacts/slices/025-coze-node-config-panel-parity/025.8/integration-secondary-nodes.txt`
- Build: `artifacts/slices/025-coze-node-config-panel-parity/025.8/build.txt`
- E2E:
  - `artifacts/slices/025-coze-node-config-panel-parity/025.8/e2e-message-question.txt`
  - `artifacts/slices/025-coze-node-config-panel-parity/025.8/e2e-information-collection.txt`
  - `artifacts/slices/025-coze-node-config-panel-parity/025.8/e2e-intent-recognition.txt`
- Browser UAT: `artifacts/slices/025-coze-node-config-panel-parity/025.8/uat.md`

### 025.9 Resource node panel alignment

- RED:
  - `artifacts/slices/025-coze-node-config-panel-parity/025.9/red-resource-node-panels.txt`
  - `artifacts/slices/025-coze-node-config-panel-parity/025.9/red-resource-readonly-debug.txt`
  - `artifacts/slices/025-coze-node-config-panel-parity/025.9/red-schema-chip-e2e.txt`
- Unit:
  - `artifacts/slices/025-coze-node-config-panel-parity/025.9/unit-node-config.txt`
  - `artifacts/slices/025-coze-node-config-panel-parity/025.9/unit-node-config-readonly-debug.txt`
  - `artifacts/slices/025-coze-node-config-panel-parity/025.9/unit-resource-panels.txt`
- Integration: `artifacts/slices/025-coze-node-config-panel-parity/025.9/integration-resource-nodes.txt`
- Build: `artifacts/slices/025-coze-node-config-panel-parity/025.9/build.txt`
- E2E: `artifacts/slices/025-coze-node-config-panel-parity/025.9/e2e-resource-node-panels.txt`
- Browser UAT: `artifacts/slices/025-coze-node-config-panel-parity/025.9/uat.md`

### 025.10 Data and structured node panel alignment

- RED: `artifacts/slices/025-coze-node-config-panel-parity/025.10/red-structured-node-config.txt`
- Unit: `artifacts/slices/025-coze-node-config-panel-parity/025.10/unit-node-config.txt`
- Integration: `artifacts/slices/025-coze-node-config-panel-parity/025.10/integration-structured-nodes.txt`
- Build: `artifacts/slices/025-coze-node-config-panel-parity/025.10/build.txt`
- E2E:
  - `artifacts/slices/025-coze-node-config-panel-parity/025.10/e2e-transform-nodes.txt`
  - `artifacts/slices/025-coze-node-config-panel-parity/025.10/e2e-variable-aggregation-assignment.txt`
  - `artifacts/slices/025-coze-node-config-panel-parity/025.10/e2e-human-input-schema.txt`
- Browser UAT: `artifacts/slices/025-coze-node-config-panel-parity/025.10/uat.md`

### Final gate

- Frontend unit: `artifacts/slices/025-coze-node-config-panel-parity/final-gate/frontend-unit.txt`
- Frontend build: `artifacts/slices/025-coze-node-config-panel-parity/final-gate/frontend-build.txt`
- Backend workflow unit/integration: `artifacts/slices/025-coze-node-config-panel-parity/final-gate/backend-workflow-tests.txt`
- E2E and Browser UAT summary: `artifacts/slices/025-coze-node-config-panel-parity/final-gate/uat.md`
