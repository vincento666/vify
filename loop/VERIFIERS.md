# Loop Verifiers

These commands verify the runtime 213-221 closure branch.

## Focused 213 Async Default

```bash
rtk uv run pytest tests/unit/core/test_config.py tests/unit/runtime_lab/test_runtime_lab_web_factory.py -q
rtk uv run pytest tests/integration/runtime_lab/test_sop_router_async_refs.py tests/integration/customer_assistant/test_worker_default_async_refs.py -q
```

## Runtime Regression

```bash
rtk uv run pytest tests/unit/core tests/unit/runtime tests/unit/runtime_lab tests/unit/workflow -q
rtk uv run pytest tests/contract/runtime tests/contract/runtime_dag tests/contract/runtime_gateway tests/contract/runtime_jobs tests/contract/runtime_lab tests/contract/workflow -q
rtk uv run pytest tests/integration/runtime tests/integration/runtime_jobs tests/integration/runtime_lab tests/integration/workflow tests/integration/chatflow tests/integration/customer_assistant -q
rtk npm --prefix frontend run test:unit -- src/router/runtime-ops-router.test.ts src/views/runtimeOps
rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts
```

## Spec 222 Protection

```bash
rtk uv run pytest tests/unit/ai_assistant/test_qwen_live_planner.py tests/contract/test_ai_assistant_kernel_api.py tests/contract/test_ai_assistant_security_api.py -q
rtk npm --prefix frontend run test:unit -- src/api/aiAssistant.test.ts src/views/aiAssistant/aiAssistantShell.test.ts
rtk git diff --name-status d6fc969c..HEAD -- app/modules/ai_assistant frontend/src/views/aiAssistant specs/222-ai-assistant-general-harness-mvp tests/unit/ai_assistant tests/contract/test_ai_assistant_*.py tests/e2e/test_ai_assistant_*.py tests/eval/test_ai_assistant_*.py tests/integration/ai_assistant tests/support/ai_assistant_memory_repo.py
rtk git diff --check
```
