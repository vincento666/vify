# Spec 015: Core Flow Nodes MVP

## Goal

Add the next group of high-value Workflow and Chatflow nodes after the existing nodes and visual canvas pass, aligned with the live Coze add-node palette where runtime boundaries are clear: CODE, TEXT_PROCESS, JSON_PARSE, VARIABLE_AGGREGATION, VARIABLE_ASSIGN, INTENT_RECOGNITION, MESSAGE, QUESTION, HUMAN_INPUT, and INFORMATION_COLLECTION.

## Product Boundary

- This spec starts only after 011/012 current-node canvas, config panel, variable selector, validation, and test run are passing.
- It extends the shared FlowGraph/runtime profile architecture.
- It does not implement Dify-style Task Stack or cross-flow dynamic intent switching.
- It does not implement full Coze node form depth unless the field is backed by runtime behavior.
- It does not hide runtime-heavy resource calls inside the LLM node unless their evidence, limits, and failure behavior are implemented.
- It defines node-level streaming output semantics and config switches for Chatflow-visible message/model output, but it does not implement full public channel streaming delivery. Channel transport, Web/API delivery, and production observe aggregation are completed in 018/019.
- It does not expose live Coze palette entries as runnable just because they appear in the add-node menu. Plugin, workflow/subflow, loop, batch, async, database CRUD, and knowledge write/search entries need explicit runtime contracts and gates before being enabled.

## Live Coze Palette Alignment

The 2026-06-01 in-app browser audit of the Coze workflow canvas observed these add-node labels:

- Top/resource: `大模型`, `插件`, `工作流`.
- Business logic: `代码`, `选择器`, `意图识别`, `循环`, `批处理`, `变量聚合`, `异步任务`.
- Input/output: `输入`, `输出`.
- Database: `SQL自定义`, `新增数据`, `更新数据`, `查询数据`, `删除数据`.
- Knowledge/data: `知识库写入`, `知识库检索`.

Hify mapping decisions:

- Existing 011 nodes cover `输入`, `输出`, `大模型`, current `CONDITION` as the user-facing `选择器`, and current `KNOWLEDGE` as `知识库检索`.
- 015 enables `代码`, `意图识别`, and `变量聚合` when runtime-backed.
- `VARIABLE_ASSIGN` is not the same as Coze `变量聚合`: aggregation normalizes values from branches/upstream nodes for downstream use; assignment writes a value into a supported scope. Keep both names separate in code and tests.
- `插件`, `工作流`, `循环`, `批处理`, `异步任务`, database CRUD, and `知识库写入` remain disabled/later-stage unless their executor, validation, persistence, and UAT gates are specified.
- Chatflow-only MESSAGE/QUESTION/HUMAN_INPUT/INFORMATION_COLLECTION are not proven by this Workflow-route screenshot; they remain in 015 based on Chatflow runtime requirements and must receive separate Chatflow browser evidence before being marked complete.

## Node Boundary

| Node | Workflow | Chatflow | Behavior |
|------|----------|----------|----------|
| CODE | Yes | Yes | Deterministic transform with bounded execution and declared outputs |
| JSON_PARSE | Yes | Yes | Parses LLM/API/code JSON string into structured outputs |
| TEXT_PROCESS | Yes | Yes | Concatenate/extract/replace/format text |
| VARIABLE_AGGREGATION | Yes | Yes | Aggregates/normalizes one or more upstream values, especially branch outputs, into declared outputs |
| VARIABLE_ASSIGN | Yes | Yes | Writes selected input value to flow/global/conversation/user/channel scope when supported |
| INTENT_RECOGNITION | Limited | Yes | LLM-driven semantic branch with intent ports plus default |
| MESSAGE | No | Yes | Emits a message, like Dify Answer, does not wait |
| QUESTION | No | Yes | Emits a question, waits for answer, can branch by answer/option |
| HUMAN_INPUT | Yes | Yes | Explicit human pause/input/approval |
| INFORMATION_COLLECTION | No | Yes | LLM-driven multi-turn slot collection with missing-field follow-up |

## Required Node Runtime Pattern

Every node added here must include:

- Coze-like node card and dynamic ports when needed.
- Minimal runtime-backed config panel.
- Variable selector support.
- Validator.
- Executor or Chatflow runtime profile adapter.
- Run evidence rendering.
- Unit and integration tests.

## Unified Resource Invocation Boundary

