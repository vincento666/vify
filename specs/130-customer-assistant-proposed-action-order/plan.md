# 130 Plan

1. Use the existing customer-assistant runtime E2E failure as RED evidence.
2. Add a service-layer formatted-action sorter so API-visible actions keep a
   stable product priority independent of row creation time.
3. Rerun the failing E2E, customer-assistant integration/contract, focused
   reply-draft contract, and Ruff.

## Commands

```bash
rtk env PYTHONPATH=. uv run pytest tests/e2e/customer_assistant/test_customer_assistant_runtime_e2e.py::CustomerAssistantRuntimeE2ETest::test_refund_and_baggage_multitask_resume_proposed_action_and_events
rtk env PYTHONPATH=. uv run pytest tests/e2e/customer_assistant tests/integration/customer_assistant tests/contract/customer_assistant
rtk env PYTHONPATH=. uv run ruff check app/modules/customer_assistant/domain/service.py
```
