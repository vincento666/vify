# 025.3 Browser UAT

Date: 2026-06-05

Target:
- `http://127.0.0.1:5173/chatflows/1705/canvas`

Checks:
- END panel does not expose `输入参数`.
- END panel renders dedicated `end-response-editor`.
- Return mode segmented control contains `返回文本` and `返回变量`.
- Text mode exposes `输出格式`, `响应内容`, `插入响应变量`, and `流式输出`.
- Response textarea has `resize: none`.
- Variable mode exposes `输出格式`, output variable rows, and add-variable button.

Evidence:
- RED unit: `red-unit.txt`
- RED E2E: `red-e2e.txt`
- Result JSON: `uat-browser.json`
- Screenshots:
  - `screenshots/uat-end-text-mode.png`
  - `screenshots/uat-end-variable-mode.png`

Result: PASS
