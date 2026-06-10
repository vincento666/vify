# Workflow/Chatflow Lifecycle UAT

## Official references

- Coze Code node: https://www.coze.com/open/docs/guides/code_node
- Coze Condition node: https://www.coze.com/open/docs/guides/condition_node
- Coze Variable merge node: https://www.coze.com/open/docs/guides/variable_merge_node
- Coze Variable assign node: https://www.coze.com/open/docs/guides/variable_assign_node
- AgentArts Variable assign node: https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0084.html

## Browser/UAT coverage

- Workflow/chatflow canvas lifecycle, node panels, toolbar, publish, run/debug surfaces.
- Condition node card branch blocks, editable branch names, branch source endpoints.
- Variable aggregation grouped editor and first non-empty strategy.
- Variable assignment compact editor with no redundant type/fx controls.
- Code node language/editor/template/runtime parity.
- Chatflow trial conversation panel, opening suggestions, message send.
- Resource nodes: tool call, execute workflow, agent call, LLM resources, generic resource panels.

## Evidence

- `e2e-canvas-ux.txt`
- `e2e-six-node-matrix.txt`
- `e2e-workflow-chatflow-llm-run.txt`
- `e2e-all-node-variable-reference.txt`
- `e2e-resource-node-panels.txt`
- `e2e-transform-nodes.txt`
- `e2e-llm-resources.txt`
- `e2e-chatflow-trial-chat-panel.txt`
- `e2e-chatflow-message-question-input.txt`
- `e2e-chatflow-information-collection.txt`
- `e2e-chatflow-intent-recognition.txt`
- `e2e-chatflow-end-panel.txt`
- `e2e-chatflow-llm-panel.txt`
- `e2e-chatflow-conversation-run.txt`
- `e2e-chatflow-publish.txt`
- `e2e-workflow-tool-call.txt`
- `e2e-workflow-execute-workflow.txt`
- `e2e-workflow-agent-call.txt`
- `e2e-workflow-publish.txt`
- `e2e-list-polish.txt`
- `e2e-toolbar-zoom.txt`
- `e2e-icon-button-polish.txt`
- `e2e-variable-selector-polish.txt`

Screenshots are under `screenshots/`.