Hify uses a shared resource picker language for Knowledge Bases, MCP tools, and subworkflows, but invocation rules differ:

- Knowledge Base as LLM context: allowed after 011/012 basic controls because `KnowledgeFacade.search_chunks` already exists and can provide retrieved text as prompt context.
- MCP Tool as LLM callable tool: requires OpenAI-compatible tool schemas, tool-call parsing, MCP execution, second LLM round, timeout/error policy, and run evidence. Chat already has this path; Workflow/Chatflow LLM nodes still need node-level resource binding before it is product behavior.
- Subworkflow as callable resource: requires an explicit `EXECUTE_WORKFLOW` style node or later equivalent, input/output mapping, nested run records, recursion guard, and timeout/error policy.
- Imageflow appears in Coze's skill vocabulary, but Hify has no current imageflow runtime and must not expose it in MVP as runnable.

Do not make MCP tools or subworkflows look runnable from the LLM Skills section before those runtime contracts exist.

## Chat History Awareness

LLM-driven Chatflow nodes can expose a "chat history awareness" option:

- Applies to INTENT_RECOGNITION, INFORMATION_COLLECTION, QUESTION answer parsing, and future LLM-like chat nodes.
- Config fields: enabled, max rounds, input source.
- History is read from Chatflow test/run profile, not from Workflow by default.
- UI label must not confuse history with Global Variable.

## Streaming Output Boundary

Streaming is required for a customer-service Chatflow MVP because users expect model answers and message output to appear progressively. 015 includes node-level streaming controls and event semantics:

- Supported nodes:
  - existing LLM node when used in Chatflow profile.
  - MESSAGE node.
  - INFORMATION_COLLECTION follow-up output when the follow-up is LLM-generated.
- Optional for Workflow runs: Workflow can show streaming in test/debug surfaces, but downstream Workflow nodes always receive the final accumulated output value, never partial chunks.
- Config fields:
  - `streamOutput`: inherit, enabled, disabled.
  - `streamTarget`: message, debug-only. Chatflow defaults to message when the run/channel supports streaming.
  - `fallbackMode`: aggregate when streaming is unsupported or provider fails to stream.
- Runtime events:
  - `message_delta`: user-visible text chunk.
  - `message_done`: final user-visible message content.
  - `llm_delta`: model-visible/debug chunk for LLM nodes when not directly user-visible.
  - `stream_error`: stream failed and either fell back to aggregate output or failed the node according to node error policy.
- Downstream contract:
  - Partial chunks are events only.
  - Node outputs and downstream variable references are populated only after the final accumulated value is available.
  - JSON output mode does not expose partial JSON as a downstream variable; it emits debug chunks and parses only the final accumulated content.
- UI behavior:
  - Right panel shows a streaming switch only on nodes whose runtime can emit stream events.
  - Node-test drawer can display progressive chunks and still render the final `输出` block.
  - Full Chatflow test panel can display user-visible streaming while preserving final run evidence.
- Transport boundary:
  - 015 defines and tests events in local run/test surfaces.
  - 018 persists streaming events into Chatflow session timelines.
  - 019 maps streaming events to Web/API/channel delivery.

## Node Contracts

### CODE

- Scope: Workflow and Chatflow.
- Config: input mappings, language, code body, output schema, timeout.
- Runtime: bounded deterministic execution.
- Output: declared variables only.
- MVP restriction: no external network, file system, or custom dependency loading.

### TEXT_PROCESS

- Scope: Workflow and Chatflow.
- Config: input text, operation, operation parameters, output variable.
- Operations: concatenate, extract by regex, replace, trim, format template.
- Runtime: deterministic string transform.
- Output: text and optional match metadata.

### JSON_PARSE

- Scope: Workflow and Chatflow.
- Config: source variable/string, parse mode, optional field map, output variable.
- Runtime: strict JSON parse first. Repair/LLM repair is future work unless separately specified.
- Output: parsed object, parse status, error message on failure, and mapped fields when configured.
- Relationship: JSON_PARSE prepares structured data; VARIABLE_AGGREGATION can normalize branch outputs, and VARIABLE_ASSIGN writes chosen data into variable scopes.

### VARIABLE_AGGREGATION

- Scope: Workflow and Chatflow.
- User-facing label: `变量聚合`.
- Config: one or more source values, merge strategy, fallback/default value, output variable schema.
- Runtime: deterministic aggregation/normalization of upstream values; it does not write durable scoped variables.
- Output: declared aggregate variable plus per-source status where useful.
- Relationship: use after branch/selector/intent paths to produce one downstream variable name.

