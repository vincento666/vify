# 184.1 Phase 0 Minimal Harness Kernel

## Modification Scope

- Added `app/modules/ai_assistant/` backend module.
- Added MySQL8 SQLAlchemy tables for session, run, message, event, and tool
  call persistence.
- Registered AI Assistant tables in `app/core/schema.py`.
- Registered `/api/v1/ai-assistant` router in `app/main.py`.
- Added unit, integration, contract, and E2E tests for Phase 0.
- Removed an obsolete `type: ignore` in `app/core/db_write.py` that blocked the
  focused mypy gate.

## RED Evidence

- `red.txt`: focused RED failed with 5 expected failures because
  `app.modules.ai_assistant` did not exist.
- `red-prompt.txt`: Prompt Assembler RED failed because
  `app.modules.ai_assistant.domain.prompt` did not exist.

Command:

```text
rtk uv run pytest tests/unit/ai_assistant/test_tool_registry.py tests/integration/ai_assistant/test_harness_repository.py tests/contract/test_ai_assistant_kernel_api.py tests/e2e/test_ai_assistant_kernel_e2e.py -q
```

## Implementation Summary

- Implemented read-only `ToolRegistry` with deterministic `echo_context`.
- Implemented minimal `PromptAssembler` with base, tools, run state, and user
  message layers.
- Implemented `AiAssistantRepository` for MySQL8-backed session, run, message,
  event, and tool-call persistence.
- Implemented monotonically increasing event sequence per run.
- Implemented a deterministic one-turn harness loop:
  `reason -> validate -> act -> observe -> final`.
- Implemented Phase 0 API endpoints for sessions, messages, runs, events,
  results, and tool manifests.
- Preserved `{code, message, data}` response envelope.
- Kept Phase 0 read-only except internal harness persistence.

## Gates Run

- `unit.txt`: `2 passed`
- `integration.txt`: `2 passed`
- `contract.txt`: `1 passed, 1 warning`
- `e2e.txt`: `1 passed, 1 warning`
- `focused.txt`: `6 passed, 1 warning`
- `lint.txt`: `All checks passed`
- `mypy.txt`: `Success: no issues found in 10 source files`
- `mysql8-boundary.txt`: `2 passed`

MySQL8 test database:

```text
HIFY_MYSQL8_TEST_DATABASE_URL=mysql+pymysql://hify:hify@127.0.0.1:3316/hify?charset=utf8mb4
HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL=mysql+pymysql://root:root@127.0.0.1:3316/mysql?charset=utf8mb4
```

## Remaining Risk

- Phase 0 has no frontend, so browser UAT and remScaleClosure are not
  applicable yet.
- Contract/E2E warnings come from Starlette TestClient deprecation in existing
  dependency stack.
- Phase 1 must add sandbox, approval, proposed-action, and audit semantics
  before any protected write-like tool exists.
