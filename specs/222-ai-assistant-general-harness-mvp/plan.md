# Plan 222: AI Assistant General Harness MVP

## Architecture Direction

Extend the existing `app/modules/ai_assistant` module into a layered runtime.
New code should keep the current API envelope convention and preserve existing
AI Assistant behavior unless a slice explicitly changes it.

Target domain components:

```text
app/modules/ai_assistant/domain/
  orchestrator.py        # RunOrchestrator and planning strategies
  plan_state.py          # first-class Plan/Task state model
  streaming_runtime.py   # raw delta stream, heartbeat, reconnect semantics
  tool_runtime.py        # ToolRunner, retry, timeout, structured errors
  business_adapter.py    # BusinessToolAdapter seam and mock adapter contract
  file_workspace.py      # read/list/search/edit/write/apply_patch
  session_runtime.py     # durable queue, checkpoints, pause/resume/cancel
  memory_context.py      # AGENTS.md, summary, working memory
  context_budget.py      # context budget and compaction accounting
  policy_runtime.py      # permission DSL
  sandbox_runtime.py     # session sandbox
  resource_lock.py       # DB-backed locks
  skill_runtime.py       # progressive skill discovery/loading
  trace_audit.py         # spans, audit export, eval/budget records
```

The exact file layout may be adjusted during implementation if the local code
shape makes a smaller change safer.

## Existing Baseline

Useful current files:

```text
app/modules/ai_assistant/domain/harness.py
app/modules/ai_assistant/domain/live_model.py
app/modules/ai_assistant/domain/tools.py
app/modules/ai_assistant/domain/scheduler.py
app/modules/ai_assistant/domain/permissions.py
app/modules/ai_assistant/domain/sandbox.py
app/modules/ai_assistant/domain/prompt.py
app/modules/ai_assistant/domain/skills.py
app/modules/ai_assistant/domain/observability.py
app/modules/ai_assistant/infra/schema.py
app/modules/ai_assistant/infra/repository.py
app/modules/ai_assistant/web/router.py
```

Do not replace the module in one broad rewrite. Each slice must introduce a
small explicit runtime layer and preserve existing contract tests until the
slice updates them with RED evidence.

## Planning Strategy

Plan/Task state is universal. User-visible modes are not the core abstraction.

Runtime strategy values:

```text
auto_lightweight
deliberate
plan_only
```

Strategy selection should consider user instruction, risk level, expected tool
count, long-running work, business side effects, and budget pressure.

## P0 Implementation Plan

### 222.0 Boundary Rebase

Documentation-only slice.

Deliver:

- `spec.md`, `plan.md`, `tasks.md`;
- `loop/CURRENT.md` points to this spec;
- `loop/STATE.md` and `loop/VERIFIERS.md` exist as operational loop files;
- no code changes.

### 222.1 PlanTaskRuntime And UI

Deliver first-class Plan and Task state.

Backend:

- plan/task domain models;
- persistence or JSON-backed records, depending on lowest-risk fit;
- planning strategy field;
- plan/task events;
- inspector plan/task payload.

Frontend:

- top-level current task;
- recognized needs;
- planned steps;
- active step;
- current tool;
- pending approval;
- final result;
- debug JSON hidden behind inspector.

### 222.2 StreamingRuntime

Deliver true streaming as the default model output path.

Backend:

- raw text delta event contract;
- heartbeat;
- Last-Event-ID support;
- afterSequence replay;
- explicit non-streaming fallback event.

Frontend:

- token delta rendering;
- reconnect from last sequence;
- snapshot + SSE recovery path.

### 222.3 ToolRuntime And Adapter Seam

Deliver ToolRunner and the business adapter seam.

Backend:

- timeout;
- retry/backoff/jitter;
- circuit breaker;
- fallback adapter;
- idempotency key;
- structured error observation;
- span and budget metadata;
- `BusinessToolAdapter` interface;
- mock aviation adapter.

Eval:

- refund;
- change ticket;
- baggage;
- flight disruption.

The eval fixtures must prove harness behavior, not real aviation rules.

### 222.4 FileWorkspace

Deliver file workspace tools:

```text
read
list
search
edit
write
apply_patch
```

Edit must include diff preview, unique candidate matching, preconditions,
atomic write, rollback snapshot, and resource lock integration.

### 222.5 SessionRuntime

Deliver durable execution lifecycle:

- durable queue/worker;
- checkpoint;
- stream cursor;
- heartbeat;
- pause/resume/cancel;
- snapshot;
- reconnect recovery;
- pending approval recovery.

### 222.6 MemoryContext And ContextBudget

Deliver MVP memory and context observability:

- recursive AGENTS.md instruction loading;
- approval-gated AGENTS.md update tool contract;
- DB-backed session summary;
- working memory key-value facts;
- context budget estimator;
- compaction snapshot;
- prompt layer token share;
- inspector context section;
- audit records for layer selection/drop decisions.

## P1 Implementation Plan