### VARIABLE_ASSIGN

- Scope: Workflow and Chatflow.
- Config: target scope, target variable, source value, write mode.
- Runtime: writes an existing value, never parses JSON.
- MVP scopes:
  - Workflow: flow-level temporary variables.
  - Chatflow: conversation/user/channel mock or configured variable scopes as available.
- Write modes: set, append for array/string where supported, clear.
- Advanced config: optional direct write targets for INFORMATION_COLLECTION completion.

### INTENT_RECOGNITION

- Scope: Chatflow first; Workflow allowed only when explicit one-shot semantic routing is needed.
- Config: input source, intents with name/description/examples, fallback/default branch, chat history awareness.
- Ports: one output port per intent plus default.
- Runtime: LLM-driven semantic classification. Tests may use deterministic fake classifier.
- Output: selected intent, optional confidence, optional reason.
- Difference from CONDITION: CONDITION evaluates deterministic expressions; INTENT_RECOGNITION evaluates semantic intent.

### MESSAGE

- Scope: Chatflow only.
- Product equivalent: Dify Answer node; Coze stream Message event for message/end-like output nodes.
- Config: content template, variable references, output format, streaming mode, fallback mode.
- Runtime: emits message events and continues immediately after the final message value is produced.
- Output: emitted content, message id if available.
- Does not trigger interrupt/resume and does not wait for user input.

### QUESTION

- Scope: Chatflow only.
- Config: question content, answer type, options or field schema, output variable, validation rules, branch mapping, timeout/default.
- Runtime: emits a question and interrupts the current flow until user reply/resume data arrives.
- Ports: continue/default plus optional answer/option ports.
- Output after resume: answer, normalized answer, selected option, validation status.
- Difference from MESSAGE: QUESTION changes control flow and requires resume.

### HUMAN_INPUT

- Scope: Workflow and Chatflow.
- Config: prompt, input schema, assignee/role placeholder, approval mode, output variable.
- Runtime: explicit pause for manual input or approval.
- Output after resume: human input payload, approved/rejected status.
- Difference from INFORMATION_COLLECTION: no automatic extraction from conversation text.

### INFORMATION_COLLECTION

- Scope: Chatflow only.
- Config:
  - fields: name, type, required, description, examples, validation hint.
  - input source: current message by default.
  - chat history awareness: enabled, max rounds.
  - state: collection key, max collection rounds.
  - completion: output variable; optional direct variable writes in advanced config.
- Runtime:
  - Reads current user message and optional history.
  - Extracts fields through LLM/fake extractor.
  - Merges extracted values with previous collected state.
  - Detects missing required fields.
  - Emits focused follow-up message/question when incomplete, optionally through streaming message events.
  - Continues collection after resume until complete or max rounds.
  - On completion, outputs structured collected data; optional advanced direct writes can target Conversation/User variables.
- Output:
  - `collected`: object of current values.
  - `missing`: required fields still missing.
  - `complete`: boolean.
  - `followup`: message/question text when incomplete.
  - `errors`: validation issues.
- Difference from QUESTION: QUESTION waits for one answer; INFORMATION_COLLECTION manages multi-field state across turns.

## Information Collection Requirements

INFORMATION_COLLECTION is a Chatflow-first node for intelligent slot filling:

- Configured fields: name, type, required, description, examples, validation hint, target variable.
- Runtime reads current user message and optional chat history.
- Runtime extracts known fields, merges with previous collected state, identifies missing required fields, asks a focused follow-up, and repeats until complete or max rounds reached.
- Output includes collected fields, missing fields, completion status, and prompt message when incomplete.
- Default completion outputs structured results. Advanced config may write directly to Conversation/User variables; otherwise use VARIABLE_ASSIGN.
- This node is not a stateless one-shot extraction form.

## JSON Parse Requirements

JSON_PARSE is separate from VARIABLE_ASSIGN:

- Input: string or object from upstream node.
- Modes: strict parse first; repair/LLM repair may be later.
- Config: source, expected schema or field map, output variable names.
- Output: parsed object and optional individual fields.
- VARIABLE_AGGREGATION can normalize parsed or branch-specific fields for downstream use.
- VARIABLE_ASSIGN can then write parsed or aggregated fields into supported scopes.

## Message / Question Boundary

