# Hify Spec Index

Specs are executed in strict order. Each spec is split into vertical slices, and
each slice must pass the gates defined in
`docs/testing/acceptance-gates.md` before the next slice starts.

## Ordered Specs

| Spec | Purpose |
|------|---------|
| 000-current-boundary-inventory | Freeze current API, schema, mock behavior, and known gaps |
| 001-backend-foundation | FastAPI backend skeleton and shared infrastructure |
| 002-frontend-foundation | Frontend compatibility and one-command local startup |
| 003-provider-management | Provider/model/health management replica |
| 004-agent-management | Agent CRUD and tool/model binding replica |
| 005-chat-engine | Chat session, sync chat, SSE streaming, context cache |
| 006-knowledge-mock-replica | Current knowledge-base mock behavior replica |
| 007-workflow-replica | Workflow persistence and execution engine replica |
| 008-mcp-replica | MCP server CRUD, connection test, tools/debug replica |
| 009-real-rag-pgvector | Replace knowledge mock with real pgvector RAG |
| 010-real-tool-calling-and-mcp | Real OpenAI tool calling and MCP execution integration |
| 011-workflow-visual-canvas | Visual draggable workflow canvas for current node/runtime boundary |
| 012-chatflow-visual-canvas | Chatflow list/canvas/profile that reuses workflow graph/runtime |
| 013-evaluation-loop-replica | Coze Loop-inspired Evaluation workbench; MVP is an Agent-only eval set, deterministic evaluator, experiment run, and report loop |
| 014-agent-workbench-mvp | Product-level Agent Workbench MVP for configuration, capability binding, mode clarity, and in-page preview |

## Required Files Per Spec

```text
spec.md   # user value, behavior, slices, acceptance gates
plan.md   # implementation approach and architecture notes
tasks.md  # executable checklist with evidence links
```
