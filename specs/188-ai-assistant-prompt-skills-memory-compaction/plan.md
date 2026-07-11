# Plan 188: AI Assistant Workspace MEMORY.md

## Architecture

Add four narrow seams under app/modules/ai_assistant:

    MemoryScopeResolver
      trusted user/workspace -> server-owned MEMORY.md path

    MarkdownMemoryStore
      heading scan -> bounded rolling read
      locked merge -> atomic replacement

    MemoryExtractionCoordinator
      completed-run cursor -> batches of three -> model extractor

    MemoryPromptProjection
      rolling MEMORY.md -> existing working-memory prompt layer
      -> compatibility inspector projection

MySQL8 stores scope binding and extraction operational metadata only. Suggested
metadata:

    user_id
    workspace_id
    batch_key
    batch_status
    source_run_ids
    last_processed_run_id
    pending_success_count
    input_memory_hash
    target_memory_hash
    last_attempt_at
    last_success_at
    last_error_code

Memory text never enters this table.

File/DB crash protocol:

1. Claim a unique batch key for the three source runs.
2. Record current input hash.
3. Under scope lock, compute merged file and record target hash without storing
   memory text in DB.
4. Atomically replace MEMORY.md.
5. Mark batch/cursor complete.
6. On retry, target hash means write already landed; input hash means write is
   still pending; any third hash forces locked reconciliation before progress.

## Migration

1. Add trusted user/workspace scope to AI Assistant sessions and all access
   paths before enabling MEMORY.md reads.
2. Introduce MEMORY.md reader/writer with fake scopes and deterministic token
   estimator.
3. Switch prompt memory truth from context_json.aiAssistantMemory to the
   rolling file projection.
4. Preserve public memory payload shape as a derived read-only projection where
   current frontend/contracts require it.
5. Stop legacy JSON writes. Existing JSON content is not auto-imported because
   it may mix session-local and durable semantics; migration requires a
   separate explicit tool if later desired.

## Slice Order

### 188.4 Scope Isolation And Markdown Store

Build:

- trusted user/workspace scope resolver;
- server-owned MEMORY.md path;
- strict date-heading parser;
- rolling 30-day line-range reader;
- per-scope lock, atomic writer, full-day 100-token merge.

RED/gates:

- traversal, symlink escape, user/workspace isolation;
- rolling start-line selection with variable lines per day;
- missing/malformed/future headings;
- concurrent write, dedupe, and 100-token cap;
- focused unit, security contract, lint/type, and diff checks.

### 188.5 Session Scope And Prompt Cutover

Build:

- persist user/workspace scope on AI Assistant session/run access;
- require scoped list/get/delete/message/inspector operations;
- inject rolling MEMORY.md into existing working-memory prompt layer;
- stop reading/writing legacy JSON memory as canonical content;
- retain read-only compatibility projection where needed.

RED/gates:

- MySQL8 cross-scope denial tests;
- contract tests for scoped APIs and compatibility payload;
- backend E2E proving later session/run receives only own 30-day memory;
- existing kernel, security, inspector, event, scheduler, and ToolRunner
  regressions.

### 188.6 Three-Successful-Run Extraction

Build:

- durable per-scope cursor and count;
- COMPLETED-only batching across sessions;
- configured model extractor with fake test adapter;
- idempotent retry and atomic cursor advance;
- batch/input/target hash recovery across DB/file crash windows;
- observable extraction result/error without changing completed run outcome.

RED/gates:

- exact trigger on third unprocessed completed run;
- failed/cancelled/denied/duplicate runs excluded;
- retry after model or file-write failure;
- crash before/after atomic replacement and before cursor completion;
- concurrent completion produces one batch;
- MySQL8 integration and backend E2E.

### 188.7 Aggregate Acceptance

- rerun 188.4-188.6 gates;
- prove DB contains operational metadata, not memory text;
- prove no fixed tail-N reader;
- prove no new legacy aiAssistantMemory writes;
- confirm daily scheduler, frontend visuals, and customer-assistant remain
  untouched;
- save Checker and Reviewer reports.

## TDD And Evidence

Before each implementation slice:

1. run loop/hooks/skill-preflight.sh --required tdd;
2. invoke the tdd skill;
3. save observable RED before implementation;
4. implement minimal GREEN and refactor;
5. run contracted gates, Checker, Reviewer, then slice commit.

Evidence root:

    artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/<slice>/

Recommended test targets:

    tests/unit/ai_assistant/test_markdown_memory_store.py
    tests/integration/ai_assistant/test_memory_scope_persistence.py
    tests/contract/test_ai_assistant_memory_scope_api.py
    tests/e2e/test_ai_assistant_memory_markdown_e2e.py

Final names may differ; behavioral coverage may not.

## Capability And Stop Gates

Available now:

- local filesystem and atomic replacement;
- MySQL8 test harness;
- existing RequestContext host seam;
- existing fake/live model adapter seams;
- mandatory tdd skill.

Stop and return to Open Loop if:

- trusted workspace identity cannot be resolved without accepting arbitrary
  client paths;
- session scope requires weakening existing auth/host isolation;
- public API removal becomes necessary;
- implementation needs customer-assistant changes, daily scheduling, or another
  durable memory source.
