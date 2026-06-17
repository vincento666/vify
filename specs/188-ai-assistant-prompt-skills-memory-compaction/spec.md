# Spec 188: AI Assistant Prompt Skills Memory Compaction

## Status

Slice `188.0` documentation sign-off is complete. Slice `188.1` domain prompt
tracer is complete for deterministic prompt layering, read-only skill manifests,
working-memory prompt items, and compaction summary injection. Durable memory
persistence, API metadata, and backend E2E memory replay remain pending in a
later backend slice.

## Numbering Note

Spec 184 originally deferred PRD Phase 5 as
`186-ai-assistant-prompt-skills-memory-compaction`. Spec 187 recorded that 186
had become a semantic reservation rather than an available implementation id.
After `187-ai-assistant-tool-scheduler-rwmutex` was committed, this Phase 5
spec uses the next requested collision-free id:

```text
188-ai-assistant-prompt-skills-memory-compaction
```

## Goal

Add a narrow backend-first PRD Phase 5 MVP for the existing `ai_assistant`
harness:

```text
session/project context
  -> layered prompt assembler
  -> read-only skill registry
  -> persisted working memory items
  -> deterministic compaction summary
  -> deterministic harness execution by default
```

This spec makes prompt context explicit and replayable without requiring live
LLM calls, frontend visual changes, or credentials.

## Existing Boundary From 184 And 187

Spec 184 delivered the first reusable AI Assistant harness with deterministic
one-turn execution, a minimal layered `PromptAssembler`, typed tool manifests,
event persistence, approval/proposed-action boundaries, and a frontend product
shell.

Spec 187 added deterministic planned tool scheduling, resource-lock metadata,
read-only batching, and write serialization for backend tool calls.

This spec extends the prompt context path only. It must preserve:

- existing `/api/v1/ai-assistant/...` response envelopes;
- MySQL8-backed persistence and replay behavior;
- deterministic default tests with fake/local handlers;
- scheduler, approval, sandbox, and proposed-action boundaries from 184 and
  187;
- no customer-assistant file changes.

## Product Boundary

In scope:

- extend `PromptAssembler` with stable layer ordering;
- add project/session instruction context as a prompt layer;
- add a read-only skill registry with typed skill manifests;
- expose active skill metadata to prompt assembly;
- persist working memory items through existing `ai_assistant` storage where
  possible, preferring JSON context before adding new tables;
- persist and replay a compaction summary;
- emit or expose safe prompt/memory metadata for contract tests;
- deterministic compaction and deterministic model/tool choice by default;
- optional OpenRouter live LLM probe only when explicitly enabled by
  environment variables;
- MySQL8-only integration and contract evidence.

Out of scope:

- frontend visual, CSS, Vue, route, or remScaleClosure changes;
- dynamic skill installation or execution of arbitrary skill code;
- recursive filesystem `AGENTS.md` discovery;
- exposing hidden chain-of-thought;
- real memory embedding, RAG, pgvector, or Weaviate;
- live LLM as a required gate;
- credentials, committed provider keys, or local secret files;
- SQLite or PostgreSQL persistence paths;
- customer-assistant runtime or dirty file edits;
- Phase 6 customer-assistant subagent bridge;
- Phase 7 benchmark, replay, cost accounting, and governance platform.

## Functional Requirements

### Layered Prompt Assembler

Prompt assembly must produce a stable ordered list of layers and a deterministic
text representation. The exact prose may evolve, but the layer names and order
are the contract:

```text
base
project_instructions
skills
working_memory
compaction_summary
tools
run_state
user_message
```

Requirements:

- each layer must be represented as structured metadata with `name` and
  `content`;
- empty optional layers must still be deterministic, either omitted by a
  documented rule or included with empty content consistently;
- tests must assert layer presence, order, and selected layer content rather
  than brittle whole-prompt snapshots;
- no hidden reasoning or private chain-of-thought may be emitted in prompt
  metadata, events, or API payloads;
- prompt metadata may include safe hashes, layer names, token estimates, or
  short safe excerpts when needed for replay and debugging.

### Read-Only Skill Registry

The skill registry is prompt context, not dynamic code execution.

Skill manifests must include:

```text
name
description
version
instruction
tags
risk_level
tool_policy_refs
enabled_by_default
```

Requirements:

- registry contents are read-only at runtime for this MVP;
- a session may activate a deterministic subset of registered skills through
  existing context or a backend-only request shape;
