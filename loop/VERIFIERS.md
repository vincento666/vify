# Loop Verifiers: Spec 190.3

## Focused

    rtk uv run pytest tests/unit/ai_assistant/test_model_usage.py tests/integration/ai_assistant/test_model_usage_repository.py tests/contract/test_ai_assistant_model_usage_capture_api.py tests/integration/ai_assistant/test_memory_extraction_cursor.py -q --tb=short

## Static

    rtk uv run ruff check app/modules/ai_assistant tests/unit/ai_assistant/test_model_usage.py tests/integration/ai_assistant/test_model_usage_repository.py tests/contract/test_ai_assistant_model_usage_capture_api.py alembic/versions/0034_ai_assistant_model_usage.py
    rtk uv run mypy app/modules/ai_assistant
    rtk git diff --check

## Required Proof

- one scoped row per call; replay is idempotent;
- pending streaming row finalizes once;
- optional token breakouts stay null when unavailable;
- cache/reasoning never inflate total;
- normal planner and memory extractor both record usage;
- enclosing run failure does not remove recorded provider usage;
- migration and persistence use MySQL8.
