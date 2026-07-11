# Loop Verifiers: Spec 190.6

## Focused

    rtk uv run pytest tests/contract/test_ai_assistant_model_usage_capture_api.py tests/integration/ai_assistant/test_model_usage_repository.py tests/contract/test_ai_assistant_usage_api.py tests/e2e/test_ai_assistant_usage_e2e.py -q --tb=short
    cd frontend && rtk npm run test:unit -- --run src/views/aiAssistant/aiAssistantUsageViewModel.test.ts src/views/aiAssistant/aiAssistantUsageDashboard.test.ts src/views/aiAssistant/aiAssistantUsageDashboard.behavior.test.ts src/router/ai-assistant-routes.test.ts src/api/aiAssistant.test.ts

## Required Proof

- planner ledger equals run inspector and aggregate API totals;
- memory extractor rows reconcile with scoped repository aggregate;
- migration, replay/idempotency, timezone, price stability, and all endpoint isolation;
- frontend projections, pagination, states, rem, build, and Browser UAT;
- no benchmark/governance/alert/budget/billing/admin scope.

## Static

    rtk uv run ruff check app/modules/ai_assistant tests/contract/test_ai_assistant_model_usage_capture_api.py tests/integration/ai_assistant/test_model_usage_repository.py tests/contract/test_ai_assistant_usage_api.py tests/e2e/test_ai_assistant_usage_e2e.py
    rtk uv run mypy app/modules/ai_assistant
    cd frontend && rtk npm run test:unit -- --run src/remScaleClosure.test.ts
    cd frontend && rtk npm run build
    cd frontend && rtk npm run dev -- --host 127.0.0.1 --port 5174
    cd frontend && rtk node e2e/ai-assistant-usage-uat.mjs
    rtk git diff --check

## Broad

    rtk uv run pytest tests/unit/ai_assistant tests/integration/ai_assistant tests/contract/test_ai_assistant_*.py -q --tb=short
    cd frontend && rtk npm run test:unit
