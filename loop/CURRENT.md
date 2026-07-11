# Current Loop Scope: Spec 188.6 Three-Successful-Run Extraction

## Status

    mode: Closed Loop
    active spec: 188-ai-assistant-prompt-skills-memory-compaction
    active slice: 188.6 Three-Successful-Run Extraction
    phase: COMPLETE
    TDD method: tdd

## Contract

    specs/188-ai-assistant-prompt-skills-memory-compaction/spec.md
    specs/188-ai-assistant-prompt-skills-memory-compaction/plan.md
    specs/188-ai-assistant-prompt-skills-memory-compaction/tasks.md

Behavior:

- count only new COMPLETED runs across sessions in one user/workspace scope;
- process oldest complete batches of three with a configured extractor;
- atomically merge durable facts into today's MEMORY.md;
- advance the cursor only after file replacement succeeds;
- recover extraction/write/cursor crash windows idempotently;
- leave a final one or two successful runs pending.

## Worktree

    branch: codex/spec-188-memory-md
    path: /Users/vincento/work/develop/hify-spec-188-memory-md
    base: 268768a7
    merge target: codex/runtime-v2-production-upgrade
    dirty before slice: no

## Frozen Scope

Allowed:

    app/modules/ai_assistant/domain/memory_extraction.py
    app/modules/ai_assistant/domain/markdown_memory.py
    app/modules/ai_assistant/domain/harness.py
    app/modules/ai_assistant/infra/repository.py
    app/modules/ai_assistant/infra/schema.py
    app/modules/ai_assistant/web/router.py
    alembic/versions/0033_ai_assistant_memory_cursor.py
    tests/unit/ai_assistant/
    tests/integration/ai_assistant/
    tests/contract/test_ai_assistant_memory_extraction_api.py
    tests/e2e/test_ai_assistant_memory_extraction_e2e.py
    specs/188-ai-assistant-prompt-skills-memory-compaction/tasks.md
    loop/CURRENT.md
    loop/STATE.md
    loop/VERIFIERS.md
    artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.6/

No daily scheduler, trailing one/two flush, token-cost, frontend,
customer-assistant, or Spec 189 changes.

## Stop Conditions

Stop and return to Open Loop/Waiting Human if:

- extraction requires storing memory text in DB;
- a live external key becomes mandatory for deterministic gates;
- daily scheduler or trailing one/two flush enters scope;
- recovery requires weakening atomic file writes;
- token-cost/frontend/customer-assistant scope is required.
