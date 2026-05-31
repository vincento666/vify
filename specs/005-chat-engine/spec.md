# Spec 005: Chat Engine

## Goal

Replicate chat sessions, message history, synchronous chat, SSE streaming,
context cache, RAG hook, workflow hook, and tool-call orchestration boundary.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 005.1 Session/message CRUD | User can create sessions and list messages | RED: route contract fails; Unit: schema; Integration: DB; E2E: chat page loads history; UAT: session create/list |
| 005.2 Sync chat replica | User can send a non-streaming message and receive assistant message | RED: fake LLM test fails; Unit: prompt builder; Integration: DB persistence; E2E: chat send; UAT: full response appears |
| 005.3 SSE streaming | User sees `delta` events followed by `done` or `error` | RED: SSE contract fails; Unit: event encoder; Integration: streaming route; E2E: stream UI; UAT: incremental text appears |
| 005.4 Context cache | Recent conversation context loads from Redis or DB fallback | RED: cache miss/hit tests fail; Unit: trimming; Integration: Redis fake/container; E2E: second turn context; UAT: multi-turn works |
| 005.5 RAG/workflow hooks | Agent bindings route chat to mock RAG or workflow path | RED: hook tests fail; Unit: orchestrator branching; Integration: bound agent; E2E: bound chat; UAT: visible RAG/workflow output |
| 005.6 Tool-call boundary replica | Current mock/fallback tool behavior is preserved | RED: tool fallback test fails; Unit: tool schema builder; Integration: fake MCP; E2E: tool-trigger chat; UAT: mock tool answer appears |

## Runtime Rules

- SSE route must not hold SQLAlchemy sessions while streaming.
- External LLM calls use `httpx.AsyncClient`.
- Concurrency is bounded with anyio limiters.
- Errors are sent as SSE `type=error` and logged.
