# Loop Verifiers: Unified Runtime V2 and Workflow/Chatflow Integration

## Merge Safety

    rtk git status --short
    rtk git diff --check
    rtk git diff --cached --check

## Runtime V2, SSE, and Customer Assistant

    rtk uv run pytest tests/integration/workflow/test_runtime_v2_parallel_waves.py tests/integration/workflow/test_runtime_v2_redis_streams.py tests/contract/runtime/test_sse_reconnect.py -q --tb=short
    rtk uv run pytest tests/integration/workflow/test_runtime_v2_provider_backed_llm.py tests/unit/chat/test_llm_request_client.py tests/contract/test_runtime_lab_sop_live_stream_api.py tests/e2e/customer_assistant/test_customer_assistant_chatflow_sop_live_stream.py -q --tb=short
    rtk uv run pytest tests/unit/runtime_lab/test_chatflow_sop_runtime_adapter_gateway.py tests/unit/workflow/test_runtime_invocation_gateway.py tests/unit/workflow/test_runtime_job_worker.py tests/integration/runtime_lab/test_chatflow_sop_runtime_adapter.py -q --tb=short

## AI Assistant Memory, Usage, and Migrations

    rtk uv run pytest tests/unit/ai_assistant/test_markdown_memory_store.py tests/unit/ai_assistant/test_memory_extraction.py tests/unit/ai_assistant/test_model_usage.py tests/unit/ai_assistant/test_model_usage_cost.py tests/integration/ai_assistant/test_memory_extraction_cursor.py tests/integration/ai_assistant/test_memory_scope_persistence.py tests/integration/ai_assistant/test_model_usage_repository.py tests/contract/test_ai_assistant_memory_context_api.py tests/contract/test_ai_assistant_memory_extraction_api.py tests/contract/test_ai_assistant_memory_scope_api.py tests/contract/test_ai_assistant_model_usage_capture_api.py tests/contract/test_ai_assistant_usage_api.py -q --tb=short

## Workflow/Chatflow Controls and Frontend

    rtk npm run test:unit -- src/views/workflow/variableCatalog.test.ts src/views/workflow/nodeTestFixtures.test.ts src/views/workflow/workflowCanvasResponsiveLayout.test.ts src/views/workflow/workflowCanvasResponsiveProgressiveCollapse.test.ts src/utils/remGovernance.test.ts src/views/workflow/workflowCanvasRemGovernance.test.ts
    rtk npm run test:unit -- --run src/views/chat/runtimeLabSopEventStream.test.ts src/views/chat/unifiedRoutingChatLab.test.ts src/api/runtimeLab.test.ts src/views/aiAssistant/aiAssistantUsageDashboard.behavior.test.ts
    rtk npm run build

Run frontend commands from `frontend/`. Browser and live-provider UAT are
historical evidence only for this merge: no new provider credentials or spend
are authorized or needed.

## Final

    rtk uv run ruff check app/modules/ai_assistant app/modules/runtime_lab app/modules/workflow
    rtk git diff --check
