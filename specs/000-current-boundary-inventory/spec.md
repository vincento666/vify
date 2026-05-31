# Spec 000: Current Boundary Inventory

## Goal

Freeze the behavior of the source project before Python implementation starts.
This spec is the reference for API compatibility, database baseline, mock
behavior, and known gaps.

## Source Snapshot

- Repository: `https://github.com/socutes/hify.git`
- Inspected HEAD: `fe4f891241012575f211e19d7818550fd4a95eac`
- Source stack: Java 17, Spring Boot 3.2.3, MyBatis-Plus 3.5.9, OkHttp,
  Resilience4j, MySQL, Redis, planned pgvector.
- Source modules: provider, mcp, agent, workflow, knowledge, chat, common, app.

## Known Gaps To Preserve Or Fix Deliberately

1. MySQL `schema.sql` contains only provider/model/mcp/agent/chat tables.
2. H2 `schema-h2.sql` contains extra knowledge/workflow tables and
   `agent.knowledge_base_id` / `agent.workflow_id`.
3. Knowledge/RAG is mock: chunks are kept in memory, pgvector is not used.
4. OpenAI tool request schema exists at DTO level but is not fully serialized or
   parsed by the adapter.
5. `CircuitBreakerService` exists but is not wired into LLM calls.
6. No source tests exist.
7. Repository includes generated artifacts (`node_modules`, `target`, `dist`).

## Database Baseline Decision

The Python Alembic baseline must use the superset required by current frontend
and Java source behavior:

- provider
- model_config
- provider_health
- mcp_server
- agent, including `knowledge_base_id` and `workflow_id`
- agent_tool
- chat_session
- chat_message
- knowledge_base
- document
- workflow
- workflow_node
- workflow_edge
- workflow_run
- workflow_node_run

The first Alembic migration must not omit knowledge/workflow tables merely
because the Java MySQL DDL is incomplete.

## API Route Matrix

All Python routes must preserve these route groups unless a later ADR changes
the contract.

| Module | Method | Path | Behavior |
|--------|--------|------|----------|
| health | GET | `/api/v1/health` | Component health check |
| provider | POST | `/api/v1/providers` | Create provider |
| provider | GET | `/api/v1/providers` | List providers |
| provider | GET | `/api/v1/providers/{id}` | Provider detail |
| provider | PUT | `/api/v1/providers/{id}` | Update provider |
| provider | DELETE | `/api/v1/providers/{id}` | Delete provider |
| provider | POST | `/api/v1/providers/{id}/test-connection` | Provider connection test |
| agent | POST | `/api/v1/agents` | Create agent |
| agent | GET | `/api/v1/agents` | List agents |
| agent | GET | `/api/v1/agents/{id}` | Agent detail |
| agent | PUT | `/api/v1/agents/{id}` | Update agent |
| agent | PUT | `/api/v1/agents/{id}/tools` | Replace tool bindings |
| agent | DELETE | `/api/v1/agents/{id}` | Delete agent |
| chat | POST | `/api/v1/chat/sessions` | Create chat session |
| chat | GET | `/api/v1/chat/sessions` | List chat sessions |
| chat | DELETE | `/api/v1/chat/sessions/{sessionId}` | Delete chat session |
| chat | GET | `/api/v1/chat/sessions/{sessionId}/messages` | List messages |
| chat | POST | `/api/v1/chat/sessions/{sessionId}/messages` | Synchronous chat |
| chat | POST | `/api/v1/chat/sessions/{sessionId}/messages/stream` | SSE chat stream |
| knowledge | POST | `/api/v1/knowledge-bases` | Create knowledge base |
| knowledge | GET | `/api/v1/knowledge-bases` | List knowledge bases |
| knowledge | GET | `/api/v1/knowledge-bases/{id}` | Knowledge base detail |
| knowledge | PUT | `/api/v1/knowledge-bases/{id}` | Update knowledge base |
| knowledge | DELETE | `/api/v1/knowledge-bases/{id}` | Delete knowledge base |
| knowledge | POST | `/api/v1/knowledge-bases/{kbId}/documents` | Upload document |
| knowledge | GET | `/api/v1/knowledge-bases/{kbId}/documents` | List documents |
| knowledge | GET | `/api/v1/documents/{id}` | Document detail |
| knowledge | GET | `/api/v1/documents/{id}/chunks` | List chunks |
| knowledge | DELETE | `/api/v1/documents/{id}` | Delete document |
| workflow | POST | `/api/v1/workflows` | Create workflow |
| workflow | GET | `/api/v1/workflows` | List workflows |
| workflow | GET | `/api/v1/workflows/{id}` | Workflow detail |
| workflow | PUT | `/api/v1/workflows/{id}` | Update workflow graph |
| workflow | DELETE | `/api/v1/workflows/{id}` | Delete workflow |
| mcp | POST | `/api/v1/mcp-servers` | Create MCP server |
| mcp | GET | `/api/v1/mcp-servers` | List MCP servers |
| mcp | GET | `/api/v1/mcp-servers/{id}` | MCP server detail |
| mcp | PUT | `/api/v1/mcp-servers/{id}` | Update MCP server |
| mcp | DELETE | `/api/v1/mcp-servers/{id}` | Delete MCP server |
| mcp | POST | `/api/v1/mcp-servers/{id}/test` | Connection test |
| mcp | GET | `/api/v1/mcp-servers/{id}/tools` | List tool details |
| mcp | POST | `/api/v1/mcp-servers/{id}/debug` | Debug tool call |

