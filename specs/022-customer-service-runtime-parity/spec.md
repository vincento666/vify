# Spec 022: Customer Service Runtime Parity

## Goal

Close the remaining runtime and product gaps that prevent Hify from being a commercial customer service foundation rather than only a canvas/runtime demo.

This spec builds on 009, 010, 017, 018, 019, and 021. It does not replace those specs. It hardens what is already implemented, adds missing customer-service primitives, and clarifies the direction for Agent, Workflow, Chatflow, tools, and knowledge-base interoperability.

## Why This Spec Exists

Recent code inspection shows several capabilities are partly or mostly present:

- `EXECUTE_WORKFLOW` exists as an explicit node and has integration coverage for Workflow invoking a published Workflow.
- Knowledge retrieval already merges keyword hits and vector chunk recall.
- Agent chat can perform native OpenAI-style function/tool calling against MCP tools.
- Agent can call a bound Workflow through `workflow_id`.

The remaining gaps are not cosmetic:

- Chatflow needs explicit subworkflow verification, especially around session state and interrupt boundaries.
- FAQ support is currently document-block retrieval, not a structured FAQ product.
- Agent tool calling works, but needs conformance hardening so it is reliable as a reusable resource capability.
- Workflow/Chatflow cannot call Agent; there is no `AGENT_CALL` node.

## Product Boundary

- Target product level: commercial customer service base edition.
- Scope includes Web/API customer service scenarios, not full omnichannel enterprise parity.
- Reuses the shared `FlowGraph` schema and `flow_type` split.
- Keeps `EXECUTE_WORKFLOW` as the explicit way to invoke subflows.
- Adds `AGENT_CALL` as an explicit node. It does not make Agent an invisible LLM skill by default.
- Productizes structured FAQ inside the existing Knowledge module.
- Preserves existing document chunk RAG and pgvector behavior.
- Does not implement Dify-style cross-flow dynamic task stack or automatic intent-switch resume.
- Does not implement a Coze plugin marketplace, third-party OAuth onboarding, or full app-store plugin lifecycle.

## Commercial Customer Service Definition

022 is done when a basic customer service operator can:

- create a Chatflow that identifies intent, collects missing information, retrieves FAQ/document knowledge, calls tools, calls a subworkflow, optionally calls an Agent, and transfers to human service;
- publish the Chatflow through Web/API channel profiles;
- expose an API endpoint for external invocation;
- inspect run/debug evidence in the composer surfaces defined by 021;
- manage FAQ entries without turning every Q&A pair into an uploaded document;
- configure tools once and let Agent, Workflow, and Chatflow call them through consistent runtime policy.

## Current Baseline

| Area | Current State | Gap |
|------|---------------|-----|
| `EXECUTE_WORKFLOW` | Implemented as a node; Workflow -> published Workflow has integration tests | Add Chatflow-specific tests and guard nested interrupt behavior |
| Knowledge hybrid retrieval | `KnowledgeFacade.search_chunks()` merges vector and keyword results | Productize structured FAQ and expose source-aware retrieval to Agent/Workflow/Chatflow |
| Agent tool calling | Agent can run two-round function/tool calling through MCP tools | Add conformance tests, policy/evidence consistency, and provider capability UX |
| Agent -> Workflow | Agent has a bound `workflow_id`; chat route invokes that Workflow before final answer | This is fixed binding, not dynamic resource invocation |
| Workflow/Chatflow -> Agent | Not supported | Add explicit `AGENT_CALL` node and runtime facade |

## Capability Matrix

| Caller | Knowledge | MCP Tool | Subworkflow | Agent |
|--------|-----------|----------|-------------|-------|
| Agent | Supported through RAG mode | Supported through native tool calls | Supported only as one bound `workflow_id` mode | N/A |
| Workflow | Supported through `KNOWLEDGE` and LLM resource context | Supported through `TOOL_CALL` and LLM callable tools | Supported through `EXECUTE_WORKFLOW` | Add `AGENT_CALL` |
| Chatflow | Supported through `KNOWLEDGE` and LLM resource context | Supported through `TOOL_CALL` and LLM callable tools | Supported by shared runtime, needs Chatflow tests | Add `AGENT_CALL` |

