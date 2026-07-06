# Spec 222: AI Assistant General Harness MVP

## Goal

Rebase the existing `ai_assistant` module into a generic, production-evaluable
AI Assistant harness.

The core harness must be able to converse, plan, call tools, stream output,
manage files, pause/resume/cancel, enforce permissions, recover sessions, audit
execution, budget context and cost, self-correct tool failures, and execute
safely under concurrency.

Civil-aviation behavior must not leak into the generic harness kernel. The
aviation boundary remains the original adapter seam plus mock aviation adapter
and aviation-style eval/UAT cases. The MVP is not complete until realistic
user cases are exercised through an external live LLM automated UAT path rather
than a mock or deterministic model path.

## Why This Spec Exists

Specs `184`, `187`, `188`, `190`, `191`, `192`, and `193` delivered useful AI
Assistant MVP pieces: a ReAct-style harness, event replay, live model streaming,
tool and approval paths, sandbox checks, scheduler metadata, prompt traces, and
the current product shell.

The remaining risk is that the harness kernel is not yet closed-loop and cannot
be considered production-evaluable until it has survived real external model
UAT on realistic cases. Mock-only or deterministic-model evidence is useful
during development, but it is not sufficient for final MVP acceptance.

This spec redefines the boundary as:

```text
conversation
  -> first-class Plan/Task state
  -> streaming runtime
  -> unified tool runtime
  -> file workspace runtime
  -> durable session runtime
  -> memory/context budget runtime
  -> permission/sandbox/resource-lock runtime
  -> progressive skill runtime
  -> trace/audit/eval/budget evidence
```

## Slice Status

```text
222.0 Boundary Rebase: complete
222.1 PlanTaskRuntime And UI: complete
222.2 StreamingRuntime: complete
222.3 ToolRuntime And Adapter Seam: complete
222.4 FileWorkspace: complete
222.5 SessionRuntime: complete
222.6 MemoryContext And ContextBudget: complete
222.7 PermissionPolicy, SandboxRuntime, And ResourceLock: complete
222.8 SkillRuntime: complete
222.9 TraceAuditEvalBudget: complete
222.10 Aggregate Production Evaluation: complete
222.11 Live LLM Real-Case UAT: complete
222.12 Real-Time Streaming And Durable Worker Correction: complete
222.13 Tool Observation Self-Correction Correction: proposed-confirmation
222.14 Production Hardening Backlog: proposed-confirmation
```

## Product Boundary

In scope:

- generic AI Assistant orchestration kernel;
- first-class Plan and Task state;
- planning strategies for lightweight, deliberate, and plan-only runs;
- true streaming by default with visible fallback semantics;
- unified ToolRunner for all tool execution;
- BusinessToolAdapter seam, mock aviation adapter for fast regression and
  aviation-style realistic case coverage;
- external live LLM streaming UAT as a required release gate;
- file workspace read/list/search/edit/write/apply_patch tools;
- durable run queue, checkpoints, stream cursors, heartbeat, pause, resume,
  cancel, and reconnect recovery;
- AGENTS.md instruction memory, DB-backed session summary, working memory, and
  context-budget observability;
- session-level permission DSL, sandbox policy, and DB-backed resource locks;
- progressive SkillRuntime loading;
- trace spans, audit export, eval fixtures, token/cost/context budget records;
- frontend plan/task/context inspector changes required by slices that affect
  user-visible state.

Out of scope:

- customer-service UI copy or customer-service operator workflow
  specialization;
- domain-specific customer mutations;
- real civil-aviation adapter implementation;
- real airline systems, rules, policies, credentials, or integrations;
- storing real provider API keys, airline credentials, secrets, or customer PII
  in the repository or artifacts;
- `memory.md` as a required MVP component or the only persistent memory source;
- hidden chain-of-thought exposure;
- committed real provider API keys or secrets;
- weakening existing MySQL8, TDD, frontend rem, UAT, or loop stop-rule gates.

## Adapter Boundary

The generic harness kernel remains business-neutral. Civil-aviation logic must
enter only through `BusinessToolAdapter` and policy-controlled tool
registrations.

Only three aviation-related preparations are required in this MVP:

