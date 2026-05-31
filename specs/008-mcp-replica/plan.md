# Plan 008: MCP Replica

## Architecture

- Use official Python MCP SDK when possible for client interactions.
- Wrap MCP operations behind `McpFacade`.
- Keep timeout and error mapping explicit.

## Slice Order

008.1 -> 008.2 -> 008.3 -> 008.4
