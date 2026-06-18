# Slice 193.14 Gates

## Unit

- `rtk uv run pytest tests/unit/ai_assistant/test_tool_duration.py -q`
  - Result: `1 passed`
- `rtk uv run pytest tests/unit/ai_assistant -q`
  - Result: `20 passed`

## Backend AI Assistant Gate

Command:

```bash
rtk uv run pytest tests/unit/ai_assistant tests/integration/ai_assistant tests/contract/test_ai_assistant_observability_api.py tests/contract/test_ai_assistant_inspector_api.py tests/contract/test_ai_assistant_kernel_api.py tests/contract/test_ai_assistant_scheduler_api.py tests/contract/test_ai_assistant_live_qwen_api.py tests/contract/test_ai_assistant_live_stream_api.py tests/contract/test_ai_assistant_customer_bridge_api.py tests/contract/test_ai_assistant_session_lifecycle_api.py tests/contract/test_ai_assistant_security_api.py tests/e2e/test_ai_assistant_kernel_e2e.py tests/e2e/test_ai_assistant_security_e2e.py -q
```

Result:

```text
41 passed, 1 warning in 23.94s
```

## Browser UAT

- Real in-app browser UAT completed against `/ai-assistant`.
- Model: OpenRouter `qwen/qwen3.5-27b`.
- Prompt required a real workspace file-read tool call.
- Visible execution step duration: `1 ms`.
- Visible tool row duration: `1 ms`.
- Visible `0 ms` durations in current step/tool rows: none.