## Runtime Contracts

### Chatflow `EXECUTE_WORKFLOW` Conformance

`EXECUTE_WORKFLOW` remains an explicit node.

Required Chatflow behavior:

- Target must be a published `WORKFLOW`.
- Target must not be a `CHATFLOW` in this MVP.
- Parent Chatflow session variables remain isolated from child Workflow run inputs unless mapped.
- Child Workflow output is copied back only through declared output mappings.
- Nested run evidence includes `nestedRunId`, status, latency, mapped input summary, mapped output summary, and error.
- Recursive target and excessive depth are rejected.
- If a child Workflow returns `INTERRUPTED`, parent Chatflow fails with a clear unsupported nested interrupt error.
- Chatflow resume checkpoints must not accidentally resume into a child Workflow.

### Structured FAQ Knowledge Base

Current FAQ-like behavior is content inside uploaded documents. 022 adds first-class FAQ entries.

FAQ entry fields:

- `id`
- `knowledge_base_id`
- `question`
- `answer`
- `alternative_questions`
- `keywords`
- `category`
- `priority`
- `enabled`
- `metadata`
- `source`
- `created_at`, `updated_at`

FAQ retrieval behavior:

- Exact question match gets highest priority.
- Keyword match can outrank vector chunk recall when confidence passes threshold.
- FAQ semantic/vector match is supported by embedding FAQ questions and alternatives.
- Document chunks remain available and are merged with FAQ hits.
- Results expose source metadata:
  - `sourceType`: `FAQ` or `DOCUMENT_CHUNK`
  - `matchType`: `EXACT`, `KEYWORD`, `VECTOR`, or `HYBRID`
  - `score`
  - `title`
  - `content`
  - `answer` when source is FAQ
  - `documentId` and `chunkId` when source is document chunk

Runtime integration:

- Agent RAG mode uses the same source-aware retrieval.
- Workflow/Chatflow `KNOWLEDGE` node can return FAQ answers and document snippets.
- LLM resource context can include FAQ answer blocks and document context blocks.
- Citations identify whether a result came from FAQ or document chunk.

Frontend behavior:

- Knowledge detail has tabs for Documents, FAQ, and Retrieval Test.
- FAQ supports manual CRUD.
- FAQ supports CSV import/export in MVP.
- Retrieval Test shows merged FAQ/document hits with scores and match type.

### Agent Native Function Calling Conformance

Agent tool calling is treated as a production runtime path, not a mock convenience.

Required behavior:

- Agent-bound MCP tools serialize into provider-compatible function/tool schema.
- Model capability metadata controls whether tool calling is enabled.
- One model-tool-model round remains MVP default.
- Tool policy includes enabled state, timeout, write-capable confirmation, argument presets, and sanitized evidence.
- Tool execution records call id, tool name, arguments summary, success/error, latency, and returned content summary.
- Agent preview/debug panel and composer debug detail show tool-call evidence.
- If provider does not support tool calls, UI blocks enabling tools or shows an actionable degraded state.

### `AGENT_CALL` Node

`AGENT_CALL` lets Workflow and Chatflow call an existing Agent explicitly.

Node scope:

- Workflow: supported.
- Chatflow: supported with conversation/session context mapping.

Config fields:

- `targetAgentId`
- `messageTemplate`
- `inputMappings`
- `variableMappings`
- `historyMode`: `none`, `current_flow`, `external`
- `sessionMode`: `ephemeral`, `reuse_chatflow_session`
- `outputFormat`: `text`, `json`
- `outputMappings`
- `timeoutMs`
- `maxDepth`
- `errorBehavior`: `fail`, `continue`, `branch`
- `outputParameters`

Runtime behavior:

- Resolves mapped inputs and renders `messageTemplate`.
- Invokes Agent through an internal `AgentInvocationFacade`.
- Uses the Agent's configured provider, knowledge, tools, and bound workflow behavior unless blocked by recursion policy.
- Returns selected output mappings to downstream nodes.
- Records nested agent run evidence.
- Rejects cycles:
  - Workflow -> Agent -> same Workflow.
  - Chatflow -> Agent -> same Chatflow once Chatflow binding exists.
  - Agent -> Workflow -> Agent loops.
