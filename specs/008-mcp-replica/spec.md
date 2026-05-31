# Spec 008: MCP Replica

## Goal

Replicate MCP Server management, connection test, tool list, debug tool, and the
current chat fallback behavior.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 008.1 MCP Server CRUD | User can create/list/detail/update/delete MCP servers | RED: route contract fails; Unit: schema; Integration: DB; E2E: MCP page; UAT: CRUD works |
| 008.2 Connection and tools | User can test endpoint and list tool details | RED: fake MCP tests fail; Unit: result mapping; Integration: MCP fake server; E2E: tools page; UAT: tools visible or error shown |
| 008.3 Debug tool | User can call a tool with JSON args and see result/error | RED: debug contract fails; Unit: argument validation; Integration: fake server; E2E: debug page; UAT: result visible |
| 008.4 Chat fallback compatibility | Chat tool schema/fallback behavior matches current project | RED: fallback tests fail; Unit: schema builder; Integration: chat fake MCP; E2E: tool chat; UAT: mock result appears |

## Compatibility Rules

- This spec may use fake MCP servers and fallback results.
- Real production-grade tool calling is deferred to `010`.
