# Current Loop Scope: Spec 188.5 Session Scope And Prompt Cutover

## Status

    mode: Closed Loop
    active spec: 188-ai-assistant-prompt-skills-memory-compaction
    active slice: 188.5 Session Scope And Prompt Cutover
    phase: COMPLETE
    TDD method: tdd

## Contract

    specs/188-ai-assistant-prompt-skills-memory-compaction/spec.md
    specs/188-ai-assistant-prompt-skills-memory-compaction/plan.md
    specs/188-ai-assistant-prompt-skills-memory-compaction/tasks.md

Behavior:

- persist trusted user/workspace scope on AI Assistant sessions;
- filter list/get/delete/message/run/inspector access by current scope;
- derive workspace identity from server-owned workspace root, never request
  path;
- inject own rolling MEMORY.md into prompt context;
- stop legacy aiAssistantMemory writes and prompt reads;
- preserve required public memory fields as MEMORY.md-derived read-only
  projections.

## Worktree

    branch: codex/spec-188-memory-md
    path: /Users/vincento/work/develop/hify-spec-188-memory-md
    base: 317fad92
    merge target: codex/runtime-v2-production-upgrade
    dirty before slice: no

## Frozen Scope

Allowed:

    app/modules/ai_assistant/domain/
    app/modules/ai_assistant/infra/repository.py
    app/modules/ai_assistant/infra/schema.py
    app/modules/ai_assistant/web/router.py
    app/modules/chat/domain/llm_request.py (typing-only static gate dependency)
    alembic/versions/0032_ai_assistant_memory_scope.py
    tests/unit/ai_assistant/
    tests/integration/ai_assistant/
    tests/contract/test_ai_assistant_memory_scope_api.py
    tests/contract/test_ai_assistant_memory_context_api.py
    tests/e2e/test_ai_assistant_memory_context_e2e.py
    specs/188-ai-assistant-prompt-skills-memory-compaction/tasks.md
    loop/CURRENT.md
    loop/STATE.md
    loop/VERIFIERS.md
    artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.5/

No extractor cadence, token-cost ledger, frontend, customer-assistant, daily
scheduler, or Spec 189 changes.

## Evidence

    artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.5/

## Stop Conditions

Stop and return to Open Loop/Waiting Human if:

- scope requires caller-provided workspace path;
- compatibility requires public field removal;
- memory content must be stored in DB;
- implementation requires customer-assistant/frontend changes;
- migration cannot preserve existing local rows safely.
