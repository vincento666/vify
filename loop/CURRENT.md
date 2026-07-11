# Current Loop Scope: Spec 188.4 MEMORY.md Store

## Status

    mode: Closed Loop
    active spec: 188-ai-assistant-prompt-skills-memory-compaction
    active slice: 188.4 Scope Isolation And Markdown Store
    phase: complete; slice commit pending
    TDD method: tdd

## Contract

    specs/188-ai-assistant-prompt-skills-memory-compaction/spec.md
    specs/188-ai-assistant-prompt-skills-memory-compaction/plan.md
    specs/188-ai-assistant-prompt-skills-memory-compaction/tasks.md

Behavior:

- trusted user/workspace scope resolves one server-owned MEMORY.md;
- arbitrary paths, traversal, and symlink escape are rejected;
- reader locates strict date headings and reads only rolling 30-day content;
- writer merges/deduplicates today's block, caps full day at 100 tokens, locks
  scope, and atomically replaces the file.

## Worktree

    branch: codex/spec-188-memory-md
    path: /Users/vincento/work/develop/hify-spec-188-memory-md
    base: 1ee8dc5e
    merge target: codex/runtime-v2-production-upgrade
    dirty before slice: no

## Frozen Scope

Allowed:

    app/modules/ai_assistant/domain/markdown_memory.py
    tests/unit/ai_assistant/test_markdown_memory_store.py
    tests/unit/ai_assistant/test_memory_context.py
    tests/unit/ai_assistant/test_file_workspace.py
    specs/188-ai-assistant-prompt-skills-memory-compaction/tasks.md
    loop/CURRENT.md
    loop/STATE.md
    loop/VERIFIERS.md
    artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.4/

No harness/session DB/API/frontend/customer-assistant changes. Those start in
later accepted slices.

Next accepted slice after commit: 188.5 Session Scope And Prompt Cutover.

## Evidence

    artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.4/

## Stop Conditions

Stop and return to Open Loop/Waiting Human if:

- trusted scope requires a caller-provided path;
- implementation needs session schema/API/harness changes;
- a new dependency is required;
- public behavior outside 188.4 must change;
- test failure cannot be reduced within frozen scope.
