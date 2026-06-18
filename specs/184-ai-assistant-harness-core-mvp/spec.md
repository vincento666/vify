# Spec 184: AI Assistant Harness Core MVP

## Goal

Build the first reusable AI Assistant harness module for Hify: a safe,
replayable, eventful assistant run that can accept an operator message, execute
controlled read-only tooling, persist visible execution events, expose approval
boundaries, and render the first non-CLI product shell with a left conversation
list, center execution timeline, and right run/task inspector.

This spec covers only PRD Phase 0 through Phase 3. PRD Phase 4 through Phase 7
are explicitly split into the follow-up specs recorded below.

## Why This Spec Exists

The existing customer-assistant runtime already proves task ledger, worker,
proposed-action, event, and sub-agent concepts for customer-service workflows.
Those concepts are valuable, but they are currently coupled to the
customer-assistant product surface.

184 creates a smaller generic harness layer first:

```text
operator message
  -> prompt assembly
  -> deterministic MVP model/tool decision
  -> permission/sandbox boundary
  -> typed tool registry dispatch
  -> durable event stream
  -> assistant answer
  -> run/task inspector state
```

The module must stay small enough to validate the kernel before migrating the
customer-assistant follow-up/Q&A shell onto it.

## Product Boundary

In scope:

- new `ai_assistant` backend module;
- independent `/api/v1/ai-assistant/...` API surface;
- database-backed session, run, message, event, tool-call, approval,
  proposed-action, task, trace-span, and memory-item models where needed by
  Phase 0 through Phase 3;
- read-only Tool Registry with typed manifests, JSON schema metadata, timeout,
  risk level, read/write resource declarations, and policy references;
- deterministic/mock harness loop using `reason -> validate -> act -> observe
  -> final`;
- durable event persistence and replay;
- minimal sandbox, permission, approval, risk, audit, and proposed-action
  boundary;
- canonical execution echo events for conversation rendering;
- frontend AI Assistant shell with conversation list, center event timeline,
  approval/tool cards, and right run/task inspector;
- tests and evidence for RED, unit, integration, contract, E2E, browser UAT,
  frontend unit, and remScaleClosure gates.

Out of scope:

- PRD Phase 4 read/write scheduler and RWMutex implementation in spec 187;
- PRD Phase 5 AGENTS.md, skills, memory, and compaction implementation in
  spec 188;
- PRD Phase 6 customer-assistant subagent bridge implementation in spec 189;
- PRD Phase 7 observability, benchmark, replay, and governance platform in
  spec 190;
- automatic business writes;
- replacing the customer-assistant runtime;
- generic workflow designer or agent-builder UI;
- exposing hidden chain-of-thought;
- live LLM dependency for default tests or gates.
- SQLite or PostgreSQL persistence paths for this module; relational
  persistence and tests must target MySQL8.

## Phase Scope

### Phase 0: Minimal Harness Kernel

Acceptance:

- an operator can create an AI Assistant session;
- the operator can send one message to a session;
- the harness creates a run and persists user/assistant messages;
- a read-only tool can be selected through the Tool Registry;
- tool input, output, status, and duration are persisted as tool calls and
  events;
- the run returns a final assistant answer;
- event replay returns the same visible execution history;
- no real business writes occur.

### Phase 1: Security Sandbox And Approval Boundary

Acceptance:

- read-only allowed tools run without approval under `smart_approval`;
- high-risk writes pause with an `approval.required` event;
- denied actions do not execute;
- approved actions record approval identity and decision;
- unsafe shell-like commands are blocked by sandbox policy and produce a
  visible `sandbox.denied` event;
- high-risk business mutations become proposed actions unless explicitly
  pre-approved by policy.

### Phase 2: Conversation Window Execution Echo

Acceptance:

- a run streams or polls persisted events into the center conversation window;
- the same run can be reloaded from persisted events after refresh;
- orchestration phases, tool output, tool errors, approval-required state, and
  final answers render as product-native cards;
- hidden reasoning is not displayed; only safe structured summaries are shown.

### Phase 3: Conversation List And Right Task Execution Panel

Acceptance:

