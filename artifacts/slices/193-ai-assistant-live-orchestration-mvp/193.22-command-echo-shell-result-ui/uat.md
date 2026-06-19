# 193.22 Command Echo Shell Result UI UAT

## Scope

- Refactor `run_shell` echoes so the outer event is `已运行 N 条命令`.
- Render each command invocation with the command itself as the fold header.
- Expand command invocations into one Codex-like `Shell` result block.
- Keep the copy action inside the Shell result block.

## Browser Evidence

- In-app browser URL: `http://127.0.0.1:5173/ai-assistant`.
- Backend: real FastAPI server on `127.0.0.1:8000`, MySQL8-backed persistence.
- Created real session `命令回显 UAT`, shell run `108`, status `COMPLETED`.
- Visible DOM after expansion:
  - event headers: `已编辑 1 个文件`, `已读取 1 个文件`, `已运行 1 条命令`
  - command header: `node tmp/ai-assistant-shell-result-uat.mjs`
  - shell output: `$ node tmp/ai-assistant-shell-result-uat.mjs` and `PASS ai-assistant-shell-result-uat`
  - generic tool detail rows for the shell command: `0`
  - shell result copy buttons: `1`
  - page vertical overflow: `0`
- Screenshot: `screenshots/browser-shell-result-expanded.png`.
- Follow-up browser verification after removing the inner completed icon:
  - event headers: `已编辑 1 个文件`, `已读取 1 个文件`, `已运行 1 条命令`
  - command header: `node tmp/ai-assistant-code-save-test-uat.mjs已完成`
  - shell header status icons: `0`
  - shell output: `$ node tmp/ai-assistant-code-save-test-uat.mjs` and `PASS ai-assistant-code-save-test-uat`
  - shell result copy buttons: `1`
  - page vertical overflow: `0`
  - screenshot: `screenshots/browser-shell-result-no-inner-status-icon.png`

## Automated Pressure UAT

- Command:
  `HIFY_E2E_BASE_URL=http://127.0.0.1:5173 HIFY_E2E_ARTIFACT_DIR=artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.22-command-echo-shell-result-ui HIFY_AI_ASSISTANT_FORCE_DETERMINISTIC=1 rtk node frontend/e2e/ai-assistant-code-save-test-uat.mjs`
- Result: passed.
- Follow-up command-header assertion result: passed with
  `toolInvocationHeaders = ["node tmp/ai-assistant-code-save-test-uat.mjs已完成"]`
  and `shellHeaderStatusIcons = 0`.
- Evidence:
  - `e2e-browser-uat.txt`
  - `code-save-test-uat.json`
  - `screenshots/code-save-completed.png`
  - `screenshots/code-save-test-completed.png`

## Notes

- Browser automation could not trigger CSS `:hover` through CUA mouse movement in this runtime; the UI contract verifies `.ai-shell-result:hover .ai-shell-result__copy`, and the real DOM verified the copy button exists inside the Shell result block with an SVG icon.
