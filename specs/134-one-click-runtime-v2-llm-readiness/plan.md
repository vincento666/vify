# 134 Plan

1. Add RED assertions to one-click seed manifest coverage.
2. Add a non-secret runtime-v2 LLM readiness section derived from existing seed
   provider/model verification.
3. Include readiness in both the written report and in-memory report.
4. Run focused seed tests and Ruff.

## Commands

```bash
rtk env PYTHONPATH=. uv run pytest tests/integration/customer_assistant/test_one_click_demo_seed.py
rtk env PYTHONPATH=. uv run ruff check app/modules/demo/mvp_seed.py tests/integration/customer_assistant/test_one_click_demo_seed.py
```
