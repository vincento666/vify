# Tasks 191: AI Assistant Live Qwen Chinese Shell

## 191.0 Documentation Sign-Off

- [x] Create `191-ai-assistant-live-qwen-zh-shell`.
- [x] Limit scope to viewport shell, Chinese copy, and Qwen live planning
      events.
- [x] Declare OpenRouter model id `qwen/qwen3.5-27b`.
- [x] Declare credentials environment-only and absent from repo artifacts.
- [x] Save documentation evidence under
      `artifacts/slices/191-ai-assistant-live-qwen-zh-shell/191.0/`.

## 191.1 One-Screen Chinese Shell

- [x] RED: frontend shell contract fails until viewport height and internal
      column scrolling are implemented.
- [x] RED: frontend shell contract fails until visible AI Assistant copy is
      Chinese.
- [x] Implement fixed one-screen shell height.
- [x] Implement independent left, center, and right vertical scrolling.
- [x] Translate AI Assistant shell labels, actions, placeholders, status labels,
      and task/inspector section titles.
- [x] Update AI Assistant browser E2E selectors to Chinese copy.
- [x] Run frontend shell unit and `remScaleClosure`.
- [x] Run browser UAT and save screenshot/evidence.

## 191.2 Qwen Live Planning Events

- [x] RED: backend unit/contract tests fail until default live model is
      `qwen/qwen3.5-27b`.
- [x] RED: backend unit/contract tests fail until fake live model planning emits
      Chinese model, thought, stream, tool, file, skill, and task-panel events.
- [x] Add AI Assistant LLM settings with OpenRouter defaults and env-only
      credentials.
- [x] Add fake-testable Qwen live planner using OpenAI-compatible payloads.
- [x] Add request `modelMode` support without making default gates live.
- [x] Route model-selected tool calls through the existing scheduler.
- [x] Keep file writes and business writes approval/sandbox guarded.
- [x] Run focused unit, contract, integration/e2e regressions, ruff, and mypy.

## 191.3 Aggregate Acceptance

- [x] RED evidence saved.
- [x] Backend unit/contract/integration/e2e evidence saved.
- [x] Frontend unit and `remScaleClosure` evidence saved.
- [x] Browser UAT evidence and screenshot saved.
- [x] Risk list updated.
- [x] Commit after gates pass.

## 191.4 Shell Lifecycle Tightening

- [x] Add contract coverage for clearing current session history/context and
      deleting a session through public API.
- [x] Add frontend coverage for center-header clear action, per-session delete
      icon, one-screen composer visibility, and collapsed event details.
- [x] Move clear history/context into the conversation header.
- [x] Move delete session to each session card as an icon action.
- [x] Clear `context_json` together with run/message/event/tool/approval
      history.
- [x] Verify real OpenRouter Qwen3.5-27B tool planning with environment-gated
      smoke test.
- [x] Run browser UAT confirming no page-level vertical scroll, visible
      composer, collapsed cards, clear history/context, and per-session delete.
