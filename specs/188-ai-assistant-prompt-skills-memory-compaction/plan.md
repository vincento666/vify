# Plan 188: AI Assistant Prompt Skills Memory Compaction

## Architecture

Extend the existing `app/modules/ai_assistant` backend module. Planned target
shape:

```text
domain/
├── prompt.py          # layered assembler extension
├── skills.py          # read-only skill registry and manifests
├── memory.py          # working memory and deterministic compaction models
├── tools.py           # existing tool manifests remain separate from skills
├── scheduler.py       # existing 187 scheduler remains authoritative
└── harness.py         # integration point for prompt/memory context

infra/
├── repository.py      # session context JSON first; table only if required
└── schema.py          # MySQL8 schema extension only if JSON is insufficient

web/
├── router.py          # optional GET /skills and safe metadata payloads
└── schemas.py         # request/response extensions if needed
```

The implementation should prefer the current `ai_assistant_session.context_json`
for MVP memory and compaction persistence if it can satisfy the acceptance
criteria. A dedicated memory table is allowed only when JSON context cannot
provide deterministic MySQL8 persistence and replay with clear tests.

## Slice Order

### 188.0 Documentation Sign-Off

- create `spec.md`, `plan.md`, and `tasks.md`;
- record the 186 semantic reservation and 188 id selection;
- keep scope backend-first and Phase 5 only;
- declare deterministic/no live LLM default behavior;
- declare OpenRouter optional and environment-gated only;
- declare MySQL8-only persistence and test evidence;
- declare no frontend visual changes;
- save planning evidence under
  `artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.0/`.

### 188.1 Domain Prompt Tracer

Backend domain-only implementation.

Build:

- optional project instruction prompt layer;
- read-only `SkillRegistry` and `SkillManifest`;
- deterministic `PromptMemoryItem` rendering;
- explicit compaction summary prompt layer;
- compatibility with the 184 default layer order when optional inputs are
  absent.

Gates:

- RED unit test for missing prompt memory and skill registry;
- focused prompt assembler unit tests;
- lint/type gates for touched AI Assistant domain/test files;
- AI Assistant kernel regression;
- SQLite/PostgreSQL boundary scan for touched files.

### 188.2 Prompt, Skills, Memory, And Compaction Backend Persistence MVP

Backend-only implementation.

Build:

- prompt layer model and assembler order:
  `base`, `project_instructions`, `skills`, `working_memory`,
  `compaction_summary`, `tools`, `run_state`, `user_message`;
- read-only `SkillRegistry` with typed manifests;
- deterministic skill activation from session context or an explicit backend
  request shape;
- working memory item model and persistence through existing AI Assistant JSON
  context where possible;
- deterministic compaction summary model and persistence;
- harness integration so later runs receive persisted memory and compaction
  layers;
- safe prompt/memory metadata in events, run result, or inspector payloads;
- optional `GET /api/v1/ai-assistant/skills` endpoint if contract tests need a
  direct registry surface.

Gates:

- RED unit tests for prompt layer ordering;
- RED unit tests for skill registry listing and activation;
- RED MySQL8 integration tests for memory and compaction persistence;
- RED contract tests for safe prompt/memory metadata;
- RED backend E2E proving persisted memory and compaction are used by a later
  run;
- focused unit tests;
- MySQL8 integration tests;
- AI Assistant contract tests;
- backend E2E tests;
- lint/type gates used by the AI Assistant backend;
- SQLite scan/boundary evidence for new tests.

### 188.3 Aggregate Backend Acceptance

- rerun 188.1 focused gates;
- rerun relevant 184 AI Assistant regressions for prompt assembly, tool
  registry, security, inspector, and event replay;
- rerun relevant 187 scheduler regressions to prove prompt/memory changes did
  not weaken scheduler metadata or ordering;
- confirm no frontend visual files changed;
- confirm no `app/modules/customer_assistant/**` files changed;
- save final evidence and residual risks;
- update `tasks.md` statuses only after evidence files exist.

## TDD Evidence Discipline

The implementation slice must start with RED tests and save failing output
under:

```text
artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.1/red.txt
```

Recommended RED targets:

```text
rtk pytest tests/unit/ai_assistant/test_prompt_assembler.py -q
rtk pytest tests/unit/ai_assistant/test_skill_registry.py -q
rtk pytest tests/integration/ai_assistant/test_memory_context_persistence.py -q
rtk pytest tests/contract/test_ai_assistant_prompt_context_api.py -q
rtk pytest tests/e2e/test_ai_assistant_prompt_memory_e2e.py -q
```

Names may change during implementation, but evidence must preserve the same
behavioral coverage.

An existing ignored artifact was observed at:

```text
artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.1/red-unit.txt
```

The implementation owner may reuse it only after rerunning and saving current
RED output for the final test names. This documentation slice does not mark any
188.1 implementation task complete.

## Backend Gate Plan

Focused implementation gates:

```text
rtk pytest tests/unit/ai_assistant -q
rtk pytest tests/integration/ai_assistant -q
rtk pytest tests/contract/test_ai_assistant_kernel_api.py tests/contract/test_ai_assistant_security_api.py tests/contract/test_ai_assistant_inspector_api.py -q
rtk pytest tests/e2e/test_ai_assistant_kernel_e2e.py tests/e2e/test_ai_assistant_security_e2e.py -q
```

Add prompt/skills/memory/compaction-specific contract and E2E paths once RED
tests exist.

MySQL8-only confirmation must include either the existing MySQL8 boundary gate
or a focused scan proving the new tests do not introduce SQLite URLs.

## Frontend Gate Plan

No frontend visual work is planned. Do not edit:

```text
frontend/src/**/*.vue
frontend/src/**/*.css
frontend/src/** visual-size TS
```

Because this slice is backend-only, browser UAT and `remScaleClosure` are not
required unless implementation later touches frontend-visible visuals. If that
happens, stop and split the frontend work into a separate spec or slice.

## Live LLM Gate Plan

No live LLM gate is required for 188. Default tests must stay deterministic.

Optional OpenRouter probe requirements:

- skip unless an explicit env flag such as `AI_ASSISTANT_LIVE_LLM=1` is set;
- target qwen3.5-9b unless a later spec explicitly changes the model;
- read credentials only from environment variables;
- do not write credentials to logs or artifacts;
- save skipped/live evidence separately from required GREEN gates;
- never make the optional probe a prerequisite for 188.1 or 188.2 completion.

## Dirty-File Boundary

This spec must not touch the existing dirty customer-assistant files:

```text
app/modules/customer_assistant/domain/service.py
app/modules/customer_assistant/domain/worker_runtime.py
app/modules/customer_assistant/infra/repository.py
```

If a future implementation appears to require those files, pause and create a
separate spec or ask for explicit approval.
