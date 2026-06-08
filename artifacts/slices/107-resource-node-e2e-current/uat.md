# 107 Resource Node E2E Current

## Scope

- API Resource + Tool Builder
- TOOL_CALL runtime and selected-node test drawer
- workflow resource policy and timeout evidence
- workflow resource registry API + current LLM tabbed skill picker
- AGENT_CALL resource node roundtrip
- EXECUTE_WORKFLOW resource node roundtrip

## RED

- `e2e-workflow-tool-call-node.txt`: failed because the old test expected raw `资源 ID` / legacy `输入映射` fields in the basic TOOL_CALL panel.
- `e2e-workflow-resource-policy.txt`: failed because the old test expected raw `超时毫秒` field in the basic TOOL_CALL panel.
- `e2e-workflow-resource-registry.txt`: failed because the old test expected the removed mixed `[data-testid="workflow-resource-registry"]` floating panel.

## GREEN

- `unit.txt`: frontend node config + resource registry contract unit tests, 22 passed.
- `integration.txt`: backend resource registry/tool call/policy/agent/subworkflow/API resource integration tests, 24 passed.
- `e2e-api-resource-tool-builder.txt`: PASS api resource tool builder workflow=7364
- `e2e-workflow-tool-call-node-after-fix.txt`: PASS workflow tool call node e2e workflow=7365
- `e2e-workflow-resource-policy-after-fix.txt`: PASS workflow resource policy e2e workflow=7366
- `e2e-workflow-resource-registry-after-fix.txt`: PASS workflow resource registry e2e
- `e2e-workflow-agent-call-node.txt`: PASS workflow agent call e2e agent=2208 workflow=7361 chatflow=7362
- `e2e-workflow-execute-workflow-node.txt`: PASS workflow execute workflow node e2e parent=7359 child=7357

## Product Decision

Current product contract keeps runtime technical values such as `resourceId`, `timeoutMs`, `serverIds`, and legacy `inputMappings` in node config data/runtime only. The ordinary panel should expose resource selectors, adapter status, schema parameter mappings, retry count, and error behavior. LLM resources use tabbed skill selection/search instead of the old mixed registry panel.
