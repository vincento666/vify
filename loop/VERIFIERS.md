# Loop Verifiers: Spec 188.5

## RED / Focused Integration

    rtk uv run pytest tests/integration/ai_assistant/test_memory_scope_persistence.py -q

## Contract And E2E

    rtk uv run pytest tests/contract/test_ai_assistant_memory_scope_api.py tests/contract/test_ai_assistant_memory_context_api.py -q
    rtk uv run pytest tests/e2e/test_ai_assistant_memory_context_e2e.py -q

## Regression

    rtk uv run pytest tests/unit/ai_assistant/test_markdown_memory_store.py tests/unit/ai_assistant/test_memory_context.py -q
    rtk uv run pytest tests/integration/ai_assistant/test_harness_repository.py -q

## Static And Migration

    rtk uv run ruff check app/modules/ai_assistant app/modules/chat/domain/llm_request.py tests/unit/ai_assistant tests/integration/ai_assistant/test_memory_scope_persistence.py tests/contract/test_ai_assistant_memory_scope_api.py tests/contract/test_ai_assistant_memory_context_api.py tests/e2e/test_ai_assistant_memory_context_e2e.py alembic/versions/0032_ai_assistant_memory_scope.py
    rtk uv run mypy app/modules/ai_assistant
    rtk git diff --check

## Gate Applicability

- Unit: required.
- MySQL8 Integration/Contract: required.
- Backend E2E/API: required.
- Migration: required.
- Browser UAT/rem/frontend: N/A; no frontend visual change.
- Live LLM: N/A; deterministic fake/local paths prove cutover.
- `app/modules/chat/domain/llm_request.py` is a typing-only static-gate
  dependency: parent 317fad92 exposed four imported errors there; this slice
  narrows dict values without runtime behavior change so full mypy can pass.

## Checker

Verify:

- TDD method and RED evidence;
- all session/run/API access is user/workspace scoped;
- workspace ID comes from trusted server root;
- rolling 30-day MEMORY.md enters prompt/inspector only for own scope;
- no legacy aiAssistantMemory write or canonical prompt read remains;
- public compatibility projection is file-derived;
- migration and MySQL8 evidence pass.

## Reviewer

Audit:

- scope filters cannot be omitted by request/background paths;
- migration backfill is explicit and safe;
- no raw workspace path is accepted;
- DB stores no memory text;
- resolver lifecycle follow-up from 188.4 is handled;
- no extractor/token-cost/frontend/customer-assistant scope drift.
