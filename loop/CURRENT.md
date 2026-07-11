# Current Loop Scope: Spec 190.4 Cost And Aggregate API

## Status

    mode: Closed Loop
    active spec: 190-ai-assistant-observability-benchmark
    active slice: 190.4 Versioned Cost And Aggregate API
    phase: COMPLETE
    TDD method: tdd

## Worktree

    branch: codex/spec-188-memory-md
    path: /Users/vincento/work/develop/hify-spec-188-memory-md
    base: 61f7e559
    merge target: codex/runtime-v2-production-upgrade
    dirty before slice: no

## Tracer

    scoped immutable ledger rows
      -> provider actual / versioned estimate / unknown
      -> timezone-aware summary, daily, session, dimension, detail APIs

## Frozen Scope

Allowed: AI Assistant domain/repository/router/schema, usage contract/unit/E2E tests,
Spec 190 tasks, loop docs, and 190.4 evidence. No frontend or 190.5 work.

## Stop Conditions

Stop if prices must be invented, historical rows must be recalculated, or a
cross-user/admin/billing/budget surface is required.

## Result

Focused 18 passed; AI Assistant broad 216 passed plus 21 subtests. Ruff, mypy,
and diff-check passed. Checker ALL GREEN; Reviewer PASS with no P0/P1/P2.

Residual risk: the bounded 366-branch daily SQL aggregate is not load-tested;
carry this non-blocking performance check into 190.6 aggregate acceptance.