### 222.7 PermissionPolicy, SandboxRuntime, And ResourceLock

Deliver session-level safety:

- policy DSL;
- sandbox runtime;
- DB-backed READ/WRITE locks with lease, TTL, fencing token;
- enforcement for `always_approve`.

### 222.8 SkillRuntime

Deliver progressive skill loading:

- directory discovery;
- metadata index;
- SKILL.md load after trigger;
- references/scripts/assets on demand;
- version/checksum;
- risk/policy;
- audit events.

### 222.9 TraceAuditEvalBudget

Deliver complete evidence:

- trace spans;
- audit export;
- eval regression set;
- token/cost budget;
- model fallback policy.

### 222.10 Aggregate Production Evaluation

Run the full acceptance path across streaming, reconnect, tool self-correction,
file safety, approval/sandbox/budget, context accounting, skill loading, and
mock adapter evidence.

### 222.11 Live LLM Real-Case UAT

Deliver the release gate that proves the harness against real external
LLM behavior on realistic user cases.

Preflight must freeze:

- external LLM provider, model, base URL, streaming capability, token/cost
  budget, and fallback policy;
- credential names and secret-handling path for the live LLM provider;
- realistic case set, including aviation-style refund, change-ticket, baggage,
  and flight-disruption scenarios through the mock aviation adapter seam;
- approval, idempotency, compensation metadata, and audit expectations for
  simulated high-risk adapter actions;
- automated browser/API UAT scripts and artifact paths.

Confirmed target for this slice: OpenRouter `qwen/qwen3.6-27b`, using runtime
secret injection and conservative live UAT limits.

Implementation must keep the harness generic. Aviation behavior remains in the
mock aviation adapter package and policy configuration, not in the core
orchestrator, ToolRunner, session runtime, memory runtime, or UI shell. Do not
add real civil-aviation API integrations in this slice.

Required automated UAT:

- live LLM token streaming case with `text.delta` before completion;
- live LLM reconnect/resume case with snapshot plus SSE continuation;
- aviation-style refund case through the mock adapter seam with a real LLM
  planner/model path;
- aviation-style change-ticket case through the mock adapter seam with a real
  LLM planner/model path;
- aviation-style baggage case through the mock adapter seam with a real LLM
  planner/model path;
- aviation-style flight-disruption case through the mock adapter seam with a
  real LLM planner/model path;
- at least one approval-gated high-risk adapter action;
- audit export containing redacted model metadata, adapter request/response
  metadata, idempotency key, compensation record, token/cost budget, context
  budget, plan/task state, and final result;
- browser UAT that confirms user-visible plan/task/tool/context/audit state for
  a seeded real-case run.

### 222.12 Real-Time Streaming And Durable Worker Correction

Deliver the P0 runtime correction for execution-time streaming and durable run
execution.

Current risk to close:

- `/runs/{id}/events/stream` can call queued-run processing before returning
  `StreamingResponse`, which can turn "streaming" into replay after synchronous
  completion;
- worker claim metadata is process-local and execution is started by opening the
  stream endpoint;
- pause/cancel can update state without interrupting an in-flight synchronous
  execution path.

Preflight must freeze:

- whether the implementation can use the existing database tables or requires a
  schema/migration change;
- worker claim/lease shape, heartbeat cadence, timeout, and stale-claim
  recovery;
- stream contract: subscribe/replay only, no synchronous run execution inside
  the SSE route;
- pause/resume/cancel interruption semantics for long-running model/tool calls;
- UAT evidence for active `text.delta` delivery before terminal completion.

Required automated evidence:

- RED contract test that fails while the stream route synchronously processes a
  queued run before yielding SSE frames;
- RED E2E test that fails until a queued run can be processed by a worker path
  without opening the stream endpoint;
- streaming test proving at least one `text.delta` is observable while the run
  status is non-terminal;
- reconnect test proving snapshot plus SSE continuation after a worker-started
  run;
- pause/cancel test proving control state is observed by the running worker or
  safely blocks until a cooperative checkpoint;
- browser UAT showing the visible run is actively streaming, not just replaying
  a finished transcript.

### 222.13 Tool Observation Self-Correction Correction

Deliver the P0 closed-loop tool failure behavior.

Current risk to close:

- ToolRunner can create model-visible structured observations, but the harness
  may finalize the run as failed immediately instead of feeding the observation
  back into planning/execution;
- plan/task state may not show the repair attempt or local replan caused by the
  tool failure.

Required behavior:

- recoverable tool errors become `observation` input to the orchestrator;
- the orchestrator can retry with repaired arguments, select fallback adapters,
  revise the plan, or degrade the answer within configured budget;
- unrecoverable permission, sandbox, approval, or exhausted-budget conditions
  finalize with structured failure;
- every repair attempt emits trace spans, audit records, tool events,
  `plan.revised` or `task.updated`, and budget usage.

Required automated evidence:

- RED unit/contract tests for recoverable timeout, 5xx, and rate-limit
  observations that currently finalize too early;
