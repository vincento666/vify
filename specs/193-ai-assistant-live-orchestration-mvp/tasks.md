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
- [ ] Commit only AI Assistant/spec/artifact changes, excluding unrelated
      dirty customer-assistant/workflow files.
