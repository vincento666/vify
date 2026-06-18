# Tasks 193: AI Assistant Live Orchestration MVP

## 193.1 Live Model And Event Transport

- [x] RED: backend contract fails for `modelConfig` payload, streaming deltas,
      and SSE events.
- [x] Implement request schema and sanitized request hashing for `modelConfig`.
- [x] Implement OpenAI-compatible streaming client with delta accumulation.
- [x] Emit live stream chunks before model completion.
- [x] Add async message start and run event stream endpoints.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.1/`.

## 193.2 Product Shell Realtime UX

- [x] RED: frontend contract fails for model config controls, async API, stream
      helper, and no fixed toolName heuristic.
- [x] Add Chinese model configuration controls.
- [x] Remove frontend fixed tool selection.
- [x] Subscribe to AI Assistant SSE events per run.
- [x] Keep only the outer shell border.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.2/`.

## 193.3 ReAct Stream Assembly And Collapsible Run Timeline

- [x] RED: backend live contract fails until tool results are fed back into the
      second Qwen ReAct round.
- [x] RED: frontend shell contract fails until run echoes are grouped into a
      collapsible task with a milestone execution line and nested details.
- [x] Assemble consecutive model stream chunks into visible model output
      segments instead of one card per chunk.
- [x] Collapse completed run groups by default and expand into event details on
      demand.
- [x] Run backend unit/contract gates that do not require privileged MySQL DDL.
- [x] Run frontend unit, `remScaleClosure`, and production build.
- [x] Run browser UAT with real OpenRouter `qwen/qwen3.5-27b`.
- [x] Close MySQL8 integration/contract/e2e gates with the test admin URL.
- [x] Commit only AI Assistant/spec/artifact changes, excluding unrelated
      dirty customer-assistant/workflow files.

## 193.4 Product-Grade Event Echo And Same-Conversation Run History

- [x] RED: frontend timeline contract fails until tool start/output/completed
      events are aggregated into one invocation with `调用详情`/`输入`/`输出`.
- [x] RED: frontend timeline contract fails until duplicate thought summaries
      are removed both before and after matching model stream output.
- [x] RED: frontend shell contract fails until the left run-record navigation
      and global echo toggle are removed.
- [x] Render persisted historical runs as folded task records in the same
      conversation window.
- [x] Show only running nodes with a spinner; completed nodes use gray dots and
      completed headers use a green check indicator.
- [x] Remove generic `里程碑`/`动态事件` detail rows from event cards.
- [x] Add explicit usage units: `输入 tokens`, `输出 tokens`, `总计 tokens`,
      `耗时 ms`.
- [x] Run full frontend unit, `remScaleClosure`, production build, backend AI
      Assistant unit, and live Qwen/stream contract subset.
- [x] Run browser UAT with real OpenRouter `qwen/qwen3.5-27b`, including
      read tools, write approval, write execution, persisted replay, and
      screenshot evidence.
- [x] Close MySQL8 integration/contract/e2e gates with the test admin URL,
      keeping the implementation on MySQL8.
- [x] Commit only AI Assistant/spec/artifact changes, excluding unrelated
      dirty customer-assistant/workflow files.

## 193.5 Final Browser UAT And Completion Audit

- [x] Run a real browser UAT journey against `/ai-assistant` with OpenRouter
      `qwen/qwen3.5-27b`, temporary model config, model stream, read tool,
      skill intent, write approval, and write completion.
- [x] Verify the ReAct event order over time instead of a fixed mock list:
      running spinner before model output, model output before tool rows,
      tool rows before approval, and completed run after approval.
- [x] Verify one-screen layout, no old echo copy, usage units, task panel real
      content, and expanded tool details with `调用详情` / `输入` / `输出`.
- [x] Save browser UAT screenshots and JSON evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.5/`.

## 193.10 Blocker Recovery And Real Qwen Revalidation

- [x] RED: prove OpenRouter reasoning-only responses were being dropped or
      duplicated into visible model output.
- [x] RED: prove OpenRouter SSE `delta.reasoning` was not preserved by the
      OpenAI-compatible stream client.
- [x] Fix live planner text separation: `reasoning` becomes thought summary,
      while `content` remains the only visible model output stream.
- [x] Fix OpenRouter stream assembly to preserve reasoning outside visible
      `content` deltas.
- [x] Fix the model-config panel so it closes on send and cannot block approval
      actions.
- [x] Hide approval action buttons once the matching approval is no longer
      pending.
- [x] Resolve MySQL8 gate blocker by running tests with
      `HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL` against the local MySQL8 container,
      without introducing SQLite or PostgreSQL fallback.
- [x] Revalidate real OpenRouter `qwen/qwen3.5-27b` browser UAT with tool
      calling, write approval, approval execution, stream output, usage metrics,
      one-screen layout, and cleanup.
- [x] Save evidence under
      `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.10-blocker-recovery/`.
