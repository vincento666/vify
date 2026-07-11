# Loop Verifiers: Spec 190.4

## Focused

    rtk uv run pytest tests/unit/ai_assistant/test_model_usage_cost.py tests/integration/ai_assistant/test_model_usage_repository.py tests/contract/test_ai_assistant_usage_api.py tests/e2e/test_ai_assistant_usage_e2e.py tests/contract/test_ai_assistant_model_usage_capture_api.py -q --tb=short

## Required Proof

- provider actual cost wins;
- versioned configured estimate is fixed at write time;
- missing price stays null with unknown counters;
- summary/session/total/daily/dimensions/detail reconcile;
- timezone date boundaries and range validation are correct;
- every endpoint enforces trusted user/workspace/session scope;
- existing envelope remains compatible.

## Static

    rtk uv run ruff check app/modules/ai_assistant tests/unit/ai_assistant/test_model_usage_cost.py tests/contract/test_ai_assistant_usage_api.py tests/e2e/test_ai_assistant_usage_e2e.py
    rtk uv run mypy app/modules/ai_assistant
    rtk git diff --check

## Broad

    rtk uv run pytest tests/unit/ai_assistant tests/integration/ai_assistant tests/contract/test_ai_assistant_*.py -q --tb=short