## Response Contract

All normal JSON APIs return:

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

Paginated APIs return `data.items`, `data.total`, `data.page`, and
`data.pageSize` or the source-compatible equivalent chosen in `001`.

SSE chat stream emits JSON data events with:

- `{"type":"delta","content":"..."}`
- `{"type":"done","finishReason":"stop","latencyMs":123}`
- `{"type":"error","message":"..."}`

## Mock Behavior Matrix

| Area | Current Behavior | Replica Requirement |
|------|------------------|---------------------|
| Provider mock | `mock` profile returns fake model list and fake chat/tool-call responses | Preserve fake provider behavior for tests/dev |
| Knowledge chunks | In-memory map keyed by document id | Preserve through `006`; replace in `009` |
| PDF parsing | Placeholder text, no actual PDF parsing | Preserve through `006`; real parser in `009` |
| RAG search | Deterministic-ish random shuffle by query hash and topK | Preserve user-visible topK behavior through `006` |
| MCP tool list | Fallback tool names inferred from server name on failure | Preserve through `008`; real mode in `010` |
| MCP tool result | Mock JSON result returned when call fails in chat path | Preserve through `008`; real mode in `010` |
| Workflow execution | Synchronous, max 50 steps, records run/node-run best effort | Preserve in `007` |

## Slices

| Slice | Behavior Boundary | Gates |
|------|-------------------|-------|
| 000.1 API inventory | List all current `/api/v1/...` routes, methods, request/response envelopes | RED=N/A inventory, Unit=N/A, Contract=route matrix reviewed, E2E=N/A, UAT=N/A |
| 000.2 Schema inventory | Reconcile MySQL and H2 schemas into target Alembic table list | RED=N/A inventory, Unit=N/A, Contract=schema diff recorded, E2E=N/A, UAT=N/A |
| 000.3 Mock behavior inventory | Record current Mock provider, knowledge, MCP fallback behavior | RED=N/A inventory, Unit=N/A, Contract=mock matrix recorded, E2E=N/A, UAT=N/A |
| 000.4 Migration readiness gate | Confirm specs 001-010 are created and ordered | RED=N/A, Unit=N/A, Contract=spec index complete, E2E=N/A, UAT=N/A |

## Acceptance

- Every current feature has a target spec.
- Database augmentation is documented before backend implementation.
- Unknown behavior is marked as explicit risk, not silently guessed.
