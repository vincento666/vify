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
- [x] Record remaining MySQL8 permission risk.
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
- [x] Record remaining MySQL8 permission risk for blocked
      integration/contract/e2e gates.
- [x] Commit only AI Assistant/spec/artifact changes, excluding unrelated
      dirty customer-assistant/workflow files.
