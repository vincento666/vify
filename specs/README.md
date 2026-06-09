# Hify Spec Index

Specs are executed by the current natural execution order below. Directory
numbers are stable historical IDs and should not be renamed once evidence paths
or references exist.

Each spec is split into vertical slices, and each slice must pass the gates
defined in `docs/testing/acceptance-gates.md` before the next slice starts.

## Current Natural Execution Order

| Order | Spec / Slice | Purpose |
|-------|--------------|---------|
| 1 | 000-020 in numeric order | Foundation, Workflow/Chatflow canvas, Agent workbench, core nodes, resources, state, publish, and evaluation baseline |
| 2 | 025.1-025.4 | Fix the core authoring loop first: variable references, Start panel, End panel, and LLM panel high-fidelity Coze alignment |
| 3 | 025.5-025.7 | Finish core canvas usability: running path/active branch animation, endpoint hover/selection affordances, and midpoint edge insert quick-connect |
| 4 | 021 remaining slices, especially 021.12 | Composer-embedded run/debug detail and publish/Open API/debug IA cleanup after the authoring surface is usable |
| 5 | 024.1-024.2 | Streaming/typewriter output and node-level token/cost/runtime evidence that feed the debug experience |
| 6 | 022 remaining slices, if any | Customer-service runtime parity: Knowledge, Tool, Subworkflow, Agent Call, and structured FAQ capabilities |
| 7 | 024.3-024.4 | API Resources, Tool Builder Lite, and multi-channel publish profiles |
| 8 | 025.8-025.10 | Secondary Chatflow panels, resource node panels, and data/structured node editors after their runtime/resource capabilities are stable |
| 9 | 023 | Integration architecture deepening and consolidation before the next broad expansion wave |
| 10 | 026 | Workflow/Chatflow polish hardening for layout, lists, shared controls, config panels, and variable selectors |
| 11 | 027 | Workflow/Chatflow config hardening for Start defaults, variable references, selectors, branches, and icon polish |
| 12 | 035 | Productize Knowledge retrieval strategy, FAQ vector recall, vector-store adapters, and lifecycle UX |

## Directory Index

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
| 014-agent-workbench-mvp | Product-level single-Agent Workbench; MVP-first implementation, then publishing, versions, memory, variables, tool policy, RAG settings, evaluation gates, sharing, and analytics |
| 015-core-flow-nodes-mvp | Next MVP nodes for data transform, variables, intent, message/question/input, and smart information collection |
| 016-frontend-rem-scale-governance | Global REM scale governance for Hify frontend, adapted from vifly-experiment continuous desktop scale |
| 017-resource-tool-subworkflow-runtime | Runtime-backed plugins/tools, LLM callable skills, and explicit subworkflow invocation for Workflow/Chatflow |
| 018-chatflow-interrupt-session-state | Chatflow sessions, scoped variables, events, checkpoints, and single-flow interrupt/resume |
| 019-human-handoff-channel-publish-observe | Chatflow transfer-to-human, Web/API channel publishing, versioned release, and observe surfaces |
| 020-coze-grade-evaluation-replica | Deepen 013 Evaluation into Coze-grade Eval Set versions/columns, Experiment stepper/mapping, and Evaluator Workbench v2 |
| 021-coze-composer-run-debug-refactor | Refactor global Observe into Coze Studio-style embedded Workflow/Chatflow/Agent run debugging and debug URL deep links |
| 022-customer-service-runtime-parity | Close customer-service runtime gaps: Chatflow subworkflow conformance, structured FAQ, Agent tool-call hardening, and explicit AGENT_CALL node |
| 023-integration-architecture-deepening | Deepen host integration, access policy, runtime evidence, FlowGraph node catalog, resource invocation, evaluation targets, conversation runtime, and persistence lifecycle for low-coupling system embedding |
| 024-runtime-streaming-resource-channel-mvp | Ship high-priority runtime product gaps: Chatflow streaming/typewriter, node usage/cost evidence, API Resources with Tool Builder Lite, and compatible channel profile adapters |
| 025-coze-node-config-panel-parity | Prioritize Coze-like Start/End/LLM panels and variable reference controls, then harden running-path, endpoint, and edge-insert canvas interactions |
| 026-workflow-chatflow-polish-hardening | Harden Workflow/Chatflow layout, lists, shared controls, config panels, and variable selector polish |
| 027-workflow-chatflow-config-hardening | Harden Start defaults, variable references, floating selectors, branch conditions, and workflow icon buttons |
| 035-knowledge-retrieval-productization | Productize Knowledge retrieval with selectable recall modes, FAQ vectorization, adapter boundaries, and lifecycle UX |

## Required Files Per Spec

```text
spec.md   # user value, behavior, slices, acceptance gates
plan.md   # implementation approach and architecture notes
tasks.md  # executable checklist with evidence links
```
