# 025.9 Browser UAT

Date: 2026-06-05

Target: `http://127.0.0.1:5176/workflows/1894/canvas`

## Result

PASS. The in-app browser opened a dedicated Workflow with Tool/API/Knowledge/Subworkflow/Agent resource nodes and verified each node panel.

Verified panels:

- `TOOL_CALL`: basic panel shows `工具`, adapter evidence, `参数映射`, and keeps MCP technical fields under `高级/兼容配置`.
- `TOOL_CALL`: schema-derived `参数值` renders `{{start.USER_INPUT}}` as a variable chip instead of a raw text input.
- `TOOL_CALL`: legacy MCP fields in `高级/兼容配置` are read-only debug data; the browser check found `0` editable input/textarea controls inside `legacy-resource-debug`.
- `API_CALL`: basic panel shows `API Resource` and schema parameter mapping before direct request fields.
- `KNOWLEDGE`: basic panel shows a Knowledge selector and query field, with `知识库 ID` moved to compatibility.
- `EXECUTE_WORKFLOW`: basic panel shows a Workflow selector and schema mapping editor, with legacy target/mapping fields only in read-only compatibility/debug data.
- `AGENT_CALL`: basic panel shows an Agent selector, message template, and schema mapping editor, with legacy target/mapping fields only in read-only compatibility/debug data.

Screenshots:

- `uat-tool-call-panel.png`
- `uat-api-call-panel.png`
- `uat-knowledge-panel.png`
- `uat-execute-workflow-panel.png`
- `uat-agent-call-panel.png`
- `e2e-resource-node-panels.png`

Runtime UAT support:

- E2E workflow `1894` ran Start -> Tool -> End using row-backed `inputMappings` and succeeded.
- Full machine-readable browser details are in `uat-browser.json`.
