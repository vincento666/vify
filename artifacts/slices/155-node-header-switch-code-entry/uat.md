# 155 Node Header / Switch / Code Entry UAT

## Official References

- AgentArts code node guide: code nodes declare input parameters, execute a fixed `main(args)` / `exports.main(args)` entry, and return a dictionary/object whose keys match output parameters.
  - https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0067.html
- Coze code node guide was checked as the peer reference for code-node product semantics.
  - https://www.coze.com/open/docs/guides/code_node

## Browser UAT

- Current in-app browser: `http://127.0.0.1:5173/chatflows/9069/canvas`
- Reloaded the current canvas after implementation.
- Opened `message_1`:
  - config header text is exactly `消息`;
  - no `message_1` node key is visible in the header;
  - `流式输出` switch row is flex-aligned with the control right edge matching the row right edge.
- Added and opened a Code node:
  - config header text is `代码`;
  - inserted template is:

```python
def main(args):
    return {
        'output': args.get('input', '')
}
```

- Screenshot: `screenshots/in-app-code-panel-template.png`

## Gates

- RED:
  - `red-integration.txt`: Python code node `main(args)` returned empty before fix.
  - `red-integration-js-exports-main.txt`: JavaScript `exports.main(args)` failed with `exports is not defined`.
  - `red-transform-e2e.txt`: Code template still used legacy `result = ...`.
  - `red-config-e2e.txt`: Message config header exposed `message_1`.
- GREEN:
  - `integration-transform-nodes.txt`: 7 transform-node integration tests passed.
  - `e2e-config-compact.txt`: config header and right-aligned switch passed.
  - `e2e-transform-nodes.txt`: workflow/chatflow transform nodes and code template passed.
  - `unit-node-config.txt`: 21 node config unit tests passed.
  - `rem.txt`: rem scale closure passed.
  - `unit-full.txt`: frontend full unit passed, 59 files / 218 tests.
  - `build.txt`: frontend build passed.

## Node Matrix Recheck

- `e2e-variable-aggregation-official.txt`: variable aggregation official-layout path passed.
- `e2e-variable-aggregation-assignment.txt`: variable aggregation/assignment path passed.
- `e2e-resource-node-panels.txt`: API/Tool/Knowledge/Subworkflow/Agent resource node panel contracts passed.
- `e2e-chatflow-intent-recognition.txt`: intent recognition passed.
- `e2e-chatflow-message-question-input.txt`: message/question/human input passed.
- `e2e-chatflow-information-collection.txt`: information collection passed.
- `e2e-workflow-execute-workflow-node.txt`: subworkflow reference/execute workflow passed.
- `e2e-workflow-tool-call-node.txt`: tool/plugin call passed.
- `e2e-api-resource-tool-builder.txt`: API Resource + Tool Builder path passed.
- `e2e-workflow-agent-call-node.txt`: agent call passed.
- `e2e-knowledge-faq-retrieval.txt`: knowledge FAQ retrieval/runtime passed.
- `integration-node-matrix.txt`: 32 backend integration tests passed for API resource/tool builder, tool call, execute workflow, agent call, knowledge FAQ runtime, message/question/input, info collection, and intent recognition.

## Scope Note

These gates prove the current core behavior and UI contracts for the listed nodes are green. They do not claim every advanced Coze/HiAgent optional setting is pixel-perfect; unsupported advanced features remain out of scope unless captured by a dedicated future slice.
