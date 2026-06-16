# Plan 017: Resource Tool And Subworkflow Runtime

## Architecture

- Add a workflow resource registry facade that normalizes MCP tools, internal tools, API tools, Knowledge Bases, and published Workflows into one frontend contract.
- Keep invocation through explicit adapters:
  - `KnowledgeContextAdapter` for existing LLM context injection.
  - `ToolInvocationAdapter` for MCP/internal/API tools.
  - `SubworkflowInvocationAdapter` for nested Workflow runs.
- Add node executors instead of embedding every call inside the LLM executor:
  - `ToolCallNodeExecutor`.
  - `ExecuteWorkflowNodeExecutor`.
  - `LlmToolCallingExecutor` or an extension to the existing LLM executor.
- Store resource invocation evidence as structured node run metadata.
- Keep provider-specific tool-call formatting behind a model/tool-call adapter.

## Frontend Notes

- Extend the add-node palette with disabled/enabled `插件` and `工作流` entries.
- Reuse the Coze-like right panel sections:
  - resource selector.
  - input mappings.
  - output schema.
  - execution policy.
  - advanced/error behavior.
- Resource picker rows show capability tags, credential status, runtime status, and disabled reason.
- Node test drawer must show a `技能调用` or `资源调用` block for resource invocation.
- Subworkflow node card should show target workflow, version, mapped inputs, and mapped outputs.

## Backend Notes

- Keep resource invocation deterministic in tests through fake adapters.
- Real adapters must enforce:
  - timeout.
  - retry limit.
  - sanitized logging.
  - schema validation.
  - write-capable resource checks.
- Subworkflow invocation must use a parent run id and nested run id, with recursion and depth guards.
- Chatflow cannot invoke nested Chatflow until 018 supports nested interrupts.

## Data Model Notes

- Extend node run metadata with `resource_calls`.
- Add parent/child run references if not already present.
- Do not store secrets in graph config. Store only resource ids and credential references.

## Slice Order

017.1 -> 017.2 -> 017.3 -> 017.4 -> 017.5
