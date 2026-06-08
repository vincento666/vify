# 104 All Node Current Matrix

- Date: 2026-06-09
- Scope: current workflow/chatflow core node matrix after condition, aggregation, assignment, variable picker, and palette hardening.

## Frontend E2E

- `e2e-transform-nodes.txt`: CODE, TEXT_PROCESS, and JSON_PARSE workflow/chatflow paths pass.
- `e2e-resource-node-panels.txt`: TOOL_CALL, API_CALL, KNOWLEDGE, EXECUTE_WORKFLOW, and AGENT_CALL panel contracts pass.
- `e2e-chatflow-message-question-input.txt`: MESSAGE, QUESTION, and HUMAN_INPUT chatflow paths pass.
- `e2e-chatflow-information-collection.txt`: INFORMATION_COLLECTION chatflow path passes.
- `e2e-chatflow-intent-recognition.txt`: INTENT_RECOGNITION chatflow path passes.
- `e2e-all-node-variable-reference-audit.txt`: all-node variable picker audit passes.

## Backend And Unit Gates

- `integration-core-chat-transform.txt`: 16 integration tests pass for transform, message/question/human input, information collection, and intent recognition.
- `integration-resource-nodes.txt`: 17 integration tests pass for API resource/tool builder, tool call, execute workflow, and agent call.
- `unit-node-matrix.txt`: node config, graph, variable catalog, and node-test fixture unit tests pass.
- `rem.txt`: frontend rem gate passes.

## Result

Current core node matrix gates pass. No product code change was required in this slice.
