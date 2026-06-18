# 193.7 In-App Browser UAT

Date: 2026-06-18
URL: http://localhost:5173/ai-assistant
Tool: Codex in-app browser (`iab`)
Model: OpenRouter `qwen/qwen3.5-27b`

## Setup

The Codex in-app browser was explicitly shown and controlled through the
browser plugin. The page was opened by the in-app browser at
`http://localhost:5173/ai-assistant`.

## Journey

Two independent user turns were executed in the in-app browser:

1. Read `pyproject.toml`, invoke `tdd`, write
   `tmp/iab-ai-assistant-uat-1781766381602-1.txt`.
2. Read `frontend/src/api/aiAssistant.ts`, invoke `code-review`, write
   `tmp/iab-ai-assistant-uat-1781766381602-2.txt`.

Both write files were inspected and removed after the test so the repository
keeps no UAT side-effect files.

## Assertions

All assertions passed:

- in-app browser was controlled directly;
- model selector and temporary model config were available;
- usage units were visible;
- page stayed one-screen with no body scroll and composer visible;
- no old event-header copy (`收起回显`, `里程碑`, `动态事件`);
- no OpenRouter API key leak in page text or artifacts;
- each round created a new run;
- each round showed a running spinner before model output;
- each round showed model stream output;
- each round showed tool echo;
- each round showed approval and the approval was clicked;
- each round reached completion;
- expanded event details showed tool input/output.

## Notes

The browser plugin emitted Statsig network timeout logs while running. These
were telemetry/network warnings from the Codex browser client and did not
affect page control or UAT assertions.

## Evidence

- `in-app-browser-uat.json`
- `screenshots/iab-start.png`
- `screenshots/iab-round-1-final.png`
- `screenshots/iab-round-2-final.png`
- `screenshots/iab-final.png`
