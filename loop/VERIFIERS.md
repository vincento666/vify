# Loop Verifiers: Spec 188.4

## RED / Focused Unit

    rtk uv run pytest tests/unit/ai_assistant/test_markdown_memory_store.py -q

Expected first RED:

    ModuleNotFoundError: app.modules.ai_assistant.domain.markdown_memory

## Regression

    rtk uv run pytest tests/unit/ai_assistant/test_memory_context.py tests/unit/ai_assistant/test_file_workspace.py -q

## Static

    rtk uv run ruff check app/modules/ai_assistant/domain/markdown_memory.py tests/unit/ai_assistant/test_markdown_memory_store.py
    rtk uv run mypy app/modules/ai_assistant/domain/markdown_memory.py
    rtk git diff --check

## Gate Applicability

- Unit: required.
- Security/path/concurrency: required in focused unit suite.
- MySQL8 Integration/Contract: N/A; 188.4 stores no DB state.
- Backend E2E/API: N/A; harness/session integration starts at 188.5.
- Browser UAT/rem/frontend: N/A; no user-visible frontend change.
- Live LLM: N/A; extractor starts at 188.6.

## Checker

Verify:

- TDD method and observable RED evidence;
- strict scoped path cannot escape configured memory root;
- rolling reader uses heading-derived byte/line boundary, not fixed tail-N;
- future/malformed dates do not enter prompt content;
- concurrent writes remain valid and today's full block is at most 100 tokens;
- focused/regression/static checks and evidence pass.

## Reviewer

Audit:

- diff stays inside frozen scope;
- public interface stays small;
- no arbitrary caller path;
- no second memory content store;
- atomic replacement and lock cleanup are safe;
- cap/dedup behavior is deterministic and testable;
- no harness/schema/API/frontend/customer-assistant scope drift.
