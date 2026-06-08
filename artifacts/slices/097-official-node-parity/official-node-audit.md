## Official Reference Baseline

Primary reference: Huawei Cloud AgentArts user manual node pages under `support.huaweicloud.com/usermanual-agentarts0/`.

- Start/End: `agentarts_05_0060.html` says the start node is the workflow data entry and the end node returns the final result.
- LLM: `agentarts_05_0062.html` describes model selection, input parameters, prompt configuration, model parameters, and structured output.
- Subworkflow: `agentarts_05_0063.html` describes invoking a published workflow as a nested subroutine.
- Agent: `agentarts_05_0064.html` describes Agent as a generic node combining LLM reasoning plus plugin calls, not conversation-only.
- Condition: `agentarts_05_0066.html` describes IF/ELSE branches, multiple conditions with AND/OR, and branch priority order.
- Intent: `agentarts_05_0069.html` describes classifying user intent and routing to downstream branches.
- Code: `agentarts_05_0067.html` describes deterministic code execution for data processing and format conversion.
- Plugin/MCP: `agentarts_05_0072.html` and `agentarts_05_0073.html` describe external capability invocation through plugins/MCP services.
- Message/Question/Input/Object extraction: `agentarts_05_0077.html`, `agentarts_05_0079.html`, `agentarts_05_0078.html`, `agentarts_05_0081.html`.
- Variable assign: `agentarts_05_0084.html` describes assigning values to memory/global or loop intermediate variables; value can come from references or operation assignment.
- Variable aggregation: `agentarts_05_0085.html` describes grouping variables and returning the first non-empty value by priority.
- Knowledge retrieval: `agentarts_05_0086.html` describes RAG retrieval where the input parameter is a query and the node outputs retrieval information.

## Current Slice Closure

- Fixed workflow palette to include `智能体`, matching AgentArts generic Agent node positioning.
- Renamed `KNOWLEDGE` node default card/config title to `知识检索`; resource selector section can still say `知识库` because it selects a knowledge base resource.
- Regressed condition branch UI after endpoint hitbox changes: branch names, branch endpoints, AND/OR secondary conditions, typed operators, and variable picker all pass.
- Updated stale E2E expectations after product copy/resource-selector changes: subworkflow panels now assert resource selection + `参数映射`, knowledge retrieval tests assert `检索测试`/`测试检索` and Chinese match-type tags, and AgentCall/FAQ runtime E2E prefer stable `mock://success` models instead of unreachable external providers.

## Covered By Gates

- Condition selector parity: `workflow-condition-branch-endpoints.mjs`, `workflow-condition-branch-values.mjs`.
- Variable assignment + aggregation runtime/UI: `workflow-variable-aggregation-assignment.mjs`.
- Resource panels: `workflow-resource-node-panels.mjs`.
- All-node variable picker replacement: `workflow-all-node-variable-reference-audit.mjs`.
- Workflow/chatflow palette mode split: `workflow-chatflow-node-palette-modes.mjs`.
- Message / Question / Information Collection / Intent / Transfer-to-human chatflow nodes: `chatflow-message-question-input.mjs`, `chatflow-information-collection.mjs`, `chatflow-intent-recognition.mjs`, `chatflow-transfer-to-human-node.mjs`.
- JSON Parse / Text Process / transform runtime: `workflow-transform-nodes.mjs`, `tests/integration/workflow/test_transform_nodes.py`.
- API Resource / Tool Builder / MCP/API schema mapping: `api-resource-tool-builder.mjs`, `workflow-resource-node-panels.mjs`.
- AgentCall / ExecuteWorkflow / Knowledge FAQ retrieval runtime: `workflow-agent-call-node.mjs`, `workflow-execute-workflow-node.mjs`, `knowledge-faq-retrieval.mjs`, `tests/integration/workflow/test_agent_call_node.py`, `tests/integration/workflow/test_execute_workflow_node.py`, `tests/integration/workflow/test_knowledge_faq_runtime.py`.
- Final frontend gates: `npm --prefix frontend run test:unit`, `npm --prefix frontend run build`.
