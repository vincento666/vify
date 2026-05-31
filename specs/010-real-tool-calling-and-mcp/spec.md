# Spec 010: Real Tool Calling And MCP

## Goal

Replace current mock/fallback tool behavior with real OpenAI-compatible tool
calling and robust MCP tool execution.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 010.1 Tool schema serialization | LLM requests include valid OpenAI-compatible `tools` payload | RED: request fixture fails; Unit: schema serializer; Integration: fake LLM capture; E2E: N/A; UAT: fixture note |
| 010.2 Tool-call parsing | LLM responses with `tool_calls` are parsed into internal calls | RED: response fixture fails; Unit: parser; Integration: fake LLM; E2E: N/A; UAT: fixture note |
| 010.3 MCP execution | Tool calls execute against bound MCP servers and return content | RED: fake MCP tool call fails; Unit: runner; Integration: fake MCP; E2E: tool chat; UAT: real tool output appears |
| 010.4 Second LLM round | Tool result is appended and second LLM round produces final answer | RED: two-round test fails; Unit: orchestrator; Integration: fake LLM+MCP; E2E: chat flow; UAT: answer references tool result |
| 010.5 Production hardening | Timeouts, partial failures, audit logs, and metrics are covered | RED: failure tests fail; Unit: error policy; Integration: metrics/log capture; E2E: failure UI; UAT: clear error displayed |
| 010.6 Live provider acceptance | OpenRouter OpenAI-compatible chat, tool-call parsing, and second round pass against the configured model | RED: skipped without explicit live flag; Unit: parser reused; Integration: live provider; E2E: N/A; UAT: artifact note |
| 010.7 Product chat live LLM default | Direct, RAG, workflow, and MCP tool chat paths use the Agent model provider by default instead of product mock responses | RED: product chat path tests fail on `Echo`/mock responses; Unit: workflow LLM completer; Integration: provider-backed product paths; E2E: live OpenRouter product paths; UAT: browser chat UI for all paths |

## Compatibility Rules

- Existing fallback behavior remains available for dev/mock mode.
- Real mode must not return fabricated tool results.
- Tool execution is bounded by timeout and agent tool bindings.
- Product chat responses must not use `Echo:`, `RAG mock:`,
  `Workflow mock:`, or `Tool mock:` as the default user-facing path.
