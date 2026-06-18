# Spec 191: AI Assistant Live Qwen Chinese Shell

## Goal

Upgrade the AI Assistant MVP shell into a one-screen, Chinese-first operator
workbench and add an explicit OpenRouter Qwen3.5-27B live-planning path for
tool orchestration.

## Scope

In scope:

- keep `/ai-assistant` at one viewport height so the page itself does not need
  vertical scrolling on desktop;
- make left sessions/runs, center event stream, and right inspector scroll
  inside their own columns when content is long;
- keep the composer visible inside the center column without page-level
  scrolling;
- default execution echo cards to collapsed details with explicit expand/collapse
  controls;
- put the current-session clear history/context action in the center
  conversation header and put delete-session actions on each session card;
- translate AI Assistant visible UI text, placeholder text, status labels,
  approval actions, event titles, and task-panel labels into Chinese;
- add AI Assistant live model settings with default model
  `qwen/qwen3.5-27b` and OpenRouter base URL
  `https://openrouter.ai/api/v1`;
- read live credentials only from environment variables such as
  `OPENROUTER_API_KEY` or `HIFY_AI_ASSISTANT_OPENROUTER_API_KEY`;
- expose safe planning/model events for model request, thought summary,
  tool-call decision, streaming chunks, file read/write intent, skill intent,
  and task-panel orchestration;
- keep real file writes and business writes approval-gated; default tests must
  not require live credentials.

Out of scope:

- committing any provider API key;
- exposing hidden chain-of-thought;
- adding SQLite/PostgreSQL paths;
- changing unrelated `customer_assistant` runtime files;
- requiring real network calls in the standard unit/contract/e2e gates.

## Acceptance Criteria

- RED evidence exists for the fixed-height Chinese shell and Qwen live config.
- The shell root uses one viewport-constrained height and internal column
  scrolling for long content.
- The composer is visible in the first viewport, event payload details are
  collapsed by default, and the echo stream can be collapsed/expanded from the
  header.
- Current-session history/context can be cleared from the conversation header;
  individual sessions can be deleted from their own session-card icon button.
- Frontend visible AI Assistant copy is Chinese, including run/task/approval
  labels and composer placeholder.
- AI Assistant backend default live model is `qwen/qwen3.5-27b`.
- Live mode emits visible Chinese events for model planning, thought summary,
  streaming output, selected tool calls, file-operation intent, skill intent,
  and task-panel orchestration.
- Live mode can be tested with a fake OpenAI-compatible client; real OpenRouter
  calls remain opt-in and environment-gated.
- Existing scheduler, approval, sandbox, event replay, inspector, and MySQL8
  contracts remain green.
