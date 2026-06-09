# 025.1 Variable Reference Foundation UAT

Target: `http://127.0.0.1:5173/chatflows/1676/canvas`

Browser UAT result:

```json
{
  "sources": ["用户变量", "应用变量", "会话变量", "系统变量", "用户画像"],
  "systemVariables": ["{{sys.query}}", "{{sys.channel_id}}", "{{sys.files}}"],
  "sysChipText": "query / 系统变量 / str.",
  "globalChipText": "brand / 应用变量 / str."
}
```

Acceptance verified:

- The LLM input row opens a grouped variable picker.
- The picker includes Start/user variables, application/global variables, conversation variables, system variables, and user profile variables.
- Disconnected and downstream nodes are not shown as selectable sources.
- Selecting `{{sys.query}}` renders a Coze-like chip with source icon, variable name, compact type badge, and clear action.
- Clearing the chip returns the row to the empty reference affordance.
- Selecting `{{global.brand}}` renders a persisted application-variable chip.

Evidence:

- JSON: `artifacts/slices/025-coze-node-config-panel-parity/025.1/uat-browser.json`
- Screenshot: `artifacts/slices/025-coze-node-config-panel-parity/025.1/screenshots/uat-variable-reference-chip.png`
