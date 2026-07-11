# Current Loop Scope: Spec 190.3 Per-Call Usage Ledger

## Status

    mode: Closed Loop
    active spec: 190-ai-assistant-observability-benchmark
    active slice: 190.3 Per-Call Usage Ledger
    phase: COMPLETE
    TDD method: tdd

## Contract

    specs/190-ai-assistant-observability-benchmark/spec.md
    specs/190-ai-assistant-observability-benchmark/plan.md
    specs/190-ai-assistant-observability-benchmark/tasks.md

Tracer:

    one live planner call or memory-extractor call
      -> one scoped idempotent ledger row
      -> provider token dimensions preserved
      -> cache/reasoning remain breakouts

## Worktree

    branch: codex/spec-188-memory-md
    path: /Users/vincento/work/develop/hify-spec-188-memory-md
    base: e40743e7
    merge target: codex/runtime-v2-production-upgrade
    dirty before slice: no

## Frozen Scope

Allowed:

    app/modules/ai_assistant/
    alembic/versions/0034_ai_assistant_model_usage.py
    tests/unit/ai_assistant/test_model_usage.py
    tests/integration/ai_assistant/test_model_usage_repository.py
    tests/contract/test_ai_assistant_model_usage_capture_api.py
    tests/integration/ai_assistant/test_memory_extraction_cursor.py
    specs/190-ai-assistant-observability-benchmark/tasks.md
    loop/
    artifacts/slices/190-ai-assistant-observability-benchmark/190.3/

No aggregate API, frontend, benchmark, governance, alert, or budget changes.

## Stop Conditions

Stop for product input if provider token dimensions cannot be normalized without
inventing values, or if trusted scope/session attribution is unavailable.