```text
BusinessToolAdapter interface
mock aviation adapter
small aviation-style eval and live-LLM UAT cases
```

`BusinessToolAdapter` must describe:

```text
tool schema
risk level
idempotency key
compensation transaction
audit fields
```

The mock aviation adapter exists only to prove the generic harness can call a
business API-shaped tool, route approval, record audit fields, and model
rollback or compensation. It must not encode real aviation policy.

Allowed aviation-style realistic scenarios:

```text
refund
change ticket
baggage
flight disruption
```

These scenarios prove harness behavior through the adapter seam. They must not
connect to real airline systems in this MVP. High-risk simulated actions still
require approval, idempotency, compensation metadata, and audit export.

## External Live LLM Gate

The MVP requires automated UAT that calls a real external LLM provider through
the AI Assistant runtime. The cases must be realistic user cases, including the
aviation-style scenarios above, but the aviation adapter remains mock per the
adapter boundary.

Current 222.11 target: OpenRouter `qwen/qwen3.6-27b`. The model slug must be
verified through the OpenRouter model catalog before live UAT, and provider
credentials must be injected only as runtime secrets.

Required evidence:

```text
real provider request and response metadata
raw text.delta streaming before completion
tool/progress events interleaved with model events when tools are used
visible fallback only when the provider truly does not stream
token/cost budget record
context budget record
redacted prompt-layer audit
run snapshot and SSE resume evidence
browser-visible final result
```

Missing API keys, network access, provider quota, or model availability cannot
be treated as success. The gate must fail or enter `waiting-human` with the
missing prerequisite recorded.

## Gap Review 2026-07-06

The 2026-07-06 gap review found that the goal-level MVP boundary is correct,
but several completed slice labels are stronger than the current code and
evidence justify under the updated production-evaluable bar.

Previously completed slices remain historically complete for their original
deterministic or mock-adapter gates. They do not by themselves prove final MVP
completion.

P0 corrective blockers:

```text
222.11 Live LLM Real-Case UAT
222.12 Real-Time Streaming And Durable Worker Correction
222.13 Tool Observation Self-Correction Correction
```

P1 production-hardening backlog:

```text
222.14 Production Hardening Backlog
```

`222.12` must close the structural risk where `/runs/{id}/events/stream`
can process a queued run synchronously before returning the SSE response. The
stream endpoint must be a replay/subscribe surface, while a durable worker path
claims and executes queued runs independently. Browser/API evidence must show
`text.delta` events arriving before terminal completion during an active run,
not only being replayed after execution completes.

`222.12` must also harden SessionRuntime beyond process-local claim metadata:
durable claim/lease semantics, checkpoint progress, heartbeat, reconnect,
pause, resume, and cancel must be observable and must not depend on opening the
SSE endpoint to start execution. If a data model or worker architecture change
is required, it must be confirmed before implementation.

`222.13` must close the ToolRunner observation loop. Structured tool errors
must be returned to the model/orchestrator as observations that can trigger
retry, argument repair, fallback, plan revision, or graceful degradation within
budget. A tool failure may finalize the run only after the configured
self-correction budget or an unrecoverable policy/sandbox/approval condition is
reached.

`222.14` tracks production-hardening gaps that are not required to start the P0
runtime correction but must be explicit before production claims:

```text
DB-backed ToolRunner idempotency ledger and circuit breaker state
event sequence concurrency safety with unique conflict retry or run-level lock
context compaction that materializes reliable summaries of dropped context
sandbox boundary clarity between policy-level controls and OS/container isolation
```

OS-level sandboxing, network isolation, CPU/memory enforcement, or new external
runtime dependencies remain human-gated and must not be implied by the current
policy-level sandbox.

## Planning Model

Plan and Task are first-class persisted state for every run. They are not only
derived from events and not only text in the model response.

This does not create two user-visible modes named "normal mode" and "plan
mode". The harness always records Plan/Task state; the selected planning
strategy determines depth and execution behavior.

Planning strategies:

```text
auto_lightweight
deliberate
plan_only
```

`auto_lightweight` is the default. Simple ReAct turns still create lightweight
`plan.created` and `task.updated` records so UI and audit surfaces can replay
the assistant's intended work.

