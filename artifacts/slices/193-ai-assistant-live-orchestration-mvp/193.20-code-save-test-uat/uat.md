# 193.20 Code Save And Test Attempt Pressure UAT

## Scope

- Browser pressure journey for AI Assistant as an engineering harness.
- User task: write code, save it to the workspace, verify readback, run the
  saved code, then ask AI Assistant to run the test command.

## Evidence

- Script: `frontend/e2e/ai-assistant-code-save-test-uat.mjs`
- Saved code path: `tmp/ai-assistant-code-save-test-uat.mjs`
- Saved code local execution output: `PASS ai-assistant-code-save-test-uat`
- Green run output: `code-save-test-uat-green.txt`
- Structured summary: `code-save-test-uat.json`
- Screenshots:
  - `screenshots/code-save-before-approval.png`
  - `screenshots/code-save-completed.png`
  - `screenshots/code-save-test-completed.png`
  - `screenshots/in-app-browser-code-save-expanded.png`

## Result

- Save run: completed after write approval.
- Save run events included `approval.required`, `approval.granted`,
  `tool.call_output`, and `run.completed`.
- The generated JS file was written to disk and executed locally with Node.
- Test command attempt via AI Assistant used `run_shell` and correctly produced
  `sandbox.denied`.
- In-app browser replay showed one persisted run block with `已编辑 1 个文件`
  and `已读取 1 个文件`.
- Right panel showed `沙箱拒绝 shell-like execution is blocked by the Phase 1 sandbox`.
- Page-level vertical overflow stayed `0`; icon-only buttons remained one size.

## Gates

- RED: `red.txt`
- Script contract: `frontend-script-contract.txt`, `frontend-script-contract-2.txt`
- Pressure UAT hardening failures: `code-save-test-uat.txt`,
  `code-save-test-uat-2.txt`, `code-save-test-uat-3.txt`,
  `code-save-test-uat-4.txt`
- Pressure UAT green: `code-save-test-uat-green.txt`
- Full frontend unit: `frontend-unit.txt`
- Frontend build: `frontend-build.txt`
- Whitespace: `rtk git diff --check`

## Remaining Risk

- Shell/test execution inside AI Assistant is intentionally blocked in this
  Phase 1 sandbox. The saved code can be verified by external UAT, but true
  in-harness test execution requires a later sandbox/approval spec.
