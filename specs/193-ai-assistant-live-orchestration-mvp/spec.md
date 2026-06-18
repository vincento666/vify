# Spec 193: AI Assistant Live Orchestration MVP

## Goal

Replace the AI Assistant shell's mock-looking fixed execution path with a
minimal live harness loop where each user message starts its own run, calls
OpenRouter Qwen3.5-27B with per-run temporary model configuration, persists
model/tool/task events as they happen, and streams those events into the product
shell.

## Scope

In scope:

- extend spec 191/192 live Qwen support from post-completion replay to real
  OpenAI-compatible streaming deltas;
- accept per-run `modelConfig` for provider, base URL, model, temporary API key
  or API-key reference, temperature, and max tokens;
- default to OpenRouter `qwen/qwen3.5-27b`;
- add an async message-start endpoint and run event SSE endpoint so the browser
  can render events while the run is executing;
- remove frontend keyword heuristics that preselect fixed tool calls;
- add Chinese model configuration controls and stream-status feedback;
- render live execution echoes as a collapsible run task group, with a vertical
  milestone line and nested event detail panels;
- assemble consecutive `model.stream_chunk` events into a single visible model
  output segment, splitting only when tool/task/approval events interleave;
- keep AI Assistant visual framing to the outer shell border only.

Out of scope:

- executing local Codex skills from `invoke_skill`;
- implementing the customer-assistant copilot window;
- memory compaction, benchmark dashboards, and long-term observability beyond
  existing inspector usage;
- committing or persisting any real provider API key;
- SQLite or PostgreSQL persistence paths.

## Acceptance Criteria

- RED evidence exists for live model config, OpenRouter delta stream events,
  event SSE streaming, frontend model configuration controls, and removal of
  fixed frontend tool heuristics.
- `modelConfig` can override model, base URL, temperature, and max tokens; API
  key values are used only for the live request and are not echoed in response
  payloads.
- Live planner emits `model.stream_chunk` with `streaming: true` and
  `source: "openrouter_delta"` before `model.call_completed` when the provider
  returns streaming content deltas.
- `/api/v1/ai-assistant/runs/{runId}/events/stream` returns
  `ai_assistant_event` SSE frames after the requested sequence.
- `/ai-assistant` submits each user message as a separate live run, opens the
  event stream immediately, updates task/inspector state from persisted events,
  and does not send hard-coded `toolName` or `toolInput`.
- Completed runs are collapsed by default; expanding the run shows a milestone
  execution line, and each milestone can expand into formatted detail rows.
- Model output renders as growing stream segments, not one UI card per token or
  delta chunk.
- The shell uses Chinese visible copy and only the outer `.ai-shell` solid
  border; the three columns and internal cards remain visually framed by
  spacing/background, not nested borders.
