# 133 Plan

1. Add RED coverage for Runtime Lab and Customer Assistant production
   entrypoints using a patched preferred agent name and fake provider client.
2. Keep legacy v1 workflow service behavior intact, especially fake-mode mock
   fallback when no provider-backed agent is present.
3. Add runtime-v2-only completer resolver wiring at the two web entrypoints.
4. Run focused entrypoint tests, Customer Assistant SOP adapter regression,
   Runtime Lab chatflow SOP e2e regression, and Ruff.

## Commands

```bash
rtk env PYTHONPATH=. uv run pytest tests/integration/runtime_lab/test_demo_entrypoint_v2_provider_backed_sop.py
rtk env PYTHONPATH=. uv run pytest tests/integration/customer_assistant/test_chatflow_sop_worker_v2_adapter.py tests/e2e/test_runtime_lab_chatflow_sop_api_e2e.py
rtk env PYTHONPATH=. uv run ruff check app/modules/runtime_lab/web/router.py app/modules/customer_assistant/web/router.py tests/integration/runtime_lab/test_demo_entrypoint_v2_provider_backed_sop.py
```
