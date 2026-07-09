# Loop Verifiers

These commands verify Spec 222 slice `222.14.1`.

## RED

```bash
/opt/homebrew/bin/rtk uv run pytest tests/integration/ai_assistant/test_harness_repository.py -q
```

Expected RED before implementation:

```text
Concurrent event append raises duplicate run/sequence or fails to produce 1..N.
```

## Focused Gates

```bash
/opt/homebrew/bin/rtk uv run pytest tests/integration/ai_assistant/test_harness_repository.py -q
/opt/homebrew/bin/rtk uv run pytest tests/contract/test_ai_assistant_event_sequence_api.py tests/contract/test_ai_assistant_streaming_api.py tests/contract/test_ai_assistant_session_runtime_api.py -q
/opt/homebrew/bin/rtk uv run pytest tests/e2e/test_ai_assistant_session_runtime_e2e.py tests/e2e/test_ai_assistant_streaming_e2e.py -q
```

## Static And Diff

```bash
/opt/homebrew/bin/rtk uv run ruff check app/modules/ai_assistant/infra/repository.py tests/integration/ai_assistant/test_harness_repository.py tests/contract/test_ai_assistant_event_sequence_api.py
/opt/homebrew/bin/rtk uv run python -m compileall app/modules/ai_assistant/infra/repository.py tests/integration/ai_assistant/test_harness_repository.py tests/contract/test_ai_assistant_event_sequence_api.py
/opt/homebrew/bin/rtk git diff --check
```

## Checker And Reviewer

Checker must verify:

```text
RED proves concurrent append was unsafe before implementation.
Integration proves same-run concurrent append stores exactly 1..N.
API contract proves afterSequence replay is ordered and gapless after concurrent append.
Existing snapshot/SSE resume gates still pass.
No schema migration or cross-module event system change was introduced.
```

Reviewer must verify:

```text
Diff scope is limited to AI Assistant repository, tests, spec/loop updates.
The fix uses existing schema constraints or run-level locking, not a new migration.
No tests or gates are weakened.
No secrets or production behavior are introduced.
```