`deliberate` is used for complex, high-risk, long-running, multi-tool, or
multi-agent work. It follows:

```text
Plan -> Act/Observe -> Replan -> Finalize
```

`plan_only` is used only when the user explicitly asks for planning without
execution.

Plans are revisable. Tool observations, approval decisions, errors, budget
pressure, or resource-lock contention may emit `plan.revised` or
`plan.blocked`.

Required plan/task events:

```text
plan.created
plan.step_started
plan.step_completed
plan.revised
plan.blocked
task.created
task.updated
task.completed
task.blocked
```

## Streaming Runtime

The default output path is true streaming. Provider deltas must be forwarded as
soon as they arrive, using raw text delta events such as `text.delta` or an
equivalent canonical event.

Non-streaming providers are allowed only as explicit fallback. The fallback
must be visible in events and audit records.

Required recovery behavior:

```text
Last-Event-ID
afterSequence
heartbeat
run snapshot
SSE resume after sequence
frontend auto reconnect
```

## Tool Runtime

All tools must execute through a unified ToolRunner. Tool-specific functions
should not own cross-cutting reliability behavior.

ToolRunner must provide:

```text
timeout
retry with backoff and jitter
circuit breaker
fallback adapter
structured error
idempotency key
tool events
trace span
budget accounting
```

Tool failures must be returned to the model as structured observations so the
model can retry, change arguments, choose a different tool, degrade, or revise
the plan within budget.

## File Workspace

The core harness requires a minimal complete file workspace:

```text
read
list
search
edit
write
apply_patch
```

Edit must support:

```text
exact match
context match
whitespace tolerance
unique candidate check
diff preview
checksum or mtime precondition
atomic write
rollback snapshot
file-level resource lock
```

Concurrent writes to the same file must not overwrite each other. Failed edits
must not damage files.

## Session Runtime

AI Assistant must have its own durable session runtime and must not rely on
customer-assistant runtime semantics.

Required capabilities:

```text
durable run queue
worker claim and heartbeat
run checkpoint
stream cursor
pause
resume
cancel
snapshot
Last-Event-ID recovery
pending approval recovery
```

Refreshing the page or reconnecting after network loss must recover run status,
plan progress, emitted tokens, tool state, and pending approvals.

## Memory And Context Budget

MVP memory has three layers:

```text
Instruction Memory: AGENTS.md
Session Summary: DB-backed compaction
Working Memory: short key-value facts
```

AGENTS.md is required for stable project/repository instructions. It must be
read recursively from the nearest applicable path and inserted into a prompt
layer. AGENTS.md updates require diff plus human approval.

AGENTS.md is not for frequent session summaries, temporary preferences, or run
intermediate conclusions.

Session Summary is DB-backed compaction stored in AI Assistant-owned persistence
or session context. It must record source message ids, source event ids,
algorithm metadata, token estimate, and summary hash.

Working Memory is a minimal key-value store for short facts such as user
preferences, project constraints, or confirmed decisions. Items require source,
timestamp, status, and delete/invalidate support.

`memory.md` is not required for MVP. It may later become a human-readable export
or edit surface.

Context usage must be measurable, explainable, and auditable.

Backend concepts:

```text
context_budget
compaction_snapshot
```

Required events:

```text
context.budget_estimated
context.compaction_started
context.compaction_completed
context.layer_selected
context.layer_dropped
```

Inspector must show:

```text
context window usage: used / max tokens and percentage
compaction delta: raw tokens -> summary tokens and saved percentage
prompt layer token share
selected layers
dropped layers
drop reason
budget warning level
```

Prompt layer accounting must include at least:

```text
AGENTS.md
session_summary
working_memory
recent_messages
tools
skills
user_message
```

Default budget thresholds:

```text
>= 70 percent: warning
>= 90 percent: compact, drop lower-priority context, or refuse to append
```

## Permission, Sandbox, And Resource Lock

Permission policy must be session-scoped and structured. Policy dimensions:

```text
tool
risk
path
command
external side effect
budget
approval requirement
```

`always_approve` must still be constrained by sandbox, policy, budget, and
resource locks.

Sandbox must be at least session-scoped:

