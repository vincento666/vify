# Plan 184: AI Assistant Harness Core MVP

## Architecture

Create a new backend module:

```text
app/modules/ai_assistant/
├── domain/
│   ├── events.py
│   ├── harness.py
│   ├── permissions.py
│   ├── prompt.py
│   ├── result.py
│   ├── sandbox.py
│   └── tools.py
├── infra/
│   ├── repository.py
│   └── schema.py
└── web/
    ├── router.py
    └── schemas.py
```

Create a frontend product shell:

```text
frontend/src/api/aiAssistant.ts
frontend/src/views/ai-assistant/
frontend/src/router/ai-assistant-routes.ts
```

The AI Assistant module may reuse shared core helpers, API envelope utilities,
and customer-assistant domain vocabulary. Existing customer-assistant runtime
modules must not import the new AI Assistant module.

## Slice Order

Slices are serialized at the code and gate level. Subagents may perform
parallel read-only exploration or non-overlapping implementation work, but a
later slice is not accepted until the previous slice evidence is complete.

### 184.0 Spec Sign-Off

- create `spec.md`, `plan.md`, and `tasks.md`;
- confirm latest spec id after `183-final-openrouter-live-gate-revalidation`;
- define Phase 0 through Phase 3 scope;
- mark Phase 4 through Phase 7 as later specs.

### 184.1 Phase 0 Minimal Harness Kernel

Backend-only MVP.

Build:

- session, run, message, event, and tool-call persistence;
- event sequence and replay;
- minimal Prompt Assembler;
- read-only Tool Registry;
- deterministic `echo_context` tool;
- one-turn harness loop using `reason -> validate -> act -> observe -> final`;
- API endpoints for sessions, sending messages, run status/result, events, and
  tool manifests.

Gates:

- RED repository/domain/API tests;
- focused unit tests;
- integration/contract API tests;
- E2E API test proving one message to final result and replay;
- UAT not applicable until frontend slice.

### 184.2 Phase 1 Sandbox And Approval Boundary

Backend safety MVP.

Build:

- risk classifier;
- sandbox policy;
- permission middleware;
- approval modes: `ask_each_time`, `smart_approval`, `always_approve`;
- approval persistence and approve/deny endpoints;
- proposed-action persistence for high-risk business writes;
- audit-style event payloads for sandbox/approval verdicts.

Gates:

- RED permission/sandbox/approval tests;
- focused unit tests;
- integration/contract API tests;
- E2E API test for approve/deny/sandbox denied;
- UAT not applicable until frontend slice.

### 184.3 Phase 2 Conversation Execution Echo

Frontend plus backend event protocol stabilization.

Build:

- frontend API client for sessions, runs, events, approvals, and tools;
- center conversation timeline;
- event cards for orchestration phases, model summaries, tool calls, approval
  required/granted/denied, sandbox denied, proposed actions, run completed,
  and run failed;
- refresh recovery from persisted run events.

Gates:

- RED frontend tests for event-card rendering and refresh recovery;
- backend contract regression for event envelope;
- frontend unit tests;
- `remScaleClosure`;
- browser UAT with saved screenshot and notes.

### 184.4 Phase 3 Conversation List And Right Inspector

Frontend product shell completion.

Build:

- left session/conversation list;
- create/select session workflow;
- right run/task inspector;
- active run status, task list, tool-call list, approval queue, recent errors,
  elapsed time, token placeholders, and event timeline;
- approve/deny controls from the UI.

Gates:

- RED frontend tests for list, inspector, approval queue, and refresh behavior;
- backend contract regression for inspector endpoint;
- frontend unit tests;
- `remScaleClosure`;
- E2E product-shell test;
- browser UAT with saved screenshot and notes.

### 184.5 Final Aggregate Acceptance

- rerun slice-specific focused gates;
- run aggregate backend unit/integration/contract/e2e gates;
- run frontend unit and remScaleClosure gates;
- run browser UAT for the AI Assistant shell;
- document risks and evidence;
- update tasks status.

## Persistence

MVP uses SQLAlchemy models consistent with existing Hify modules, backed by
MySQL8. Do not add SQLite or PostgreSQL persistence branches for this module.
JSON columns may store structured payload snapshots, but stable status,
identity, sequence, and timestamps should be explicit columns.

Required durable records:

- assistant session;
- assistant run;
- assistant message;
- assistant event;
- assistant tool call;
- assistant approval;
- assistant proposed action;
- assistant task;
- assistant trace span placeholder;
- assistant memory item placeholder.

Phase 0 only uses session/run/message/event/tool-call. Later records may be
introduced in Phase 1 through Phase 3 when needed by acceptance criteria.

## TDD Evidence Discipline

For each slice:

1. write the smallest failing test first;
2. run the focused command and save RED output under
   `artifacts/slices/184-ai-assistant-harness-core-mvp/<slice>/red.txt`;
3. implement the minimal code needed to pass;
4. run focused gates and save outputs;
5. update `tasks.md` only after evidence exists.

Backend tests that touch persistence must use MySQL8 fixtures or the existing
MySQL8 test harness. SQLite and PostgreSQL shortcuts are not acceptable RED or
GREEN evidence for this spec.

## Subagent Coordination

Each implementation subagent owns one disjoint slice or file set and must
return:

- modification scope;
- RED evidence;
- implementation summary;
- gates run;
- remaining risks.

The main agent owns:

- spec synthesis;
- cross-slice merge;
- conflict resolution;
- final aggregate gates;
- browser UAT;
- goal completion decision.

## Dependencies

Helpful existing modules:

- `app.core.responses` for response envelope conventions;
- `app.core.database` and existing module `infra/schema.py` patterns;
- `app.modules.customer_assistant` for event/proposed-action vocabulary;
- existing frontend router/API/test patterns;
- `frontend/src/remScaleClosure.test.ts` for visual unit governance.

## Non-Goals

Do not implement:

- RWMutex scheduler;
- project AGENTS.md loader;
- skill registry;
- working memory and compaction;
- customer-assistant subagent bridge;
- benchmark/replay governance;
- real LLM calls as default behavior;
- automatic high-risk business writes.