- MESSAGE sends content and continues immediately.
- QUESTION sends content and waits for user reply.
- MESSAGE can stream user-visible chunks; QUESTION may stream only its question text before emitting the interrupt event.
- They may share UI components, but remain separate node types because QUESTION changes runtime control flow, output variables, and branch ports.
- Dify Answer is treated as equivalent to Hify MESSAGE, not QUESTION.
- Coze Message events represent output from message/end-like nodes; Coze Interrupt events represent waiting behavior and resume contract.

## Event Model

New Chatflow nodes use the shared run records plus profile-level events:

- `message`: emitted by MESSAGE and by INFORMATION_COLLECTION follow-up output.
- `message_delta`: emitted when MESSAGE, Chatflow LLM output, or INFORMATION_COLLECTION follow-up streams user-visible chunks.
- `message_done`: emitted when the final user-visible message is complete.
- `llm_delta`: emitted for debug/model-visible streaming chunks when not directly user-visible.
- `stream_error`: emitted when a streaming provider/path fails before final aggregation.
- `interrupt`: emitted by QUESTION, HUMAN_INPUT, and incomplete INFORMATION_COLLECTION.
- `resume`: resumes the same flow run from an interrupt event.
- `done`: emitted when the flow completes.
- `error`: emitted when node validation or runtime execution fails.

The MVP does not support cross-flow task switching; interrupt/resume is bound to the same flow run.

## Intent Recognition Requirements

INTENT_RECOGNITION is LLM-driven semantic routing, not a rule-only condition:

- Config: input source, intents, description, examples, fallback/default.
- Output ports: one per intent plus default.
- Output: selected intent, optional confidence/reason.
- In replica phase, tests may use deterministic fake LLM behavior; product semantics remain LLM-driven.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 015.1 Data transform nodes | CODE, TEXT_PROCESS, JSON_PARSE work in Workflow and Chatflow | RED: transform tests fail; Unit: executors/parsers; Integration: run records; E2E: canvas run; UAT: outputs visible |
| 015.2 Variable aggregation and assignment | VARIABLE_AGGREGATION normalizes upstream values; VARIABLE_ASSIGN writes current supported scopes and shows scope selector | RED: aggregation/assignment tests fail; Unit: aggregator and scope resolver; Integration: persisted/mock variables; E2E: aggregate or assign then use; UAT: selector visible |
| 015.3 LLM intent branch | INTENT_RECOGNITION creates dynamic ports and routes by fake/LLM intent | RED: branch test fails; Unit: intent picker; Integration: node run; E2E: branch output; UAT: correct branch state |
| 015.4 Chat message/question/input | MESSAGE, QUESTION, HUMAN_INPUT render and pause/continue as runtime supports; MESSAGE supports streaming config and final aggregation | RED: interrupt/streaming tests fail; Unit: event model; Integration: resume contract; E2E: ask/answer/stream; UAT: wait and stream states visible |
| 015.5 Smart info collection | INFORMATION_COLLECTION supports multi-turn slot filling with history option and optional streaming follow-up output | RED: slot-fill test fails; Unit: slot merger; Integration: checkpoint/mock state; E2E: missing-field follow-up; UAT: completion and streaming follow-up visible |

## Evidence

- Coze Studio API Reference: Message event is output from message/end-like nodes; Interrupt event carries `event_id/type` and resume data. Chatflow API accepts `additional_messages`, and `USER_INPUT` is passed there rather than normal parameters.
- Coze live add-node audit: `artifacts/research/coze-workflow/spec-011-015-live-audit-20260601.md`.
- Coze Studio backend node guide: branch-capable nodes include condition, intent recognition, and question answering; node input/output are `map[string]any`.
- Coze Studio frontend node guide: dynamic ports and node form are explicit extension points.
- Dify Workflow & Chatflow docs: both use a shared visual canvas and node system; Workflow ends with Output, Chatflow ends with Answer.
- Dify Answer docs: Answer delivers content in Chatflow applications and can include variable substitution and dynamic content.
- Dify key concepts: Chatflow adds conversation-specific variables, memory in LLM nodes, and streaming formatted outputs; variable references use dropdown/slash insertion.
- Qianfan info collection node: information collection asks users, collects answers, outputs replies/history/extraction result, and uses interrupt/resume.
- Feishu Aily global variables: query, files, message, messageHistory, session, and channel show chat-context and channel variables for conversational workflows.
