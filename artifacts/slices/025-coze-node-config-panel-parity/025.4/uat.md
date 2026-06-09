# 025.4 Browser UAT

Date: 2026-06-05

Target:
- `http://127.0.0.1:5173/chatflows/1714/canvas`

Checks:
- LLM panel section order is `单次`, `模型`, `技能`, `输入参数`, `系统提示词`, `用户提示词`, `输出`.
- System prompt and user prompt sections each expose a `变量` trigger.
- Output section keeps output variable rows.
- Existing skill/resource area remains visible before input/prompt/output sections.

Evidence:
- RED unit: `red-unit.txt`
- RED E2E: `red-e2e.txt`
- Result JSON: `uat-browser.json`
- Screenshot: `screenshots/uat-llm-panel-order.png`

Result: PASS
