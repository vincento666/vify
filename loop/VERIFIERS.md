# Loop Verifiers: Spec 188.6

## RED / Focused Integration

    rtk uv run pytest tests/integration/ai_assistant/test_memory_extraction_cursor.py -q

## Contract And E2E

    rtk uv run pytest tests/contract/test_ai_assistant_memory_extraction_api.py -q
    rtk uv run pytest tests/e2e/test_ai_assistant_memory_extraction_e2e.py -q

## Regression

    rtk uv run pytest tests/unit/ai_assistant/test_markdown_memory_store.py tests/unit/ai_assistant/test_memory_extraction.py -q
    rtk uv run pytest tests/integration/ai_assistant/test_harness_repository.py -q

## Static And Migration

    rtk uv run ruff check app/modules/ai_assistant tests/unit/ai_assistant tests/integration/ai_assistant/test_memory_extraction_cursor.py tests/contract/test_ai_assistant_memory_extraction_api.py tests/e2e/test_ai_assistant_memory_extraction_e2e.py alembic/versions/0033_ai_assistant_memory_cursor.py
    rtk uv run mypy app/modules/ai_assistant
    rtk git diff --check

## Gate Applicability

- Unit, MySQL8 integration/contract, backend E2E, migration: required.
- Browser/rem/frontend/live LLM: N/A; deterministic fake extractor required.

## Checker

Verify:

- only COMPLETED, unreplayed runs count across sessions;
- batches are oldest-first, exactly three, scoped, and cursor-backed;
- failed extraction/write never advances cursor or changes run completion;
- target/input hash recovery is idempotent across crash windows;
- memory/resource named locks remain on their acquiring physical connection and release succeeds;
- DB stores operational metadata only, never extracted memory text.

## Reviewer

Audit:

- coordination is concurrency-safe and does not hold DB sessions over model calls;
- atomic file replacement is the commit point before cursor advance;
- retry does not lose or duplicate a batch;
- no daily scheduler/token-cost/frontend/customer-assistant scope drift.