```text
per-session workspace
per-run temp
env and secret scope
fixed cwd
network policy
resource limits
shell allowlist
output redaction
```

Resource locks must be DB-backed READ/WRITE locks with lease, TTL, and fencing
tokens.

## Skill Runtime

SkillRuntime must align with progressive disclosure:

```text
directory discovery
metadata index
load name/description/path at startup
read SKILL.md only after trigger match
read references/scripts/assets on demand
version and checksum metadata
risk and policy integration
event audit
optional script/tool invocation through ToolRuntime policy
```

The harness must not load all skill contents into prompt context by default.

## Trace, Audit, Eval, And Budget

Required span coverage:

```text
run
model call
tool call
approval
stream
retry
fallback
skill load
file edit
resource lock
context compaction
context budget
business adapter seam
```

Required audit outputs:

```text
prompt-layer record
context-budget record
compaction-snapshot record
plan record
tool args/result record
retry/fallback record
approval record
token/cost budget record
file diff record
business adapter audit record
final result
```

## Slice Order

P0:

```text
222.0 Boundary Rebase
222.1 PlanTaskRuntime And UI
222.2 StreamingRuntime
222.3 ToolRuntime And Adapter Seam
222.4 FileWorkspace
222.5 SessionRuntime
222.6 MemoryContext And ContextBudget
```

P1:

```text
222.7 PermissionPolicy, SandboxRuntime, And ResourceLock (complete)
222.8 SkillRuntime
222.9 TraceAuditEvalBudget
222.10 Aggregate Production Evaluation
```

Release gate:

```text
222.11 Live LLM Real-Case UAT
222.12 Real-Time Streaming And Durable Worker Correction
222.13 Tool Observation Self-Correction Correction
```

`222.11`, `222.12`, and `222.13` reopen MVP completion. `222.10` remains complete for the
deterministic/internal aggregate boundary, but it is not sufficient for final
MVP acceptance after the 2026-07-05 and 2026-07-06 corrections because it did
not prove the harness against a real external LLM on realistic cases, a
decoupled real-time worker stream, or a model-visible tool self-correction
loop.

## Aggregate Acceptance Criteria

- Pure text output streams token deltas by default.
- Non-streaming providers are explicitly marked as fallback.
- Refresh or network reconnect restores run status, plan progress, emitted
  tokens, pending approvals, and tool state.
- Tool 5xx, timeout, and rate-limit failures retry or degrade through
  structured observations; final errors can trigger replan.
- Concurrent writes to the same file cannot overwrite each other.
- Edit failure leaves files intact.
- High-risk tools require approval by default.
- Approval relaxation remains bounded by policy, sandbox, budget, and resource
  locks.
- Each run can export full audit evidence: prompt layers, context usage, plan,
  tool args/results, retries, approvals, token/cost, file diffs, adapter audit,
  and final result.
- Skill content is loaded on demand, not injected wholesale at startup.
- Mock aviation adapter proves the aviation adapter seam and aviation-style
  scenarios only; real civil-aviation integration remains out of scope for this
  MVP.
- External live LLM UAT proves the runtime can stream real provider tokens,
  recover from reconnect, account for context/cost, and produce an audited
  final result on realistic user cases.
- Real-case UAT must be automated through browser/API scripts and saved as
  artifacts. Manual-only UAT is not sufficient for final spec acceptance.
- SSE streaming must prove execution-time delivery. Replaying events after a
  synchronously completed run is not sufficient.
- SessionRuntime must prove execution can start from a durable worker path
  without being triggered by the stream endpoint.
- Tool failure observations must drive at least one automatic retry, argument
  repair, fallback, or plan revision before final failure, unless policy or
  sandbox denies recovery.

## Spec Launch Acceptance Rule

Every new spec must define at least one real-case automated UAT before
implementation starts.

Required properties:

```text
uses the real application surface or public API
uses real browser automation for user-visible flows
uses real external services when the spec's value depends on them
records objective assertions, screenshots, logs, and exported audit evidence
fails or blocks when credentials, services, data, or budgets are missing
does not convert missing live prerequisites into PASS or silent skip
```

Manual exploratory UAT may still be used to find issues, but it cannot replace
the automated real-case UAT gate.