- RED E2E test that fails until the model/orchestrator repairs at least one bad
  tool call and completes the run;
- RED budget test proving self-correction stops when the configured retry or
  token/cost budget is exhausted;
- browser UAT showing a failed tool, repair/replan progress, and final result or
  structured terminal failure.

### 222.14 Corrective Wave Contract

Deliver a bounded corrective wave for backend closure and evidence credibility.
Do not fold sandbox isolation, HA workers, multi-tenancy, business adapters, or
durable ToolRunner idempotency implementation into this wave.

Slice order:

1. `222.14.1 Event Sequence Concurrency Safety`
2. `222.14.2 Aggregate Eval Runtime Evidence`
3. `222.14.3 Backend Autonomous Worker MVP`
4. `222.14.4 Live Gate Rerun`
5. `222.14.5 Durable Idempotency And Circuit Breaker Spec`

#### 222.14.1 Event Sequence Concurrency Safety

Implementation direction:

- add an AI Assistant-specific concurrent append regression before changing the
  repository;
- make per-run event sequence assignment atomic under MySQL8 concurrent writers,
  either by a run-level lock/update strategy or by a unique sequence constraint
  with retry;
- preserve `afterSequence`, snapshot, and SSE replay ordering;
- do not change runtime v2, customer assistant, or chatflow event systems.

Human gate:

- stop if the chosen fix needs a database migration or new schema index that is
  not already present and confirmed for this corrective wave.

#### 222.14.2 Aggregate Eval Runtime Evidence

Implementation direction:

- replace source-code-string checks with an explicit runtime evidence reader;
- accept evidence from run events, run snapshot, audit export, Browser UAT
  artifact, and live gate artifact;
- make each requirement fail with a missing-evidence reason when runtime
  evidence is absent;
- cover at least token delta default, reconnect recovery, tool failure
  self-correction, file workspace concurrency safety, and context visibility.

Non-goal:

- do not rebuild the company-wide evaluation framework.

#### 222.14.3 Backend Autonomous Worker MVP

Implementation direction:

- keep the MVP same-process and module-local;
- after `messages/async`, trigger backend consumption of the queued run without
  depending on the frontend to call `worker/process`;
- keep `/events/stream` as subscribe/replay only;
- make explicit `worker/process` idempotent so existing frontend behavior does
  not double-execute the run;
- preserve current lease, checkpoint, pause, resume, and cancel semantics.

Non-goals:

- no standalone worker service;
- no cross-machine HA takeover;
- no broker or distributed scheduler.

#### 222.14.4 Live Gate Rerun

Implementation direction:

- reuse the existing 222.11 live UAT target and OpenRouter
  `qwen/qwen3.6-27b`;
- require `HIFY_RUN_LIVE_AI_ASSISTANT=1` and `OPENROUTER_API_KEY`;
- on missing credentials, quota, network, or model availability, produce an
  `env-blocked` or `waiting-human` artifact rather than PASS;
- update only live gate artifacts and evidence references, not provider/model
  scope.

#### 222.14.5 Durable Idempotency And Circuit Breaker Spec

Implementation direction:

- create a separate spec directory with `spec.md`, `plan.md`, and `tasks.md`;
- define durable ToolRunner ledger and circuit breaker semantics before code;
- answer key generation, UNKNOWN retention, release authority, fallback
  operation identity, read-vs-side-effect differences, and persistent circuit
  state;
- do not implement code in this corrective wave.

Human gates:

- database schema or migration changes;
- new worker, broker, container, seccomp, firejail, or OS sandbox dependency;
- production runtime deployment behavior;
- any claim that policy-level sandbox controls are OS/container isolation;
- external live-provider execution when credentials, quota, or budget are
  missing.

## Persistence Guidance

Prefer MySQL8-backed persistence consistent with existing Hify conventions.
JSON columns may be used for early structured snapshots only when tests prove
round-trip behavior. Stable identity, status, sequence, timestamps, and lock
tokens should be explicit columns when they become cross-run contracts.

Do not introduce SQLite or PostgreSQL shortcuts for this module.

## Testing Strategy

Each implementation slice must follow RED -> implementation -> focused gates.

Expected gate families:

```text
unit
integration
contract
e2e
frontend unit
frontend remScaleClosure
automated real-case browser UAT
docs
```

Docs-only `222.0` does not require RED evidence. Every behavior-changing slice
after `222.0` does.

Frontend visual changes must run the rem gate required by `AGENTS.md`.

Live external gates are not optional for a spec whose value depends on a real
external provider. Missing credentials, quota, network, or model access must
produce a blocking artifact, not a passing skip. Domain adapters remain real or
mock according to the active spec boundary.
User-visible flows must include browser UAT evidence.

## Human Gates

Stop before:

- implementing real aviation adapters;
- making `memory.md` mandatory;
- changing auth, permissions, sandbox, billing, secrets, or external-service
  behavior outside the active slice;
- adding dependencies;
- weakening tests or gates;
- crossing from one slice into the next before evidence is complete.