- an operator can create and select conversations;
- historical runs remain inspectable;
- the right panel shows active run status, tasks, tool calls, approvals, recent
  errors, elapsed time, token placeholders, and event timeline;
- pending approvals can be approved or denied from the UI;
- UI state survives page refresh.

## Follow-Up Specs

- `187-ai-assistant-tool-scheduler-rwmutex`: PRD Phase 4, read-only parallel
  batches, write serialization, and later resource-keyed RWMutex.
- `188-ai-assistant-prompt-skills-memory-compaction`: PRD Phase 5, layered
  prompt assembler, project instructions, skill registry, working memory, and
  compaction.
- `189-ai-assistant-customer-assistant-subagent-bridge`: PRD Phase 6,
  customer-assistant subagent spawn/status/events/result integration.
- `190-ai-assistant-observability-benchmark`: PRD Phase 7, trace spans,
  token/cost/latency accounting, benchmark, replay, audit, and governance
  gates.

## Event Contract

Canonical visible event types:

```text
run.started
orchestration.phase_started
orchestration.phase_completed
model.call_started
model.call_completed
model.call_failed
tool.call_started
tool.call_output
tool.call_completed
tool.call_failed
approval.required
approval.granted
approval.denied
sandbox.denied
task.created
task.updated
proposed_action.created
run.completed
run.failed
```

Event envelope:

```text
id
session_id
run_id
task_id?
tool_call_id?
type
level
status
visible_title
visible_summary
payload
sequence
created_at
correlation_ids
```

Events must be persisted with monotonically increasing sequence numbers per
run. UI rendering must consume structured event types rather than parsing
assistant text.

## Tool Registry Contract

Tool manifests must include:

```text
name
description
input_schema
output_schema
timeout_ms
risk_level
read_resources
write_resources
policy_ref
```

MVP required tool:

- `echo_context`: deterministic read-only tool used to prove harness dispatch,
  event persistence, and UI tool cards.

## API Surface

Initial endpoints:

```text
POST /api/v1/ai-assistant/sessions
GET  /api/v1/ai-assistant/sessions
GET  /api/v1/ai-assistant/sessions/{sessionId}
POST /api/v1/ai-assistant/sessions/{sessionId}/messages
GET  /api/v1/ai-assistant/runs/{runId}
GET  /api/v1/ai-assistant/runs/{runId}/events
GET  /api/v1/ai-assistant/runs/{runId}/result
GET  /api/v1/ai-assistant/approvals
POST /api/v1/ai-assistant/approvals/{approvalId}/approve
POST /api/v1/ai-assistant/approvals/{approvalId}/deny
GET  /api/v1/ai-assistant/tools
GET  /api/v1/ai-assistant/runs/{runId}/inspector
```

All responses must preserve the existing `{code, message, data}` envelope.

## Testing Requirements

- Tests verify externally observable behavior: API responses, persisted
  events, replay ordering, tool metadata, permission decisions, approval
  outcomes, sandbox decisions, and UI rendering.
- Backend persistence tests must use the repository's MySQL8 test harness and
  must not add SQLite or PostgreSQL fallback behavior.
- Prompt assembly is deterministic and tested by layer presence/order for the
  MVP, not exact whole-prompt strings unless a string is the contract.
- Tool Registry tests verify schema metadata, allowlist behavior, risk
  metadata, timeout metadata, and handler dispatch.
- Permission tests verify read, low-write, business-write, destructive, and
  external-side-effect decisions.
- Event Store tests verify append, sequence ordering, replay, and refresh
  recovery.
- Product-shell tests verify conversation list, inline execution cards,
  approval cards, right inspector state, and refresh recovery.
- Browser UAT is required for Phase 2 and Phase 3 frontend slices.
- Frontend visual work must pass `remScaleClosure` and full frontend unit
  gates.

## Completion Evidence

Spec 184 is complete only when all Phase 0 through Phase 3 slices have saved
evidence under `artifacts/slices/184-ai-assistant-harness-core-mvp/`,
including:

- RED failure output for each slice;
- focused unit output;
- integration and contract output;
- E2E output;
- frontend unit and remScaleClosure output for frontend slices;
- browser UAT notes and screenshots for frontend slices;
- final high-spec aggregate gates;
- resolved or explicitly accepted residual risk list.
