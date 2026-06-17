# 132 Plan

1. Add API-level RED coverage for provider-backed runtime-v2 LLM execution.
2. Expose a small WorkflowService completer factory that reuses the existing
   live-agent/provider/model/fallback logic.
3. Let runtime-v2 resolve a completer by owner id at execution time so async
   completion threads and resume paths share the same behavior.
4. Wire workflow/chatflow runtime-v2 router services and background completion
   services to that resolver.
5. Run focused integration gates, legacy LLM regressions, runtime-v2
   regressions, and Ruff.

## Commands

```bash
rtk env PYTHONPATH=. uv run pytest tests/integration/workflow/test_runtime_v2_provider_backed_llm.py
rtk env PYTHONPATH=. uv run pytest tests/unit/workflow/test_llm_node_completer.py tests/unit/workflow/test_service_provider_llm.py
rtk env PYTHONPATH=. uv run pytest tests/unit/workflow/test_runtime_v2_core.py tests/integration/workflow/test_workflow_runtime_v2_facade.py tests/integration/workflow/test_chatflow_runtime_v2_facade.py tests/integration/workflow/test_runtime_v2_safe_node_coverage_pack2.py
rtk env PYTHONPATH=. uv run ruff check app/modules/workflow/domain/runtime_v2.py app/modules/workflow/domain/service.py app/modules/workflow/web/router.py tests/integration/workflow/test_runtime_v2_provider_backed_llm.py
```
