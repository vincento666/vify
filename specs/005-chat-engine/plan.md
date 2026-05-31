# Plan 005: Chat Engine

## Architecture

Split the current Java `ChatServiceImpl` into:

- `ChatOrchestrator`
- `ConversationContextStore`
- `PromptBuilder`
- `LlmGateway`
- `SseEventEncoder`
- `ToolCallRunner`
- `RagRetriever`
- `WorkflowRunner`

## Testing Notes

- Use fake LLM adapter fixtures for sync and stream.
- Use contract tests for SSE event payloads.
- Use Playwright to verify incremental chat UI behavior.

## Slice Order

005.1 -> 005.2 -> 005.3 -> 005.4 -> 005.5 -> 005.6
