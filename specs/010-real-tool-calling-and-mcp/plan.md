# Plan 010: Real Tool Calling And MCP

## Architecture

- `ToolSchemaBuilder` converts MCP tool metadata to OpenAI-compatible schemas.
- `ToolCallParser` handles provider-specific response formats.
- `ToolCallRunner` validates agent binding and calls MCP facade.
- `ChatOrchestrator` owns two-round LLM flow.

## Slice Order

010.1 -> 010.2 -> 010.3 -> 010.4 -> 010.5
