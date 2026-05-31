# Plan 010: Real Tool Calling And MCP

## Architecture

- `ToolSchemaBuilder` converts MCP tool metadata to OpenAI-compatible schemas.
- `ToolCallParser` handles provider-specific response formats.
- `ToolCallRunner` validates agent binding and calls MCP facade.
- `ChatOrchestrator` owns two-round LLM flow.
- `ChatService` resolves the Agent model config and uses a provider-backed
  OpenAI-compatible client for direct, RAG, workflow, and MCP tool chat paths.
- Workflow chat injects the same provider-backed client into workflow LLM
  nodes, so workflow-bound chat does not rely on the workflow mock executor.

## Slice Order

010.1 -> 010.2 -> 010.3 -> 010.4 -> 010.5 -> 010.6 -> 010.7
