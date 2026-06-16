# Spec 017: Resource Tool And Subworkflow Runtime

## Goal

Make Workflow and Chatflow capable of calling runtime-backed business resources in a controlled, observable way. This spec turns the Coze-style `插件` and `工作流` entries from disabled palette shells into explicit, testable resource invocation nodes and upgrades LLM `技能` from a visual placeholder to a guarded callable context where supported.

## Product Boundary

- Starts only after 015 core nodes pass, because tool/subworkflow input and output mapping depends on stable variable reference, JSON parsing, aggregation, assignment, and node test behavior.
- Reuses the shared FlowGraph schema and `flow_type` profile from 011/012.
- Reuses existing MCP/tool-calling foundations from 010 where possible, but Workflow/Chatflow must still have their own node-level runtime contract, run evidence, and validation.
- Enables runtime-backed resource calls only. A resource appearing in a picker is not enough to make it runnable.
- Does not implement third-party plugin marketplace installation, credential onboarding, OAuth consent screens, or arbitrary package execution.
- Does not implement cross-flow dynamic task switching. Subworkflow invocation is explicit and preconfigured.
- Does not allow Chatflow subflows that can themselves pause unless 018 resume and nested checkpoint behavior is explicitly supported.

## Commercial Customer Service Value

Customer service flows need to query orders, check logistics, create tickets, request refunds, update CRM fields, and call internal tools. These operations must be visible as first-class nodes or LLM skills with clear input mapping, output schema, timeout, retry, error policy, and audit evidence.

## Node And Resource Boundary

| Capability | Workflow | Chatflow | Behavior |
|------------|----------|----------|----------|
| TOOL_CALL | Yes | Yes | Explicitly invoke one configured tool/resource with mapped inputs and declared outputs |
| EXECUTE_WORKFLOW | Yes | Yes | Invoke a published Workflow as a subflow with input/output mapping |
| LLM callable skills | Yes | Yes | Allow selected MCP/internal tools to be exposed to the LLM node as callable tools |
| Knowledge context | Already | Already | Continue using 011/012 knowledge context behavior |
| Plugin marketplace | No | No | Later-stage commercial integration |
| Arbitrary remote auth setup | No | No | Later-stage channel/admin feature |

## Coze Palette Alignment

- `插件` maps to `TOOL_CALL` when the selected resource is runtime-backed.
- `工作流` maps to `EXECUTE_WORKFLOW`, not an invisible LLM prompt trick.
- LLM `技能` section can show Knowledge, Tools, and Subworkflows together, but only Knowledge is already runnable before this spec.
- Disabled resources must show why they are disabled: missing schema, missing credential, unsupported runtime, or unsafe flow type.

## Node Contracts

### TOOL_CALL

- Scope: Workflow and Chatflow.
- User-facing label: `插件` or `工具调用`, depending on resource type.
- Config fields:
  - resource type: MCP tool, internal tool, API tool.
  - resource id and display name.
  - input mappings: variable reference or literal value per tool parameter.
  - output schema: named variables and types exposed downstream.
  - execution policy: timeout, retry count, error behavior.
  - credential status: readonly health/auth state.
- Runtime:
  - Resolves mapped inputs from current execution context.
  - Validates input schema before invocation.
  - Calls the resource through a tool adapter.
  - Stores request summary, response summary, latency, and error state in node run evidence.
  - Emits output variables only from declared mapping.
- Error behavior:
  - `fail`: stop current run with error.
  - `continue`: expose error output and continue on default edge.
  - `branch`: use success/error ports when configured.

### EXECUTE_WORKFLOW

- Scope: Workflow and Chatflow.
- User-facing label: `工作流`.
- Config fields:
  - target workflow id/version.
  - input mapping from current variables to target workflow input variables.
  - output mapping from target output variables to current flow variables.
  - timeout and recursion depth limit.
  - run isolation mode: nested run records with parent run id.
- Runtime:
  - Target must be published or explicitly allowed in test mode.
  - Target flow must be `WORKFLOW` in MVP. Calling `CHATFLOW` is blocked until 018 can safely handle nested interrupts.
  - Creates a nested run with parent metadata.
  - Copies mapped outputs back to parent context.
  - Rejects recursive cycles and excessive nesting.
- Output:
  - declared mapped variables.
  - nested run id.
  - status and error message.

### LLM Callable Skills

- Scope: Workflow and Chatflow LLM nodes.
- Config fields:
  - selected callable tools.
  - tool choice mode: auto, required, disabled.
  - max tool call rounds, default 1 in MVP.
  - timeout and error behavior.
  - tool result inclusion: append to final answer or expose as separate output.
- Runtime:
  - Builds OpenAI-compatible tool schemas or provider-compatible equivalents.
  - Sends tools to the model only when the selected provider/model supports tool calls.
  - Executes approved tool calls through the same adapter as TOOL_CALL.
  - Supports one model-tool-model round in MVP.
  - Records tool call evidence in the node test drawer and full run debug dock.
- Guardrails:
  - Tool calls are disabled for models/providers without capability metadata.
  - Tool calls never mutate persistent state unless the tool is explicitly marked as write-capable and authorized.
  - Chatflow history may be included according to the 012/015 history setting.

## Resource Registry

All resource-capable nodes use one registry shape:

- `resource_id`
- `resource_type`
- `display_name`
- `description`
- `input_schema`
- `output_schema`
- `capabilities`
- `flow_type_support`
- `credential_status`
- `runtime_status`
- `health_status`

The frontend picker must display enabled, disabled, and unhealthy states without pretending unsupported resources are runnable.

## Run Evidence

Every resource invocation must appear in:

- single-node test drawer.
- full-flow debug dock.
- backend node run record.
- observe/tracing surface in 019.

Evidence includes sanitized input, output, latency, adapter name, resource id, status, error message, retry count, and nested run link when present.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 017.1 Resource registry and picker contract | Frontend/backend share resource status, schemas, enabled/disabled reasons | RED: picker contract test fails; Unit: registry mapper; Integration: resource list; E2E: disabled resource visible but not runnable |
| 017.2 TOOL_CALL node | Explicit tool invocation runs with mapped inputs and declared outputs | RED: tool node test fails; Unit: adapter/input mapper; Integration: run record; E2E: tool output selectable downstream; UAT: node test shows tool call evidence |
| 017.3 LLM callable skills | LLM node can call selected runtime-backed tools with guarded one-round tool call | RED: LLM skill call test fails; Unit: tool schema builder; Integration: model-tool-model path or fake adapter; E2E: skill evidence visible; UAT: disabled unsupported model state |
| 017.4 EXECUTE_WORKFLOW node | Published Workflow can be invoked as a nested subflow | RED: subworkflow test fails; Unit: recursion guard/input-output mapping; Integration: parent/nested run records; E2E: mapped output feeds downstream |
| 017.5 Resource error and security policy | Timeout, retry, auth missing, and unsafe mutation behavior are explicit | RED: resource failure tests fail; Unit: policy resolver; Integration: failure records; E2E: error branch/default behavior; UAT: debug dock shows failure reason |

## Evidence

- 011/012: current LLM `技能` UI already distinguishes Knowledge runnable resources from MCP/subworkflow disabled resources.
- 015: core nodes provide variable mapping, JSON parsing, assignment, and aggregation required by resource nodes.
- Coze live palette audit: `插件` and `工作流` appear as top resource entries and must remain guarded until runtime-backed.
