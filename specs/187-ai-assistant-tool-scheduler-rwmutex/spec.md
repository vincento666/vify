# Spec 187: AI Assistant Tool Scheduler RWMutex

## Status

Slice `187.0` documentation sign-off is complete. Slice `187.1` backend
scheduler tracer is complete for deterministic planned tool calls, read-only
parallel dispatch, write/unresolved resource serialization decisions, MySQL8
metadata roundtrip, and API/event metadata. Slice `187.2` aggregate acceptance
remains pending.

## Numbering Note

Spec 184 originally deferred PRD Phase 4 as
`185-ai-assistant-tool-scheduler-rwmutex` and PRD Phase 5 as
`186-ai-assistant-prompt-skills-memory-compaction`.

The repository now contains `185-mysql8-runtime-unit-harness-hardening`, so the
AI Assistant scheduler cannot use spec id 185 without colliding with committed
work. No `186-*` directory exists in this checkout, but 186 already has a
semantic reservation in the 184 roadmap for prompt, skills, memory, and
compaction. This spec therefore uses 187 for PRD Phase 4 and records that the
later 184 placeholders must be renumbered before those later phases start.

## Goal

Add the narrow backend-first PRD Phase 4 scheduler layer for the existing
`ai_assistant` harness:

```text
planned tool calls
  -> resolve manifest read/write resource templates
  -> group compatible read-only calls into parallel batches
  -> serialize writes through resource-keyed RWMutex rules
  -> persist resource-lock metadata on tool calls and events
  -> preserve MySQL8-backed replay and approval boundaries
```

The scheduler must make concurrency decisions deterministic and observable
without changing the frontend visual surface.

## Existing Boundary From 184

Spec 184 delivered:

- the `app/modules/ai_assistant` backend module;
- deterministic one-turn harness execution;
- read-only `echo_context`;
- high-risk `update_customer_profile` proposed-action behavior;
- sandbox-denied `run_shell` behavior;
- persisted session, run, message, event, tool-call, approval, and
  proposed-action records;
- frontend event echo and inspector views.

This spec extends only the backend scheduling path. It must preserve all 184
API envelopes and event replay semantics.

## Product Boundary

In scope:

- scheduler domain service for ordered planned tool calls;
- resource resolver for manifest templates such as `session:{session_id}` and
  `customer:{customerId}`;
- resource-keyed RWMutex decision model;
- read-only parallel batch execution for compatible read locks;
- write serialization for any planned call with write resources;
- fallback serialization when resource keys cannot be resolved safely;
- persisted scheduler/resource-lock metadata for tool calls and visible events;
- deterministic tests with fake/local tools only;
- MySQL8-only persistence and test evidence.

Out of scope:

- frontend visual, CSS, Vue, or remScaleClosure changes;
- replacing the 184 product shell;
- automatic business writes after approval;
- real LLM scheduler planning;
- OpenRouter or other live-provider gates by default;
- SQLite or PostgreSQL test/persistence paths;
- Phase 5 prompt, skills, memory, and compaction;
- Phase 6 customer-assistant subagent bridge;
- Phase 7 observability, benchmark, replay, and governance platform.

## Functional Requirements

### Read-Only Parallel Batches

- The scheduler accepts an ordered list of planned tool calls.
- Calls whose manifests declare no `write_resources` are read-only candidates.
- Compatible read-only calls may run in the same bounded parallel batch.
- The batch decision must be visible in event payloads and persisted tool-call
  metadata.
- Run replay must return the same tool-call records and ordered event sequence
  even when read-only execution completes out of order internally.

### Write Serialization

- Calls with non-empty `write_resources` must not run in parallel with any
  other call that reads or writes the same resolved resource key.
- Multiple writes must serialize in the original planned order unless a later
  spec explicitly introduces a different ordering policy.
- Calls with unresolved resource templates must use a conservative serial lock.
- Existing 184 approval/proposed-action behavior remains authoritative:
  high-risk business writes pause before execution and must not perform a real
  business mutation in this spec.

### Resource Lock Metadata

Each scheduled tool call must expose scheduler metadata sufficient for
inspection and replay:

```text
scheduler_batch_id
scheduler_position
lock_mode: READ | WRITE | SERIAL
read_resource_keys
write_resource_keys
resource_lock_reason
parallel_eligible
```

The exact storage may use explicit SQL columns and/or JSON payload fields, but
the contract tests must verify that MySQL8 persistence round-trips the metadata
without relying on SQLite behavior.

### Event Contract Additions

Reuse 184 event envelope fields. Add visible structured events:

```text
scheduler.batch_started
scheduler.batch_completed
scheduler.lock_wait_started
scheduler.lock_acquired
scheduler.lock_released
```

Existing tool events (`tool.call_started`, `tool.call_output`,
`tool.call_completed`, `tool.call_failed`) must include scheduler metadata in
their payloads when produced by the scheduler.

## API Surface

No new frontend route is required. Existing AI Assistant endpoints may return
additional scheduler metadata through run, event, result, and inspector payloads
without changing the `{code, message, data}` envelope.

Implementation tests may introduce a backend-only deterministic request shape
for planned tool calls if needed, but it must remain under
`/api/v1/ai-assistant/...` and be covered by contract tests.

## MySQL8 Boundary

All persistence tests for this spec must use the existing MySQL8 test harness.
SQLite and PostgreSQL are not acceptable RED or GREEN evidence.

Required evidence:

- focused unit tests for scheduler/RWMutex decisions;
- MySQL8 integration tests for resource-lock metadata persistence;
- contract tests for scheduler metadata in API/event payloads;
- backend E2E proving read-only batching and write serialization;
- boundary or scan evidence that the new tests did not introduce SQLite
  fixtures.

## LLM Boundary

Default tests must use deterministic planned tool calls and fake/local handlers.
Real LLM tests are deferred. Any future optional live LLM probe must be skipped
unless explicitly enabled by environment variables, and OpenRouter credentials
must be read only from environment such as `OPENROUTER_API_KEY`.

## Acceptance Criteria

- RED evidence exists before implementation for read-only parallel batching,
  write serialization, unresolved-resource serialization, metadata persistence,
  and API/event metadata.
- Read-only compatible calls are grouped into one parallel batch and persisted
  with matching `scheduler_batch_id` metadata.
- A write call touching `customer:C-9` serializes before/after any read or write
  of `customer:C-9`.
- Unresolved resource templates serialize conservatively and expose the reason.
- Event sequence remains monotonically increasing per run.
- The existing 184 high-risk approval/proposed-action behavior is not weakened.
- All relevant backend gates pass against MySQL8.
- No frontend visual files are modified.