- Enforces max depth across Agent and Workflow nested invocations.

Output:

- `content`
- `agentRunId`
- `status`
- `toolCalls`
- `knowledgeReferences`
- `workflowRunId` when the Agent used its bound Workflow
- `error`

## Resource Registry Changes

The Workflow resource registry must include Agent resources:

- `resourceType`: `AGENT`
- `resourceId`: `agent:{id}`
- `displayName`
- `description`
- `enabled`
- `inputSchema`
- `outputSchema`
- `capabilities`: `agent_call`, `rag`, `tool_call`, `workflow_binding`
- `runtimeStatus`
- `disabledReason`

Agents are selectable in `AGENT_CALL`, not inside LLM `skills` for this MVP.

## API Surface

Backend endpoints may follow existing router conventions, but behavior must include:

- FAQ:
  - list/create/update/delete FAQ entries under a knowledge base.
  - import/export FAQ CSV.
  - retrieval test returning FAQ and chunk hits.
- Agent invocation:
  - internal facade for `AGENT_CALL`.
  - optional internal debug endpoint for selected-node testing.
- Resources:
  - workflow resource registry includes Agent resources.
- Published run debug:
  - output remains compatible with 021 composer debug URLs.

## Frontend Behavior

- Workflow/Chatflow palette exposes `调用 Agent` after runtime exists.
- `AGENT_CALL` node card shows target Agent, message source, output variable names, and error policy.
- Right config panel follows the Coze-style section layout already used by flow nodes.
- Knowledge page gains FAQ tab and retrieval test tab.
- LLM node skills section continues to show tools and knowledge; Agents are not shown as LLM skills in this MVP.
- Debug dock shows nested Agent, tool, workflow, and knowledge calls in one timeline.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 022.1 Capability conformance inventory | Tests lock current working behavior and document gaps | RED: missing conformance tests fail; Unit/Integration: current EXECUTE_WORKFLOW, RAG, tool-call paths covered |
| 022.2 Chatflow subworkflow conformance | Chatflow can call published Workflow safely through `EXECUTE_WORKFLOW` | RED: Chatflow subworkflow test fails; Integration: nested run, output mapping, recursion, nested interrupt block |
| 022.3 Structured FAQ knowledge product | FAQ CRUD/import/retrieval merges with document chunks | RED: FAQ model/API/retrieval tests fail; Integration: FAQ outranks chunks when appropriate; E2E: FAQ tab and retrieval test |
| 022.4 Agent tool-call hardening | Agent function calling is policy-driven and observable | RED: provider capability/policy/evidence tests fail; Integration: two-round tool flow and disabled provider state |
| 022.5 `AGENT_CALL` node | Workflow/Chatflow can explicitly invoke Agent and map outputs | RED: AGENT_CALL executor tests fail; Integration: nested agent run, recursion guard, selected-node test |
| 022.6 Customer service end-to-end scenario | One published Chatflow uses FAQ, tool, subworkflow, Agent call, and handoff | RED: E2E scenario fails; Integration/E2E/Browser UAT: full customer service path with debug evidence |

## Evidence

Each slice must save evidence under:

```text
artifacts/slices/022-customer-service-runtime-parity/{slice-id}/
├── red.txt
├── unit.txt
├── integration.txt
├── e2e.txt
├── uat.md
└── screenshots/
```

## Done Criteria

022 is done when:

- `EXECUTE_WORKFLOW` is verified for Chatflow, not only Workflow.
- Structured FAQ is a first-class Knowledge product surface and retrieval source.
- Agent native function calling has policy, provider capability, and debug evidence parity.
- Workflow and Chatflow can call Agent through `AGENT_CALL`.
- A published customer service Chatflow can combine FAQ, tool calls, subworkflow, Agent call, interrupt/resume, transfer-to-human, and composer debug inspection.
- Remaining gaps are explicitly future-scoped: task stack, full plugin marketplace, third-party channel parity, and multi-agent orchestration.
