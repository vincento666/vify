# 193.3 Gate Evidence

## Passed

- Backend unit:
  `rtk uv run pytest tests/unit/ai_assistant`
  Result: 16 passed.
- Backend live/SSE contract:
  `rtk uv run python -m unittest tests.contract.test_ai_assistant_live_qwen_api tests.contract.test_ai_assistant_live_stream_api`
  Result: 5 passed.
- Python compile:
  `rtk uv run python -m compileall app/modules/ai_assistant app/modules/chat/domain/llm_request.py`
  Result: passed.
- Ruff:
  `rtk uv run ruff check app/modules/ai_assistant app/modules/chat/domain/llm_request.py tests/contract/test_ai_assistant_live_qwen_api.py tests/contract/test_ai_assistant_live_stream_api.py tests/support/ai_assistant_memory_repo.py`
  Result: All checks passed.
- Frontend focused unit + rem:
  `rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/aiAssistantShell.test.ts src/views/aiAssistant/aiAssistantTimeline.test.ts src/remScaleClosure.test.ts`
  Result: 14 passed.
- Frontend full unit:
  `rtk npm --prefix frontend run test:unit`
  Result: 95 files passed, 385 tests passed.
- Frontend build:
  `rtk npm --prefix frontend run build`
  Result: passed.
- MySQL8-backed AI Assistant integration:
  `rtk env HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL=<redacted> uv run pytest tests/integration/ai_assistant -q`
  Result: 3 passed.
- MySQL8-backed AI Assistant contract:
  `rtk env HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL=<redacted> uv run pytest tests/contract/test_ai_assistant_*.py -q`
  Result: 16 passed.
- MySQL8-backed AI Assistant e2e:
  `rtk env HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL=<redacted> uv run pytest tests/e2e/test_ai_assistant_kernel_e2e.py tests/e2e/test_ai_assistant_security_e2e.py -q`
  Result: 2 passed.
- Real OpenRouter Qwen live smoke:
  `rtk env OPENROUTER_API_KEY=<redacted> uv run pytest tests/e2e/test_ai_assistant_live_qwen_openrouter_e2e.py -q`
  Result: 1 passed.

## MySQL8 Privilege Closure

The following MySQL-backed gates were first attempted without
`HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL` and failed before test bodies could run
because the local `hify` MySQL8 user could create disposable databases but
could not grant table/index privileges inside them:

- `rtk uv run pytest tests/integration/ai_assistant`
- `rtk uv run pytest tests/e2e/test_ai_assistant_kernel_e2e.py tests/e2e/test_ai_assistant_security_e2e.py tests/e2e/test_ai_assistant_live_qwen_openrouter_e2e.py`
- `rtk uv run pytest tests/contract/test_ai_assistant_kernel_api.py tests/contract/test_ai_assistant_security_api.py tests/contract/test_ai_assistant_scheduler_api.py tests/contract/test_ai_assistant_inspector_api.py tests/contract/test_ai_assistant_observability_api.py tests/contract/test_ai_assistant_session_lifecycle_api.py tests/contract/test_ai_assistant_customer_bridge_api.py`

Failure:
`INDEX command denied to user 'hify'@'192.168.97.1' for table 'ai_assistant_session'`

The same gates pass when the test helper is run as designed with a MySQL8
admin URL that creates the disposable database and grants privileges to the
application user. The implementation was not switched to SQLite/PostgreSQL and
did not use an in-memory repository fallback for the MySQL8 gate.
