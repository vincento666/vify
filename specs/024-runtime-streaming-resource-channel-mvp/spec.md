# Spec 024: Runtime Streaming, API Resources, and Channel MVP

## Goal

Close the highest-priority Workflow/Chatflow runtime-product gaps that are easy
to ship without redesigning the whole platform:

- Chatflow-visible streaming/typewriter output;
- node-level token/cost/runtime evidence;
- API configuration as a reusable resource, then invocation from the canvas;
- multi-channel publish profiles that extend the current API/Web logic.

The goal is commercial customer-service usability, not full Coze parity. The
spec keeps the current shared FlowGraph runtime, current Workflow/Chatflow
tables, current `/api/v1/...` envelope, and current channel/run APIs
compatible.

## Product Boundary

In scope:

- streaming events for Chatflow-visible model/message/end output;
- debug and published-channel delivery of progressive text when supported;
- final accumulated output remains the only downstream variable value;
- node-level usage/evidence fields for LLM, Agent, Tool, Knowledge, API,
  Subworkflow, Message, Question, Information Collection, and End where
  applicable;
- reusable API Resource management with validation and test call;
- Tool Builder Lite that can wrap an API Resource as a business tool;
- `TOOL_CALL` invocation of API-backed tools;
- existing direct `API_CALL` remains available for compatibility and advanced
  one-off HTTP calls;
- channel profile configuration deepened from current API/Web shells, plus
  adapter registration for future Feishu/DingTalk/WeCom/WeChat.

Out of scope:

- full plugin marketplace;
- database CRUD node;
- identity verification and privacy policy engine;
- full Coze model/plugin/auth field depth;
- full third-party channel credential handshakes;
- Dify-style cross-flow task stack;
- speculative resources that cannot be invoked or tested.

## Current Baseline

| Area | Current State | Gap |
|------|---------------|-----|
| Streaming | Chat has SSE; `MESSAGE` and `INFORMATION_COLLECTION` have event-shaped output in runtime | Chatflow node test, full run, End node, and published channel delivery are not consistently typewriter-aware |
| Usage evidence | Chat stores token counts; provider adapters parse some usage; Workflow node runs mainly store input/output/status/latency | Node-level token/cost/evidence is not normalized across Workflow/Chatflow resources |
| API calls | `API_CALL` config lives inside a canvas node | No reusable API Resource with auth/test/schema/reuse, and no business Tool wrapper |
| Tools | MCP/internal tools and Tool Call runtime exist | API-backed business tools are not first-class resources |
| Channels | Chatflow has API/Web runnable shells and disabled third-party shells | Channel adapters are not yet a product-extensible registry with delivery/evidence parity |

## Product Decisions

### Streaming/typewriter

- Streaming is a Chatflow user-experience feature first.
- Workflow may display debug-only progressive chunks, but Workflow downstream
  variables always receive the final value.
- JSON output mode must not expose partial JSON as variables.
- When a provider/channel cannot stream, runtime falls back to aggregate output
  and records the fallback in evidence.

Supported initial event types:

- `message_delta`;
- `message_done`;
- `llm_delta`;
- `stream_error`;
- `node_usage`;

Supported initial nodes:

- Chatflow `LLM`;
- `MESSAGE`;
- `INFORMATION_COLLECTION` follow-up output;
- `END`;
- node-test drawers and full Chatflow test panel;
- API/Web published channel responses when the transport supports streaming.

### Node-level token/cost evidence

Every node run should expose a common evidence projection:

- `nodeKey`;
- `nodeType`;
- `status`;
- `latencyMs`;
- `inputSummary`;
- `outputSummary`;
- `errorSummary`;
- `inputTokens`;
- `outputTokens`;
- `totalTokens`;
- `costEstimate`;
- `resourceType`;
- `resourceId`;
- `events`;

Usage can be exact when the provider returns usage, or estimated when only text
is available. Evidence must make exact vs estimated clear.

### API Resource vs Tool

API Resource is a technical integration definition:

- base URL or endpoint;
- method;
- authentication mode;
- headers/body templates;
- input schema;
- output mapping;
- timeout;
- test payload;
- risk classification placeholder for future policy specs.

