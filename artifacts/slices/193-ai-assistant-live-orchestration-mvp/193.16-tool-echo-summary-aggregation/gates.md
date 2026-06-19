# Gate Evidence

## Frontend Focused

Command:
`rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/aiAssistantTimeline.test.ts`

Result:
`13 passed`

## Frontend Unit + remScaleClosure

Command:
`rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/aiAssistantTimeline.test.ts src/views/aiAssistant/aiAssistantShell.test.ts src/remScaleClosure.test.ts`

Result:
`32 passed`

## Full Frontend Unit

Command:
`rtk npm --prefix frontend run test:unit`

Result:
`96 passed, 414 passed`

## Frontend Build

Command:
`rtk npm --prefix frontend run build`

Result:
`vue-tsc && vite build` completed successfully.

## Backend AI Assistant Unit/Integration/Contract/E2E

Command:
`rtk uv run pytest tests/unit/ai_assistant tests/integration/ai_assistant tests/contract/test_ai_assistant_observability_api.py tests/contract/test_ai_assistant_inspector_api.py tests/contract/test_ai_assistant_kernel_api.py tests/contract/test_ai_assistant_scheduler_api.py tests/contract/test_ai_assistant_live_qwen_api.py tests/contract/test_ai_assistant_live_stream_api.py tests/contract/test_ai_assistant_customer_bridge_api.py tests/contract/test_ai_assistant_session_lifecycle_api.py tests/contract/test_ai_assistant_security_api.py tests/e2e/test_ai_assistant_kernel_e2e.py tests/e2e/test_ai_assistant_security_e2e.py -q`

Result:
`49 passed, 1 warning`
