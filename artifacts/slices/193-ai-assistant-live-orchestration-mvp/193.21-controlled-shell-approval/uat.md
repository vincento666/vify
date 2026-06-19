## 193.21 Controlled Shell Approval + Header Alignment UAT

- Browser: Codex in-app browser at `http://localhost:4174/ai-assistant`.
- Scenario: switch composer to `完全访问权限`, save a JS test file, read it back, run `node tmp/ai-assistant-code-save-test-uat.mjs`, expand command echo details.
- Result: run completed, no approval rows, no sandbox denial, command stdout appeared in nested command details and final answer.
- Visual follow-up: refreshed the preview build and measured the processed run header.
- Header evidence: `justifyContent=start`, `justifyItems=start`, `textAlign=left`, title/meta same row, and status/title/meta/chevron x positions increase left-to-right.
- Remaining risk: controlled shell is intentionally limited to sandbox-approved executables and workspace script paths; broader command execution remains out of scope.
