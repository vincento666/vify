# Product Research: ReAct Event Echo

Date: 2026-06-18

## Sources

- OpenAI Responses streaming: semantic SSE events, typed schemas, and
  incremental output deltas.
  https://developers.openai.com/api/docs/guides/streaming-responses
- Claude Code hooks: lifecycle events such as `MessageDisplay`,
  `PreToolUse`, `PermissionRequest`, `PostToolUse`, `TaskCreated`, and
  `TaskCompleted`.
  https://code.claude.com/docs/en/hooks
- Claude Code skills: skills are discoverable/invocable instruction bundles
  backed by `SKILL.md`, with optional dynamic context injection.
  https://code.claude.com/docs/en/skills
- Claude Agent SDK overview: agent loops expose built-in tools, sessions,
  permissions, hooks, and real-time streamed messages.
  https://code.claude.com/docs/en/agent-sdk/overview
- Cursor CLI: terminal agent UX highlights commands, shell mode, safety checks,
  output display, model selection, and automation scripting.
  https://cursor.com/cli
- Windsurf/Cascade hooks: pre/post read, write, command, MCP tool, prompt, and
  response hooks provide observability and guardrails around actions.
  https://docs.devin.ai/desktop/cascade/hooks

## Applied UI Rules

- Model text is a first-class stream item. Consecutive `model.stream_chunk`
  events are assembled into one visible model output block per phase, instead
  of one card per token/chunk.
- Tool/action echo is a separate structured item that can be interleaved with
  model text in event sequence order. The header contains only tool type/name
  and completion state; details expand into `调用详情`, `输入`, and `输出`.
- Reasoning/thought summaries are not duplicated as normal model output. They
  remain collapsible and are suppressed when the same text already appears in
  model stream output.
- Running state is local to the current event node: only the currently running
  node animates with a spinner; completed nodes become neutral timeline dots
  and their headers show a green check.
- Historical runs are persisted as folded task records inside the same
  conversation timeline. Selecting old runs in a side list is avoided because
  it disconnects the audit trail from the user message that caused the run.
- Task panel content is derived from real run events, approvals, tool calls, and
  persisted inspector data. It does not pre-render a fixed path before the
  model/tool loop emits events.
- Usage labels include explicit units (`tokens`, `ms`) and do not repeat a
  generic completed state already visible in the folded run record.
