# Plan 022: Customer Service Runtime Parity

## Architecture Strategy

022 is an integration-hardening spec. It should avoid creating parallel runtimes.

- Keep Workflow and Chatflow on the shared execution engine.
- Keep tools behind the MCP/tool adapter already used by Agent and Workflow.
- Keep knowledge retrieval behind `KnowledgeFacade`, but upgrade the result shape to support structured FAQ and document chunks.
- Add Agent invocation through a narrow facade instead of importing ChatService internals into Workflow executor code.
- Add resource registry support for Agents, but expose Agents only to `AGENT_CALL` in MVP.

## Implementation Areas

### 1. Conformance Tests First

Before adding new behavior, add tests that lock current behavior:

- Workflow `EXECUTE_WORKFLOW` invokes a published Workflow.
- Chatflow `QUESTION` resume still works.
- Agent RAG calls `KnowledgeFacade`.
- Agent tool calling performs model-tool-model execution.
- Workflow/Chatflow `KNOWLEDGE` node calls `KnowledgeFacade`.
- LLM node can call configured MCP tools when provider supports tool calling.

These tests keep 022 from regressing existing slices while refactoring shared facades.

### 2. Chatflow `EXECUTE_WORKFLOW`

Reuse `ExecuteWorkflowNodeExecutor`.

Required additions:

- Chatflow-specific integration fixtures.
- Parent Chatflow session/event compatibility checks.
- Nested interrupt guard.
- Debug evidence shape for nested runs.
- Publish validation that allows `EXECUTE_WORKFLOW` only when target Workflow is published.

Do not allow Chatflow target subflows in this spec.

### 3. Structured FAQ

Add database tables:

- `knowledge_faq`
- optional `knowledge_faq_embedding`

Recommended columns for `knowledge_faq`:

- id, knowledge_base_id, question, answer.
- alternative_questions as JSON.
- keywords as JSON.
- category.
- priority.
- enabled.
- metadata as JSON.
- source.
- deleted.
- created_at, updated_at.

Recommended retrieval flow:

1. Build FAQ exact/keyword candidates.
2. Build FAQ semantic candidates from question and alternatives.
3. Build document chunk vector candidates.
4. Merge, dedupe, score, and sort by source priority and score.
5. Return a source-aware DTO.

Keep current `search_chunks()` compatibility at first:

- either wrap source-aware hits into old `KnowledgeSearchResult`;
- or add a new `search_context()` API and migrate callers slice by slice.

Frontend:

- Add FAQ tab in Knowledge detail.
- Add table CRUD.
- Add CSV import/export.
- Add retrieval test panel that shows FAQ and document hits together.

### 4. Agent Tool-Call Hardening

Keep current `ChatOrchestrator`.

Add:

- provider/model capability checks for tool calling.
- policy validation for write-capable tools.
- consistent audit/evidence DTO.
- debug panel fields for tool calls.
- conformance tests that prove disabled/unsupported tools fail visibly.

This slice should not invent a new plugin system.

### 5. `AGENT_CALL` Node

Add new node type across frontend and backend:

- `WorkflowCanvasNodeType`.
- default node config.
- node config schema.
- variable catalog output support.
- palette entry.
- card icon and port behavior.
- selected-node run fixture.

Backend:

- Add `AgentInvocationFacade`.
- Add `AgentCallNodeExecutor`.
- Add recursion/depth guard that spans Workflow and Agent invocation.
- Record nested agent evidence in node run output.

The facade should expose a focused method such as:

```python
invoke_agent(
    agent_id: int,
    message: str,
    variables: dict[str, Any],
    history: list[dict[str, Any]] | None,
    invocation_context: InvocationContext,
) -> AgentInvocationResult
```

The facade may internally reuse ChatService logic, but Workflow runtime should depend on the facade interface only.

### 6. End-to-End Customer Service Scenario

Build one scenario that proves the base edition hangs together:

- Chatflow starts with `sys.query`.
- Intent node routes to order/refund path.
- Information collection asks for missing order id.
- Knowledge retrieval returns FAQ answer.
- Tool call retrieves order state.
- Subworkflow formats or validates business result.
- Agent call drafts or enriches final response.
- Message sends response.
- Transfer-to-human branch creates handoff when confidence is low.
- Published API/Web channel run returns a composer debug URL.
- Debug dock shows all nested calls and evidence.

## Risk Notes

- `AGENT_CALL` can easily create recursive execution. Do recursion guard before happy-path polish.
- FAQ scoring can destabilize RAG answers. Keep deterministic tests and explain source priority.
- Do not mix Chatflow interrupt checkpoints into child Workflow runs.
- Do not expose secrets in graph config, node evidence, debug URL, or FAQ metadata.
- Avoid making Agent a hidden LLM skill until user experience and recursion behavior are mature.

## Testing Strategy

- Unit:
  - FAQ ranking and merge.
  - Agent invocation facade.
  - recursion guard.
  - node config schema.
- Integration:
  - Chatflow `EXECUTE_WORKFLOW`.
  - Agent two-round tool calling with policy.
  - FAQ retrieval through Agent and Workflow.
  - `AGENT_CALL` Workflow and Chatflow runs.
- E2E:
  - FAQ CRUD/retrieval test UI.
  - add and run `AGENT_CALL` node.
  - customer service full path.
- Browser UAT:
  - Knowledge FAQ tab.
  - Workflow/Chatflow canvas with `AGENT_CALL`.
  - debug dock nested evidence.
  - published run debug URL.
