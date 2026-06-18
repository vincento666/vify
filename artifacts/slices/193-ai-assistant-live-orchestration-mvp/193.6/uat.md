# 193.6 AI Assistant Browser Stress UAT

Date: 2026-06-18
URL: http://localhost:5173/ai-assistant
Model: OpenRouter `qwen/qwen3.5-27b`

## Journey

Ran a 3-round browser pressure journey with real model configuration, real
event streaming, read tools, skill intent records, write approvals, and write
completion.

Round prompts:

1. Read `pyproject.toml`, invoke `tdd`, write
   `tmp/ai-assistant-stress-1781765664073-1.txt`.
2. Read `frontend/src/api/aiAssistant.ts`, invoke `code-review`, write
   `tmp/ai-assistant-stress-1781765664073-2.txt`.
3. Read `specs/193-ai-assistant-live-orchestration-mvp/tasks.md`, invoke
   `playwright`, write `tmp/ai-assistant-stress-1781765664073-3.txt`.

The temporary files were inspected and removed after the run so the worktree
does not keep UAT side effects.

## Raw Stress Result

The first stress script reported raw issues:

- round 2/3 `completionObserved` failed;
- global `noOldCopy` failed;
- round 3 `noOldCopy` failed.

These were reviewed against the saved samples and replay state.

## Interpretation

- Round 2/3 completion was a script assertion issue. The script compared
  right-panel/global approval counts against a previous active run. After
  approval both rounds had zero pending approval rows, zero running spinners,
  completion text, and expanded tool details.
- Round 3 old-copy detection was a tool-output false positive. The run read
  `specs/193.../tasks.md`, whose file content intentionally mentions
  `里程碑` / `动态事件` as removed-copy test text. Frontend AI Assistant source
  and replayed UI headers do not contain those labels.

## Normalized Acceptance

Normalized replay passed:

- 3 independent run groups persisted in the same conversation;
- each round created a new run;
- each round showed running state before model output;
- each round showed model stream output;
- each round showed tool echo with expanded input/output details;
- each round showed approval and the approval was clicked;
- each round reached completion after approval;
- no page body scroll; composer remained visible;
- model selector/config and usage units were visible;
- no API key leak detected in page text or artifacts;
- task panel showed real task/tool/approval content.

## Evidence

- `browser-stress-uat.json`: raw per-second samples and raw assertions.
- `browser-stress-uat-normalized.json`: reviewed acceptance result.
- `screenshots/stress-start.png`
- `screenshots/round-1-final.png`
- `screenshots/round-2-final.png`
- `screenshots/round-3-final.png`
- `screenshots/stress-final.png`
- `screenshots/stress-replay.png`
