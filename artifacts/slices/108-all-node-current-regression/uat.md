# 108 All Node Current Regression

## Scope

- Condition branch cards, editable branch names, branch endpoint alignment, and condition value controls.
- Variable aggregation and variable assignment official/product-shaped panels.
- Resource nodes: tool/API/knowledge/subworkflow/agent panel alignment.
- Chatflow-only nodes: message, question, information collection, and intent recognition.
- Transform nodes: code/text/JSON/aggregation/assignment workflow and chatflow runtime.
- All-node variable reference picker audit.
- Node palette mode separation and config-panel zoom stability.

## RED

- `red-integration.txt`: backend matrix failed because the six-node matrix knowledge facade stub did not accept the current retrieval keyword arguments.

## GREEN

- `unit-frontend.txt`: workflow node config, graph, palette, variable catalog, node-test fixtures, and canvas controls: 64 tests passed.
- `integration-backend.txt`: workflow condition, chatflow message/question, information collection, intent recognition, six-node matrix, tool/resource/agent/subworkflow runtime: 38 tests passed.
- `e2e-condition-branch-endpoints.txt`: PASS workflow condition branch endpoints e2e.
- `e2e-condition-branch-values.txt`: PASS workflow condition branch values e2e.
- `e2e-variable-aggregation-official.txt`: PASS workflow variable aggregation official e2e.
- `e2e-variable-aggregation-assignment.txt`: PASS workflow/chatflow variable aggregation assignment e2e.
- `e2e-resource-node-panels.txt`: PASS workflow resource node panels e2e.
- `e2e-transform-nodes.txt`: PASS workflow/chatflow transform nodes e2e.
- `e2e-chatflow-message-question-input.txt`: PASS chatflow message question human input e2e.
- `e2e-chatflow-information-collection.txt`: PASS chatflow information collection e2e.
- `e2e-chatflow-intent-recognition.txt`: PASS chatflow intent recognition e2e.
- `e2e-all-node-variable-reference-audit.txt`: PASS all node variable reference picker audit.
- `e2e-config-panel-zoom-stability.txt`: PASS workflow config panel zoom stability e2e.
- `e2e-node-palette-modes.txt`: PASS workflow chatflow node palette modes e2e.

## Product Notes

- Opening and closing a node config panel must not change the canvas zoom.
- Workflow and chatflow palettes intentionally differ only for conversation-only nodes.
- Variable aggregation remains group-first and auto-adds an empty candidate row; it does not expose advanced compatibility fields.
- Assignment, aggregation, condition, and resource nodes all use the shared Coze-like variable reference controls in the verified panels.
