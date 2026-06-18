# 193.5 Final Gate Evidence

Date: 2026-06-18

## Backend

- Unit:
  `rtk uv run pytest tests/unit/ai_assistant -q`
  Result: 16 passed.
- Integration, MySQL8:
  `rtk env HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL=<redacted> uv run pytest tests/integration/ai_assistant -q`
  Result: 3 passed.
- Contract, MySQL8:
  `rtk env HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL=<redacted> uv run pytest tests/contract/test_ai_assistant_*.py -q`
  Result: 16 passed.
- E2E, MySQL8:
  `rtk env HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL=<redacted> uv run pytest tests/e2e/test_ai_assistant_kernel_e2e.py tests/e2e/test_ai_assistant_security_e2e.py -q`
  Result: 2 passed.
- Real OpenRouter Qwen smoke:
  `rtk env OPENROUTER_API_KEY=<redacted> uv run pytest tests/e2e/test_ai_assistant_live_qwen_openrouter_e2e.py -q`
  Result: 1 passed.

## Frontend

- Focused AI Assistant + rem:
  `rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/aiAssistantShell.test.ts src/views/aiAssistant/aiAssistantTimeline.test.ts src/api/aiAssistant.test.ts src/remScaleClosure.test.ts`
  Result: 4 files passed, 18 tests passed.
- Full unit:
  `rtk npm --prefix frontend run test:unit`
  Result: 95 files passed, 388 tests passed.
- Production build:
  `rtk npm --prefix frontend run build`
  Result: passed.

## Browser UAT

- Complex journey:
  Result: passed.
- Final assertions:
  one-screen shell, model config, no old echo copy, model stream, tool echo,
  approval, completion, usage units, and real task panel content all passed.
- Expanded details:
  14 detail panels, 32 detail rows, 4 input anchors, 4 output anchors,
  `调用详情` / `输入` / `输出` present, old copy absent.
