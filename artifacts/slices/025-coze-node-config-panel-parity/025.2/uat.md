# 025.2 Browser UAT

Date: 2026-06-05

Target:
- `http://127.0.0.1:5173/chatflows/1691/canvas`

Checks:
- Real in-app browser hit-test over the Start node resolves to `.vue-flow__node[data-id="start"]`.
- Start node opens a dedicated `输入` panel, not the old generic `输出变量` layout.
- Start panel shows `变量名`, `变量类型`, and `必填`.
- Start variables include `USER_INPUT` and custom `ticket_id`.
- Downstream LLM input row can select `{{start.ticket_id}}` from `用户变量` and render a Coze-like chip.

Evidence:
- RED pointer gate: `browser-node-pointer-red.txt`
- Result JSON: `uat-browser.json`
- Screenshots:
  - `screenshots/uat-start-panel.png`
  - `screenshots/uat-start-downstream-picker.png`

Result: PASS
