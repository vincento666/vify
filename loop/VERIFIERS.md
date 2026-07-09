# Loop Verifiers

These commands verify Spec 222 slice `222.14.3`.

## RED

```bash
/opt/homebrew/bin/rtk uv run pytest tests/contract/test_ai_assistant_session_runtime_api.py::AiAssistantSessionRuntimeApiContractTest::test_async_message_autonomously_runs_without_worker_process_api -q
```

Expected RED before implementation:

```text
messages/async leaves the run QUEUED without backend autonomous worker consumption.
```

## Focused Gates

```bash
/opt/homebrew/bin/rtk uv run pytest tests/contract/test_ai_assistant_session_runtime_api.py -q
/opt/homebrew/bin/rtk uv run pytest tests/e2e/test_ai_assistant_session_runtime_e2e.py tests/e2e/test_ai_assistant_streaming_e2e.py tests/e2e/test_ai_assistant_memory_context_e2e.py -q
```

## Static And Diff

```bash
/opt/homebrew/bin/rtk uv run ruff check app/modules/ai_assistant/web/router.py tests/contract/test_ai_assistant_session_runtime_api.py tests/e2e/test_ai_assistant_session_runtime_e2e.py tests/e2e/test_ai_assistant_streaming_e2e.py
/opt/homebrew/bin/rtk uv run python -m py_compile app/modules/ai_assistant/web/router.py tests/contract/test_ai_assistant_session_runtime_api.py tests/e2e/test_ai_assistant_session_runtime_e2e.py tests/e2e/test_ai_assistant_streaming_e2e.py
/opt/homebrew/bin/rtk git diff --check
```

## Checker And Reviewer

Checker must verify:

```text
RED proves messages/async alone previously did not close the backend loop.
Contract proves messages/async reaches terminal without worker/process.
Duplicate worker/process call does not double-execute the run.
SSE stream tests still pass and do not start execution.
No broker, dependency, schema migration, or standalone worker service was introduced.
```

Reviewer must verify:

```text
Diff scope is limited to AI Assistant router, session-runtime tests, spec/loop updates.
The worker trigger is module-local, in-process, and guarded by runId in-flight de-dupe plus existing claim.
No tests or gates are weakened.
No secrets or production behavior are introduced.
```