Tool is a business capability wrapper:

- user-facing name and description;
- input/output schema in business terms;
- backing adapter: API Resource, MCP tool, internal adapter, or future
  subworkflow;
- model-callable flag;
- default timeout/retry/error behavior;
- sanitized invocation evidence.

Canvas behavior:

- `API_CALL` can still configure a direct HTTP request for compatibility.
- `API_CALL` can optionally reference an API Resource and override safe fields.
- `TOOL_CALL` can choose API-backed tools just like MCP-backed tools.
- LLM Skills can only bind published Tools marked `modelCallable=true`, not raw
  API Resources.
- LLM Skills UI groups selectable resources by product type first: API-backed
  Tool, MCP Tool, Knowledge, Subworkflow, and Agent. Each group exposes search
  and scrolling; raw mixed-resource dropdowns are not acceptable for large
  installations.

### Multi-channel compatibility

- Creation remains flow-type based: Workflow vs Chatflow.
- Channel selection remains a publish/profile decision.
- Current API/Web adapters stay runnable and compatible.
- Existing disabled Feishu/DingTalk/WeCom/WeChat shells become adapter
  descriptors with explicit unavailable reasons until credentials and
  signatures are implemented.
- All channel inbound requests normalize to:
  - `sys.query`;
  - `sys.channel`;
  - `sys.channel_id`;
  - `sys.conversation_id`;
  - `sys.user_id`;
  - `sys.files`;
  - `channel.metadata`.

## Slices

| Slice | User Value | Acceptance Gate |
|-------|------------|-----------------|
| 024.1 Streaming/typewriter run events | Chatflow authors and testers see progressive output for model/message/end replies | RED: streaming event tests fail; Unit: stream accumulator; Integration: Chatflow run emits deltas and final output; E2E/UAT: debug panel shows typewriter |
| 024.2 Node usage and cost evidence | Operators can inspect token/cost/latency per node | RED: evidence projection lacks usage; Integration: LLM/Tool/API/Knowledge nodes record usage/evidence; E2E/UAT: run detail shows per-node usage |
| 024.3 API Resource and Tool Builder Lite | Users configure APIs once and call them from Workflow/Chatflow | RED: API resource CRUD/test and API-backed Tool call fail; Integration: Tool Call invokes API Resource; E2E/UAT: resource created, tested, selected, run |
| 024.4 Channel profile adapter registry | Chatflows publish to API/Web with a path ready for more channels | RED: channel adapter descriptor tests fail; Integration: API/Web profiles normalize inputs and record deliveries; E2E/UAT: publish profile and test channel still work |

## Completion Evidence

- 024.1 complete: `artifacts/slices/024-runtime-streaming-resource-channel-mvp/024.1/`.
- 024.2 complete: `artifacts/slices/024-runtime-streaming-resource-channel-mvp/024.2/`.
- 024.3 complete: `artifacts/slices/024-runtime-streaming-resource-channel-mvp/024.3/`
  contains RED, unit, integration, E2E, build, Browser UAT JSON, and screenshots.
- 024.4 complete: `artifacts/slices/024-runtime-streaming-resource-channel-mvp/024.4/`
  contains RED, unit/integration regressions, E2E, build, Browser UAT JSON, and
  screenshots.
- Final gate complete: `artifacts/slices/024-runtime-streaming-resource-channel-mvp/final-gate/`
  contains frontend unit/build, backend workflow unit/integration, relevant E2E,
  Browser UAT summary, and screenshots.

## Success Criteria

- Existing Workflow/Chatflow creation, execution, publish, and channel test APIs
  stay compatible.
- A Chatflow can stream a user-visible answer in test/debug and still store a
  final output value for downstream variables.
- Run evidence can answer "which node spent tokens/cost/time and which resource
  did it call?"
- A user can create an API Resource, wrap it as a Tool, call it via `TOOL_CALL`,
  and view sanitized invocation evidence.
- API/Web channel profiles still work, and future channel adapters can be added
  without changing the core runtime.
