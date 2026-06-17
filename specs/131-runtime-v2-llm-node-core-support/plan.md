# 131 Plan

1. Add RED integration coverage that expects a Workflow runtime-v2 LLM node to
   execute and emit node events.
2. Keep unsupported graph coverage by using a publishable `branching_edges`
   topology at API level and a still-unsupported `TOOL_CALL` node at
   compatibility-checker level.
3. Reuse `LlmNodeExecutor` from the legacy engine inside runtime v2.
4. Run focused runtime-v2 tests and Ruff.

## Commands

```bash
rtk env PYTHONPATH=. uv run pytest tests/integration/workflow/test_workflow_runtime_v2_facade.py::WorkflowRuntimeV2FacadeTest::test_workflow_v2_executes_llm_node_with_runtime_events
rtk env PYTHONPATH=. uv run pytest tests/unit/workflow/test_runtime_v2_core.py tests/integration/workflow/test_workflow_runtime_v2_facade.py tests/integration/workflow/test_chatflow_runtime_v2_facade.py tests/integration/workflow/test_runtime_v2_safe_node_coverage_pack2.py tests/integration/customer_assistant/test_chatflow_sop_worker_v2_adapter.py
rtk env PYTHONPATH=. uv run pytest tests/unit/workflow/test_llm_node_completer.py tests/integration/workflow/test_llm_model_parameters.py tests/integration/workflow/test_workflow_linear_run.py tests/integration/workflow/test_chatflow_conversation_run.py
rtk env PYTHONPATH=. uv run ruff check app/modules/workflow/domain/runtime_v2.py tests/unit/workflow/test_runtime_v2_core.py tests/integration/workflow/test_workflow_runtime_v2_facade.py tests/integration/workflow/test_chatflow_runtime_v2_facade.py tests/integration/workflow/test_runtime_v2_safe_node_coverage_pack2.py tests/integration/customer_assistant/test_chatflow_sop_worker_v2_adapter.py
```