- unknown skill names are ignored with a visible validation reason or rejected
  through a typed API error, but the behavior must be deterministic;
- skill instructions are included in the prompt only through the `skills`
  layer;
- no file writes, package installs, subprocesses, or arbitrary skill scripts
  are allowed.

### Working Memory Items

Working memory items are short durable facts used by later runs in the same
session. MVP fields:

```text
id
session_id
key
value
source
priority
status
created_at
updated_at
```

Requirements:

- implementation should first reuse existing `ai_assistant` storage if it can
  satisfy persistence and replay, especially `ai_assistant_session.context_json`
  or run/event JSON payloads;
- if an explicit memory table is required, it must live under the
  `ai_assistant` schema, use the existing SQLAlchemy/MySQL8 conventions, and be
  covered by MySQL8 integration tests;
- memory item writes must be deterministic and local to the AI Assistant
  harness;
- memory must not mutate customer business records;
- memory payloads must be included in replayable prompt context without
  relying on SQLite JSON behavior.

### Compaction Summary

Compaction stores a short deterministic summary of prior session context so
longer conversations can keep relevant context without replaying everything.

MVP fields:

```text
session_id
summary
source_message_ids
source_event_ids
memory_item_keys
algorithm
token_estimate
updated_at
```

Requirements:

- the default compactor must be deterministic and local;
- the compactor may be extractive or rule-based for the MVP;
- compaction must produce the same summary for the same persisted inputs;
- compaction summary must appear only in the `compaction_summary` prompt layer;
- no live LLM is required to create compaction summaries;
- optional live compaction through OpenRouter is allowed only behind explicit
  environment flags and skipped by default.

## API Surface

Existing AI Assistant endpoints remain authoritative and must preserve the
`{code, message, data}` envelope.

Allowed backend additions:

```text
GET /api/v1/ai-assistant/skills
```

Allowed payload extensions under existing endpoints:

- session creation context may seed project instructions, active skill names,
  working memory items, and compaction summary;
- message requests may include deterministic prompt context only if needed for
  backend tests;
- run result, events, or inspector payloads may expose safe prompt layer,
  skill, memory, and compaction metadata.

No frontend route or visual surface is required by this spec.

## Event Contract Additions

Reuse the 184 event envelope. Implementation may add visible structured events:

```text
prompt.assembled
memory.item_upserted
memory.compaction_updated
```

Event payloads must be safe for UI display and replay. They may include layer
names, selected skill names, memory item keys, compaction algorithm, and token
estimates. They must not expose hidden reasoning.

## MySQL8 Boundary

All persistence tests for this spec must use the existing MySQL8 test harness.
SQLite and PostgreSQL are not acceptable RED or GREEN evidence.

Required evidence:

- focused unit tests for prompt layer order and skill registry behavior;
- MySQL8 integration tests for memory and compaction persistence;
- contract tests for safe prompt/memory metadata in API/event/inspector
  payloads;
- backend E2E proving a later run receives persisted memory and compaction
  context;
- boundary or scan evidence that new tests did not introduce SQLite fixtures.

## LLM Boundary

Default behavior must be deterministic and must not call a live LLM.

Optional OpenRouter real LLM probes are allowed only when all of the following
are true:

- an explicit opt-in flag such as `AI_ASSISTANT_LIVE_LLM=1` is set;
- credentials are read only from environment variables such as
  `OPENROUTER_API_KEY`;
- the model name is read from environment or a safe default;
- tests are skipped by default when the opt-in flag or credentials are absent;
- skipped/live evidence is saved separately from required GREEN gates.

No credentials or provider secrets may be committed.

## Acceptance Criteria

- RED evidence exists before implementation for prompt layer ordering, skill
  registry listing/activation, memory persistence, compaction persistence, and
  API/event metadata.
- Prompt assembly exposes the required layer order deterministically.
- Read-only skill manifests can be listed and included in the prompt by
  deterministic activation rules.
- Working memory survives a MySQL8-backed session reload and appears in a later
  run's prompt metadata.
- Compaction summary survives a MySQL8-backed session reload and appears in the
  `compaction_summary` prompt layer.
- Existing scheduler, approval, sandbox, and proposed-action behavior is not
  weakened.
- Default tests run without live LLM calls or credentials.
- Optional OpenRouter checks are env-gated and skipped by default.
- No frontend visual files are modified.
- No `app/modules/customer_assistant/**` files are modified.
