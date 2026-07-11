# Loop Verifiers: Spec 188.7

## Aggregate Behavior

    rtk uv run pytest tests/unit/ai_assistant/test_markdown_memory_store.py tests/unit/ai_assistant/test_memory_extraction.py tests/integration/ai_assistant/test_memory_scope_persistence.py tests/integration/ai_assistant/test_memory_extraction_cursor.py tests/contract/test_ai_assistant_memory_scope_api.py tests/contract/test_ai_assistant_memory_context_api.py tests/contract/test_ai_assistant_memory_extraction_api.py tests/e2e/test_ai_assistant_memory_context_e2e.py tests/e2e/test_ai_assistant_memory_extraction_e2e.py tests/unit/ai_assistant/test_memory_context.py tests/unit/ai_assistant/test_qwen_live_planner.py -q --tb=short

## Broad Regression

    rtk uv run pytest tests/unit/ai_assistant tests/integration/ai_assistant tests/contract/test_ai_assistant_*.py -q --tb=short

## Static

    rtk uv run ruff check app/modules/ai_assistant tests/unit/ai_assistant tests/integration/ai_assistant/test_memory_scope_persistence.py tests/integration/ai_assistant/test_memory_extraction_cursor.py tests/contract/test_ai_assistant_memory_scope_api.py tests/contract/test_ai_assistant_memory_context_api.py tests/contract/test_ai_assistant_memory_extraction_api.py tests/e2e/test_ai_assistant_memory_context_e2e.py tests/e2e/test_ai_assistant_memory_extraction_e2e.py alembic/versions/0032_ai_assistant_memory_scope.py alembic/versions/0033_ai_assistant_memory_cursor.py
    rtk uv run mypy app/modules/ai_assistant
    rtk git diff --check

## Boundary Scans

- inspect 0032/0033 and live schema for memory-text columns;
- search production writes for `aiAssistantMemory` and tail-based MEMORY.md reads;
- inspect Spec 188 commit path lists for frontend/customer-assistant/Spec 189 drift;
- confirm no daily scheduler implementation was introduced.

## Gate Applicability

- Unit, MySQL8 integration/contract, backend E2E, migration, static: required.
- Browser/rem/frontend/live LLM: N/A because Spec 188 explicitly has no visual change and deterministic fake extraction is the required gate.
