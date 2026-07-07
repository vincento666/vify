# Loop Verifiers

These commands verify Spec 222 slice `222.13`.

## RED

```bash
/opt/homebrew/bin/rtk uv run pytest tests/unit/ai_assistant/test_tool_self_correction.py -q
/opt/homebrew/bin/rtk uv run pytest tests/contract/test_ai_assistant_tool_self_correction_api.py -q
/opt/homebrew/bin/rtk uv run pytest tests/e2e/test_ai_assistant_tool_self_correction_e2e.py -q
```

## Focused Backend

```bash
/opt/homebrew/bin/rtk uv run pytest tests/unit/ai_assistant/test_tool_runtime.py tests/unit/ai_assistant/test_tool_self_correction.py -q
/opt/homebrew/bin/rtk uv run pytest tests/contract/test_ai_assistant_tool_runtime_api.py tests/contract/test_ai_assistant_tool_self_correction_api.py tests/contract/test_ai_assistant_trace_audit_api.py -q
/opt/homebrew/bin/rtk uv run pytest tests/e2e/test_ai_assistant_tool_runtime_e2e.py tests/e2e/test_ai_assistant_tool_self_correction_e2e.py tests/e2e/test_ai_assistant_trace_audit_e2e.py -q
```

## Frontend And Browser UAT

```bash
/opt/homebrew/bin/rtk npm --prefix frontend run test:unit -- src/api/aiAssistant.test.ts src/views/aiAssistant/aiAssistantShell.test.ts
/opt/homebrew/bin/rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts
```

Browser UAT uses the in-app browser at `/ai-assistant` and records:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/browser-uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/screenshots/
```

## Static And Diff

```bash
/opt/homebrew/bin/rtk uv run ruff check app/modules/ai_assistant tests/unit/ai_assistant tests/contract/test_ai_assistant_tool_self_correction_api.py tests/e2e/test_ai_assistant_tool_self_correction_e2e.py
/opt/homebrew/bin/rtk uv run python -m compileall app/modules/ai_assistant tests/unit/ai_assistant tests/contract tests/e2e
/opt/homebrew/bin/rtk git diff --check
```

## Checker And Reviewer

Checker must verify:

```text
RED evidence exists for timeout, 5xx, rate-limit, and budget exhaustion.
Recoverable observation re-enters orchestration and completes after repair or fallback.
Unrecoverable permission/sandbox/approval/budget failures remain structured terminal failures.
Trace/audit export includes repair attempts, plan/task updates, tool events, and budget usage.
Browser UAT shows failed tool -> repair/replan -> final result or structured terminal failure.
```

Reviewer must verify diff scope, no weakened tests/gates, no secrets, and no
claim of `222.14` completion.
