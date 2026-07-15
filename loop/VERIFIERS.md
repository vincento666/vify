# Loop Verifiers: Spec 225

## Focused

    rtk uv run pytest tests/integration/workflow/test_runtime_v2_parallel_waves.py -q --tb=short
    rtk uv run pytest tests/integration/workflow/test_runtime_v2_redis_streams.py tests/contract/runtime/test_sse_reconnect.py -q --tb=short
    rtk uv run pytest tests/integration/workflow/test_runtime_v2_error_routing.py tests/integration/workflow/test_runtime_v2_shared_core.py tests/contract/test_runtime_lab_sop_live_stream_api.py tests/e2e/customer_assistant/test_customer_assistant_chatflow_sop_live_stream.py -q --tb=short

    rtk uv run pytest tests/unit/chat/test_llm_request_client.py tests/unit/customer_assistant/test_shadow.py tests/integration/customer_assistant/test_shadow_runtime.py tests/integration/customer_assistant/test_llm_primary_runtime.py tests/integration/customer_assistant/test_chatflow_sop_worker_v2_adapter.py tests/integration/customer_assistant/test_worker_default_async_refs.py tests/integration/runtime_lab/test_demo_entrypoint_v2_provider_backed_sop.py tests/e2e/customer_assistant/test_customer_assistant_sse_streaming.py tests/e2e/customer_assistant/test_customer_assistant_chatflow_sop_live_stream.py tests/e2e/customer_assistant/test_customer_assistant_runtime_e2e.py -q --tb=short

    rtk uv run pytest tests/contract/test_runtime_lab_sop_live_stream_api.py tests/integration/runtime_lab/test_sop_live_stream.py -q --tb=short
    rtk uv run pytest tests/unit/runtime_lab/test_chatflow_sop_runtime_adapter_gateway.py tests/unit/workflow/test_runtime_invocation_gateway.py tests/unit/workflow/test_runtime_job_worker.py tests/integration/runtime_lab/test_chatflow_sop_runtime_adapter.py -q --tb=short
    rtk uv run pytest tests/integration/workflow/test_runtime_v2_provider_backed_llm.py tests/unit/chat/test_llm_request_client.py tests/e2e/test_runtime_lab_chatflow_sop_api_e2e.py -q --tb=short
    cd frontend && rtk npm run test:unit -- --run src/views/chat/runtimeLabSopEventStream.test.ts src/views/chat/unifiedRoutingChatLab.test.ts src/api/runtimeLab.test.ts

## Required Proof

- `messages:stream` emits compatible `delta|done|error`, while JSON `messages`
  stays compatible;
- real provider chunks are evented before node/run completion; non-stream
  providers do not fake chunks;
- start and resume return durable refs and worker owns execution;
- reconnect cursor is ordered and duplicate-free within retained events;
- UI incrementally merges, reconnects, cleans up, and uses JSON fallback only
  before any stream frame; post-frame disconnect is explicit and retryable;
- no Customer Assistant, scheduler/deployment, migration, or unrelated public
  contract drift.
- Provider Transport async capability is hidden behind the existing synchronous
  facade; Customer Assistant's public SSE, worker, and shadow behavior remains
  compatible.
- 225.7 proves only selected independent LLM/KNOWLEDGE/safe-TOOL frontier
  overlap; safe Tool pre-dispatch idempotency/receipt and duplicate/takeover
  behavior are covered without an attempt ledger; timeout is fail-fast and late
  output is fenced; Workflow result data adds `errorCode` and a sanitized
  generic-message `failure`, RuntimeLab adds `failure` to compatible SSE
  `error`, and a failed Chatflow turn cannot poison the next eligible turn.
- A production MCP Tool without a provider-native idempotency receipt remains
  serial. The safe-Tool overlap proof applies only to adapters that expose the
  explicit native idempotent-dispatch contract; it must not be interpreted as
  a claim about the current `McpFacade`.
- 225.8 must prove a Redis XADD/outbox publication reorder cannot reorder or
  duplicate the Runtime V2 SSE projection: the normal contiguous path stays
  Redis-only, while a gap reads a fresh durable backlog before terminal output.

## Static

    rtk uv run ruff check app/modules/runtime_lab app/modules/workflow tests/contract/test_runtime_lab_sop_live_stream_api.py tests/integration/runtime_lab/test_sop_live_stream.py
    rtk uv run mypy app/modules/runtime_lab app/modules/workflow
    cd frontend && rtk npm run test:unit -- --run src/remScaleClosure.test.ts
    cd frontend && rtk npm run build
    cd frontend && rtk npm run dev -- --host 127.0.0.1 --port 5174
    cd frontend && rtk node e2e/runtime-lab-sop-live-stream-uat.mjs
    rtk git diff --check

## Broad

    rtk uv run pytest tests/unit/runtime_lab tests/integration/runtime_lab tests/contract/test_runtime_lab_*.py tests/e2e/test_runtime_lab_chatflow_sop_api_e2e.py tests/e2e/test_chatflow_runs_stream_api_e2e.py tests/integration/workflow/test_chatflow_streaming_api.py -q --tb=short
    cd frontend && rtk npm run test:unit
