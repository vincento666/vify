# Spec 188: AI Assistant Prompt Skills Memory Compaction

## Status

Slice `188.0` documentation sign-off is complete. Slice `188.1` domain prompt
tracer is complete for deterministic prompt layering, read-only skill manifests,
working-memory prompt items, and compaction summary injection. API persistence,
durable memory tables, and frontend presentation are deferred to later slices.

## Numbering Note

Spec 184 originally listed PRD Phase 5 as
`186-ai-assistant-prompt-skills-memory-compaction`, but later repository work
used nearby ids for other slices. Spec 187 now owns Phase 4 scheduler/RWMutex.
This spec uses 188 for PRD Phase 5 to avoid collisions.

## Goal

Add the first backend-first Phase 5 prompt layer for the AI Assistant harness:

```text
base instruction
  -> project instructions
  -> tool registry summary
  -> read-only skill registry summary
  -> working memory items
  -> compaction summary
  -> run state
  -> user message
```

The implementation must remain deterministic and must not depend on live LLMs
for default tests.

## Scope

In scope:

- extend `PromptAssembler` with optional project instructions;
- add a read-only `SkillRegistry` with manifest metadata;
- add prompt memory item rendering with deterministic ordering;
- add compaction summary as an explicit prompt layer;
- preserve the 184 minimal prompt behavior when optional inputs are absent;
- keep tests backend-only and deterministic;
- keep MySQL8-only boundary rules for future persistence tests.

Out of scope:

- frontend UI or visual changes;
- durable memory table migrations in this first tracer;
- automatic memory writes;
- real skill execution or tool-call changes;
- live LLM gates by default;
- SQLite/PostgreSQL persistence paths;
- customer-assistant subagent bridge;
- observability/benchmark/governance.

## Acceptance Criteria

- RED evidence shows Phase 5 prompt concepts missing before implementation.
- Existing 184 prompt layer order remains unchanged when optional inputs are
  absent.
- When project instructions, skills, memory, and compaction are supplied, prompt
  layers appear in deterministic order.
- Skill manifests are read-only metadata and do not execute tools.
- Memory item rendering is stable across runs.
- Default gates use deterministic local tests only.
- Any future real LLM probe must be opt-in and read OpenRouter credentials only
  from environment variables.

