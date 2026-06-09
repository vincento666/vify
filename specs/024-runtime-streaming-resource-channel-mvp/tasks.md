# Tasks 024: Runtime Streaming, API Resources, and Channel MVP

## 024.1 Streaming/typewriter run events

- [x] RED: add failing unit tests for stream accumulator final-value semantics.
- [x] RED: add failing integration test for Chatflow `MESSAGE`/`END` streaming events.
- [x] Add stream event DTOs: `message_delta`, `message_done`, `llm_delta`, `stream_error`, `node_usage`.
- [x] Add stream accumulator that records deltas and final accumulated content.
- [x] Wire Chatflow `MESSAGE` output into the backend stream event projection.
- [x] Wire Chatflow `LLM` output through the accumulator when provider streaming is available or fake-stream fallback is enabled.
- [x] Wire Chatflow `INFORMATION_COLLECTION` follow-up output through the accumulator.
- [x] Wire `END` final reply output into the backend stream event projection for Chatflow-visible responses.
- [x] Guarantee downstream variables only receive final accumulated values.
- [x] Add frontend debug drawer rendering for progressive chunks and final output.
- [x] Add full Chatflow test panel typewriter rendering.
- [x] Integration green: Chatflow run emits deltas and final output.
- [x] E2E green: node test and full run show streaming then final result.
- [x] Browser UAT: capture typewriter/debug screenshots.
- [x] Save evidence under `artifacts/slices/024-runtime-streaming-resource-channel-mvp/024.1/`.
- [x] Gates pass.

## 024.2 Node usage and cost evidence

- [x] RED: add failing tests for normalized node evidence usage fields.
- [x] Add usage DTO fields: `inputTokens`, `outputTokens`, `totalTokens`, `costEstimate`, `usageEstimated`.
- [x] Map exact provider usage when available.
- [x] Add fallback token estimate for text-only node output.
- [x] Add cost estimate helper using provider/model config when pricing exists; otherwise return null with `usageEstimated=true`.
- [x] Record usage evidence for LLM nodes.
- [x] Record latency/resource evidence for Knowledge, API, Tool, Subworkflow, Agent, Message, Question, Information Collection, and End nodes where applicable.
- [x] Sanitize input/output summaries before exposing run evidence.
- [x] Add frontend per-node usage row in run detail.
- [x] Add observe/debug compatibility projection so existing run detail still opens.
- [x] Integration green: representative LLM/API/TOOL/KNOWLEDGE run records usage/evidence.
- [x] E2E green: run detail shows token/cost/latency per node.
- [x] Browser UAT: capture run detail evidence.
- [x] Save evidence under `artifacts/slices/024-runtime-streaming-resource-channel-mvp/024.2/`.
- [x] Gates pass.

## 024.3 API Resource and Tool Builder Lite

- [x] RED: add failing API Resource CRUD contract tests.
- [x] RED: add failing API Resource test-call integration test.
- [x] RED: add failing API-backed Tool invocation through `TOOL_CALL`.
- [x] Add API Resource table/model with name, endpoint/base URL, method, auth mode, headers/body templates, schemas, timeout, enabled state.
- [x] Add API Resource CRUD routes under `/api/v1/api-resources`.
- [x] Add API Resource test-call endpoint with sanitized request/response evidence.
- [x] Add Tool Builder Lite model or extend existing resource registry to create API-backed Tools.
- [x] Add Tool CRUD/list route or registry endpoint that exposes API-backed Tools with business name/description/schema.
- [x] Add API Resource invocation adapter behind `TOOL_CALL`.
- [x] Keep direct `API_CALL` behavior unchanged.
- [x] Let `API_CALL` optionally reference an API Resource while preserving direct endpoint fields.
- [x] Let LLM Skills picker show only published/model-callable Tools, not raw API Resources.
- [x] Let LLM Skills picker group resource choices by type with tabs/search/scroll, not one mixed dropdown.
- [x] Add frontend API Resource list/create/edit/test surface.
- [x] Add frontend Tool Builder Lite surface for wrapping an API Resource.
- [x] Add canvas `TOOL_CALL` selector support for API-backed Tools.
- [x] Integration green: create API Resource -> wrap Tool -> call from Workflow/Chatflow.
- [x] E2E green: API-backed Tool can be selected and run.
- [x] Browser UAT: capture API Resource test and canvas invocation.
- [x] Save evidence under `artifacts/slices/024-runtime-streaming-resource-channel-mvp/024.3/`.
- [x] Gates pass.

## 024.4 Channel profile adapter registry

- [x] RED: add failing tests for channel descriptor registry and API/Web compatibility.
- [x] Add channel adapter descriptor model with id, display name, runnable flag, config schema, delivery capabilities, unavailable reason.
- [x] Wrap current API/Web adapters in the descriptor registry.
- [x] Keep disabled Feishu/DingTalk/WeCom/WeChat shells as descriptors with unavailable reasons.
- [x] Keep existing Chatflow channel config table and service API compatible.
- [x] Normalize inbound channel requests to `sys.query`, `sys.channel`, `sys.channel_id`, `sys.conversation_id`, `sys.user_id`, `sys.files`, and `channel.metadata`.
- [x] Add delivery capability flags: sync, streaming, files, cards.
- [x] Ensure channel test records delivery/evidence with channel id and conversation id.
- [x] Add frontend channel profile display using registry descriptors.
- [x] Add channel test UI compatibility for existing API/Web channels.
- [x] Integration green: API/Web channel profile test still runs and records normalized input.
- [x] E2E green: publish Chatflow, test API/Web channel, open debug detail.
- [x] Browser UAT: capture channel profiles and test result.
- [x] Save evidence under `artifacts/slices/024-runtime-streaming-resource-channel-mvp/024.4/`.
- [x] Gates pass.

## Final gate

- [x] Full backend unit/integration/contract suite green.
- [x] Full frontend unit suite green.
- [x] Relevant E2E suite green.
- [x] Browser UAT evidence saved.
- [x] `spec.md`, `plan.md`, and `tasks.md` updated with final evidence.
- [x] `specs/README.md` remains ordered and accurate.
