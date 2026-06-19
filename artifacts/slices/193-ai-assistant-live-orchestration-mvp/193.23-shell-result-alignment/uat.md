# UAT: 193.23 Shell Result Alignment Polish

## Scope

- Fix third-level expanded Shell result blocks so the content block is not
  visually narrowed or indented below the command fold header.
- Preserve the Codex-like command fold header, Shell block, stdout display, and
  hover/focus copy affordance.

## Evidence

- RED: `red-shell-result-alignment.txt`
- Focused green: `unit-shell-result-alignment.txt`
- Frontend AI Assistant + rem gate: `unit-rem.txt`
- Full frontend unit: `frontend-unit-full.txt`
- Frontend build: `frontend-build.txt`
- Deterministic pressure UAT: `e2e-browser-uat.txt`
- In-app browser screenshot:
  `screenshots/browser-shell-result-aligned.png`

## Browser UAT Notes

- Scripted pressure UAT created and ran
  `tmp/ai-assistant-code-save-test-uat.mjs` through AI Assistant in
  full-access mode.
- Scripted browser geometry result: `shellResultLeftDelta = 0`.
- Codex in-app browser live OpenRouter `qwen/qwen3.5-27b` run produced a
  completed command echo for `node tmp/ai-assistant-code-save-test-uat.mjs`.
- In-app browser geometry result:
  `shellHeaderLeft = 278.75`, `shellResultLeft = 278.75`,
  `shellResultLeftDelta = 0`, `pageOverflowY = 0`.

## Remaining Risk

- None for the requested alignment issue. Generic non-Shell tool detail rows
  keep their existing indentation because this slice only targets the Shell
  result block shown in the reported screenshot.
